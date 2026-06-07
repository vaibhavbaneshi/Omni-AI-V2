#!/bin/sh
# Run API + RQ worker in one Railway service (shared /data volume + filesystem).
set -e
cd /app/backend
echo "Starting RQ ingestion worker + uvicorn on 0.0.0.0:${PORT:-8000}"
python -m app.worker &
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
