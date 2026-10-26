"""Logo matching of embedded raster images; not text OCR or signature validation."""
import io
from pathlib import Path

import cv2
import numpy as np
import pymupdf
from PIL import Image, ImageOps

from .config import LIMITS


def descriptors(data: bytes, limits=LIMITS):
    with Image.open(io.BytesIO(data)) as image:
        if image.width * image.height > limits.image_pixels:
            raise ValueError('La imagen supera el límite de píxeles para esta versión.')
        image = ImageOps.exif_transpose(image).convert('RGB')
        image.thumbnail((1800, 1800))
        gray = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2GRAY)
    return cv2.SIFT_create(nfeatures=3500).detectAndCompute(cv2.equalizeHist(gray), None)[1]


def load_reference(path: Path, limits=LIMITS):
    try:
        features = descriptors(path.read_bytes(), limits)
    except Exception as error:
        raise ValueError('No se pudo leer la referencia como imagen PNG/JPEG.') from error
    if features is None or len(features) < 12:
        raise ValueError('El logotipo tiene pocos detalles. Usa una imagen nítida y de mayor tamaño.')
    return features


def inspect_pdf(path: Path, reference, evidence_dir: Path, limits=LIMITS) -> dict:
    result = dict(state='review', matches=[], images=0, message='')
    failures = []
    try:
        with pymupdf.open(path) as document:
            if document.needs_pass:
                raise ValueError('PDF protegido con contraseña.')
            if len(document) > limits.pages:
                raise ValueError(f'Este piloto admite hasta {limits.pages} páginas por PDF.')
            for page_number, page in enumerate(document, start=1):
                for image_number, image_info in enumerate(page.get_images(full=True), start=1):
                    if result['images'] >= limits.images:
                        raise ValueError('El PDF contiene demasiadas imágenes para este piloto.')
                    try:
                        if image_info[2] * image_info[3] > limits.image_pixels:
                            raise ValueError('La imagen incrustada supera el límite de píxeles.')
                        extracted = document.extract_image(image_info[0])
                        data = extracted['image']
                        if len(data) > limits.file_bytes:
                            raise ValueError('Imagen incrustada demasiado grande.')
                        features = descriptors(data, limits)
                        result['images'] += 1
                        if features is None or len(features) < 12:
                            failures.append(f'Página {page_number}, imagen {image_number}: sin detalles suficientes para comparar.')
                            continue
                        matcher = cv2.FlannBasedMatcher(dict(algorithm=1, trees=5), dict(checks=50))
                        pairs = matcher.knnMatch(reference, features, k=2)
                        good = sum(1 for pair in pairs if len(pair) == 2 and pair[0].distance < .7 * pair[1].distance)
                        if good > 10:
                            evidence_dir.mkdir(parents=True, exist_ok=True)
                            filename = f'pagina-{page_number}-imagen-{image_number}.png'
                            with Image.open(io.BytesIO(data)) as preview:
                                preview.thumbnail((1200, 1200))
                                preview.convert('RGB').save(evidence_dir / filename)
                            result['matches'].append(dict(page=page_number, image=filename, features=good))
                    except Exception as error:
                        failures.append(f'Página {page_number}, imagen {image_number}: {error}')
        if failures:
            result['message'] = 'Evaluación incompleta. ' + '; '.join(failures[:3])
        elif not result['images']:
            result['message'] = 'No hay imágenes incrustadas utilizables; requiere revisión manual.'
        else:
            result['state'] = 'match' if result['matches'] else 'no_match'
            result['message'] = 'Coincidencia encontrada.' if result['matches'] else 'Sin coincidencia en las imágenes evaluadas.'
    except Exception as error:
        result['message'] = str(error) or 'No se pudo leer el PDF.'
    return result
