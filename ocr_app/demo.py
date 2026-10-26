"""Small fictional dataset processed by exactly the same pipeline as uploaded files."""
import io
import random
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageFont

from .processing import file_record


def create_demo(directory: Path):
    image = Image.new('RGB', (480, 300), '#eef5f2')
    draw = ImageDraw.Draw(image)
    rng = random.Random(26)
    draw.rounded_rectangle((12, 12, 468, 288), radius=24, outline='#126f65', width=6)
    for _ in range(55):
        x, y = rng.randrange(30, 440), rng.randrange(30, 250)
        draw.ellipse((x, y, x + 15, y + 15), fill=tuple(rng.randrange(40, 150) for _ in range(3)))
    draw.rectangle((55, 112, 425, 195), fill='#ffffff')
    font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 40) if Path('C:/Windows/Fonts/arialbd.ttf').exists() else ImageFont.load_default(size=40)
    draw.text((88, 125), 'ALBA DEMO', fill='#126f65', font=font)
    reference = directory / 'reference.png'
    image.save(reference)
    logo = reference.read_bytes()
    rng = random.Random(320)
    other = Image.frombytes('RGB', (480, 300), rng.randbytes(480 * 300 * 3))
    stream = io.BytesIO()
    other.save(stream, format='PNG')
    records = []
    for group, name, embedded in [('Distribuidor Alba', 'convenio.pdf', logo),
                                  ('Distribuidor Brisa', 'acuerdo.pdf', stream.getvalue()),
                                  ('Distribuidor Cauce', 'anexo.pdf', None)]:
        relative = f'{group}/{name}'
        path = directory / 'input' / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with pymupdf.open() as document:
            page = document.new_page()
            page.insert_text((48, 58), 'PROYECTO OCR - DOCUMENTO FICTICIO', fontsize=18)
            page.insert_text((48, 90), group + ' / Demostracion local', fontsize=12)
            page.insert_text((48, 125), 'Este archivo no contiene informacion empresarial real.', fontsize=11)
            if embedded:
                page.insert_image(pymupdf.Rect(60, 165, 540, 465), stream=embedded)
            else:
                page.insert_text((48, 170), 'Documento de texto sin imagenes incrustadas.', fontsize=12)
            document.save(path)
        records.append(file_record(path, directory, relative, group))
    return records, 'reference.png'
