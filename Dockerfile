FROM python:3.11-slim AS backend

WORKDIR /app/backend

# build-essential only needed if a wheel is missing; prod image has no PyTorch.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend /app/backend

RUN chmod +x /app/backend/scripts/railway_web_and_worker.sh

ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

EXPOSE 8000

# Railway injects $PORT — do not hardcode 8000 in production.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
