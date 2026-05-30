# Observability & Monitoring

OmniAI uses a layered observability stack: HTTP middleware, structured spans, PostgreSQL analytics tables, and optional LangSmith.

## Architecture

```
Request → TraceMiddleware → FastAPI route
                ↓                    ↓
           api_usage table     traced_span / llm_invoke
                ↓                    ↓
           X-Trace-Id header    model_usage + token_usage
                                       ↓
                              LangSmith (optional)
```

## Response headers

Every HTTP response includes:

| Header | Description |
|--------|-------------|
| `X-Trace-Id` | UUID for correlating logs, DB rows, and LangSmith |
| `X-Response-Time-Ms` | End-to-end request duration |

## PostgreSQL analytics tables

Migration: `20260525_0003_analytics_tables`

### `api_usage`

Records every HTTP request (except health/docs when tracked):

- `method`, `path`, `status_code`, `duration_ms`
- `user_id`, `username` (from JWT when present)
- `trace_id`, `created_at`

### `model_usage`

Records LLM and ingestion operations:

- `provider`, `model`, `endpoint`
- `latency_ms`, `success`, `error_message`
- `user_id`, `session_id`, `trace_id`

### `token_usage`

Linked to `model_usage`:

- `prompt_tokens`, `completion_tokens`, `total_tokens`
- `prompt_chars`, `completion_chars` (always captured)
- Token counts from Groq/OpenAI when available; otherwise estimated (`chars / 4`)

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_USAGE_TRACKING` | `true` | Write metrics to PostgreSQL |
| `LANGCHAIN_TRACING_V2` | `false` | Enable LangSmith |
| `LANGCHAIN_API_KEY` | — | LangSmith API key |
| `LANGCHAIN_PROJECT` | `OmniAI` | LangSmith project name |

Set `ENABLE_USAGE_TRACKING=false` if the analytics tables are not migrated yet — the app continues to work; only DB writes are skipped.

## Structured logs

Logger: `omni.telemetry` and `omni.http`

Example `llm.complete` event:

```json
{
  "event": "llm.complete",
  "trace_id": "abc-123",
  "provider": "groq",
  "model": "llama-3.3-70b-versatile",
  "endpoint": "rag.stream",
  "latency_ms": 842.15,
  "prompt_chars": 4200,
  "completion_chars": 512,
  "prompt_tokens": 1050,
  "completion_tokens": 128,
  "total_tokens": 1178,
  "success": true
}
```

Logs are written to `backend/logs/backend.log` (rotating) and stdout.

## Health checks

- `GET /health` — liveness
- `GET /health?deep=true` — Postgres, Chroma, LLM provider probes

## Querying metrics (SQL examples)

```sql
-- Average chat stream latency (approximate via api_usage)
SELECT path, AVG(duration_ms) AS avg_ms, COUNT(*) AS requests
FROM api_usage
WHERE path = '/chat-stream'
GROUP BY path;

-- Token usage by model (last 24h)
SELECT model, SUM(total_tokens) AS tokens
FROM token_usage
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY model;

-- Upload ingestion success rate
SELECT success, COUNT(*)
FROM model_usage
WHERE endpoint = 'document.ingest'
GROUP BY success;
```

## Phase 6 dashboard

These tables feed the upcoming analytics dashboard (`GET /analytics/overview`). See `doc/implementation-plan.md`.

## Related docs

- [LangSmith setup](./langsmith-setup.md)
- [Implementation plan](../implementation-plan.md)
