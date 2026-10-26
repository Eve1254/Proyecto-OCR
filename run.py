"""Start the app on loopback; a free local port is chosen when the default is busy."""
import argparse
import socket
import threading
import urllib.error
import urllib.request
import webbrowser

import uvicorn

from ocr_app.app import create_app
from ocr_app.config import DATA_ROOT
from ocr_app.runtime import InstanceLock


def available_port(preferred):
    for port in range(preferred, preferred + 20):
        with socket.socket() as probe:
            try:
                probe.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    raise RuntimeError('No hay un puerto local disponible. Cierra otra instancia de Proyecto OCR.')


def main():
    parser = argparse.ArgumentParser(description='Proyecto OCR local')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    if not 1024 <= args.port <= 65000:
        parser.error('El puerto debe estar entre 1024 y 65000.')
    port = available_port(args.port)
    lock = InstanceLock(DATA_ROOT.parent / 'instance.lock')
    if not lock.acquire(port):
        existing = lock.port()
        print('Proyecto OCR ya está abierto. Usa la ventana existente.', flush=True)
        if existing and not args.no_browser:
            webbrowser.open(f'http://127.0.0.1:{existing}')
        return
    url = f'http://127.0.0.1:{port}'
    app = create_app()
    if not args.no_browser:
        def open_when_ready():
            for _ in range(40):
                try:
                    with urllib.request.urlopen(url+'/api/health', timeout=1):
                        webbrowser.open(url)
                        return
                except (urllib.error.URLError, OSError):
                    threading.Event().wait(.25)
        threading.Thread(target=open_when_ready, daemon=True).start()
    print('\nProyecto OCR: '+url+'\nConserva esta ventana abierta. Para cerrar la aplicación, pulsa Ctrl+C.\n', flush=True)
    try:
        uvicorn.run(app, host='127.0.0.1', port=port, log_level='warning')
    finally:
        lock.release()


if __name__ == '__main__':
    main()
