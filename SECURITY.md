# OmniAI Security

## Protections Implemented

- Authentication uses short-lived access tokens and rotating refresh tokens.
- Global frontend auth-expiration handling clears local/session auth state, JS-readable cookies, React auth context, and redirects to login with a friendly message.
- Refresh tokens are stored server-side as HMAC-SHA256 hashes and are rotated on every refresh.
- Logout revokes the active refresh-token session.
- Backend protected routes reject expired, invalid, unknown-user, and revoked-session tokens.
- Uploads are limited to PDF, DOCX, TXT, Markdown and 20MB.
- Upload validation checks extension, MIME type, file magic bytes where applicable, empty content, and blocked executable/archive extensions.
- Upload filenames are normalized and sanitized to prevent path traversal, command injection, and unsafe Unicode.
- Uploaded source files are staged in OS temp storage and cleaned after ingestion.
- A pluggable upload scanner hook exists in `app.services.file_scanner`; integrate ClamAV or a managed scanner there.
- Security audit logs record auth sessions, refresh rotation/rejection, logout, uploads, deletes, and prompt-injection attempts without secrets.
- API middleware adds rate limits for auth, chat, uploads, and general API traffic with rate-limit headers.
- Security headers include HSTS in production, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, and Permissions-Policy.
- CORS is environment-driven and production startup fails if wildcard origins are configured.
- React Markdown rendering skips raw HTML.
- Chat/session/settings inputs have stricter length, format, and enum validation.
- Chroma retrieval is user-scoped; unscoped vector reads return no documents.
- Retrieved RAG context is marked as untrusted data and prompt-injection patterns in chats/documents are detected and logged.

## Operational Notes

- Set `JWT_SECRET_KEY` to a unique 32+ character secret in production.
- Set `CORS_ORIGINS` to exact frontend origins only.
- Keep `CHROMA_DB_PATH` on persistent storage if vector data must survive deploys.
- Configure a real malware scanner by replacing the no-op hook in `backend/app/services/file_scanner.py`.
- Use Redis or another shared store for rate limiting when running multiple backend workers.

## Remaining Risks

- OAuth access and refresh tokens are returned through the callback URL for compatibility with the existing SPA flow. Prefer an HttpOnly Secure SameSite cookie flow in a future auth redesign.
- The current in-memory rate limiter is process-local.
- Prompt-injection detection is heuristic and should feed monitoring rather than hard blocking normal chat usage.
