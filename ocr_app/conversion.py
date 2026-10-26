"""Document conversion for local Word and isolated Linux LibreOffice workers."""
import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from .word_worker import convert_docx


def converter_available(backend):
    return bool(shutil.which('libreoffice') or shutil.which('soffice')) if backend == 'libreoffice' else os.name == 'nt'


def validate_docx(source: Path):
    with zipfile.ZipFile(source) as archive:
        entries = archive.infolist()
        if len(entries) > 1500 or sum(e.file_size for e in entries) > 60 * 1024**2:
            raise ValueError('El documento comprimido supera el límite de expansión del piloto.')
        for entry in entries:
            name = entry.filename.lower()
            if entry.flag_bits & 1 or entry.file_size > 10 * 1024**2 or entry.file_size > max(1, entry.compress_size) * 100:
                raise ValueError('Documento comprimido no compatible o con expansión excesiva.')
            if 'vbaproject' in name or name.startswith('word/embeddings/'):
                raise ValueError('El piloto no admite macros ni objetos incrustados en Word.')
            if name.endswith(('.rels', '.xml')):
                data = archive.read(entry)
                if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
                    raise ValueError('XML no compatible dentro del documento.')
                root = ET.fromstring(data)
                for node in root.iter():
                    attributes = {key.rsplit('}', 1)[-1]: value for key, value in node.attrib.items()}
                    if attributes.get('TargetMode', '').strip().casefold() == 'external':
                        raise ValueError('El piloto no convierte documentos con vínculos externos. Elimínalos o carga un PDF.')
                    instruction = (node.text or '') if node.tag.rsplit('}', 1)[-1] == 'instrText' else attributes.get('instr', '')
                    if re.search(r'\b(DDEAUTO|DDE|INCLUDETEXT|INCLUDEPICTURE|LINK|DATABASE)\b', instruction, re.I):
                        raise ValueError('El documento contiene un campo con contenido externo no permitido.')
        if 'word/document.xml' not in archive.namelist():
            raise ValueError('El archivo no contiene un documento Word compatible.')


def terminate_tree(process):
    """Only terminate this worker's process and its descendants."""
    import psutil
    try:
        parent = psutil.Process(process.pid)
        children = parent.children(recursive=True)
    except psutil.Error:
        children = []
    for child in reversed(children):
        try:
            child.kill()
        except psutil.Error:
            pass
    try:
        process.kill()
    except OSError:
        pass
    process.wait(timeout=10)


def convert_document(source: Path, destination: Path, backend='word', timeout=90):
    if backend == 'word':
        return convert_docx(source, destination, timeout=timeout)
    validate_docx(source)
    executable = shutil.which('libreoffice') or shutil.which('soffice')
    if not executable:
        raise RuntimeError('La conversión no está disponible en este servidor. Carga el archivo en PDF.')
    with tempfile.TemporaryDirectory(prefix='convert-', dir=destination.parent) as temporary:
        root = Path(temporary)
        profile = root / 'profile'
        (profile / 'user').mkdir(parents=True)
        (profile / 'user/registrymodifications.xcu').write_text(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<oor:items xmlns:oor="http://openoffice.org/2001/registry">'
            '<item oor:path="/org.openoffice.Office.Common/Security/Scripting">'
            '<prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop>'
            '<prop oor:name="DisableMacrosExecution" oor:op="fuse"><value>true</value></prop></item>'
            '<item oor:path="/org.openoffice.Office.Writer/Content/Update">'
            '<prop oor:name="Link" oor:op="fuse"><value>0</value></prop></item></oor:items>', encoding='utf-8')
        command = [executable, '-env:UserInstallation=' + profile.as_uri(), '--headless', '--nologo',
                   '--nodefault', '--norestore', '--nofirststartwizard', '--convert-to', 'pdf:writer_pdf_Export',
                   '--outdir', str(root), str(source.resolve())]
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            terminate_tree(process)
            raise RuntimeError('La conversión excedió el tiempo máximo. Prueba con un PDF.')
        output = root / (source.stem + '.pdf')
        if process.returncode or not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError('No se pudo convertir el documento. Comprueba el archivo o carga un PDF.')
        output.replace(destination)
