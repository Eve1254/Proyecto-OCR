"""Job-scoped paths and atomic JSON persistence; no original files are modified."""
import json
import re
import shutil
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

RESERVED = re.compile(r'^(CON|PRN|AUX|NUL|COM[0-9¹²³]|LPT[0-9¹²³])(?:\.|$)', re.I)


def now():
    return datetime.now(timezone.utc).isoformat()


def group_key(file: dict) -> str:
    return file.get('group_key', 'folder:' + file['group'].casefold())


def safe_relative(name: str) -> Path:
    if not name or len(name) > 180 or name.startswith('/') or '\\' in name:
        raise ValueError('La ruta del archivo no es válida o es demasiado larga.')
    parts = name.split('/')
    for part in parts:
        if (not part or part in {'.', '..'} or part[-1:] in {' ', '.'}
                or len(part) > 100 or RESERVED.match(part)
                or any(ord(c) < 32 or c in '<>:"|?*' for c in part)):
            raise ValueError('Nombre de archivo no permitido: ' + name)
    return Path(*parts)


def contained(root: Path, candidate: Path) -> Path:
    root = root.resolve()
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root) or resolved == root:
        raise ValueError('La ruta debe permanecer dentro del trabajo.')
    relative = candidate.absolute().relative_to(root)
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink() or (hasattr(current, 'is_junction') and current.is_junction()):
            raise ValueError('No se permiten enlaces en los archivos del trabajo.')
    return resolved


def unique_path(root: Path, relative: Path) -> Path:
    relative = safe_relative(relative.as_posix())
    candidate = contained(root, root / relative)
    candidate.parent.mkdir(parents=True, exist_ok=True)
    existing = {p.name.casefold() for p in candidate.parent.iterdir()}
    number = 2
    base = candidate
    while candidate.name.casefold() in existing:
        candidate = base.with_name(f'{base.stem}_{number}{base.suffix}')
        number += 1
    return candidate


class JobStore:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        for job in self.list():
            if job['status'] in {'running', 'cancelling', 'uploading', 'preparing'}:
                job.update(status='interrupted', stage='Interrumpido por cierre de la aplicación')
                job['logs'].append('El trabajo se interrumpió. Crea uno nuevo para repetir el proceso.')
                self.save(job)

    def directory(self, job_id: str) -> Path:
        if not re.fullmatch(r'[a-f0-9]{32}', job_id):
            raise ValueError('Identificador de trabajo no válido.')
        return contained(self.root, self.root / job_id)

    def create(self, options: dict, demo=False, status='ready') -> dict:
        job = dict(id=uuid.uuid4().hex, created=now(), status=status, stage='Preparado',
                   demo=demo, options=options, files=[], groups=[], errors=[], logs=[],
                   progress={'done': 0, 'total': 0}, reference=None, artifacts=[],
                   name='Demostración' if demo else 'Mis documentos')
        directory = self.directory(job['id'])
        for child in ('input', 'derived', 'evidence', 'output'):
            (directory / child).mkdir(parents=True, exist_ok=True)
        self.save(job)
        return job

    def save(self, job: dict):
        with self.lock:
            directory = self.directory(job['id'])
            target = directory / 'job.json'
            temporary = directory / ('state-' + uuid.uuid4().hex + '.tmp')
            temporary.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding='utf-8')
            temporary.replace(target)

    def get(self, job_id: str) -> dict:
        with self.lock:
            path = self.directory(job_id) / 'job.json'
            if not path.is_file():
                raise KeyError('No se encontró el trabajo.')
            return json.loads(path.read_text(encoding='utf-8'))

    def list(self) -> list[dict]:
        with self.lock:
            jobs = []
            for path in self.root.iterdir():
                if re.fullmatch('[a-f0-9]{32}', path.name):
                    try:
                        jobs.append(self.get(path.name))
                    except (ValueError, KeyError, OSError):
                        continue
            return sorted(jobs, key=lambda job: job['created'], reverse=True)

    def delete(self, job_id: str):
        with self.lock:
            directory = self.directory(job_id)
            if directory.is_dir():
                shutil.rmtree(directory)
