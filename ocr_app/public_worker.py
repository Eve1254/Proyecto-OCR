"""One disposable document worker; receives no browser-session secret."""
import os
import sys
import threading

from .config import Settings
from .storage import JobStore


def main():
    if os.name == 'posix':
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (180, 180))
        resource.setrlimit(resource.RLIMIT_FSIZE, (96 * 1024**2, 96 * 1024**2))
    from .processing import run_pipeline
    store = JobStore(sys.argv[1], limits=Settings(public=True).limits(), recover=False)
    run_pipeline(store, sys.argv[2], threading.Event())


if __name__ == '__main__':
    main()
