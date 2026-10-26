# Validación de la primera versión local

Fecha: 25 de octubre de 2026. Equipo Windows con Python 3.14.3 y Microsoft Word instalado.

## Resultado

La suite completa pasó **39 pruebas**, activando la integración real de Word con `OCR_TEST_WORD=1`. La comprobación de sintaxis JavaScript y `pip check` también finalizaron correctamente.

Se verificaron rutas peligrosas, nombres repetidos, persistencia, exclusión de instancias, reconocimiento positivo/negativo, PDF sin imágenes y con imágenes sin características, cancelación, origen de peticiones, límites de carga, reportes, descargas y borrado acotado. Un MSG ficticio en formato OLE se leyó con extract-msg y su adjunto PDF se recuperó sin alteraciones.

La conversión real abrió una instancia propia de Word, produjo un PDF legible de un DOCX ficticio y mantuvo intacto el archivo de entrada. También se comprobó la salida por tiempo máximo mediante un subproceso controlado.

## Recorrido comprobado en navegador

- Inicio y comprobación de disponibilidad de Word.
- Demo completa con tres resultados distintos y evidencia visible.
- Descarga real de Excel y ZIP; se abrió la estructura de ambos archivos para validarlos.
- Selector de archivos con un DOCX y un PDF, aviso por referencia ausente, selección de logo, preparación y ejecución real.
- Selector de carpeta conservando tres subcarpetas de distribuidores.
- Cierre de evidencia con Escape y conservación de foco.
- Disposición a 360 y 1280 píxeles sin desbordamiento horizontal.
- Consola del navegador sin errores o advertencias durante el recorrido.
- Lanzamiento repetido detectado sin abrir una segunda instancia sobre el mismo historial.

## Revisión independiente y correcciones

La revisión del código detectó imágenes sin características clasificadas como negativas y un adjunto defectuoso que impedía recuperar los siguientes. Se añadieron regresiones que fallaron antes de la corrección y pasaron después.

También se reforzaron dos casos de coherencia: impedir inicio/borrado mientras un lote se está preparando y separar internamente los archivos de raíz de una carpeta que se llame «Archivos sueltos». La normalización de nombres MSG tolera terminadores nulos encontrados durante la prueba del parser real.

No quedaron hallazgos materiales pendientes de la revisión. La precisión del reconocimiento y la compatibilidad con documentos empresariales representativos todavía deben medirse con una muestra real; la demostración verifica funcionamiento, no una tasa de precisión.

## Captura

![Interfaz funcional de Proyecto OCR](screenshots/proyecto-ocr.png)
