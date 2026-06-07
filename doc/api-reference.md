# OmniAI API Reference

Base URL: `http://localhost:8000` (development) or your deployed API origin.

**Authentication:** Most endpoints require `Authorization: Bearer <access_token>` from login/register/OAuth.

**Streaming:** `/chat-stream` returns `application/x-ndjson` — one JSON object per line.

---

## Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Service banner |
| GET | `/health/live` | No | Liveness probe |
| GET | `/health/ready` | No | Readiness after startup |
| GET | `/health?deep=true` | No | Deep dependency checks |

---

## Auth & users

Auth routes are mounted under `/auth` (OAuth, refresh, logout). User profile:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/users/me` | Current user profile |

---

## Chat

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat` | Legacy non-streaming chat |
| POST | `/chat-stream` | Streaming NDJSON chat |

**`/chat-stream` parameters** (query string or JSON body):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `query` | string | Yes | 1–12,000 chars |
| `session_id` | int | Yes | Owned chat session |
| `mode` | string | No | `research`, `coding`, `writing`, `analyst`, `deep-research` |
| `model` | string | No | Override routed model |
| `workspace_id` | string | No | Default `default` |
| `collection_id` | int | No | Scope retrieval to collection |

**Stream event types:** `status`, `meta`, `token`, `title`, `error`, `cancelled`, `done`

---

## Sessions

| Method | Path | Description |
|--------|------|-------------|
| POST | `/sessions/create?first_message=` | Create session with title |
| GET | `/sessions` | List sessions (pin/folder metadata) |
| GET | `/sessions/{id}/messages` | Message history |
| PATCH | `/sessions/{id}` | Rename session |
| PATCH | `/sessions/{id}/organization` | Pin / assign folder |
| DELETE | `/sessions/{id}` | Delete session |
| POST | `/sessions/{id}/title/refine` | Regenerate title |

---

## Documents & collections

| Method | Path | Description |
|--------|------|-------------|
| POST | `/upload` | Upload file (`session_id` required) |
| GET | `/documents` | List session documents |
| GET | `/documents/{id}/status` | Indexing progress |
| DELETE | `/documents/id/{id}` | Delete by ID |
| GET | `/collections` | List collections |
| POST | `/collections` | Create collection |
| PATCH | `/collections/{id}` | Rename |
| DELETE | `/collections/{id}` | Delete (moves docs to Default) |
| PATCH | `/documents/id/{id}/collection` | Move document |

Supported uploads: PDF, TXT, MD, DOCX (see `SUPPORTED_UPLOADS_LABEL` in backend).

---

## Document intelligence

| Method | Path | Description |
|--------|------|-------------|
| GET | `/documents/{id}/insights` | Fetch persisted insights |
| POST | `/documents/{id}/insights/generate?force=false` | Generate/regenerate insights |

Payload includes executive summary, FAQs, action items, metadata (keywords, topics, entities).

---

## Agents

Prefix: `/agents` — requires `ENABLE_AGENT_WORKFLOWS=true`.

| Method | Path | Flags | Description |
|--------|------|-------|-------------|
| POST | `/agents/research` | `ENABLE_DEEP_RESEARCH` | Run research agent, persist report |
| GET | `/agents/research/{report_id}` | — | Fetch report |
| POST | `/agents/document-analysis` | — | Run document analysis agent |

---

## Workspace

| Method | Path | Description |
|--------|------|-------------|
| GET | `/folders` | List chat folders |
| POST | `/folders` | Create folder |
| PATCH | `/folders/{id}` | Rename |
| DELETE | `/folders/{id}` | Delete (unassigns sessions) |
| GET | `/search?q=` | Global search (sessions, messages, documents, insights) |

Search `types` filter: comma-separated `session`, `message`, `document`, `insight`.

---

## Memory, settings, analytics

| Method | Path | Description |
|--------|------|-------------|
| GET/POST/DELETE | `/memory` | User long-term memory |
| GET/PATCH | `/settings/*` | Profile, 2FA, preferences, billing |
| GET | `/analytics/*` | Admin analytics (email allowlist) |
| POST | `/evaluation/run` | RAG eval (admin) |
| GET | `/models`, `/models/route` | Model catalog & routing preview |

---

## Admin queue (ingestion)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/ingestion-queue/metrics` | Queue depth, workers |
| GET | `/admin/ingestion-queue/dlq` | Dead-letter jobs |
| POST | `/admin/ingestion-queue/requeue/{job_id}` | Requeue failed job |

---

## Response headers

| Header | Description |
|--------|-------------|
| `X-Trace-Id` | Correlation ID for logs |
| `X-Response-Time-Ms` | Request duration |
| `X-RateLimit-*` | Rate limit status |
| `Retry-After` | Present on HTTP 429 |

---

## Error codes

| Code | Meaning |
|------|---------|
| 400 | Validation / business rule failure |
| 401 | Missing or invalid JWT |
| 403 | Feature disabled or forbidden |
| 404 | Resource not found |
| 413 | Upload too large |
| 422 | Invalid request body / params |
| 429 | Rate limit exceeded |
| 503 | Starting up or dependency unavailable |

OpenAPI docs: `/docs` (development).
