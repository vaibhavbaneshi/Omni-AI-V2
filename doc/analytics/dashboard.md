# Analytics Dashboard

Phase 6 admin and user analytics powered by PostgreSQL usage tables.

## API Endpoints

| Method | Path | Access | Description |
|--------|------|--------|-------------|
| GET | `/analytics/overview?days=30` | Authenticated | User-scoped metrics |
| GET | `/analytics/platform?days=30` | Admin | Platform-wide metrics |
| GET | `/analytics/users?days=30` | Admin | User activity summary |
| GET | `/analytics/rag?days=30` | Admin | RAG upload/ingestion stats |

## Metrics

### User overview (`/analytics/overview`)

- Sessions, messages, API requests
- Total tokens, average latency, model breakdown
- Daily token time series
- Document uploads and ingestion runs

### Platform (`/analytics/platform`)

- Total users, active users (24h and period)
- Total chats, messages, tokens
- Endpoint latency breakdown (admin)
- RAG uploads and chunk counts

## Admin access

```env
ANALYTICS_ADMIN_EMAILS=admin@company.com,ops@company.com
# Falls back to EVAL_ADMIN_EMAILS if unset
```

In **development**, platform analytics are available to all authenticated users when no admin list is configured.

In **production**, platform endpoints return `403` unless the user's email is listed.

## Frontend

Dashboard at `/dashboard`:

- Live stats from `/analytics/overview`
- Recharts area chart for daily tokens
- Model mix breakdown
- Recent sessions from `/sessions`
- Admin-only endpoint latency chart when `/analytics/platform` succeeds

## Requirements

- `ENABLE_USAGE_TRACKING=true` (default)
- Migration `20260525_0003` applied
- Usage accumulates as users chat and upload documents

## Related

- [Observability](../monitoring/observability.md)
- [Implementation plan](../implementation-plan.md)
