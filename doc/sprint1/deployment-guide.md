# Sprint 1 Deployment Guide: Redis + RQ Ingestion Worker

## Local Development

### 1. Start Redis

```bash
docker run -d --name omniai-redis -p 6379:6379 redis:7-alpine
```

### 2. Configure `.env`

```env
INGEST_IN_BACKGROUND=true
INGEST_QUEUE_ENABLED=true
REDIS_URL=redis://localhost:6379/0
INGEST_JOB_MAX_RETRIES=3
INGEST_JOB_RETRY_INTERVALS=30,60,120
EVAL_ADMIN_EMAILS=your@email.com
```

For sync debugging (no worker):

```env
INGEST_IN_BACKGROUND=false
# or
INGEST_QUEUE_ENABLED=false
```

### 3. Install dependencies

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
```

### 4. Run API + Worker (two terminals)

```bash
# Terminal 1 — API
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Worker
python -m app.worker
```

### 5. Verify

```bash
# Upload via UI or curl, then:
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/admin/ingestion-queue/metrics
```

---

## Railway Production

### Services

| Service | Command | Notes |
|---------|---------|-------|
| `backend` | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` | Existing API |
| `ingest-worker` | `python -m app.worker` | **New** — same repo, different start command |
| `redis` | Railway Redis plugin | Shared broker |

### Environment Variables (both API + worker)

```env
INGEST_IN_BACKGROUND=true
INGEST_QUEUE_ENABLED=true
REDIS_URL=${{Redis.REDIS_URL}}
INGEST_JOB_MAX_RETRIES=3
EMBEDDING_PROVIDER=huggingface
HF_TOKEN=<token>
CHROMA_DB_PATH=/data/chroma_db
DATABASE_URL=${{Postgres.DATABASE_URL}}
EVAL_ADMIN_EMAILS=ops@yourcompany.com
```

Mount volume at `/data` on **both** services if worker needs Chroma access (same path as API).

### Worker Dockerfile (optional)

If using a single Dockerfile, override start command in Railway:

- API: default `uvicorn` CMD
- Worker: `python -m app.worker`

### Health Checks

- **API:** `GET /health`
- **Worker:** no HTTP port — monitor via:
  - Railway logs (`Starting ingestion worker`)
  - `GET /admin/ingestion-queue/metrics` on API
  - Alert if `queue_length` > threshold for > 5 min

### Scaling

| Load | Recommendation |
|------|----------------|
| Low (<10 uploads/min) | 1 worker |
| Medium | 2–3 workers (RQ is fork-based; one job per worker process) |
| High | Horizontal worker replicas + Redis |

Do **not** scale API replicas for ingestion — scale workers.

---

## Monitoring Checklist

Daily / on-call:

- [ ] `queue_length` < 50
- [ ] `failed_jobs` not increasing
- [ ] `dlq_length` reviewed
- [ ] Worker logs show `[INGEST_JOB_COMPLETE]`
- [ ] No documents stuck at `queued` > 45s

### Metrics Response Example

```json
{
  "enabled": true,
  "queue_name": "ingest",
  "dlq_name": "ingest-dlq",
  "queue_length": 2,
  "dlq_length": 0,
  "active_jobs": 1,
  "failed_jobs": 0,
  "completed_jobs": 142,
  "deferred_jobs": 0,
  "scheduled_jobs": 0
}
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Upload stuck at `queued` | Worker not running → start `python -m app.worker` |
| `REDIS_URL must be set` in prod | Add Redis plugin + env var |
| Jobs in DLQ | Check `failure_reason`; fix root cause; requeue |
| Chroma not found in worker | Share `/data` volume or same `CHROMA_DB_PATH` |
| HF embedding timeout | See embedding docs; worker has 30min job timeout |

---

## Security

- Redis should not be public; use Railway private networking
- Admin queue endpoints require `EVAL_ADMIN_EMAILS`
- Do not expose worker process to HTTP
