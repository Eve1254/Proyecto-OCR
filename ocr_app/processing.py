import re
import threading
import uuid
import zipfile
from pathlib import Path

from .config import LIMITS
from .recognition import inspect_pdf, load_reference
from .reports import write_report
from .storage import JobStore, contained, now, unique_path
from .word_worker import convert_docx


class Cancelled(Exception):
    pass


def file_record(path: Path, directory: Path, relative: str, group: str, original=True):
    return dict(id=uuid.uuid4().hex, path=path.relative_to(directory).as_posix(), relative=relative,
                group=group, kind=path.suffix.lower()[1:], size=path.stat().st_size,
                original=original, state='pending', message='', matches=[])


def attachment_name(name, index):
    basename = str(name or f'adjunto-{index}.pdf').replace('\\', '/').split('/')[-1]
    basename = re.sub(r'[<>:"|?*\x00-\x1f]', '_', basename).strip(' .')
    stem = Path(basename).stem[:65] or 'adjunto'
    # Prefix avoids reserved device names while retaining an understandable filename.
    return f'adjunto-{index}-{stem}.pdf'


def run_pipeline(store: JobStore, job_id: str, cancelled: threading.Event):
    job = store.get(job_id)
    directory = store.directory(job_id)
    options = job['options']

    def checkpoint():
        if cancelled.is_set():
            raise Cancelled()

    def stage(name, done=0, total=0):
        checkpoint()
        job['stage'] = name
        job['progress'] = dict(done=done, total=total)
        store.save(job)

    def problem(file, message):
        file.update(state='review', message=str(message)[:1500])
        job['errors'].append(dict(file=file['relative'], message=file['message']))

    def register(path, parent):
        if path.stat().st_size > LIMITS.file_bytes or sum(f['size'] for f in job['files']) + path.stat().st_size > LIMITS.job_bytes:
            path.unlink(missing_ok=True)
            raise ValueError('Los archivos generados superan el límite de tamaño del trabajo.')
        if len(job['files']) >= 2000:
            path.unlink(missing_ok=True)
            raise ValueError('Se alcanzó el límite de archivos generados.')
        relative = path.relative_to(directory / 'derived').as_posix()
        record = file_record(path, directory, relative, parent['group'], original=False)
        job['files'].append(record)

    try:
        checkpoint()
        job.update(status='running', started=now())
        originals = list(job['files'])
        for index, file in enumerate(originals):
            stage('Preparando documentos', index, len(originals))
            path = contained(directory, directory / file['path'])
            if file['kind'] == 'pdf':
                continue
            enabled = options.get('extract') if file['kind'] == 'msg' else options.get('convert')
            if not enabled:
                problem(file, 'Preparación desactivada: este documento queda pendiente de evaluar.')
                continue
            try:
                relative_parent = Path(file['relative']).parent
                if file['kind'] == 'docx':
                    target = unique_path(directory / 'derived', relative_parent / (Path(file['relative']).stem + '.pdf'))
                    convert_docx(path, target)
                    register(target, file)
                    file.update(state='processed', message='Convertido a PDF.')
                else:
                    import extract_msg
                    message = extract_msg.Message(str(path))
                    extracted = 0
                    try:
                        for number, attachment in enumerate(message.attachments, start=1):
                            checkpoint()
                            name = attachment.longFilename or attachment.shortFilename or ''
                            if not str(name).lower().endswith('.pdf'):
                                continue
                            data = attachment.data
                            if not isinstance(data, bytes) or len(data) > LIMITS.file_bytes:
                                raise ValueError('Adjunto PDF no compatible o demasiado grande.')
                            folder = relative_parent / (Path(file['relative']).stem[:50] + '_adjuntos')
                            target = unique_path(directory / 'derived', folder / attachment_name(name, number))
                            target.write_bytes(data)
                            register(target, file)
                            extracted += 1
                    finally:
                        message.close()
                    file.update(state='processed', message=f'{extracted} adjuntos PDF extraídos.')
            except Cancelled:
                raise
            except Exception as error:
                problem(file, error)
            store.save(job)
        reference = load_reference(directory / job['reference']) if options.get('recognize') else None
        pdfs = [file for file in job['files'] if file['kind'] == 'pdf']
        for index, file in enumerate(pdfs):
            stage('Reconociendo logotipo' if reference is not None else 'Organizando archivos', index, len(pdfs))
            if reference is not None:
                result = inspect_pdf(contained(directory, directory / file['path']), reference, directory / 'evidence' / file['id'])
                file.update(result)
                if result['state'] == 'review':
                    job['errors'].append(dict(file=file['relative'], message=result['message']))
            else:
                file.update(state='unclassified', message='Reconocimiento desactivado.')
            job['progress']['done'] = index + 1
            store.save(job)
        stage('Organizando resultados')
        job['groups'] = []
        for name in dict.fromkeys(f['group'] for f in job['files']):
            files = [f for f in job['files'] if f['group'] == name]
            pdfs = [f for f in files if f['kind'] == 'pdf']
            if not options.get('classify'):
                state = 'unclassified'
            elif any(f['state'] in {'review', 'pending'} for f in files) or not pdfs:
                state = 'review'
            elif any(f['state'] == 'match' for f in pdfs):
                state = 'match'
            else:
                state = 'no_match'
            job['groups'].append(dict(name=name, state=state))
        if options.get('report', True):
            write_report(job, directory)
            job['artifacts'].append('excel')
        stage('Creando paquete de resultados')
        categories = {'review': 'Revisar', 'match': 'Con logotipo', 'no_match': 'Sin coincidencia', 'unclassified': 'Sin clasificar'}
        groups = {g['name']: categories[g['state']] for g in job['groups']}
        target = directory / 'output/resultados.zip'
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
            for file in job['files']:
                checkpoint()
                origin = 'Originales' if file['original'] else 'Generados'
                arcname = f"{groups[file['group']]}/{origin}/{file['relative']}"
                archive.write(contained(directory, directory / file['path']), arcname)
            if options.get('evidence', True):
                for file in job['files']:
                    for match in file.get('matches', []):
                        path = directory / 'evidence' / file['id'] / match['image']
                        archive.write(path, f"Evidencias/{file['id']}/{match['image']}")
            if 'excel' in job['artifacts']:
                archive.write(directory / 'output/reporte.xlsx', 'reporte.xlsx')
            archive.writestr('LEEME.txt', 'Clasificación sugerida por coincidencia de logotipo.\nNo valida firmas ni extrae texto.\nLos archivos originales se conservan sin modificaciones.\n')
        job['artifacts'].append('zip')
        job.update(status='completed_with_errors' if job['errors'] else 'completed', stage='Proceso finalizado')
        job['logs'].append(f"Finalizado: {len(job['files'])} archivos y {len(job['errors'])} incidencias.")
    except Cancelled:
        job.update(status='cancelled', stage='Cancelado; los originales se conservan')
        job['logs'].append('Cancelado por la persona usuaria.')
    except Exception as error:
        job.update(status='failed', stage='El proceso no pudo finalizar')
        job['errors'].append(dict(file='Trabajo', message=str(error)[:1500]))
    finally:
        if job['status'] not in {'completed', 'completed_with_errors'}:
            job['artifacts'] = []
            for filename in ('resultados.zip', 'reporte.xlsx'):
                (directory / 'output' / filename).unlink(missing_ok=True)
        job['finished'] = now()
        store.save(job)
