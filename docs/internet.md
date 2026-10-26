# Piloto de Internet

Esta versión permite abrir la aplicación desde un navegador sin instalar Python, Word ni otro programa. El procesamiento ocurre en el servidor. La configuración está preparada para **Render Free**; tener el código en GitHub no significa que el servicio ya esté desplegado.

## Experiencia de la persona visitante

1. Abre el enlace HTTPS del despliegue y elige **Probar con un ejemplo**, o selecciona archivos de prueba.
2. Revisa las opciones y pulsa **Preparar lote → Iniciar procesamiento**.
3. Si hay otro trabajo activo, espera su turno en la cola. Puedes cancelar tanto la espera como el procesamiento.
4. Revisa las incidencias y descarga los resultados antes de la hora de caducidad indicada.

Cada navegador tiene una sesión anónima mediante una cookie necesaria para separar sus trabajos. No hay registro ni historial compartido. Cambiar de navegador o eliminar la cookie hace perder el acceso a los trabajos anteriores.

Los trabajos caducan **una hora después de su creación**. A partir de ese momento no se pueden consultar ni descargar. La limpieza se ejecuta cada minuto mientras el servidor está activo; los trabajos en ejecución se cancelan antes de borrar sus archivos. Un reinicio, suspensión o nuevo despliegue puede eliminar los documentos antes. Usa el ejemplo o documentos sin información confidencial para probar este piloto.

## Límites del piloto

| Recurso | Límite |
| --- | --- |
| Archivos por lote | 20 |
| Tamaño de cada archivo | 10 MB |
| Originales y derivados por lote | 30 MB |
| Imagen de referencia | 2 MB |
| PDF | 50 páginas y 150 imágenes |
| Imagen individual | 6 millones de píxeles |
| Registros originales y derivados | 200 |
| Trabajos guardados | 3 por visitante, 12 en el servicio |
| Preparaciones por hora | 6 por visitante, 30 en el servicio |
| Procesamiento | 1 activo y hasta 4 en espera |
| Duración del procesamiento | 180 segundos por trabajo |

La conversión de DOCX usa LibreOffice en el servidor. Puede haber diferencias de formato respecto a Word. El piloto rechaza macros, objetos incrustados, vínculos externos y documentos comprimidos que excedan sus límites. Como alternativa, convierte el documento a PDF antes de subirlo.

El reconocimiento sigue buscando logotipos en imágenes incrustadas. No extrae texto ni valida firmas o convenios. Los documentos incompletos o no compatibles requieren revisión.

## Desplegar en Render

1. Inicia sesión en tu cuenta de Render. Usa el repositorio público `https://github.com/Eve1254/Proyecto-OCR` y la revisión que haya superado las pruebas.
2. Crea un **Blueprint** con `render.yaml`. Comprueba que el servicio indique **Free** y no añadas bases de datos, discos ni recursos de pago.
3. Render genera `OCR_SESSION_SECRET`. No copies este secreto en el código, README ni conversaciones.
4. El contenedor ejecuta las pruebas de Linux y una conversión real con LibreOffice antes de completar la compilación.
5. Espera a que el servicio esté activo. Abre su dirección HTTPS y ejecuta la demostración completa antes de compartirla.

El origen autorizado se obtiene de `RENDER_EXTERNAL_HOSTNAME`. Si usas un dominio propio, configura `OCR_PUBLIC_ORIGIN=https://tu-dominio` sin ruta ni barra final. No se utiliza un Host enviado por un visitante para decidir el origen válido.

Los despliegues automáticos están desactivados en el Blueprint: comprueba las pruebas de GitHub antes de desplegar manualmente una revisión nueva. El servicio necesita **una instancia y un proceso HTTP**; no aumentes trabajadores de Uvicorn sin rediseñar la cola y las cuotas.

Render Free ofrece 512 MB de RAM, se suspende por inactividad y puede tardar alrededor de un minuto en reactivarse. Sus archivos son efímeros. Consulta las [condiciones vigentes](https://render.com/docs/free) y los límites de tu cuenta. No se requiere contratar un plan de pago para este piloto.

## Configuración

| Variable | Valor / uso |
| --- | --- |
| `OCR_MODE` | `public` |
| `OCR_DATA_DIR` | `/app/data/jobs` en el contenedor; una carpeta separada de los trabajos locales |
| `OCR_SESSION_SECRET` | Valor secreto aleatorio de al menos 32 caracteres |
| `OCR_PUBLIC_ORIGIN` | Origen HTTPS; opcional en Render si existe su hostname automático |
| `PORT` | `8000` en el Blueprint |

El modo público no arranca con una configuración incompleta. El contenedor funciona sin privilegios y los trabajadores no reciben el secreto de las sesiones. Se vigilan tiempo, memoria y espacio de cada proceso y sus hijos. La versión local se sigue abriendo con **Iniciar OCR.cmd**, con sus límites anteriores.

Solo para pruebas locales, `OCR_PUBLIC_PREVIEW=1` permite un origen HTTP de loopback (`127.0.0.1` o `localhost`); nunca habilites esta opción en el despliegue. Las cookies siguen siendo Secure y el navegador debe reconocer loopback como contexto seguro.

## Comprobaciones

```powershell
python -m pytest -q
node --check ocr_app/static/app.js
docker build --target test -t proyecto-ocr-test .
docker build --target production -t proyecto-ocr .
```

La prueba real de LibreOffice se ejecuta cuando el programa está disponible, como ocurre dentro del contenedor. La prueba de Microsoft Word sigue siendo opcional en Windows con `OCR_TEST_WORD=1`. GitHub Actions construye y comprueba el contenedor Linux en cada cambio a la rama del piloto.

Antes de compartir un despliegue, prueba con dos navegadores distintos: el segundo debe tener un historial vacío y no poder usar un enlace de descarga del primero. Comprueba también la demo, una conversión DOCX ficticia y las descargas de Excel y ZIP.
