# OmniAI Deployment Guide

This guide covers local development and production (Railway-oriented) deployment for Phases A–F.

## Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL (or SQLite for local-only dev)
- Redis 7+ (required for RQ ingestion queue and optional Redis rate limits)
- LLM API key (Groq or OpenAI recommended)

---

## Local development

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env
# Edit .env — set JWT_SECRET_KEY, GROQ_API_KEY or OPENAI_API_KEY, DATABASE_URL
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 2. Redis + worker (recommended)

```bash
docker run -d --name omniai-redis -p 6379:6379 redis:7-alpine
```

In `.env`:

```env
INGEST_IN_BACKGROUND=true
INGEST_QUEUE_ENABLED=true
REDIS_URL=redis://localhost:6379/0
ENABLE_REDIS_RATE_LIMIT=true
```

Second terminal:

```bash
cd backend && python -m app.worker
```

For synchronous debugging: `INGEST_IN_BACKGROUND=false`.

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
# NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

Open `http://localhost:3000`.

---

## Environment variables (production checklist)

| Variable | Required | Notes |
|----------|----------|-------|
| `ENVIRONMENT` | Yes | `production` |
| `JWT_SECRET_KEY` | Yes | ≥32 chars, not dev default |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `GROQ_API_KEY` / `OPENAI_API_KEY` | Yes | Match `LLM_PROVIDER` |
| `CORS_ORIGINS` | Yes | Frontend origin(s), no `*` |
| `REDIS_URL` | If queue enabled | Required when `INGEST_QUEUE_ENABLED=true` |
| `EMBEDDING_PROVIDER` | Yes | Use `openai` or `huggingface` on Railway |
| `HF_TOKEN` | If HF embeddings | For HuggingFace inference |
| `SENTRY_DSN` | Optional | Backend error tracking |
| `NEXT_PUBLIC_SENTRY_DSN` | Optional | Frontend error tracking |

See `backend/.env.example` and `frontend/.env.example` for the full list.

---

## Railway production

### Services

| Service | Command | Notes |
|---------|---------|-------|
| `backend` | Dockerfile CMD or `sh /app/backend/scripts/railway_web_and_worker.sh` | API + RQ worker in one container |
| `redis` | Railway Redis plugin | Shared broker |
| `postgres` | Railway Postgres | Primary database |
| `frontend` | `npm run build && npm start` | Next.js |

**Important:** Use the bundled web+worker script so ingestion workers share upload storage and Chroma paths with the API.

### Health checks

- **Liveness:** `GET /health/live`
- **Readiness:** `GET /health/ready`
- Do not point Railway health checks at `GET /health?deep=true` — it probes DB/Chroma/LLM and may timeout.

### Migrations

Migrations run in a background thread on startup. For controlled deploys, run manually:

```bash
cd backend && alembic upgrade head
```

Recent migrations (Phases A–D):

- `20260603_0010` — document insights
- `20260604_0011` — research reports
- `20260605_0012` — chat folders, session organization

### Volumes

Mount persistent storage for:

- `CHROMA_DB_PATH` (vector index)
- Upload staging (`UPLOAD_STAGING_DIR` or default `uploads/`)

---

## Sentry (Phase F)

**Backend** — set in Railway/backend `.env`:

```env
SENTRY_DSN=https://<key>@o<org>.ingest.sentry.io/<project>
SENTRY_RELEASE=omniai@1.0.0
SENTRY_TRACES_SAMPLE_RATE=0.1
```

**Frontend** — set in Vercel/Railway frontend env:

```env
NEXT_PUBLIC_SENTRY_DSN=https://<key>@o<org>.ingest.sentry.io/<project>
NEXT_PUBLIC_SENTRY_ENVIRONMENT=production
```

Optional CI source maps: `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, `SENTRY_PROJECT`.

Sentry is a no-op when DSN is empty — safe for local dev.

---

## Embedding providers on Railway

| Provider | RAM | Recommendation |
|----------|-----|----------------|
| `openai` | Low | **Recommended** for production |
| `huggingface` | Low | Requires `HF_TOKEN` |
| `local` | ~1GB+ PyTorch | Dev only unless `ENABLE_LOCAL_ML=true` |

Set `ENABLE_RERANKER=false` on memory-constrained plans (~300MB saved).

---

## Verify deployment

```bash
curl https://<api>/health/live
curl -H "Authorization: Bearer $TOKEN" https://<api>/sessions
curl https://<api>/admin/ingestion-queue/metrics
```

Upload a test PDF in the UI and confirm `GET /documents/{id}/status` reaches `ready`.

---

## Related docs

- [Sprint 1 deployment details](./sprint1/deployment-guide.md)
- [Ingestion queue architecture](./sprint1/ingestion-queue-architecture.md)
- [Architecture](./architecture.md)
- [Security](./security.md)
