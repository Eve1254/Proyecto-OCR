import fitz  # PyMuPDF
import os
from PIL import Image
import io
import cv2  # OpenCV para comparación
import numpy as np
import imageio.v3 as iio
import shutil

def comparacionDetallada(image):
    """mejora la comparación si la imágen tiene otro color o si está borrosa."""
    # Convierte a escala de grises
    EscalaGrises = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2GRAY)
    # Normaliza la intensidad
    NormalizadorImagen = cv2.equalizeHist(EscalaGrises)
    return NormalizadorImagen

def ComparacionInicial(image1, image2):
    # Preprocesa las imágenes
    image1 = comparacionDetallada(image1)
    image2 = comparacionDetallada(image2)

    # Inicializa el detector SIFT
    sift = cv2.SIFT_create()

    # Detecta y calcula los puntos clave y descriptores
    keypoints1, descriptors1 = sift.detectAndCompute(image1, None)
    keypoints2, descriptors2 = sift.detectAndCompute(image2, None)

    # Verifica si se encontraron descriptores suficientes
    if descriptors1 is None or descriptors2 is None or len(descriptors1) < 2 or len(descriptors2) < 2:
        return False

    # Coincidencia de descriptores usando el método FLANN
    index_params = dict(algorithm=1, trees=5)
    search_params = dict(checks=50)
    flann = cv2.FlannBasedMatcher(index_params, search_params)

    try:
        matches = flann.knnMatch(descriptors1, descriptors2, k=2)
    except cv2.error as e:
        print(f"Error en la comparación de imágenes: {e}")
        return False

    # Filtra buenas coincidencias usando la razón de Lowe
    good_matches = [m for m, n in matches if m.distance < 0.7 * n.distance]

    # Si hay suficientes coincidencias, consideramos que las imágenes son similares
    return len(good_matches) > 10

def delete_empty_folders(folder_path):
    """Elimina recursivamente las carpetas vacías."""
    for root, dirs, files in os.walk(folder_path, topdown=False):
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            if not os.listdir(dir_path):
                try:
                    os.rmdir(dir_path)
                    print(f"Carpeta eliminada: {dir_path}")
                except OSError as e:
                    print(f"Error al eliminar carpeta {dir_path}: {e}")


def extract_logo_from_pdfs(directory_path, reference_image_path):
    # Verifica si la ruta existe
    if not os.path.isdir(directory_path):
        print(f"La ruta {directory_path} no existe.")
        return

    if not os.path.isfile(reference_image_path):
        print(f"La imagen de referencia {reference_image_path} no existe.")
        return

    # Carga la imagen de referencia
    reference_image = Image.open(reference_image_path)

    # Recorre todos los subdirectorios
    for root, _, files in os.walk(directory_path):
        output_dir = os.path.join(root, "archivos_encontrados")

        # Omite carpetas que ya tienen resultados
        if os.path.exists(output_dir) and os.listdir(output_dir):
            print(f"Omitiendo carpeta: {root} (archivos_encontrados no está vacío)")
            continue

        os.makedirs(output_dir, exist_ok=True)

        logo_saved = False

        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_path = os.path.join(root, file)
                print(f"Procesando: {pdf_path}")

                try:
                    # Abre el archivo PDF
                    pdf_document = fitz.open(pdf_path)
                except Exception as e:
                    print(f"No se pudo abrir el archivo {pdf_path}. Error: {e}")
                    continue

                for page_num in range(len(pdf_document)):
                    page = pdf_document[page_num]

                    # Extrae imágenes de la página
                    images = page.get_images(full=True)

                    for img_index, img in enumerate(images):
                        xref = img[0]
                        base_image = pdf_document.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"].lower()

                        # Filtra formatos no soportados
                        if image_ext not in ["jpeg", "jpg", "png"]:
                            print(f"Formato de imagen no soportado: {image_ext}")
                            continue

                        try:
                            # Usa imageio para leer la imagen
                            image_array = iio.imread(io.BytesIO(image_bytes))
                            image = Image.fromarray(image_array)
                        except Exception as e:
                            print(f"Error al leer la imagen: {e}")
                            continue

                        # Compara la imagen extraída con la de referencia usando SIFT
                        if ComparacionInicial(reference_image, image):
                            logo_saved = True

                            # Asegúrate de que la imagen esté en formato RGB
                            if image.mode == "RGBA":
                                image = image.convert("RGB")

                            # Guarda el logotipo como archivo de imagen
                            output_path = os.path.join(output_dir, f"logo_{os.path.splitext(file)[0]}_page{page_num + 1}_img{img_index + 1}.{image_ext}")
                            image.save(output_path)
                            print(f"Logotipo guardado en: {output_path}")

                pdf_document.close()

        # Elimina la carpeta si está vacía o solo contiene subcarpetas vacías
        if not logo_saved:
            print(f"No se encontraron logotipos en {root}. Verificando para eliminar archivos_encontrados.")
            delete_empty_folders(output_dir)

# Ejemplo de uso
directory_path = "C:/Users/cohevmu/Essity/GRP-GOPS-Información Sell-Out COSMOS - Documentos/COSMOS 2.0/4. Informacion Juridica"
reference_image_path = "C:/Users/cohevmu/Essity/GRP-GOPS-Información Sell-Out COSMOS - Documentos/COSMOS 2.0/4. Informacion Juridica/Referencia reconocimiento/ref.png"
extract_logo_from_pdfs(directory_path, reference_image_path)

