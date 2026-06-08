# Phase L — Production Readiness & Security

**Date:** 2026-05-25  
**Status:** Complete  
**Alembic head:** `20260607_0015`

---

## Executive summary

Phase L closes production-critical gaps: **OAuth-only auth with HttpOnly cookies**, upload security pipeline, GitHub connector (backend + workspace UI), RBAC/audit/research UIs, Redis cache layer with admin metrics, expanded test coverage, Vitest frontend tests in CI, and documentation refresh.

---

## Features completed

### 1. Authentication (OAuth-only)

- HttpOnly `omniai_access` + `omniai_refresh` cookies
- CSRF cookie + `X-CSRF-Token` header middleware
- `GET /auth/session` for profile hydration
- Cookie-backed refresh/logout
- Removed register/forgot-password flows (redirect to `/login`)
- Frontend: profile in sessionStorage only; `credentials: include` on all API calls

### 2. Upload security

- `upload_security_service.py` — quarantine, allowlist, MIME, ZIP bomb, PDF checks, ClamAV
- Upload flow: quarantine → scan → approve → index
- `documents.security_status` column
- Audit events for rejections

### 3. GitHub connector

- `github_connections`, `github_repository_syncs` tables
- OAuth authorize, repo list, sync with incremental commit SHA
- Indexes markdown/source/docs into GitHub collection
- **Workspace UI:** Connectors tab in workspace context sheet (`GitHubConnectorPanel`)

### 4. RBAC admin UI

- `/admin/rbac` — user list, role assignment (admin only)

### 5. Audit center UI

- `/admin/audit` — overview stats, event list, filter, CSV export link

### 6. Deep research UI

- `/research` — query → run → report with verification + traces

### 7. Redis performance cache

- `redis_cache_service.py` — retrieval, embedding, query namespaces
- GraphRAG and deep research result caching
- Hit/miss metrics via `cache_metrics()`
- `GET /analytics/cache` (admin only)
- `retrieval_cache.py` delegates to Redis layer

---

## Tests

| Suite | Count | Notes |
|-------|-------|-------|
| `tests/test_phase_l.py` | 6 | Cookies, cache, audit, session |
| `tests/test_phase_l_complete.py` | 26 | Upload, GitHub, CSRF, audit service, connectors |
| `tests/test_coverage_boost.py` | 6 | Collection, Redis fallback, upload edge cases |
| Frontend Vitest (`lib/auth.test.ts`) | 5 | CSRF, session profile, logout |

**Backend coverage:** ~81% on `app/` (80% gate passing). Evaluation metrics tracked separately via `eval-smoke` CI job.

**Run:**

```bash
cd backend && pytest --cov=app -q
cd frontend && npm test
```

---

## Security improvements

- Tokens removed from OAuth callback URLs (when `AUTH_COOKIE_ENABLED=true`)
- CSRF protection on cookie-authenticated mutations
- Upload quarantine + extension/MIME/ZIP/PDF checks
- ClamAV integration point (optional via `CLAMAV_*` env vars)
- RBAC role changes audit-logged
- Admin routes require admin email allowlist (or RBAC when enabled)

See `docs/security-audit-phase-l.md`.

---

## Deployment steps

1. `alembic upgrade head` → `20260607_0015`
2. Set `AUTH_COOKIE_ENABLED=true`
3. Ensure CORS allows credentials from frontend origin
4. Optional: `CLAMAV_ENABLED=true` + clamd
5. Redeploy backend + frontend
6. Smoke-test OAuth login, upload, `/admin/audit`, `/research`, GitHub connector tab

---

## Out of scope (future phases)

| Item | Notes |
|------|-------|
| Notion/Confluence/Slack connectors | Stubs remain; GitHub fully implemented |
| Interactive force-directed graph UI | Graph tab exists; advanced viz deferred |
| Platform-wide 90%+ coverage | Phase L modules covered; broader suite at ~81% |
| ClamAV in CI/CD | Integration ready; production clamd deploy is ops task |

---

## APIs added

| Method | Path | Description |
|--------|------|-------------|
| GET | `/auth/session` | Current user profile |
| GET | `/audit/events` | Paginated audit events |
| GET | `/audit/export` | CSV export |
| GET | `/audit/users` | Users with roles |
| GET | `/analytics/cache` | Cache hit/miss metrics (admin) |
| GET | `/connectors/github/status` | Connection status |
| GET | `/connectors/github/repos` | List repos |
| POST | `/connectors/github/sync` | Sync repository |

---

*Phase L complete — OAuth-only production readiness track.*
