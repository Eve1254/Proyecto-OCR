import os
import subprocess
import sys
import zipfile

import pymupdf
import pytest

from ocr_app.word_worker import convert_docx


def make_docx(path):
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        archive.writestr('_rels/.rels', '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        archive.writestr('word/document.xml', '<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Documento ficticio Proyecto OCR</w:t></w:r></w:p><w:sectPr/></w:body></w:document>')


@pytest.mark.skipif(os.name != 'nt', reason='Windows only')
def test_word_timeout_does_not_hang(tmp_path, monkeypatch):
    import ocr_app.word_worker as word
    original = subprocess.Popen
    def sleeping_process(command, **kwargs):
        return original([sys.executable, '-c', 'import time; time.sleep(15)'], **kwargs)
    monkeypatch.setattr(word.subprocess, 'Popen', sleeping_process)
    with pytest.raises(RuntimeError, match='tiempo máximo'):
        convert_docx(tmp_path / 'test.docx', tmp_path / 'out.pdf', timeout=.2)


@pytest.mark.skipif(os.environ.get('OCR_TEST_WORD') != '1', reason='Enable OCR_TEST_WORD=1 for real local Microsoft Word integration')
def test_real_word_converts_a_fictional_document(tmp_path):
    source = tmp_path / 'Documento de prueba.docx'
    output = tmp_path / 'resultado.pdf'
    make_docx(source)
    original = source.read_bytes()
    convert_docx(source, output)
    with pymupdf.open(output) as document:
        assert len(document) == 1
        assert 'Proyecto OCR' in document[0].get_text()
    assert source.read_bytes() == original
