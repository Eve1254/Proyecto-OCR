"""OS-level lock to keep two launchers from processing the same history."""
import os
from pathlib import Path


class InstanceLock:
    def __init__(self, path: Path):
        self.path = path
        self.handle = None

    def acquire(self, port: int) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open('a+b')
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b' ')
            handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            return False
        self.handle = handle
        # The first byte remains locked; the port is readable after it.
        handle.seek(1)
        handle.truncate()
        handle.write(str(port).encode('ascii'))
        handle.flush()
        return True

    def port(self):
        try:
            with self.path.open('rb') as handle:
                handle.seek(1)
                return int(handle.read().decode('ascii'))
        except (OSError, ValueError):
            return None

    def release(self):
        if self.handle is not None:
            self.handle.close()
            self.handle = None
