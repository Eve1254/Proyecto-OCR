import os
from openpyxl import Workbook

def generar_reporte_excel(directorio, archivo_salida):
    """
    Genera un reporte en Excel con los nombres de las carpetas existentes y el número de archivos en cada una.

    :param directorio: Ruta del directorio a analizar.
    :param archivo_salida: Nombre del archivo de Excel de salida.
    """
    if not os.path.isdir(directorio):
        print(f"Error: La ruta proporcionada no es válida: {directorio}")
        return

    # Crear un archivo Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte de Carpetas"

    # Agregar encabezados
    ws.append(["Carpeta", "Validación de Convenio"])  # Encabezados de las columnas

    # Recorrer todas las carpetas y subcarpetas
    for root, dirs, _ in os.walk(directorio):
        for carpeta in dirs:
            # Obtener solo el nombre de la carpeta (sin la ruta completa)
            nombre_carpeta = os.path.basename(carpeta)
            # Contar el número de archivos en la carpeta
            ruta_carpeta = os.path.join(root, carpeta)
            num_archivos = len(os.listdir(ruta_carpeta))
            # Agregar la información al Excel
            ws.append([nombre_carpeta, num_archivos])

    # Guardar el archivo Excel
    try:
        wb.save(archivo_salida)
        print(f"Reporte generado correctamente: {archivo_salida}")
    except PermissionError:
        print(f"Error: No se pudo guardar el archivo. Verifica que no esté abierto: {archivo_salida}")
    except Exception as e:
        print(f"Error inesperado al guardar el archivo: {e}")


ruta_directorio = input("Introduce la ruta del directorio a analizar: ")
archivo_resultados = input("Introduce el nombre del archivo de salida (ej.: reporte.xlsx): ")


generar_reporte_excel(ruta_directorio, archivo_resultados)
