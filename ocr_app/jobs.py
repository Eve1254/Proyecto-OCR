import threading
from concurrent.futures import ThreadPoolExecutor

from .processing import run_pipeline


class BusyError(ValueError):
    pass


class JobManager:
    def __init__(self, store):
        self.store = store
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='ocr')
        self.active = None
        self.cancelled = threading.Event()

    def start(self, job_id):
        with self.lock:
            if self.active is not None:
                raise BusyError('Ya hay un trabajo en curso. Espera a que termine o cancélalo.')
            job = self.store.get(job_id)
            if job['status'] != 'ready':
                raise BusyError('Este trabajo ya se ejecutó. Carga los archivos en un trabajo nuevo.')
            self.active = job_id
            self.cancelled = threading.Event()
            job.update(status='running', stage='Iniciando proceso')
            self.store.save(job)
            self.executor.submit(self._run, job_id, self.cancelled)
            return job

    def _run(self, job_id, cancelled):
        try:
            run_pipeline(self.store, job_id, cancelled)
        finally:
            with self.lock:
                if self.active == job_id:
                    self.active = None

    def cancel(self, job_id):
        with self.lock:
            self.store.get(job_id)
            if self.active != job_id:
                raise BusyError('Este trabajo no está en ejecución.')
            self.cancelled.set()

    def delete(self, job_id):
        with self.lock:
            if self.active == job_id:
                raise BusyError('Espera a que termine la cancelación antes de borrar el trabajo.')
            self.store.get(job_id)
            self.store.delete(job_id)

    def close(self):
        self.cancelled.set()
        self.executor.shutdown(wait=True)
