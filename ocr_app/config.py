import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Limits:
    files: int = 500
    file_bytes: int = 50 * 1024 * 1024
    job_bytes: int = 500 * 1024 * 1024
    reference_bytes: int = 10 * 1024 * 1024
    image_pixels: int = 25_000_000
    word_timeout: int = 90
    pages: int = 300
    images: int = 1500
    generated_files: int = 2000


LIMITS = Limits()
DATA_ROOT = Path(os.environ.get('OCR_DATA_DIR', PROJECT_ROOT / 'data' / 'jobs'))
SUPPORTED = {'.pdf', '.docx', '.msg'}
TERMINAL = {'completed', 'completed_with_errors', 'cancelled', 'failed', 'interrupted'}


@dataclass
class Settings:
    public: bool = False
    origin: str = ''
    secret: str = ''
    preview: bool = False
    retention_seconds: int = 3600
    job_seconds: int = 180
    worker_memory_bytes: int = 340 * 1024**2
    job_storage_bytes: int = 96 * 1024**2
    upload_total_seconds: float = 30
    upload_idle_seconds: float = 10

    @classmethod
    def from_env(cls):
        mode = os.environ.get('OCR_MODE', 'local')
        if mode not in {'local', 'public'}:
            raise ValueError('OCR_MODE debe ser local o public.')
        if mode == 'local':
            return cls()
        origin = os.environ.get('OCR_PUBLIC_ORIGIN', '')
        if not origin and os.environ.get('RENDER_EXTERNAL_HOSTNAME'):
            origin = 'https://' + os.environ['RENDER_EXTERNAL_HOSTNAME']
        secret = os.environ.get('OCR_SESSION_SECRET', '')
        preview = os.environ.get('OCR_PUBLIC_PREVIEW') == '1'
        parsed = urlsplit(origin)
        local_preview = preview and parsed.scheme == 'http' and parsed.hostname in {'127.0.0.1', 'localhost'}
        if (not parsed.hostname or (parsed.scheme != 'https' and not local_preview)
                or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password
                or any(c.isspace() for c in origin) or len(secret) < 32):
            raise ValueError('El modo público requiere un origen HTTPS válido y un secreto de al menos 32 caracteres.')
        _ = parsed.port
        return cls(public=True, origin=origin, secret=secret, preview=local_preview)

    def limits(self):
        if not self.public:
            return LIMITS
        return Limits(files=20, file_bytes=10 * 1024**2, job_bytes=30 * 1024**2,
                      reference_bytes=2 * 1024**2, image_pixels=6_000_000,
                      word_timeout=60, pages=50, images=150, generated_files=200)
