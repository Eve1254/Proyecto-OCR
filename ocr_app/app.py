import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, ValidationError

from .config import DATA_ROOT, LIMITS, SUPPORTED
from .demo import create_demo
from .jobs import BusyError, JobManager
from .processing import file_record
from .recognition import load_reference
from .security import LocalOnlyMiddleware
from .storage import JobStore, contained, safe_relative, unique_path


class Options(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    convert: bool = True
    extract: bool = True
    recognize: bool = True
    classify: bool = True
    report: bool = True
    evidence: bool = True


def word_available():
    if os.name != 'nt':
        return False
    import winreg
    for key in (r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\WINWORD.EXE',
                r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\WINWORD.EXE'):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key) as entry:
                if Path(winreg.QueryValue(entry, None)).is_file():
                    return True
        except OSError:
            continue
    return False


def create_app(data_root: Path | None = None):
    store = JobStore(data_root or DATA_ROOT)
    manager = JobManager(store)

    @asynccontextmanager
    async def lifespan(app):
        yield
        manager.close()

    app = FastAPI(title='Proyecto OCR', lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store = store
    app.state.manager = manager
    app.add_middleware(LocalOnlyMiddleware)

    @app.exception_handler(BusyError)
    async def busy_error(request, error):
        return JSONResponse({'detail': str(error)}, status_code=409)

    @app.exception_handler(KeyError)
    async def missing_error(request, error):
        return JSONResponse({'detail': 'No se encontró el trabajo.'}, status_code=404)

    @app.exception_handler(ValueError)
    async def invalid_error(request, error):
        return JSONResponse({'detail': str(error)}, status_code=400)

    @app.get('/api/health')
    def health():
        return dict(name='Proyecto OCR', version='1.0.0', local=True, word=word_available(),
                    limits=dict(files=LIMITS.files, file_mb=LIMITS.file_bytes // 1024**2,
                                job_mb=LIMITS.job_bytes // 1024**2, reference_mb=LIMITS.reference_bytes // 1024**2))

    @app.get('/api/jobs')
    def jobs():
        return [dict(id=j['id'], name=j['name'], status=j['status'], created=j['created'],
                     demo=j['demo'], count=sum(f['original'] for f in j['files'])) for j in store.list()]

    @app.get('/api/jobs/{job_id}')
    def get_job(job_id: str):
        job = store.get(job_id)
        job['cancellation_requested'] = manager.active == job_id and manager.cancelled.is_set()
        return job

    @app.post('/api/jobs')
    async def upload(files: list[UploadFile] = File(...), paths: str = Form('[]'),
                     options: str = Form('{}'), reference: UploadFile | None = File(None)):
        job = None
        try:
            try:
                selected = Options.model_validate_json(options).model_dump()
                names = json.loads(paths)
            except (ValidationError, json.JSONDecodeError):
                raise ValueError('Las opciones o rutas del lote no son válidas.')
            if not isinstance(names, list) or any(not isinstance(n, str) for n in names):
                raise ValueError('Las rutas deben ser una lista de nombres.')
            if names and len(names) != len(files):
                raise ValueError('La lista de rutas no coincide con los archivos.')
            if not files or len(files) > LIMITS.files:
                raise HTTPException(413, f'Selecciona entre 1 y {LIMITS.files} archivos.')
            if selected['classify'] and not selected['recognize']:
                raise ValueError('Activa reconocimiento para clasificar por logotipo.')
            if selected['recognize'] and reference is None:
                raise ValueError('Selecciona el logotipo de referencia para reconocer documentos.')
            relative_paths = [safe_relative(n) for n in (names or [f.filename or '' for f in files])]
            if any(path.suffix.lower() not in SUPPORTED for path in relative_paths):
                raise ValueError('Solo se admiten archivos PDF, DOCX y MSG.')
            job = store.create(selected)
            job['status'] = 'uploading'
            store.save(job)
            directory = store.directory(job['id'])
            total = 0
            for uploaded, relative in zip(files, relative_paths):
                target = unique_path(directory / 'input', relative)
                size = 0
                with target.open('xb') as destination:
                    while chunk := await uploaded.read(1024 * 1024):
                        size += len(chunk)
                        total += len(chunk)
                        if size > LIMITS.file_bytes or total > LIMITS.job_bytes:
                            raise HTTPException(413, 'Los archivos superan el límite de tamaño del lote o de un archivo.')
                        destination.write(chunk)
                if not size:
                    raise ValueError('El archivo está vacío: ' + str(relative))
                actual = target.relative_to(directory / 'input')
                group = actual.parts[0] if len(actual.parts) > 1 else 'Archivos sueltos'
                job['files'].append(file_record(target, directory, actual.as_posix(), group))
            if reference is not None and selected['recognize']:
                extension = Path(reference.filename or '').suffix.lower()
                if extension not in {'.png', '.jpg', '.jpeg'}:
                    raise ValueError('La referencia debe ser PNG o JPEG.')
                data = await reference.read(LIMITS.reference_bytes + 1)
                if len(data) > LIMITS.reference_bytes:
                    raise HTTPException(413, 'El logotipo supera 10 MB.')
                target = directory / ('reference' + extension)
                target.write_bytes(data)
                load_reference(target)
                job['reference'] = target.name
            job['name'] = f"{len(job['files'])} documentos"
            job['status'] = 'ready'
            store.save(job)
            return job
        except Exception:
            if job:
                store.delete(job['id'])
            raise
        finally:
            for uploaded in files:
                await uploaded.close()
            if reference:
                await reference.close()

    @app.post('/api/demo')
    def demo():
        job = store.create(Options(convert=False, extract=False).model_dump(), demo=True)
        try:
            job['files'], job['reference'] = create_demo(store.directory(job['id']))
            store.save(job)
            return job
        except Exception:
            store.delete(job['id'])
            raise

    @app.post('/api/jobs/{job_id}/start')
    def start(job_id: str):
        return manager.start(job_id)

    @app.post('/api/jobs/{job_id}/cancel')
    def cancel(job_id: str):
        manager.cancel(job_id)
        return {'message': 'Cancelación solicitada; se terminará el archivo actual.'}

    @app.delete('/api/jobs/{job_id}')
    def delete(job_id: str):
        manager.delete(job_id)
        return {'deleted': True}

    @app.get('/api/jobs/{job_id}/download/{kind}')
    def download(job_id: str, kind: str):
        job = store.get(job_id)
        mapping = {'excel': ('reporte.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                   'zip': ('resultados.zip', 'application/zip')}
        if kind not in mapping or kind not in job['artifacts']:
            raise HTTPException(404, 'La descarga todavía no está disponible.')
        name, mime = mapping[kind]
        path = contained(store.directory(job_id), store.directory(job_id) / 'output' / name)
        if not path.is_file():
            raise HTTPException(404, 'El archivo de resultados ya no está disponible.')
        return FileResponse(path, filename=name, media_type=mime)

    @app.get('/api/jobs/{job_id}/evidence/{file_id}/{image}')
    def evidence(job_id: str, file_id: str, image: str):
        job = store.get(job_id)
        file = next((f for f in job['files'] if f['id'] == file_id), None)
        if not file or image not in [m['image'] for m in file.get('matches', [])]:
            raise HTTPException(404, 'Evidencia no encontrada.')
        directory = store.directory(job_id)
        path = contained(directory, directory / 'evidence' / file_id / image)
        if not path.is_file():
            raise HTTPException(404, 'Evidencia no disponible.')
        return FileResponse(path, media_type='image/png')

    static = Path(__file__).parent / 'static'
    if static.is_dir():
        app.mount('/', StaticFiles(directory=static, html=True), name='interface')
    return app
