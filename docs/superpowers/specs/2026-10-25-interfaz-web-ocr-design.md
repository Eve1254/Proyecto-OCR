# Interfaz web local para Proyecto OCR

Estado: propuesta pendiente de aprobación. Fecha: 25 de octubre de 2026.

## Propósito y decisiones de la usuaria

La persona usuaria quiere recuperar su proyecto de Python, probarlo mediante una interfaz gráfica, permitir que otras personas lo utilicen desde sus equipos en una etapa posterior y presentarlo como experiencia profesional. Eligió una **web local**, abierta en el navegador y con procesamiento en su computador.

La primera entrega será una aplicación funcional para una persona, con datos de demostración y documentación para explicar el proyecto. El acceso de otras personas y la publicación en Internet son una etapa posterior; no se configurarán ni publicarán automáticamente.

## Punto de partida

Los originales están en `C:/Users/evely/Downloads/ESTUDIO/PROCESO PRACTICANTE/PROCESO PRACTICANTE/Proyecto OCR/`. Son seis scripts separados, sin interfaz, manifiesto de dependencias ni pruebas. Sus funciones son convertir DOCX con Microsoft Word, contar elementos de carpetas en Excel, extraer adjuntos PDF de MSG, comparar imágenes incrustadas en PDF con un logotipo de referencia usando SIFT, mover carpetas según las imágenes encontradas y borrar las carpetas temporales.

Varios scripts se ejecutan al importarlos y contienen rutas fijas de un computador anterior. No se importarán ni ejecutarán directamente. La aplicación se construirá en `C:/Users/evely/Documents/ChatGPT/OCR/`, aprovechando y adaptando los algoritmos. Los originales de Downloads se conservarán.

Se verificó Python 3.14.3 y Microsoft Word en este computador. Las dependencias del proyecto aún deben instalarse en un entorno aislado. No hay motor de extracción de texto ni de validación de firmas en los scripts. El documento histórico describe algunas aspiraciones adicionales; no se interpretan como funciones ya implementadas ni como instrucciones para ejecutar operaciones sobre archivos.

## Enfoques considerados

1. **Web local con motor Python (elegido)**: permite utilizar el navegador, conservar la lógica existente y preparar una futura aplicación compartida. Requiere un pequeño servidor local y separar la interfaz del procesamiento. Es la recomendación aceptada en la conversación.
2. **Aplicación de escritorio para Windows**: integración directa con carpetas y Word; cada persona necesitaría instalar y actualizar su propia copia. Facilita el uso individual, pero hace menos directa una futura experiencia compartida.

La elección de FastAPI y una interfaz HTML/CSS/JavaScript sin framework es una propuesta técnica del asistente, no una preferencia expresada por la persona usuaria. Reduce componentes de instalación y permite centrar el trabajo en el procesamiento, la claridad visual y la presentación del caso.

## Experiencia de uso propuesta

Interfaz en español, clara y adaptable al ancho de la ventana. El uso principal será en un computador. Nombre provisional: **Proyecto OCR**, con la descripción «Organización y reconocimiento de documentos». Estilo propuesto: fondo claro, texto oscuro, acento verde azulado, tarjetas sencillas, estados con texto además de color y controles accesibles por teclado.

La navegación ofrecerá tres vistas:

- **Procesar documentos**: cargar una carpeta o archivos, ver el inventario, seleccionar procesos y añadir el logotipo de referencia cuando haga falta. Un resumen explicará qué se va a ejecutar antes de iniciar.
- **Resultados**: progreso del trabajo actual, conteos reales, eventos legibles, resultados por archivo y descargas del reporte y del paquete de salida. Los trabajos terminados estarán disponibles al volver a abrir la aplicación.
- **Sobre el proyecto**: problema original, flujo de trabajo, tecnologías, límites y evolución del proyecto. Servirá como material de apoyo para presentar la experiencia; no mostrará métricas de ahorro ni precisión que no se hayan medido.

Habrá un botón «Probar con un ejemplo» que cargará un pequeño conjunto de documentos ficticios y un logotipo de prueba. Los resultados provendrán del mismo motor que procesa archivos propios. El ejemplo estará identificado como demostración; no se usarán archivos empresariales del proyecto original.

### Carga y conservación de archivos

La entrada admitirá seleccionar una carpeta desde el navegador, archivos individuales PDF/DOCX/MSG y una imagen de referencia PNG/JPEG. En la primera versión no se admitirá ZIP de entrada: mantener un único flujo de carga evita añadir complejidad innecesaria. Sí se ofrecerá un ZIP de resultados.

La selección de carpeta conservará rutas relativas. La interfaz mostrará qué archivos son compatibles y cuáles serán omitidos. El navegador enviará copias al servidor local, sin mover ni borrar los originales. Cada trabajo usará un identificador y un directorio propio bajo `data/jobs/`.

