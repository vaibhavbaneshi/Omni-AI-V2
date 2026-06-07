#!/bin/sh
# Run API + RQ worker in one Railway service (shared /data volume + filesystem).
cd /app/backend

worker_supervisor() {
  while true; do
    echo "[worker-supervisor] starting ingestion worker..."
    python -m app.worker
    exit_code=$?
    echo "[worker-supervisor] worker exited with code ${exit_code} — restarting in 5s"
    sleep 5
  done
}

worker_supervisor &
echo "Starting uvicorn on 0.0.0.0:${PORT:-8000} (RQ worker supervised in background)"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
