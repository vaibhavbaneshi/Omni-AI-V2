# Deployment Guide

## Prerequisites

- PostgreSQL 14+
- Redis (ingestion queue + cache)
- Python 3.11+
- Node 20+ / pnpm

## Database migrations

```bash
cd backend && alembic upgrade head
# Head: 20260607_0015 (Phase L)
```

## Environment variables (Phase L)

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_COOKIE_ENABLED` | `true` | HttpOnly cookie sessions |
| `CLAMAV_ENABLED` | `false` | Enable ClamAV scanning |
| `CLAMAV_REQUIRED` | `false` | Fail uploads if ClamAV unavailable |
| `ENABLE_RBAC` | `false` | DB role enforcement |
| `GITHUB_CLIENT_ID/SECRET` | — | OAuth login + GitHub connector |

## Production checklist

1. Set strong `JWT_SECRET_KEY` (32+ chars)
2. Configure `CORS_ORIGINS` + `FRONTEND_URL`
3. Set `EVAL_ADMIN_EMAILS` for admin access when RBAC off
4. Enable Redis: `REDIS_URL`
5. Run RQ worker for background indexing
6. Optional: `CLAMAV_ENABLED=true` with clamd socket
7. Deploy frontend with `NEXT_PUBLIC_API_URL` pointing to API

## Health checks

- `GET /health/live` — liveness
- `GET /health/ready` — readiness + migrations
- `GET /health/migrations` — Alembic status

## Cookie notes (cross-origin)

For production HTTPS, cookies use `Secure` + `SameSite=None`. Frontend and API must be on allowed CORS origins with credentials enabled.