Propuesta de límites del piloto: 500 archivos compatibles, 50 MB por archivo, 500 MB por trabajo y referencia de hasta 10 MB. El servidor comprobará los límites, rutas y tipos; la interfaz explicará los rechazos. Estos valores podrán configurarse. No se aceptarán rutas absolutas, segmentos `..`, enlaces simbólicos ni nombres que puedan salir del directorio del trabajo.

## Procesos funcionales

### Inventario y reporte

El inventario inicial mostrará archivos por formato y agrupación. El reporte Excel contará archivos reales, no subcarpetas como hacía el script original. Incluirá hojas de resumen, carpetas, archivos y errores. Las cadenas procedentes de nombres de archivos se escribirán como texto, evitando interpretarlas como fórmulas. Las carpetas vacías no se pueden representar mediante la carga de carpetas del navegador: esta limitación se indicará y no se presentará un conteo falso de ellas.

### Adjuntos de Outlook

Se leerán archivos `.msg` locales, sin conectarse a cuentas de correo. Se extraerán únicamente adjuntos PDF, conservando siempre el grupo del MSG de origen. La carpeta `Convenio` se conservará como parte de la ruta, pero no modificará el grupo. Esta unificación es una decisión del asistente para que un adjunto y los demás documentos del mismo grupo se evalúen juntos. Los nombres se sanearán, se evitarán colisiones y se cerrarán los recursos después de cada mensaje. Un adjunto inválido no cancelará todo el lote.

### Word a PDF

Conversión opcional de `.docx` mediante una instancia propia de Microsoft Word en la sesión local de la usuaria. No se cerrarán las instancias de Word que ella tenga abiertas. Cada documento se abrirá sin ejecutar macros y se cerrará en todos los caminos de salida. Un bloqueo de Word deberá producir un error controlado y no congelar la interfaz indefinidamente; el conversor se aislará en un proceso con tiempo máximo por documento. Si Word o la dependencia faltan, la interfaz explicará cómo resolverlo y permitirá los demás procesos.

Este adaptador es para el piloto local. No se trasladará sin cambios a un servidor multiusuario o un servicio desatendido. Antes de publicar se elegirá otro mecanismo de conversión o se limitarán las entradas a PDF. Microsoft documenta restricciones y posibles bloqueos al automatizar Office en servidores.

### Reconocimiento del logotipo

Se reutilizará el enfoque del original: imágenes incrustadas en PDF, normalización de grises, descriptores SIFT y comparación de características. La referencia será obligatoria para este proceso y se validará que contenga características suficientes. Se conservarán los parámetros iniciales como configuración interna, sin presentar su resultado como una probabilidad.

El resultado por PDF distinguirá «Coincidencia encontrada», «Sin coincidencia» y «Revisar». Un PDF ilegible, protegido, sin imágenes utilizables o con procesamiento incompleto irá a «Revisar». Un documento escaneado podrá funcionar si su página está incrustada como una imagen adecuada, pero no se prometerá reconocimiento de todas las variantes, logotipos vectoriales ni extracción de texto.

La evidencia podrá indicar página, imagen extraída y cantidad de coincidencias. No habrá validación de firma ni evaluación de validez de convenios.

### Clasificación

Se clasificará **por carpeta de primer nivel** bajo la carpeta seleccionada; los archivos cargados individualmente o situados directamente en la raíz pertenecerán a un grupo común. Los subdirectorios se conservarán. La carpeta seleccionada se retirará como envoltorio de las rutas del navegador. Por ejemplo, al seleccionar `Lote`, tanto `Lote/Norte/DistribuidorA/Convenio/correo.msg` como `Lote/Norte/DistribuidorA/documento.pdf` y sus derivados pertenecerán a `Norte`. La interfaz mostrará los grupos antes de ejecutar; para agrupar directamente por distribuidor se seleccionará `Norte`. La identidad del grupo se asignará al cargar y todos sus derivados la heredarán.

En cada grupo, si alguna evidencia no se pudo evaluar, la clasificación será «Revisar», aunque otro PDF tenga una coincidencia. Esto incluye DOCX o MSG cuya conversión o extracción se haya desactivado, fallado o cancelado: no se deducirá una clasificación completa a partir de un subconjunto. Si todos los documentos procesables se evaluaron y algún PDF tiene coincidencia, será «Con logotipo». Si todos se evaluaron correctamente y ninguno coincide, será «Sin coincidencia». Un grupo sin PDF evaluable irá a «Revisar». Un MSG leído correctamente sin adjuntos PDF contará como inspeccionado y aparecerá así en el reporte.

No se tratarán los nombres COSMOS/BIC como una certificación automática: en esta primera versión las categorías describen el resultado observado. La interfaz explicará que son sugerencias. La clasificación dependerá del reconocimiento; si no se ejecuta reconocimiento, los archivos se podrán descargar sin clasificar. Se copiarán los resultados dentro del trabajo, conservando la estructura relativa, nunca se moverán las carpetas originales.

### Limpieza

