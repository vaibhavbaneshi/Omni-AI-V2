# Sprint 1 Migration Plan: BackgroundTasks → Redis + RQ

## Prerequisites

1. Redis instance (local Docker, Railway Redis plugin, or Upstash)
2. Backend migration `20260601_0008` applied (`indexing_job_id` column)
3. `pip install -r requirements.txt` (adds `redis`, `rq`)

## Phase 1 — Infrastructure (no traffic impact)

1. Provision Redis and set `REDIS_URL` in staging
2. Deploy backend with new code but **`INGEST_QUEUE_ENABLED=false`**
3. Run migration: `alembic upgrade head`
4. Verify API starts and existing BackgroundTasks path still works

## Phase 2 — Worker deployment

1. Deploy worker service: `python -m app.worker`
2. Confirm worker connects to Redis (logs: `Starting ingestion worker`)
3. Smoke test: manually enqueue via staging upload with queue disabled still

## Phase 3 — Enable RQ in staging

```env
INGEST_IN_BACKGROUND=true
INGEST_QUEUE_ENABLED=true
REDIS_URL=redis://...
```

1. Upload a small `.txt` file
2. Verify logs: `[INGEST_RQ_ENQUEUED]` on API, `[INGEST_JOB_START]` on worker
3. Confirm status progresses: `queued` → `loading` → … → `ready`
4. Check metrics: `GET /admin/ingestion-queue/metrics`

## Phase 4 — Failure & retry validation

1. Upload a corrupt file → job fails → retries → DLQ → `failed` status
2. Verify `GET /admin/ingestion-queue/dlq` lists the job
3. Test requeue: `POST /admin/ingestion-queue/requeue/{job_id}`

## Phase 5 — Production cutover

1. Add Railway Redis + worker service (see deployment guide)
2. Set production env vars
3. Enable `INGEST_QUEUE_ENABLED=true`
4. Monitor queue metrics for 24h
5. Remove reliance on `--reload` for ingestion (worker is separate process)

## Phase 6 — Decommission BackgroundTasks path

After 1 week stable:

- Keep `INGEST_QUEUE_ENABLED=true` in all environments
- Document `INGEST_QUEUE_ENABLED=false` as rollback-only
- Optional: remove BackgroundTasks code path in a future cleanup PR

## Environment Variable Checklist

| Variable | Staging | Production |
|----------|---------|------------|
| `REDIS_URL` | ✓ | ✓ |
| `INGEST_QUEUE_ENABLED` | `true` | `true` |
| `INGEST_IN_BACKGROUND` | `true` | `true` |
| `INGEST_JOB_MAX_RETRIES` | `3` | `3` |
| `EVAL_ADMIN_EMAILS` | admin email | admin email |

## Data Migration

No backfill required. Documents stuck in `queued` from old BackgroundTasks:

1. Identify via stale detection (>45s at queued)
2. Re-upload or manually requeue if job id exists in failed registry

## Rollback

See `rollback-plan.md`. Quick rollback: `INGEST_QUEUE_ENABLED=false` (returns to BackgroundTasks).
