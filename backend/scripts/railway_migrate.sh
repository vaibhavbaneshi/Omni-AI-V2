#!/bin/sh
# Apply Alembic migrations before the API accepts traffic (required on Railway deploy).
set -e
cd /app/backend

echo "[migrate] Running alembic upgrade head..."
alembic upgrade head
echo "[migrate] Database schema is at head."
