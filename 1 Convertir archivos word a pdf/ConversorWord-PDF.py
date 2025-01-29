
import os  #manejo de operaciones del sistema operativo, como navegación en carpetas.
import comtypes.client  # automatización de Word en Windows.


def ConvertidorPdfAWord(Ruta_Carpeta):  # Define una función que toma como entrada la ruta de una carpeta.
    # Asegúrate de que la carpeta existe
    if not os.path.isdir(Ruta_Carpeta):  # Verifica si la ruta proporcionada corresponde a una carpeta.
        print("La carpeta especificada no existe.")  # Imprime un mensaje si la carpeta no existe.
        return 

    # Itera sobre todos los archivos en la carpeta
    for Nombre_Archivo in os.listdir(Ruta_Carpeta):  # Recorre cada archivo en la carpeta especificada.
        if Nombre_Archivo.endswith(".docx"):  # Filtra solo los archivos que terminan en ".docx".
            Ruta_Word = os.path.join(Ruta_Carpeta, Nombre_Archivo)  # Obtiene la ruta completa del archivo .docx.
            Ruta_PDF = os.path.join(Ruta_Carpeta, Nombre_Archivo.replace(".docx", ".pdf"))  # Define la ruta del archivo PDF con el mismo nombre.

            # Abre Word y convierte el archivo
            word = comtypes.client.CreateObject("Word.Application")  # Abre una instancia de Microsoft Word.
            doc = word.Documents.Open(Ruta_Word)  # Abre el archivo .docx en Word.
            doc.SaveAs(Ruta_PDF, FileFormat=17)  # Guarda el archivo en formato PDF (17 es el código para PDF en Word).
            doc.Close()  # Cierra el documento en Word.
            word.Quit()  # Cierra la aplicación de Word.

            print(f"Convertido: {Nombre_Archivo} a PDF.")  # Imprime un mensaje de éxito para cada archivo convertido.

        #Verifica archivos one drive
    for Nombre_Archivo in os.listdir(Ruta_Carpeta):
        Ruta_Archivo_Drive = os.path.join(Ruta_Carpeta, Nombre_Archivo)
        if not os.path.exists(Ruta_Archivo_Drive):
            print(f"El archivo {Ruta_Archivo_Drive} no está disponible localmente.")
        else:
            print(f"El archivo {Ruta_Archivo_Drive} está listo para usar.")


Ruta_Carpeta = r"C:/Users/cohevmu/Essity/GRP-GOPS-Información Sell-Out COSMOS - Documentos/COSMOS 2.0/4. Informacion Juridica/CO-CBIA-DTR-0086 - SAN ISIDRO"  # Cambia esto por la ruta de tu carpeta
ConvertidorPdfAWord(Ruta_Carpeta)  
          
