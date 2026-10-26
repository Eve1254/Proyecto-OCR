"""Anonymous browser ownership and bounded, expiring storage for the public pilot."""
import hashlib
import hmac
import re
import secrets
import shutil
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

COOKIE = '__Host-ocr_session'


class AccessPolicy:
    def __init__(self, store, settings):
        self.store, self.settings = store, settings
        self.lock = threading.RLock()
        self.events = defaultdict(deque)
        self.global_events = deque()

    def signature(self, identity):
        return hmac.new(self.settings.secret.encode(), ('ocr-browser:' + identity).encode(), hashlib.sha256).hexdigest()

    def read_cookie(self, request):
        value = request.cookies.get(COOKIE, '')
        if not re.fullmatch(r'[a-f0-9]{64}\.[a-f0-9]{64}', value):
            return None
        identity, signature = value.split('.')
        return identity if hmac.compare_digest(signature, self.signature(identity)) else None

    def session(self, request, response):
        if self.settings.public:
            identity = self.read_cookie(request) or secrets.token_hex(32)
            response.set_cookie(COOKIE, identity + '.' + self.signature(identity),
                                httponly=True, secure=True, samesite='strict', path='/')
        return {'local': not self.settings.public,
                'retention_seconds': self.settings.retention_seconds if self.settings.public else None}

    def owner(self, request):
        if not self.settings.public:
            return None
        identity = self.read_cookie(request)
        if identity is None:
            raise HTTPException(401, 'La sesión no está disponible. Recarga la página para iniciar una nueva.')
        return identity

    def expiration(self, job):
        return datetime.fromisoformat(job['created']) + timedelta(seconds=self.settings.retention_seconds)

    def expired(self, job):
        return self.settings.public and self.expiration(job) <= datetime.now(timezone.utc)

    def visible(self, job, owner):
        return not self.settings.public or (job.get('owner') == owner and not self.expired(job))

    def get(self, job_id, owner):
        try:
            job = self.store.get(job_id)
        except (KeyError, ValueError):
            raise HTTPException(404, 'No se encontró el trabajo.')
        if not self.visible(job, owner):
            raise HTTPException(404, 'No se encontró el trabajo o ya expiró.')
        return job

    def present(self, job):
        result = {key: value for key, value in job.items() if key != 'owner'}
        if self.settings.public:
            result['expires_at'] = self.expiration(job).isoformat()
        return result

    def create(self, options, owner, *, demo=False, status='ready'):
        with self.lock:
            if self.settings.public:
                jobs = self.store.list()
                if sum(j.get('owner') == owner for j in jobs) >= 3:
                    raise HTTPException(429, 'Ya tienes 3 trabajos guardados. Borra uno antes de crear otro.')
                if len(jobs) >= 12 or shutil.disk_usage(self.store.root).free < 256 * 1024**2:
                    raise HTTPException(429, 'El espacio del piloto está ocupado. Inténtalo más tarde.')
                current = time.monotonic()
                for key in list(self.events):
                    while self.events[key] and current - self.events[key][0] >= 3600:
                        self.events[key].popleft()
                    if not self.events[key]:
                        del self.events[key]
                while self.global_events and current - self.global_events[0] >= 3600:
                    self.global_events.popleft()
                if len(self.global_events) >= 30 or len(self.events.get(owner, [])) >= 6:
                    raise HTTPException(429, 'Se alcanzó el límite de pruebas por hora. Inténtalo más tarde.')
                self.events[owner].append(current)
                self.global_events.append(current)
            return self.store.create(options, demo=demo, status=status, owner=owner)

    def cleanup(self, manager):
        if not self.settings.public:
            return
        for job in self.store.list():
            if job.get('owner') and self.expired(job):
                try:
                    if job['status'] in {'running', 'queued'}:
                        manager.cancel(job['id'])
                    else:
                        manager.delete(job['id'])
                except (ValueError, KeyError):
                    # Preparation and cancellation finish before their next cleanup pass.
                    continue
