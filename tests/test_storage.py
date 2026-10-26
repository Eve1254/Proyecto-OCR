from pathlib import Path

import pytest

from ocr_app.storage import JobStore, safe_relative, unique_path


@pytest.mark.parametrize('name', ['../a.pdf', 'C:/a.pdf', '/a.pdf', '//server/a.pdf',
    'x/CON.pdf', 'a:stream.pdf', 'a./b.pdf', 'a /b.pdf', 'x/../b.pdf', 'x\\b.pdf', '', 'a\x00.pdf'])
def test_rejects_unsafe_upload_names(name):
    with pytest.raises(ValueError):
        safe_relative(name)


def test_preserves_relative_unicode_path():
    assert safe_relative('Álvaro/Convenio/a.pdf').as_posix() == 'Álvaro/Convenio/a.pdf'


def test_collision_does_not_overwrite(tmp_path):
    original = tmp_path / 'Informe.pdf'
    original.write_bytes(b'original')
    other = unique_path(tmp_path, Path('informe.pdf'))
    other.write_bytes(b'new')
    assert other != original
    assert original.read_bytes() == b'original'
    assert other.read_bytes() == b'new'


def test_jobs_persist_and_interrupted_jobs_are_identified(tmp_path):
    store = JobStore(tmp_path)
    job = store.create({'recognize': False})
    job['status'] = 'running'
    store.save(job)
    reopened = JobStore(tmp_path)
    assert reopened.get(job['id'])['status'] == 'interrupted'
    assert reopened.get(job['id'])['options']['recognize'] is False
    assert len(reopened.list()) == 1


def test_deletion_is_limited_to_job_directory(tmp_path):
    store = JobStore(tmp_path / 'jobs')
    outside = tmp_path / 'keep.pdf'
    outside.write_bytes(b'keep')
    job = store.create({})
    with pytest.raises(ValueError):
        store.delete('../keep.pdf')
    store.delete(job['id'])
    assert not store.directory(job['id']).exists()
    assert outside.read_bytes() == b'keep'
