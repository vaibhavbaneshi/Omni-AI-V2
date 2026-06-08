# Security

## Authentication

- **OAuth-only** — Google and GitHub; no email/password
- **HttpOnly cookies** for access + refresh tokens
- **CSRF** double-submit cookie on mutating requests
- Session revocation via `user_sessions.revoked_at`

## Upload security

- Extension allowlist + blocked executables/scripts
- MIME validation
- ZIP bomb protection (entry count + uncompressed size)
- PDF JavaScript detection
- Optional ClamAV integration (`CLAMAV_ENABLED`)
- Quarantine workflow before indexing

## RBAC

Roles: `admin`, `manager`, `editor`, `viewer`. Admin-only role assignment audited as `rbac.role.changed`.

## Audit logging

Security events in `security_audit_logs`. Admin APIs at `/audit/*`.

## Headers

Security headers middleware (CSP, X-Frame-Options, etc.) via `SecurityHeadersMiddleware`.

## Rate limiting

Redis-backed when `REDIS_URL` set; in-memory fallback otherwise.

See [security audit Phase L](security-audit-phase-l.md) for full review.
