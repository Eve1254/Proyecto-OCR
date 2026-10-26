# Piloto de Proyecto OCR en Internet

## Objetivo y decisiones

La usuaria autorizó preparar y publicar una versión accesible desde otros computadores sin instalar software. Eligió un enlace abierto, sin registro, documentos separados por visitante y borrado automático después de una hora, en Render gratuito sin contratar un plan de pago. Se mantiene la interfaz aprobada y la versión local.

## Enfoques

- **Render gratuito con contenedor Python (elegido):** conserva el motor y permite publicar desde GitHub. Ofrece 512 MB de RAM; se limita el tamaño de los lotes y se procesa uno cada vez. Puede suspenderse por inactividad y perder los archivos al reiniciar. Es un piloto, no un archivo documental permanente.
- **Servidor contratado:** permitiría más capacidad y disponibilidad, pero no corresponde a la elección de comenzar sin pagar.
- Sites está orientado a Workers de JavaScript; no ejecuta directamente este motor Python con OpenCV, PyMuPDF y LibreOffice, por lo que no se usará para simular un procesamiento que necesita servidor.

## Funcionamiento propuesto

Una cookie aleatoria, HttpOnly, Secure y SameSite=Strict identifica este navegador durante la visita. El servidor firma y verifica la cookie. No hay cuentas ni recuperación del historial al cambiar de navegador o borrar cookies. Todos los accesos a trabajos, evidencias, descargas, cancelación y borrado comprueban al propietario. Los trabajos locales anteriores nunca se exponen en el modo público.

Los originales, derivados y resultados se eliminan una hora después de crear el trabajo, con una limpieza periódica cada minuto mientras el servicio está activo. El acceso expira exactamente al cumplirse la hora. Un reinicio o suspensión puede eliminarlos antes. Un trabajo expirado en ejecución se cancela y se limpia al terminar el proceso. La interfaz explica el envío al servidor y la duración antes de subir archivos; el ejemplo usa solo información ficticia.

Decisiones técnicas del implementador para el piloto: 20 archivos de hasta 10 MB, 30 MB por lote, referencia de hasta 2 MB, 50 páginas y 150 imágenes por PDF, 6 millones de píxeles por imagen, 200 archivos derivados como máximo. Hasta 3 trabajos guardados por visitante, 12 globales, 6 preparaciones por visitante cada hora y 30 globales cada hora. Una cola corta admite 4 trabajos pendientes y procesa uno cada vez. Se rechazan sobrecargas con mensajes comprensibles. Se limita además el espacio global reservado para trabajos.

Cada trabajo público se procesa en un subproceso con tiempo máximo de 180 segundos, seguimiento de memoria y cancelación del árbol de procesos. El servicio mantiene un solo proceso HTTP y un solo ejecutor para respetar el plan gratuito. El modo local mantiene su comportamiento y sus límites actuales.

La conversión de DOCX en Linux usa LibreOffice sin interfaz, con perfil temporal propio, macros desactivadas, sin actualizar vínculos y sin reutilizar procesos. Se rechazan documentos comprimidos desproporcionados y relaciones externas antes de abrirlos. Se explican posibles diferencias de formato respecto a Microsoft Word. Word sigue usándose en Windows local.

El modo público exige un origen HTTPS explícito (o el hostname de Render), un secreto de sesión y una carpeta distinta a los datos locales. Valida Host/Origin y no acepta un origen arbitrario enviado por el visitante. No habilita CORS general ni confía en direcciones IP reenviadas para autorizar acceso. Configuración incompleta impide iniciar el servicio público. El contenedor usa usuario sin privilegios, no contiene secretos ni documentos locales, y no expone paneles de administración.

## Publicación y verificación

Se entrega Dockerfile, render.yaml con plan free, instrucciones y pruebas de aislamiento entre dos navegadores, caducidad, origen, carga limitada, cola, cancelación y recuperación. Se comprueba la conversión real en Linux y el ejemplo completo dentro del contenedor, además de conservar las pruebas locales.

La publicación real requiere una sesión de Render de la usuaria. No se aceptarán términos, planes de pago ni permisos de cuenta nuevos en su nombre sin el paso correspondiente de la interfaz. Se prepara todo el código y la configuración mientras ella inicia sesión. Solo un despliegue exitoso y una prueba por HTTPS permiten afirmar que está publicada.

## Límites

No se añade OCR de texto, validación de firmas, cuentas de usuario, almacenamiento permanente ni métricas de precisión. La disponibilidad y capacidad del plan gratuito son limitadas. Los mensajes de la interfaz identifican claramente este alcance.

Fuentes de alojamiento consultadas: https://render.com/docs/free, https://render.com/pricing, https://render.com/docs/blueprint-spec.
