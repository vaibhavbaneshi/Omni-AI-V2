# OmniAI Security

Security is layered across transport headers, authentication, input validation, upload scanning, rate limiting, and audit logging.

## Security architecture

```
Request
  → SecurityHeadersMiddleware (CSP, HSTS, X-Frame-Options, …)
  → RateLimitMiddleware (Redis or in-memory sliding window)
  → JWT auth (get_current_user)
  → Pydantic validation (chat/upload schemas)
  → sanitize_user_query / upload_validation
  → abuse_detection_service (injection + spam heuristics)
  → security_audit_service (structured audit log)
```

---

## Authentication

- **JWT access tokens** — HS256, configurable expiry (`JWT_EXPIRE_MINUTES`, default 15).
- **Refresh tokens** — stored hashed in PostgreSQL; rotation via `/auth/refresh`.
- **OAuth** — GitHub and Google (`/auth/github`, `/auth/google`) with PKCE/state validation.
- **Session registry** — active sessions tracked in user settings; revoke via settings API.

Production startup validates:

- Strong `JWT_SECRET_KEY` (≥32 chars, not dev default)
- No wildcard CORS
- Required API keys for configured providers

---

## Rate limiting

Implemented in `backend/app/middleware/production.py` with rules from `rate_limit_service.py`:

| Scope | Limit | Window |
|-------|-------|--------|
| `/chat*` | 30 requests | 60s |
| `/upload*` | 10 requests | 3600s |
| `/auth/*` | 10 requests | 60s |
| Other API | `RATE_LIMIT_PER_MINUTE` (default 120) | 60s |

Exempt paths: `/health/*`, `/`, `/docs`, `/openapi.json`.

When `ENABLE_REDIS_RATE_LIMIT=true` and `REDIS_URL` is set, limits are enforced via Redis sorted sets (multi-worker safe). Otherwise an in-memory sliding window is used.

HTTP 429 responses include `Retry-After` and `X-RateLimit-*` headers. Exceeded limits are audit-logged as `rate_limit.exceeded`.

---

## Input validation

### Chat

- `ChatStreamRequest` — query length, mode allowlist, workspace ID pattern.
- Accepts JSON body or query params (backward compatible).
- `sanitize_user_query` strips control characters and enforces `MAX_QUERY_CHARS`.

### Uploads

- Extension allowlist (PDF, TXT, MD, DOCX — no executables/archives).
- Magic-byte checks for PDF.
- Max size: `MAX_UPLOAD_BYTES` (default 20MB).
- Filename sanitization (path traversal blocked).
- Optional ClamAV-style scan via `file_scanner`.

---

## Prompt injection & abuse

`abuse_detection_service.py`:

- **Injection patterns** — `detect_prompt_injection()` in `sanitize.py` (e.g. "ignore previous instructions").
- **Spam heuristics** — repeated characters, known spam phrases, excessive special characters.
- **Audit events** — `prompt_injection.detected`, `abuse.pattern.detected` written to `security_audit_logs`.

Injection detection does not block the request by default — it logs and sanitizes. Extend `evaluate_chat_query()` to set `blocked=True` if hard-blocking is required.

---

## Security headers

Set on every response in production middleware:

| Header | Value |
|--------|-------|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | Restrict camera, mic, geolocation |
| `Content-Security-Policy` | Restrictive default for API |
| `Strict-Transport-Security` | Production only, 1 year |

---

## Audit logging

`security_audit_service.audit_log()` writes to:

1. Structured logger (`omni.security`)
2. PostgreSQL `security_audit_logs` (when DB session available)

Common actions:

| Action | Trigger |
|--------|---------|
| `prompt_injection.detected` | Chat query matches injection patterns |
| `abuse.pattern.detected` | Spam/heuristic match |
| `rate_limit.exceeded` | Rate limit middleware 429 |
| `upload.received` | Successful upload |
| `upload.rejected.malware` | File scan failure |
| `upload.deleted` | Document deletion |

Sensitive fields (tokens, passwords) are redacted before persistence.

---

## Secrets management

- Never commit `.env` — use `.env.example` as template.
- Rotate `JWT_SECRET_KEY` and OAuth secrets on compromise.
- Use Railway/Vercel secret stores in production.
- `SENTRY_DSN` and LLM keys are server-side only; frontend uses `NEXT_PUBLIC_*` only for non-secret config.

---

## Testing

Integration tests: `backend/tests/integration/test_security_integration.py`

- Rate limit 429 + audit
- Invalid chat body 422
- Prompt injection audit trail
- Blocked upload extensions
- Invalid workspace ID 422

Run:

```bash
cd backend && pytest tests/integration/test_security_integration.py -q
```

---

## Related docs

- [Architecture](./architecture.md)
- [Deployment](./deployment.md)
- [API reference](./api-reference.md)
