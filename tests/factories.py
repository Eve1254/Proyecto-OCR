import io
import random
import struct
import uuid

import pymupdf
from PIL import Image, ImageDraw


def picture(seed=17):
    image = Image.new('RGB', (420, 260), 'white')
    draw = ImageDraw.Draw(image)
    rng = random.Random(seed)
    if seed != 17:
        # An unrelated raster, without the identical text in the reference fixture.
        image = Image.frombytes('RGB', (420, 260), rng.randbytes(420 * 260 * 3))
        out = io.BytesIO()
        image.save(out, format='PNG')
        return out.getvalue()
    for _ in range(65):
        x, y = rng.randrange(390), rng.randrange(230)
        draw.rectangle((x, y, x + rng.randrange(8, 30), y + rng.randrange(8, 30)),
                       fill=tuple(rng.randrange(220) for _ in range(3)))
    draw.text((18, 100), 'DOCUMENTO FICTICIO - LOGO DE PRUEBA', fill='black', stroke_width=1)
    out = io.BytesIO()
    image.save(out, format='PNG')
    return out.getvalue()


def pdf(path, image=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((50, 50), 'Documento ficticio para pruebas')
        if image:
            page.insert_image(pymupdf.Rect(50, 90, 470, 350), stream=image)
        document.save(path)
    return path


def entry(path, relative, group='Alba'):
    return dict(id=uuid.uuid4().hex, relative=relative, path='input/' + relative,
                group=group, kind=path.suffix.lower()[1:], size=path.stat().st_size,
                state='pending', message='', matches=[], original=True)


def synthetic_msg(path, attachment_data):
    """Minimal real OLE MSG, containing one fictional PDF attachment."""
    from extract_msg.ole_writer import OleWriter
    writer = OleWriter()
    writer.addEntry('__properties_version1.0', b'\0' * 32 + struct.pack('<IIII', 0x3FFD0003, 6, 1252, 0))
    writer.addEntry('__substg1.0_001A001E', b'IPM.Note\0')
    writer.addEntry('__substg1.0_0037001E', b'Demostracion ficticia Proyecto OCR\0')
    writer.addEntry('__nameid_version1.0', storage=True)
    for name in ('00020102', '00030102', '00040102'):
        writer.addEntry('__nameid_version1.0/__substg1.0_' + name, b'')
    attachment = '__attach_version1.0_#00000000'
    writer.addEntry(attachment, storage=True)
    writer.addEntry(attachment + '/__properties_version1.0', b'\0' * 8 + struct.pack('<IIII', 0x37050003, 6, 1, 0))
    writer.addEntry(attachment + '/__substg1.0_3707001E', b'documento.pdf\0')
    writer.addEntry(attachment + '/__substg1.0_37010102', attachment_data)
    writer.write(str(path))
    return path
