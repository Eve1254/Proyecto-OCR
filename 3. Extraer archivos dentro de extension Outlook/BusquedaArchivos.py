import os
import extract_msg as msg
"""
Búsqueda y extracción de archivos dentro de extensiones de outlook
"""


COSMOS1_0 = r"C:/Users/cohevmu/Essity/GRP-GOPS-Información Sell-Out COSMOS - Documentos/COSMOS 1.0/Distribuidores/Republica Dominicana/Extracciones"  # Ruta de entrada
COSMOS2_0 = r"C:/Users/cohevmu/Essity/GRP-GOPS-Información Sell-Out COSMOS - Documentos/COSMOS 2.0/4. Informacion Juridica"  # Ruta de destino

# Validación de exitencia de carpeta COSMOS2.0
os.makedirs(COSMOS2_0, exist_ok=True)

def extraer_y_organizar_adjuntos(origen, destino):
    # Recorre todas las subcarpetas de la ruta de entrada
    for root, dirs, files in os.walk(origen):
        for file in files:
            if file.endswith(".msg"):  # Solo archivos .msg
                archivo_msg = os.path.join(root, file)
                
                # Verifica si la carpeta contiene "Convenio"
                partes_ruta = root.split(os.sep)
                if "Convenio" in partes_ruta:  # Solo procesar si está en "Convenio"
                    # Obtiene la carpeta de destino (la carpeta que está antes de "Convenio")
                    index_convenio = partes_ruta.index("Convenio")
                    carpeta_destino = partes_ruta[index_convenio - 1]
                    
                    # Ruta completa de la carpeta destino dentro de "4. Informacion Juridica"
                    ruta_destino = os.path.join(destino, carpeta_destino)
                    os.makedirs(ruta_destino, exist_ok=True)  # Crea la subcarpeta si no existe
                    
                    try:
                        # Carga el archivo .msg
                        mensaje = msg.Message(archivo_msg)
                        
                        # Procesa los adjuntos del archivo .msg
                        for adjunto in mensaje.attachments:
                            if adjunto.longFilename.endswith(".pdf"):  # Solo PDFs
                                destino_pdf = os.path.join(ruta_destino, adjunto.longFilename)
                                with open(destino_pdf, "wb") as pdf_file:
                                    pdf_file.write(adjunto.data)  # Guarda el PDF
                                print(f"Adjunto extraído: {adjunto.longFilename} en {ruta_destino}")
                    except Exception as e:
                        print(f"Error procesando {archivo_msg}: {e}")


extraer_y_organizar_adjuntos(COSMOS1_0, COSMOS2_0)
print(f"Proceso completado. PDFs organizados en: {COSMOS2_0}")
