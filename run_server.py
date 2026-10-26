"""Public single-instance entry point for Render or a Docker container."""
import os

import uvicorn

from ocr_app.app import create_app
from ocr_app.config import Settings


def main():
    settings = Settings.from_env()
    if not settings.public:
        raise ValueError('Este lanzador requiere OCR_MODE=public. Para uso local ejecuta run.py.')
    port = int(os.environ.get('PORT', '8000'))
    if not 1024 <= port <= 65535:
        raise ValueError('PORT debe estar entre 1024 y 65535.')
    app = create_app(settings=settings)
    uvicorn.run(app, host='0.0.0.0', port=port, workers=1, proxy_headers=False,
                access_log=False, log_level='warning', timeout_keep_alive=10,
                limit_concurrency=40, limit_max_requests=100000)


if __name__ == '__main__':
    main()
