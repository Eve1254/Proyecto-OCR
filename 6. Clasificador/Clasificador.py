import os
import shutil

def mover_carpetas(ruta_principal, ruta_destino_con_imagenes, ruta_destino_sin_imagenes):
    # Asegurarse de que las carpetas de destino existan
    if not os.path.exists(ruta_destino_con_imagenes):
        os.makedirs(ruta_destino_con_imagenes)
        print(f"Carpeta de destino creada: {ruta_destino_con_imagenes}")
    if not os.path.exists(ruta_destino_sin_imagenes):
        os.makedirs(ruta_destino_sin_imagenes)
        print(f"Carpeta de destino creada: {ruta_destino_sin_imagenes}")
    
    print(f"Escaneando en: {ruta_principal}")
    
    # Recorrer todas las carpetas principales
    for carpeta in os.listdir(ruta_principal):
        ruta_carpeta = os.path.join(ruta_principal, carpeta)
        
        if os.path.isdir(ruta_carpeta):  # Solo procesar directorios
            print(f"Revisando carpeta: {ruta_carpeta}")
            
            # Verificar si existe la subcarpeta "ARCHIVOS ENCONTRADOS"
            ruta_archivos_encontrados = os.path.join(ruta_carpeta, "archivos_encontrados")
            if os.path.exists(ruta_archivos_encontrados):
                print(f"Subcarpeta encontrada: {ruta_archivos_encontrados}")
                
                # Buscar imágenes dentro de la subcarpeta
                hay_imagen = False
                for archivo in os.listdir(ruta_archivos_encontrados):
                    print(f"Archivo encontrado: {archivo}")
                    
                    # Comprobar si el archivo tiene una extensión de imagen
                    if archivo.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff')):
                        hay_imagen = True
                        print(f"Imagen detectada: {archivo}")
                        break
                
                # Mover la carpeta principal según el resultado
                if hay_imagen:
                    destino_carpeta = os.path.join(ruta_destino_con_imagenes, carpeta)
                    shutil.move(ruta_carpeta, destino_carpeta)
                    print(f"Movida la carpeta con imágenes: {ruta_carpeta} a {destino_carpeta}")
                else:
                    destino_carpeta = os.path.join(ruta_destino_sin_imagenes, carpeta)
                    shutil.move(ruta_carpeta, destino_carpeta)
                    print(f"Movida la carpeta sin imágenes: {ruta_carpeta} a {destino_carpeta}")
            else:
                print(f"No se encontró la subcarpeta 'ARCHIVOS ENCONTRADOS' en: {ruta_carpeta}")
        else:
            print(f"'{ruta_carpeta}' no es una carpeta, omitiendo.")



# Proporcionar las rutas
ruta_principal = "C:/Users/cohevmu/Essity/GRP-GOPS-Información Sell-Out COSMOS - Documentos/COSMOS 2.0/4. Informacion Juridica"
ruta_destino_con_imagenes = "C:/Users/cohevmu/Essity/GRP-GOPS-Información Sell-Out COSMOS - Documentos/COSMOS 2.0/4. Informacion Juridica/Convenio COSMOS"
ruta_destino_sin_imagenes = "C:/Users/cohevmu/Essity/GRP-GOPS-Información Sell-Out COSMOS - Documentos/COSMOS 2.0/4. Informacion Juridica/Convenio BIC"

# Llamar a la función
mover_carpetas(ruta_principal, ruta_destino_con_imagenes, ruta_destino_sin_imagenes)













