# Security Audit — Phase L

**Date:** 2026-05-25  
**Scope:** Full codebase review for Phase L production readiness

---

## Methodology

Static review of auth, upload, RBAC, audit, connectors, chat/RAG, and middleware. Cross-referenced with OWASP top risks.

---

## Vulnerabilities found & fixes applied

| Risk | Severity | Finding | Fix |
|------|----------|---------|-----|
| Token exposure | **High** | OAuth tokens in callback URL + localStorage | HttpOnly cookies; callback uses `/auth/session` |
| CSRF | **Medium** | No CSRF on cookie auth | Double-submit CSRF cookie + middleware |
| Malicious uploads | **High** | No-op scanner | Quarantine pipeline + allowlist + ClamAV hook |
| ZIP bombs | **Medium** | No archive limits | Entry count + size caps |
| PDF XSS vectors | **Medium** | No PDF checks | JS embedding detection |
| Dead auth surface | **Low** | Register/forgot-password pages | Redirect to OAuth login |
| Privilege escalation | **Medium** | Role assign without audit | Admin-only + `rbac.role.changed` audit |
| Path traversal (archives) | **Medium** | Unvalidated ZIP paths | Reject `..` and absolute paths |

---

## Controls verified (existing)

| Control | Status |
|---------|--------|
| SQL injection | ✅ SQLAlchemy ORM parameterized queries |
| JWT validation | ✅ jose decode + session JTI revocation check |
| CORS | ✅ Allowlist + credentials support |
| Rate limiting | ✅ Redis/in-memory middleware |
| Prompt injection | ⚠️ Logged, not blocked (acceptable for chat) |
| XSS (frontend) | ✅ Markdown `skipHtml`; React escaping |
| User-scoped RAG | ✅ user_id filters on Chroma queries |
| Upload size limits | ✅ MAX_UPLOAD_BYTES |

---

## Remaining risks

| Risk | Severity | Notes |
|------|----------|-------|
| ClamAV off by default | **Medium** | Enable in production with `CLAMAV_ENABLED=true` |
| JWT in Bearer header (legacy) | **Low** | Still supported for tests/API clients |
| OAuth connector callback | **Low** | Requires prior login; cookies must be sent |
| No frontend E2E auth tests | **Low** | Manual smoke test required |
| DuckDuckGo web scrape | **Low** | Third-party dependency for web search |
| Monolithic chat page | **Info** | Large attack surface for UI bugs |

---

## Recommendations

1. Enable ClamAV in production environments accepting user uploads
2. Set `EVAL_ADMIN_EMAILS` in all non-dev environments
3. Add Vitest/Playwright for OAuth cookie flow regression tests
4. Consider Content-Security-Policy tightening for admin pages
5. Rotate GitHub connector tokens on disconnect/re-auth

---

*Audit performed as part of Phase L implementation.*
