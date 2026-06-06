# Sprint 1 Rollback Plan

## Trigger Conditions

- Redis unavailable / persistent connection failures
- Worker not processing jobs (queue length growing unbounded)
- DLQ spike indicating systemic ingestion failures
- Critical production incident tied to RQ deployment

## Immediate Rollback (< 5 minutes)

Set in Railway / `.env`:

```env
INGEST_QUEUE_ENABLED=false
INGEST_IN_BACKGROUND=true
```

Redeploy **API only** (worker can stay running; it will idle).

**Effect:** Uploads return to in-process FastAPI BackgroundTasks (pre-Sprint-1 behavior).

**Caveats:**

- Jobs lost on API restart (same as before Sprint 1)
- Do not use `uvicorn --reload` in production
- Documents already in Redis queue will remain until worker drains or jobs expire

## Full Rollback (drain queue)

1. Set `INGEST_QUEUE_ENABLED=false` on API
2. Keep worker running until `queue_length=0` (check metrics endpoint)
3. Stop worker service
4. Optional: flush Redis ingest keys (only if no other services use same Redis DB)

## Stuck Documents

Documents in `queued` with no worker:

| Symptom | Action |
|---------|--------|
| `queued` > 45s | Start worker OR set sync mode temporarily |
| `failed` with retry message | `POST /admin/ingestion-queue/requeue/{job_id}` |
| No job_id on record | Re-upload file |

## Temporary Sync Mode (local debug)

```env
INGEST_IN_BACKGROUND=false
```

Upload blocks until indexing completes; errors return immediately in HTTP response.

## Code Rollback (git)

If code defects require revert:

```bash
git revert <sprint-1-merge-commit>
```

Migration `20260601_0008` adds nullable `indexing_job_id` — safe to leave in place after revert.

## Recovery After Rollback

1. Root-cause Redis/worker issue
2. Re-enable in staging first: `INGEST_QUEUE_ENABLED=true`
3. Validate metrics + upload E2E before production

## What NOT to roll back

- `indexing_stage` progress columns (frontend depends on these)
- HuggingFace router migration (separate from queue)
- Status polling endpoints
