#!/bin/sh
set -e

# Wait for PostgreSQL to accept TCP connections.
python - <<'PY'
import os
import socket
import time

host = os.getenv('DB_HOST', 'db')
port = int(os.getenv('DB_PORT', '5432'))
timeout_seconds = int(os.getenv('DB_WAIT_TIMEOUT', '60'))

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

exec python run.py
