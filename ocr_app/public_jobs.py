"""A small shared queue with bounded, cancellable subprocesses for public documents."""
import os
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import psutil

from .config import PROJECT_ROOT
from .conversion import terminate_tree
from .jobs import BusyError
from .storage import now


class PublicJobManager:
    def __init__(self, store, settings):
        self.store, self.settings = store, settings
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='public-ocr')
        self.pending = []
        self.active = None
        self.cancelled = threading.Event()
        self.closing = False

    def start(self, job_id):
        with self.lock:
            job = self.store.get(job_id)
            if self.closing or job['status'] != 'ready':
                raise BusyError('Este trabajo ya se inició. Crea uno nuevo para repetirlo.')
            if len(self.pending) >= 4:
                raise BusyError('La cola del piloto está llena. Espera unos minutos e inténtalo de nuevo.')
            job.update(status='queued', stage='En espera de un turno de procesamiento')
            self.store.save(job)
            self.pending.append(job_id)
            self.executor.submit(self._run, job_id)
            return job

    def _run(self, job_id):
        with self.lock:
            if job_id not in self.pending:
                return
            self.pending.remove(job_id)
            job = self.store.get(job_id)
            if self.closing or job['status'] != 'queued':
                return
            self.active = job_id
            self.cancelled = threading.Event()
            job.update(status='running', stage='Iniciando procesamiento')
            self.store.save(job)
        process = None
        reason = None
        try:
            env = {key: value for key, value in os.environ.items()
                   if key.upper() in {'PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'TMPDIR', 'HOME', 'LANG', 'LC_ALL'}}
            env.update(PYTHONIOENCODING='utf-8', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
            command = [sys.executable, '-m', 'ocr_app.public_worker', str(self.store.root), job_id]
            process = subprocess.Popen(command, cwd=PROJECT_ROOT, env=env, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            started = time.monotonic()
            while process.poll() is None:
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(job['created'])).total_seconds()
                if self.cancelled.is_set() or age >= self.settings.retention_seconds:
                    reason = 'Cancelado por solicitud o por caducidad del trabajo.'
                    break
                if time.monotonic() - started > self.settings.job_seconds:
                    reason = 'El documento excedió el tiempo máximo del piloto. Prueba con un lote más pequeño.'
                    break
                try:
                    root = psutil.Process(process.pid)
                    processes = [root] + root.children(recursive=True)
                    memory = 0
                    for child in processes:
                        try:
                            memory += child.memory_info().rss
                        except psutil.Error:
                            pass
                    if memory > self.settings.worker_memory_bytes:
                        reason = 'El lote excedió la memoria disponible del piloto. Usa documentos más pequeños.'
                        break
                except psutil.NoSuchProcess:
                    pass
                size = 0
                for path in self.store.directory(job_id).rglob('*'):
                    try:
                        if path.is_file():
                            size += path.stat().st_size
                    except FileNotFoundError:
                        # The worker atomically replaces job.json and removes its scratch files.
                        continue
                if size > self.settings.job_storage_bytes:
                    reason = 'Los resultados excedieron el espacio disponible para este trabajo.'
                    break
                self.cancelled.wait(.1)
            if reason:
                terminate_tree(process)
            elif process.returncode:
                reason = 'El proceso terminó antes de completar el lote. Prueba con un archivo más pequeño.'
        except Exception:
            reason = 'No se pudo completar el proceso en el servidor. Inténtalo con un lote más pequeño.'
        finally:
            if process is not None and process.poll() is None:
                terminate_tree(process)
            with self.lock:
                job = self.store.get(job_id)
                if reason or job['status'] in {'queued', 'running'}:
                    for name in ('derived', 'evidence', 'output'):
                        target = self.store.directory(job_id) / name
                        shutil.rmtree(target, ignore_errors=True)
                        target.mkdir(exist_ok=True)
                    job.update(status='cancelled' if reason and reason.startswith('Cancelado') else 'failed',
                               stage='Procesamiento detenido', artifacts=[], finished=now())
                    job['errors'].append({'file': 'Trabajo', 'message': reason or 'El proceso no produjo resultados.'})
                    self.store.save(job)
                self.active = None

    def cancel(self, job_id):
        with self.lock:
            job = self.store.get(job_id)
            if job_id in self.pending:
                self.pending.remove(job_id)
                job.update(status='cancelled', stage='Cancelado antes de iniciar', finished=now())
                self.store.save(job)
            elif self.active == job_id:
                self.cancelled.set()
            else:
                raise BusyError('Este trabajo no está en ejecución ni en espera.')

    def delete(self, job_id):
        with self.lock:
            job = self.store.get(job_id)
            if self.active == job_id or job_id in self.pending or job['status'] in {'preparing', 'uploading'}:
                raise BusyError('Espera a que termine la cancelación antes de borrar el trabajo.')
            self.store.delete(job_id)

    def close(self):
        with self.lock:
            self.closing = True
            for job_id in list(self.pending):
                self.cancel(job_id)
            self.cancelled.set()
        self.executor.shutdown(wait=True)
