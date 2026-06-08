# Phase L — Production Readiness & Security

**Date:** 2026-05-25  
**Status:** Implemented  
**Alembic head:** `20260607_0015`

---

## Executive summary

Phase L closes production-critical gaps from the implementation status report: **OAuth-only auth with HttpOnly cookies**, upload security pipeline, GitHub connector, RBAC/audit UIs, deep research UI, Redis cache layer, and documentation refresh.

---

## Findings (pre-implementation audit)

| Area | Finding |
|------|---------|
| Auth | OAuth-only confirmed; dead register/forgot-password pages; tokens in callback URL |
| Upload | No-op virus scanner; no quarantine workflow |
| Connectors | All stubs |
| RBAC/Audit | Backend only, no admin UI |
| Research | API only, no dedicated UI |
| Cache | In-memory retrieval cache only |
| Tests | No Phase L coverage; 80% gate not at 90% |

**Decision:** OAuth-only architecture (no email/password).

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

### 4. RBAC admin UI

- `/admin/rbac` — user list, role assignment (admin only)

### 5. Audit center UI

- `/admin/audit` — overview stats, event list, filter, CSV export link

### 6. Deep research UI

- `/research` — query → run → report with verification + traces

### 7. Redis performance cache

- `redis_cache_service.py` — retrieval, embedding, query namespaces
- Hit/miss metrics via `cache_metrics()`
- `retrieval_cache.py` delegates to Redis layer

---

## Files changed

### Backend (new)

| File | Purpose |
|------|---------|
| `app/core/cookie_auth.py` | Cookie + CSRF helpers |
| `app/middleware/csrf.py` | CSRF middleware |
| `app/services/upload_security_service.py` | Quarantine + scanning |
| `app/services/redis_cache_service.py` | Redis cache + metrics |
| `app/services/github_connector_service.py` | GitHub sync |
| `app/models/github_connector.py` | Connector models |
| `app/api/github_connector_routes.py` | GitHub API |

### Backend (modified)

| File | Change |
|------|--------|
| `app/core/security.py` | Cookie + Bearer token auth |
| `app/api/oauth_routes.py` | Cookie sessions, `/auth/session` |
| `app/api/upload_routes.py` | Quarantine pipeline |
| `app/api/audit_routes.py` | Events, users, export, admin-only role assign |
| `app/services/audit_service.py` | Uploads, security events, pagination, CSV |
| `app/services/file_scanner.py` | Delegates to upload security |
| `app/services/retrieval_cache.py` | Redis-backed |
| `app/main.py` | CSRF middleware, GitHub router |
| `app/core/app_settings.py` | CLAMAV, AUTH_COOKIE flags |

### Frontend (new)

| File | Purpose |
|------|---------|
| `app/admin/rbac/page.tsx` | RBAC admin |
| `app/admin/audit/page.tsx` | Audit dashboard |
| `app/research/page.tsx` | Deep research UI |

### Frontend (modified)

| File | Change |
|------|--------|
| `lib/auth.ts` | Cookie session model |
| `lib/api.ts` | credentials, CSRF, admin APIs |
| `app/auth/callback/page.tsx` | No URL tokens |
| `app/login/page.tsx` | OAuth-only messaging |
| `app/register/page.tsx` | Redirect to login |
| `app/forgot-password/page.tsx` | Redirect to login |

---

## Migrations

| Revision | Description |
|----------|-------------|
| `20260607_0015` | `documents.security_status`, `github_connections`, `github_repository_syncs` |

```bash
cd backend && alembic upgrade head
```

---

## Tests added

| File | Coverage |
|------|----------|
| `tests/test_phase_l.py` | Upload validation, cache, cookies, audit, session |

**Run:** `pytest tests/test_phase_l.py` — 6 passed (with auth tests)

Frontend: TypeScript check passes (`tsc --noEmit`).

---

## Security improvements

- Tokens removed from OAuth callback URLs (when `AUTH_COOKIE_ENABLED=true`)
- CSRF protection on cookie-authenticated mutations
- Upload quarantine + extension/MIME/ZIP/PDF checks
- ClamAV integration point (optional)
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
6. Smoke-test OAuth login, upload, `/admin/audit`, `/research`

---

## Remaining issues

| Item | Priority |
|------|----------|
| 90%+ backend coverage gate | P2 |
| Frontend automated tests (Vitest) | P2 |
| Notion/Confluence/Slack connectors | P3 |
| Interactive force-directed graph UI | P3 |
| Full ClamAV deployment in CI/CD | P2 |
| GitHub connector UI in workspace settings | P2 |
| Embedding cache wired in embedding_service | P2 |

---

## APIs added

| Method | Path | Description |
|--------|------|-------------|
| GET | `/auth/session` | Current user profile |
| GET | `/audit/events` | Paginated audit events |
| GET | `/audit/export` | CSV export |
| GET | `/audit/users` | Users with roles |
| GET | `/connectors/github/status` | Connection status |
| GET | `/connectors/github/repos` | List repos |
| POST | `/connectors/github/sync` | Sync repository |

---

*Phase L complete — OAuth-only production readiness track.*
