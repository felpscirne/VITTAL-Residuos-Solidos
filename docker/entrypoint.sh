#!/bin/sh
set -e

# Wait for PostgreSQL to accept TCP connections.
python - <<'PY'
import os
import socket
import time
from urllib.parse import urlparse

def env_int(name, default):
    raw = os.getenv(name)
    if raw is None:
        return default
    raw = str(raw).strip()
    if raw == "":
        return default
    return int(raw)

database_url = os.getenv('DATABASE_URL', '').strip()
parsed = urlparse(database_url) if database_url else None

host = os.getenv('DB_HOST') or (parsed.hostname if parsed else None) or 'db'
port = env_int('DB_PORT', parsed.port if parsed and parsed.port else 5432)
timeout_seconds = env_int('DB_WAIT_TIMEOUT', 60)

start = time.time()
while True:
    try:
        with socket.create_connection((host, port), timeout=2):
            break
    except OSError:
        if time.time() - start > timeout_seconds:
            raise SystemExit(f"Timeout waiting for database at {host}:{port}")
        time.sleep(1)
PY
if [ "$#" -gt 0 ]; then
  exec "$@"
fi

exec python run.py
