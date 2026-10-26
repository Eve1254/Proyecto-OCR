# Interfaz web OCR Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** entregar una aplicación web local funcional, con demo reproducible y lanzador Windows.

**Architecture:** servicios Python independientes de HTTP, almacén de trabajos con JSON atómico y un ejecutor de un solo trabajo. FastAPI sirve una interfaz estática en español y API del mismo origen.

**Tech Stack:** Python, FastAPI, Uvicorn, PyMuPDF, OpenCV, Pillow, openpyxl, extract-msg, comtypes, HTML/CSS/JavaScript; pytest/httpx para pruebas.

**Spec:** `docs/superpowers/specs/2026-10-25-interfaz-web-ocr-design.md`

## Global Constraints

- Servir exclusivamente en `127.0.0.1`; validar Host/Origin y no abrir CORS.
- Trabajar en este repositorio, separado de los scripts originales en Downloads.
- Copias por trabajo bajo `data/jobs/`; 500 entradas, 50 MB por entrada, 500 MB por lote y 10 MB por referencia.
- Un único trabajo en ejecución; cancelación entre archivos; conversión Word en proceso con tiempo máximo.
- Reconocimiento de imágenes incrustadas, sin prometer OCR de texto ni validación de firmas.
- Agrupación por primer nivel; derivados heredan grupo; entradas sin evaluar producen Revisar.
- Datos ficticios para demo; ninguna publicación o exposición de red.

## Review Focus

- Nombres Windows especiales, colisiones por mayúsculas, rutas UNC/absolutas y enlaces: rechazo o nombres únicos dentro del trabajo (tarea 1).
- PDF dañado/protegido/sin imágenes y referencia sin características: estado Revisar o rechazo previo (tarea 2).
- MSG con nombres de adjuntos repetidos/peligrosos y documentos omitidos: no sobrescribir y no clasificar como completos (tarea 2).
- Inicio/cancelación/borrado simultáneos y reinicio durante trabajo: estados persistentes coherentes (tarea 3).
- DOCX cuyo Word no responde, descarga sin archivo e interfaz a 360 px: error entendible y sin bloqueo (tarea 4).

### Task 1: Almacenamiento y entrada segura

**Files:** `ocr_app/storage.py`, `ocr_app/config.py`, `tests/test_storage.py`, `requirements.txt`, `requirements-dev.txt`.
**Interfaces:** `JobStore(root: Path)`, `create(options: dict, demo=False) -> dict`, `get(job_id) -> dict`, `save(job)`, `directory(job_id) -> Path`, `delete(job_id)`; `safe_relative(name: str) -> Path`, `unique_path(root: Path, relative: Path) -> Path`.

- [x] Escribir pruebas parametrizadas: rechazar `../a.pdf`, `C:/a.pdf`, `/a.pdf`, `x/CON.pdf`, `a:stream.pdf`, `a./b.pdf`; preservar `Álvaro/a.pdf`; nombres repetidos distintos; JSON persiste y reinicio marca trabajos activos interrumpidos.
- [x] Ejecutar `python -m pytest tests/test_storage.py -q`: falla por implementación ausente.
- [x] Implementar validación de rutas/nombres, directorios de trabajo y persistencia atómica, sin efectos fuera del almacén.
- [x] Ejecutar la prueba: debe pasar; commit de la tarea.

### Task 2: Procesamiento documental

**Files:** `ocr_app/recognition.py`, `ocr_app/processing.py`, `ocr_app/word_worker.py`, `ocr_app/demo.py`, `ocr_app/reports.py`, `tests/test_processing.py`.
**Interfaces:** `inspect_pdf(path, reference, evidence_dir) -> dict`; `run_pipeline(store, job_id, cancelled: Event) -> None`; `create_demo(job_dir) -> (list[dict], str)`; `write_report(job, directory) -> Path`.

- [x] Crear PDFs reproducibles con imagen coincidente, imagen distinta, sin imágenes y corrupto. Probar que producen match/no_match/review/review; referencia vacía se rechaza.
- [x] Probar que DOCX/MSG omitido mantiene grupo en review; ZIP conserva originales; celdas de Excel que empiezan por `=` son texto; adjuntos con nombres repetidos no se pisan.
- [x] Ejecutar `python -m pytest tests/test_processing.py -q`: falla por motor ausente.
- [x] Implementar reconocimiento SIFT, extracción MSG, conversión aislada Word, clasificación conservadora, reporte y ZIP; entradas/derivados guardan rutas y grupo explícitos.
- [x] Ejecutar suite y confirmar resultados de demo; commit de la tarea.

### Task 3: API local, trabajos y controles

**Files:** `ocr_app/app.py`, `ocr_app/jobs.py`, `tests/test_api.py`.
**Interfaces:** `create_app(data_root: Path | None = None) -> FastAPI`; `GET /api/health`, `GET/POST /api/jobs`, `POST /api/demo`, `GET /api/jobs/{id}`, `POST /api/jobs/{id}/start`, `/cancel`, `DELETE /api/jobs/{id}`, `GET /api/jobs/{id}/download/{kind}`, evidencia por ID de archivo y nombre validado.

- [x] Probar carga multipart con rutas relativas, límites con ajustes de test, rechazo de origen externo, demo hasta estado terminal y descargas ZIP/XLSX válidas; rechazo de dos inicios y borrado de trabajo activo.
- [x] Ejecutar `python -m pytest tests/test_api.py -q`: falla por API ausente.
- [x] Implementar carga en bloques, validación, un hilo de procesamiento, historial persistente, cancelación y borrado acotado; middleware de acceso local.
- [x] Ejecutar suite completa; commit de la tarea.

### Task 4: Interfaz, inicio y entrega verificable

**Files:** `ocr_app/static/index.html`, `styles.css`, `app.js`, `run.py`, `Iniciar OCR.cmd`, `Preparar OCR.cmd`, `README.md`, `docs/experiencia.md`, `tests/test_word.py`.
**Interfaces:** frontend usa API de tarea 3; `run.py --no-browser --port N` inicia loopback; launcher usa `.venv` y muestra errores de instalación.

- [x] Escribir prueba de DOCX ficticio mediante OOXML mínimo y conversión real opcional `OCR_TEST_WORD=1`; timeout prueba con proceso controlado sin matar Word ajeno.
- [x] Ejecutar prueba de conversión; implementar/ajustar adaptador si procede. La prueba real debe producir PDF legible.
- [x] Implementar diseño aprobado, selección de carpeta/archivos con grupos visibles, opciones, logo, demo, progreso/cancelación, historial, detalle, evidencia, descargas y confirmación de borrado.
- [x] Crear lanzadores, dependencias fijadas y documentación de uso y experiencia con límites reales.
- [x] Verificar navegador: demo, carga real de fixtures, navegación/teclado, errores, descargas y disposición estrecha. Ejecutar `python -m pytest -q`, `node --check ocr_app/static/app.js`, `git diff --check`.
- [x] Revisión independiente del conjunto, resolver fallos materiales con regresiones; commit final. Abrir aplicación para la persona usuaria y entregar rutas e instrucciones concisas.
