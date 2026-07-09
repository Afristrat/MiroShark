"""
WSGI entry point for gunicorn (production, ADR-006 / US-207).

Used only by the Linux Docker image via ``gunicorn --preload wsgi:app``
(see package.json ``backend:prod``). Local developer machines (including
Windows, where gunicorn cannot run — no ``fork()``) keep using
``backend/run.py`` through ``npm run dev``.

Config.validate() runs at import time so that, combined with gunicorn's
``--preload``, a fail-closed configuration error aborts the master process
before any worker forks — mirroring run.py's boot-time validation.
"""

import sys

from app import create_app
from app.config import Config


_errors = Config.validate()
if _errors:
    print("Configuration errors:", file=sys.stderr)
    for _err in _errors:
        print(f"  - {_err}", file=sys.stderr)
    print("\nRefusing to boot with invalid configuration.", file=sys.stderr)
    sys.exit(1)

app = create_app()
