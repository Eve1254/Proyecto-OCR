import io
import threading
import zipfile

import openpyxl
import pytest
from PIL import Image

from ocr_app.storage import JobStore
from ocr_app.recognition import inspect_pdf, load_reference
from ocr_app.processing import run_pipeline
from tests.factories import picture, pdf, entry, synthetic_msg


def test_recognition_distinguishes_match_nonmatch_and_unreadable(tmp_path):
    reference = tmp_path / 'reference.png'
    reference.write_bytes(picture())
    descriptors = load_reference(reference)
    good = pdf(tmp_path / 'match.pdf', picture())
    different = pdf(tmp_path / 'different.pdf', picture(46))
    no_image = pdf(tmp_path / 'text.pdf')
    bad = tmp_path / 'bad.pdf'
    bad.write_bytes(b'not pdf')
    result = inspect_pdf(good, descriptors, tmp_path / 'evidence')
    assert result['state'] == 'match'
    assert result['matches'][0]['page'] == 1
    assert (tmp_path / 'evidence' / result['matches'][0]['image']).is_file()
    assert inspect_pdf(different, descriptors, tmp_path / 'different-evidence')['state'] == 'no_match'
    assert inspect_pdf(no_image, descriptors, tmp_path / 'no-evidence')['state'] == 'review'
    assert inspect_pdf(bad, descriptors, tmp_path / 'bad-evidence')['state'] == 'review'


def test_reference_without_features_is_rejected(tmp_path):
    path = tmp_path / 'plain.png'
    Image.new('RGB', (100, 100), 'white').save(path)
    with pytest.raises(ValueError):
        load_reference(path)


def test_featureless_embedded_image_requires_review(tmp_path):
    reference = tmp_path / 'reference.png'
    reference.write_bytes(picture())
    image = io.BytesIO()
    Image.new('RGB', (200, 200), 'white').save(image, format='PNG')
    document = pdf(tmp_path / 'blank-image.pdf', image.getvalue())
    result = inspect_pdf(document, load_reference(reference), tmp_path / 'evidence')
    assert result['state'] == 'review'


def test_incomplete_group_is_not_confidently_classified_and_exports_are_valid(tmp_path):
    store = JobStore(tmp_path / 'jobs')
    job = store.create(dict(convert=False, extract=False, recognize=True, classify=True, report=True, evidence=True))
    directory = store.directory(job['id'])
    reference = directory / 'reference.png'
    reference.write_bytes(picture())
    job['reference'] = 'reference.png'
    matching = pdf(directory / 'input/Alba/match.pdf', picture())
    pending = directory / 'input/Alba/word.docx'
    pending.write_bytes(b'unprocessed')
    formula = pdf(directory / 'input/Brisa/=danger.pdf', picture(46))
    job['files'] = [entry(matching, 'Alba/match.pdf'), entry(pending, 'Alba/word.docx'),
                    entry(formula, 'Brisa/=danger.pdf', '=Brisa')]
    store.save(job)
    before = matching.read_bytes()
    run_pipeline(store, job['id'], threading.Event())
    result = store.get(job['id'])
    groups = {item['name']: item['state'] for item in result['groups']}
    assert groups == {'Alba': 'review', '=Brisa': 'no_match'}
    assert result['status'] == 'completed_with_errors'
    assert matching.read_bytes() == before
    with zipfile.ZipFile(directory / 'output/resultados.zip') as archive:
        assert any(name.endswith('Alba/match.pdf') for name in archive.namelist())
        assert archive.testzip() is None
    workbook = openpyxl.load_workbook(directory / 'output/reporte.xlsx')
    assert workbook.sheetnames == ['Resumen', 'Carpetas', 'Archivos', 'Incidencias']
    cell = next(cell for row in workbook['Carpetas'] for cell in row if cell.value == '=Brisa')
    assert cell.data_type == 's'
    workbook.close()


def test_msg_extracts_pdf_safely_with_repeated_attachment_names(tmp_path, monkeypatch):
    import extract_msg
    source_pdf = pdf(tmp_path / 'source.pdf', picture()).read_bytes()
    class Attachment:
        longFilename = '../../adjunto.pdf'
        shortFilename = None
        data = source_pdf
    class Message:
        attachments = [Attachment(), Attachment()]
        def __init__(self, path): pass
        def close(self): pass
    monkeypatch.setattr(extract_msg, 'Message', Message)
    store = JobStore(tmp_path / 'jobs')
    job = store.create(dict(convert=False, extract=True, recognize=False, classify=False, report=True, evidence=False))
    directory = store.directory(job['id'])
    path = directory / 'input/Alba/Convenio/mensaje.msg'
    path.parent.mkdir(parents=True)
    path.write_bytes(b'msg')
    job['files'] = [entry(path, 'Alba/Convenio/mensaje.msg')]
    store.save(job)
    run_pipeline(store, job['id'], threading.Event())
    result = store.get(job['id'])
    derived = [f for f in result['files'] if not f['original']]
    assert len(derived) == 2
    assert len({f['path'] for f in derived}) == 2
    assert {f['group'] for f in derived} == {'Alba'}
    assert all((directory / f['path']).read_bytes() == source_pdf for f in derived)
    assert all((directory / f['path']).resolve().is_relative_to(directory) for f in derived)


def test_cancel_before_processing_leaves_originals_and_terminal_state(tmp_path):
    store = JobStore(tmp_path)
    job = store.create(dict(recognize=False))
    cancelled = threading.Event()
    cancelled.set()
    run_pipeline(store, job['id'], cancelled)
    assert store.get(job['id'])['status'] == 'cancelled'


def test_bad_msg_attachment_does_not_suppress_later_pdf(tmp_path, monkeypatch):
    import extract_msg
    data = pdf(tmp_path / 'source.pdf', picture()).read_bytes()
    class Bad:
        longFilename = 'bad.pdf'
        shortFilename = None
        data = None
    class Good:
        longFilename = 'good.pdf'
        shortFilename = None
    good = Good()
    good.data = data
    class Message:
        attachments = [Bad(), good]
        def __init__(self, path): pass
        def close(self): pass
    monkeypatch.setattr(extract_msg, 'Message', Message)
    store = JobStore(tmp_path / 'jobs')
    job = store.create(dict(extract=True, recognize=False, classify=False, report=True))
    directory = store.directory(job['id'])
    source = directory / 'input/message.msg'
    source.write_bytes(b'msg')
    job['files'] = [entry(source, 'message.msg')]
    store.save(job)
    run_pipeline(store, job['id'], threading.Event())
    result = store.get(job['id'])
    generated = [file for file in result['files'] if not file['original']]
    assert len(generated) == 1
    assert (directory / generated[0]['path']).read_bytes() == data
    assert result['files'][0]['state'] == 'review'


def test_real_msg_parser_recovers_fictional_pdf_attachment(tmp_path):
    store = JobStore(tmp_path / 'jobs')
    job = store.create(dict(extract=True, recognize=False, classify=False, report=True))
    directory = store.directory(job['id'])
    data = pdf(tmp_path / 'source.pdf', picture()).read_bytes()
    source = synthetic_msg(directory / 'input/demo.msg', data)
    job['files'] = [entry(source, 'demo.msg')]
    store.save(job)
    run_pipeline(store, job['id'], threading.Event())
    result = store.get(job['id'])
    assert result['status'] == 'completed', result['errors']
    generated = [file for file in result['files'] if not file['original']]
    assert len(generated) == 1
    assert (directory / generated[0]['path']).read_bytes() == data