La opción de salida «Incluir evidencias del reconocimiento» controlará si las imágenes extraídas aparecen en el ZIP. El motor liberará temporales de trabajo que ya no necesite. Esta función reemplaza el borrado recursivo general del script antiguo. Borrar un trabajo desde la aplicación tendrá confirmación y solo afectará a su carpeta generada; no podrá borrar archivos de la usuaria fuera de `data/jobs/`.

## Ejecución y manejo de errores

El orden será inventario, extracción MSG, conversión DOCX, reconocimiento, clasificación y reporte/ZIP. Las etapas seleccionadas se validarán antes de comenzar. Se permitirá un trabajo en ejecución a la vez; la interfaz seguirá respondiendo. Los trabajos mostrarán estados preparado, procesando, completado, completado con incidencias, cancelado o fallido.

El progreso mostrará etapa y cantidades procesadas; no se inventarán porcentajes globales mientras se descubren nuevos adjuntos. La cancelación será cooperativa entre archivos y se informará cuando se esté terminando el archivo actual. El subproceso de Word tendrá un límite independiente. Los errores por archivo se acumularán en el reporte y permitirán continuar cuando sea posible. Una interrupción del servidor dejará el trabajo marcado como interrumpido al siguiente inicio; no se reanudará silenciosamente.

## Arquitectura e instalación propuestas

- Backend Python con FastAPI y Uvicorn, con servicios independientes de HTTP.
- Frontend estático servido por la misma aplicación; sin conexión a CDN ni servicios externos para funcionar.
- Dependencias previstas: PyMuPDF, OpenCV, Pillow, NumPy, openpyxl, extract-msg, comtypes en Windows y soporte multipart. Versiones se fijarán después de verificar compatibilidad; si Python 3.14 impide una dependencia esencial, se instalará un runtime compatible aislado, sin cambiar el predeterminado del sistema.
- Trabajos persistidos en archivos JSON y carpetas locales, con escritura atómica; no se necesita una base de datos para este piloto. No se expondrán rutas arbitrarias para descargar archivos.
- Servidor enlazado únicamente a `127.0.0.1`, con comprobación de Host/Origin en operaciones de escritura, sin CORS abierto. Esto es una aplicación local, no un despliegue multiusuario.
- Lanzadores de Windows para preparar el entorno y abrir la aplicación, mensaje claro de errores y README en español. La implementación estará versionada en el repositorio de trabajo.

## Presentación de la experiencia

La documentación incluirá la motivación, flujo original y nuevo, decisiones técnicas, instrucciones de demostración, límites conocidos y siguientes pasos. Se reconocerá la autoría original de la persona usuaria y se distinguirá de las mejoras incorporadas durante esta colaboración. El nombre público se podrá completar posteriormente. No se publicará en GitHub, redes ni servicios externos en esta etapa.

Los posibles siguientes pasos son medir resultados con documentos representativos, añadir extracción de texto si resulta necesaria, evaluar otro conversor DOCX y preparar autenticación, almacenamiento separado por usuario y procesamiento persistente para una versión compartida. No se anunciará esta capacidad como terminada.

## Criterios de aceptación

1. La persona usuaria puede iniciar la aplicación y completar una demostración desde el navegador, sin editar rutas en código.
2. Se pueden cargar archivos propios compatibles y reconocer un logotipo de referencia, mostrando resultados, errores y evidencia.
3. El flujo genera Excel y ZIP descargables y conserva todos los archivos de origen.
4. La conversión DOCX se prueba en este computador con un documento ficticio; cualquier limitación real queda documentada.
5. Se prueban los límites de rutas, colisiones de nombres, PDFs defectuosos y clasificación de casos incompletos. La prueba de reconocimiento incluye coincidencia y ausencia de coincidencia con fixtures reproducibles.
6. Se verifica visualmente la interfaz en navegador y su uso con teclado, incluyendo carga, progreso, errores y descargas.
7. La demostración y la explicación del proyecto están listas para mostrar localmente, con resultados medidos y sin datos empresariales.

## Decisiones que quedan al implementador

Organización exacta de módulos, biblioteca de pruebas, tamaños tipográficos, iconos, puertos disponibles, política de nombres únicos, frecuencia de actualización del progreso y estructura interna del reporte se resolverán sin añadir nuevas etapas de aprobación. No deben cambiar el alcance, exponer la aplicación a la red ni borrar originales.

## Revisión del diseño

Un revisor independiente detectó dos ambigüedades: agrupación de adjuntos bajo `Convenio` y clasificación cuando se omite conversión o extracción. Se resolvieron con herencia estable del grupo original y clasificación «Revisar» para entradas compatibles pendientes de evaluación. Ambas son decisiones propuestas por el asistente y se incluyen en esta versión para aprobación.

## Referencias técnicas

- [Carga de archivos en FastAPI](https://fastapi.tiangolo.com/tutorial/request-files/).
- [Tareas en segundo plano en FastAPI](https://fastapi.tiangolo.com/tutorial/background-tasks/).
- [Consideraciones de Microsoft sobre automatización de Office en servidores](https://support.microsoft.com/es-es/visio/considerations-for-server-side-automation-of-office).
