import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Limits:
    files: int = 500
    file_bytes: int = 50 * 1024 * 1024
    job_bytes: int = 500 * 1024 * 1024
    reference_bytes: int = 10 * 1024 * 1024
    image_pixels: int = 25_000_000
    word_timeout: int = 90


LIMITS = Limits()
DATA_ROOT = Path(os.environ.get('OCR_DATA_DIR', PROJECT_ROOT / 'data' / 'jobs'))
SUPPORTED = {'.pdf', '.docx', '.msg'}
TERMINAL = {'completed', 'completed_with_errors', 'cancelled', 'failed', 'interrupted'}
