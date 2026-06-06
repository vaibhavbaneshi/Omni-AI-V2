#!/bin/sh
# Run API + RQ worker in one Railway service (shared /data volume + filesystem).
set -e
cd /app/backend
python -m app.worker &
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
