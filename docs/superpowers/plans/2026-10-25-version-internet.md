# Versión de Internet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Publicar un piloto sin registro con trabajos privados por navegador y borrado en una hora.

**Architecture:** FastAPI conserva el modo local y añade configuración pública explícita. La API comprueba sesiones y propiedad; un ejecutor con subprocesos limita recursos y usa LibreOffice dentro de Docker. Render aloja el contenedor en su plan gratuito.

**Tech Stack:** Python 3.14, FastAPI, cookies HMAC, OpenCV, PyMuPDF, LibreOffice, Docker, Render.

**Spec:** docs/superpowers/specs/2026-10-25-version-internet-design.md

## Global Constraints

- HTTPS, sin registro, cookie firmada segura, documentos privados por visitante; no exponer datos locales.
- Acceso expira a los 3600 segundos; limpieza cada 60 segundos, sin prometer permanencia frente a reinicios.
- Límites públicos: 20 archivos, 10 MB/archivo, 30 MB/lote, 2 MB/referencia, 50 páginas, 150 imágenes, 6 millones de píxeles, 200 derivados.
- Cuotas: 3 trabajos/visitante, 12 globales, 6 preparaciones/hora/visitante, 30 globales; 4 trabajos en espera, uno activo; 180 segundos/trabajo.
- Mantener límites y pruebas del modo local. No contratar planes de pago ni publicar datos de prueba privados.

## Review Focus

1. Otro visitante intenta usar directamente un ID conocido para leer, descargar, cancelar o borrar: 404 sin revelar existencia.
2. Expiración durante ejecución/descarga: acceso denegado, proceso cancelado y limpieza sin resucitar archivos.
3. Cookie alterada, ausencia de secreto, Host/Origin ajeno y peticiones grandes: rechazo antes de acceder a trabajos.
4. DOCX con vínculos externos o expansión ZIP desproporcionada, PDF lento/dañado: rechazo o salida limitada sin bloquear el servidor.
5. Reinicios, cola llena, memoria o disco limitados: estado comprensible, sin divulgar historiales ni dejar procesos huérfanos.

### Task 1: Sesiones y ciclo de vida público

**Files:** config.py, security.py, storage.py, app.py, nuevo access.py, tests/test_public.py.
**Interfaces:** create_app(data_root=None, settings=None); Settings.from_env(); JobStore.create(..., owner=None); AccessPolicy controla cookie, cuotas, propietario y expiración. Los endpoints públicos usan Request y exponen trabajos sin el campo de propietario.

- [x] Escribir y ver fallar pruebas de dos clientes, cookie alterada, origen/host, cuotas y expiración.
- [x] Añadir configuración por instancia y límites propagados a almacenamiento/procesamiento.
- [x] Proteger todos los endpoints y añadir limpieza periódica; modo local sigue compatible.
- [x] Ejecutar pytest completo y guardar commit.

### Task 2: Ejecución y conversión en servidor

**Files:** jobs.py, processing.py, recognition.py, nuevo public_worker.py, conversion.py, tests/test_public_jobs.py, tests/test_conversion.py.
**Interfaces:** PublicJobManager(store, settings) conserva start/cancel/delete/close; estado queued y posición; run_pipeline usa store.limits. convert_document(source, target, backend='word', timeout=90) selecciona conversor. Worker recibe rutas locales controladas y límites públicos.

- [x] Escribir y ver fallar pruebas de cola/cancelación, tiempo máximo, recuperación y rechazo de DOCX inseguros.
- [x] Implementar subproceso acotado y limpieza de su árbol; límites de páginas/imágenes/derivados.
- [x] Añadir LibreOffice con perfil independiente y pruebas de conversión real opcionales en Linux.
- [x] Ejecutar suite y guardar commit.

### Task 3: Interfaz y paquete de despliegue

**Files:** static/index.html, app.js, styles.css; Dockerfile, .dockerignore, render.yaml, run_server.py, docs/internet.md, README.md.
**Interfaces:** /api/health informa local, converter, limits, retention_seconds; /api/session inicia cookie antes de listar trabajos; queued activa sondeo y cancelación; expires_at visible en resultados.

- [x] Adaptar mensajes y avisos de envío, sesión, caducidad, cola y conversión; conservar diseño.
- [x] Crear contenedor sin privilegios y Blueprint gratuito con secreto generado, sin datos locales.
- [x] Construir Docker y probar demo, carga/conversión, dos visitantes y descargas; comprobar navegador y suite completa.
- [x] Revisión independiente de la rama y correcciones con regresiones; guardar cambios en GitHub.

### Task 4: Publicar el piloto

- [x] Confirmar sesión y cuenta de Render, seleccionar el repositorio de Eve1254 y plan gratuito.
- [x] Publicar la versión comprobada y esperar resultado definitivo.
- [x] Comprobar HTTPS, demo y aislamiento; entregar enlace público y límites reales.
