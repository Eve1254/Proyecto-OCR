"""Private Word instance in a short-lived subprocess; never attach to user's Word."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from .config import LIMITS, PROJECT_ROOT


def convert_docx(source: Path, destination: Path, timeout=None):
    if os.name != 'nt':
        raise RuntimeError('La conversión Word requiere Windows y Microsoft Word instalado.')
    marker = destination.with_suffix('.word-process.json')
    command = [sys.executable, '-m', 'ocr_app.word_worker', str(source.resolve()),
               str(destination.resolve()), str(marker.resolve())]
    process = subprocess.Popen(command, cwd=PROJECT_ROOT, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        stdout, stderr = process.communicate(timeout=timeout or LIMITS.word_timeout)
    except subprocess.TimeoutExpired:
        # Only the PID returned by this private COM instance may be terminated.
        try:
            import psutil
            identity = json.loads(marker.read_text())
            word = psutil.Process(identity['pid'])
            if word.name().casefold() == 'winword.exe' and abs(word.create_time() - identity['created']) < .1:
                word.terminate()
        except Exception:
            pass
        process.kill()
        process.communicate()
        raise RuntimeError('Word excedió el tiempo máximo. Revisa el documento o conviértelo a PDF manualmente.')
    finally:
        marker.unlink(missing_ok=True)
    if process.returncode or not destination.is_file():
        detail = (stderr or stdout).decode('utf-8', errors='replace').strip()
        raise RuntimeError('No se pudo convertir con Word. ' + detail[-600:])


def worker(source, destination, marker):
    import ctypes
    import comtypes
    import comtypes.client
    import psutil
    word = document = None
    comtypes.CoInitialize()
    try:
        word = comtypes.client.CreateObject('Word.Application', dynamic=True)
        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(word.Hwnd, ctypes.byref(pid))
        identity = dict(pid=pid.value, created=psutil.Process(pid.value).create_time())
        Path(marker).write_text(json.dumps(identity), encoding='utf-8')
        word.Visible = False
        word.DisplayAlerts = 0
        word.AutomationSecurity = 3
        document = word.Documents.Open(FileName=source, ReadOnly=True,
                                       AddToRecentFiles=False, ConfirmConversions=False)
        document.ExportAsFixedFormat(destination, 17)
    finally:
        try:
            if document is not None:
                document.Close(0)
        finally:
            try:
                if word is not None:
                    word.Quit(0)
            finally:
                comtypes.CoUninitialize()


if __name__ == '__main__':
    try:
        worker(*sys.argv[1:])
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
