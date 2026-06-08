#!/bin/sh
# Railway / Docker entrypoint — migrate then start API (optionally with RQ worker).
set -e
cd /app/backend

sh /app/backend/scripts/railway_migrate.sh

if [ "${START_RQ_WORKER:-false}" = "true" ]; then
  python -m app.worker &
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
