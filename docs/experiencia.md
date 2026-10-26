# Proyecto OCR como experiencia de automatización

## El problema

El proyecto original buscaba organizar documentos de convenio que llegaban en distintos formatos y carpetas. Incluía convertir Word a PDF, recuperar adjuntos PDF de mensajes de Outlook, generar un inventario y reconocer un logotipo como apoyo a la clasificación.

## La contribución original

La persona que creó el proyecto diseñó el flujo de trabajo y desarrolló seis scripts Python para cubrir sus etapas. Esa experiencia combina análisis de un proceso operativo, manejo de archivos, integración con aplicaciones de Windows y reconocimiento de imágenes.

## Evolución a una herramienta utilizable

Esta primera aplicación web local se desarrolló con asistencia de Codex a partir de esos scripts y del diseño aprobado. Reúne las etapas en una interfaz, sustituye rutas escritas en código por selección de archivos y permite consultar resultados, evidencias e incidencias. Trabaja sobre copias y deja trazabilidad en un reporte descargable.

Para presentar honestamente la experiencia, distingue el trabajo original y las mejoras realizadas con asistencia: ambos forman parte del recorrido, pero no tienen la misma autoría.

## Una demostración de tres minutos

1. Explica el problema y muestra los tres documentos ficticios del ejemplo.
2. Ejecuta el proceso y explica las categorías Con logotipo, Sin coincidencia y Revisar.
3. Abre una evidencia y el reporte Excel. Señala que un archivo que no pudo evaluarse no se clasifica como si se hubiera revisado correctamente.
4. Muestra cómo la selección de procesos permite reutilizar las tareas de preparación sin depender del reconocimiento.
5. Cierra con lo aprendido y las próximas validaciones: documentos reales representativos, medición de precisión y preparación de una versión compartida.

## Texto breve para adaptar a tu portafolio

Desarrollé un proyecto de automatización documental en Python para organizar archivos, convertir documentos Word a PDF, recuperar adjuntos de Outlook e identificar un logotipo como apoyo a la clasificación. Posteriormente lo evolucioné, con asistencia de IA, hacia una aplicación web local con carga de documentos, seguimiento de procesos, revisión de evidencias y exportación a Excel. El proyecto me permitió conectar un problema operativo con una solución técnica y trabajar en su usabilidad, manejo de errores y validación.

## Qué puedes afirmar y qué falta medir

Puedes mostrar las funcionalidades comprobadas con la demostración y explicar sus decisiones técnicas. No atribuyas todavía un porcentaje de precisión, un ahorro de horas o resultados empresariales a esta versión: requieren un conjunto representativo, revisión humana y mediciones antes/después.

La herramienta reconoce características de imágenes, no valida firmas ni determina la validez de documentos. La versión local todavía no es un servicio multiusuario publicado. Estos límites también son parte de una presentación técnica responsable.

## Próximos pasos

Validar documentos representativos, anotar falsos positivos/negativos, medir tiempos y ajustar el reconocimiento. Después evaluar acceso compartido con autenticación y separación por usuario, y un conversor de documentos apto para servidor.
