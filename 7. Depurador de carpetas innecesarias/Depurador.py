import os
import shutil
import stat

def eliminar_subcarpeta(carpeta_principal, subcarpeta_objetivo):
    """Elimina la subcarpeta especificada en todas las carpetas dentro de la carpeta principal."""
    def quitar_proteccion(func, ruta, exc_info):
        """Cambia los permisos de solo lectura y vuelve a intentar."""
        os.chmod(ruta, stat.S_IWRITE)
        func(ruta)

    for raiz, directorios, archivos in os.walk(carpeta_principal):
        if subcarpeta_objetivo in directorios:
            ruta_subcarpeta = os.path.join(raiz, subcarpeta_objetivo)
            try:
                shutil.rmtree(ruta_subcarpeta, onerror=quitar_proteccion)  # Elimina la carpeta y su contenido
                print(f"Eliminado: {ruta_subcarpeta}")
            except Exception as e:
                print(f"Error al eliminar {ruta_subcarpeta}: {e}")

if __name__ == "__main__":
    # Solicita al usuario la ruta de la carpeta principal
    carpeta_principal = input("Ingresa la ruta de la carpeta principal: ").strip()
    subcarpeta_objetivo = "archivos_encontrados"

    # Verifica si la ruta proporcionada es válida
    if os.path.exists(carpeta_principal) and os.path.isdir(carpeta_principal):
        eliminar_subcarpeta(carpeta_principal, subcarpeta_objetivo)
    else:
        print("Ruta de carpeta no válida.")



