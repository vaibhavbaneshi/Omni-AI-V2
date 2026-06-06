#!/bin/sh
# Railway / Docker entrypoint — migrate then start API (optionally with RQ worker).
set -e
cd /app/backend

python -c "from app.db.migrations import run_migrations; run_migrations()" \
  || echo "WARN: migrations failed; API may start before schema is ready"

if [ "${START_RQ_WORKER:-false}" = "true" ]; then
  python -m app.worker &
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
