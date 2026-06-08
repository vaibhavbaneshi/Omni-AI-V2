# OmniAI Architecture

## Overview

```
Browser (Next.js)
    │ credentials: include + CSRF header
    ▼
FastAPI API
    ├── OAuth (Google/GitHub) → HttpOnly cookies
    ├── Chat stream → Agent orchestrator → RAG / web / memory
    ├── Upload → Quarantine → Security scan → Index (RQ)
    ├── Document intelligence → timeline/entities → knowledge graph
    ├── Multi-agent platform → agent traces
    └── Admin: audit, RBAC, connectors
    ▼
PostgreSQL · ChromaDB · Redis (cache + RQ)
```

## Auth architecture (OAuth-only)

1. User clicks Google/GitHub on `/login`
2. Backend OAuth callback issues JWT + refresh, sets **HttpOnly cookies**
3. Frontend stores **profile only** in sessionStorage (no tokens)
4. All API calls use `credentials: include`
5. Mutating requests include `X-CSRF-Token` from readable CSRF cookie
6. Session refresh via `POST /auth/refresh` (cookie-backed)
7. Logout clears cookies via `POST /auth/logout`

## Cache architecture

Redis-backed cache (`redis_cache_service.py`) with in-memory fallback:

| Namespace | Content | TTL |
|-----------|---------|-----|
| `retrieval` | RAG context strings | 300s |
| `embedding` | Embedding vectors | 3600s |
| `query/*` | Research, GraphRAG, intelligence | 600s |

Metrics: `cache_metrics()` — hits, misses, hit_rate_pct.

## Upload security pipeline

```
Upload → Quarantine dir → Extension/MIME/ZIP/PDF checks → ClamAV (optional) → Storage → Index
```

Rejected uploads audit-logged as `upload.rejected.security`.

## Knowledge graph

Document entities → `graph_nodes` / `graph_edges` → GraphRAG injected in retrieval.

## Multi-agent flow

Planner → parallel specialists → critic → summarizer → `agent_traces` table.
