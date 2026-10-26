import shutil
import zipfile

import pymupdf
import pytest

from tests.test_word import make_docx


def test_rejects_external_docx_relations_before_conversion(tmp_path):
    from ocr_app import conversion
    source = tmp_path / 'external.docx'
    make_docx(source)
    with zipfile.ZipFile(source, 'a') as archive:
        archive.writestr('word/_rels/document.xml.rels', '<Relationships><Relationship TargetMode="External" Target="http://127.0.0.1/private"/></Relationships>')
    with pytest.raises(ValueError, match='extern'):
        conversion.validate_docx(source)


def test_rejects_zip_bomb_before_conversion(tmp_path):
    from ocr_app import conversion
    source = tmp_path / 'compressed.docx'
    with zipfile.ZipFile(source, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('word/document.xml', 'x' * 4_000_000)
    with pytest.raises(ValueError, match='comprim'):
        conversion.validate_docx(source)


def test_docx_validation_preserves_original(tmp_path):
    from ocr_app import conversion
    source = tmp_path / 'example.docx'
    make_docx(source)
    original = source.read_bytes()
    conversion.validate_docx(source)
    assert source.read_bytes() == original


@pytest.mark.skipif(not shutil.which('libreoffice') and not shutil.which('soffice'), reason='Requires LibreOffice')
def test_real_libreoffice_conversion(tmp_path):
    from ocr_app.conversion import convert_document
    source, output = tmp_path / 'example.docx', tmp_path / 'different-name.pdf'
    make_docx(source)
    original = source.read_bytes()
    convert_document(source, output, backend='libreoffice')
    with pymupdf.open(output) as document:
        assert len(document) == 1
        assert 'Proyecto OCR' in document[0].get_text()
    assert source.read_bytes() == original
