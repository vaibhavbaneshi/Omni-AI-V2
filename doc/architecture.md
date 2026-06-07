# OmniAI Architecture

OmniAI is a full-stack RAG (Retrieval-Augmented Generation) platform: users upload documents, chat with an agent that retrieves relevant chunks, and optionally run research or document-analysis workflows.

## High-level diagram

```
┌─────────────┐     HTTPS/NDJSON      ┌──────────────────────────────────────┐
│  Next.js    │ ◄──────────────────► │  FastAPI (app/main.py)                │
│  frontend   │     JWT Bearer        │  Trace → Rate limit → Security hdrs  │
└─────────────┘                       └──────────────┬───────────────────────┘
                                                     │
         ┌───────────────────────────────────────────┼───────────────────────────┐
         │                                           │                           │
         ▼                                           ▼                           ▼
  PostgreSQL / SQLite                          ChromaDB                    Redis (optional)
  users, sessions, messages,                   vector embeddings           RQ ingest queue
  documents, insights, reports                 hybrid + BM25               rate limits
         │                                           │
         └───────────────────────┬───────────────────┘
                                 ▼
                    ┌────────────────────────┐
                    │  Agent orchestrator      │
                    │  tool_calling_agent    │
                    └───────────┬────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
        retrieval_tool    web_search_tool    document-analysis
        (hybrid RAG)                          / research agents
              │
              ▼
        LLM providers (Groq / OpenAI / Ollama)
```

## Backend layers

| Layer | Location | Responsibility |
|-------|----------|----------------|
| API routes | `backend/app/api/` | HTTP endpoints, auth, validation |
| Services | `backend/app/services/` | Business logic (RAG, ingest, memory, search) |
| Agents | `backend/app/agent/` | Orchestrator, research & document-analysis agents |
| Tools | `backend/app/tools/` | Retrieval, web search, calculator, summarizer |
| Core | `backend/app/core/` | Settings, LLM clients, security, telemetry, Sentry |
| Middleware | `backend/app/middleware/production.py` | Trace IDs, rate limits, security headers |
| Models | `backend/app/models/` | SQLAlchemy ORM |
| Worker | `backend/app/worker.py` | RQ consumer for background document indexing |

## Request flow — streaming chat

1. Client `POST /chat-stream` with query + `session_id` (query params or JSON body).
2. `TraceMiddleware` assigns `X-Trace-Id`; rate limiter checks path-scoped limits.
3. `evaluate_chat_query` audits prompt-injection / abuse patterns.
4. `tool_calling_agent` runs the orchestrator: selects RAG, web search, research, or document-analysis route.
5. Optional query rewriting (`query_contextualizer_service`) expands follow-ups before retrieval.
6. `stream_response` yields NDJSON events: `status` → `meta` → `token` → `done`.
7. Messages and conversation summaries persist to PostgreSQL; usage metrics optionally recorded.

## Document ingestion

1. `POST /upload` validates file type/size, scans for malware, stores file on disk.
2. `DocumentRecord` created with `indexing_stage=queued`.
3. If `INGEST_QUEUE_ENABLED=true` and Redis is configured → RQ job; else in-process `BackgroundTasks` or sync ingest.
4. Worker runs `ingestion_service.run_ingest_document_record`: extract text → chunk → embed → Chroma upsert.
5. Optional post-index document intelligence when `ENABLE_DOCUMENT_INTELLIGENCE=true`.

## Frontend

| Area | Path |
|------|------|
| Chat UI | `frontend/app/chat/page.tsx` |
| Dashboard | `frontend/app/dashboard/page.tsx` |
| API client | `frontend/lib/api.ts` |
| Stream hook | `frontend/hooks/useChatStream.ts` |
| Workspace panels | collections, search, document insights components |

Auth tokens live in client storage; all API calls send `Authorization: Bearer <jwt>`.

## Feature flags (env)

| Variable | Effect |
|----------|--------|
| `ENABLE_QUERY_REWRITING` | Follow-up query expansion before retrieval |
| `ENABLE_AGENT_WORKFLOWS` | Formal `/agents/*` endpoints |
| `ENABLE_DEEP_RESEARCH` | Research agent with persisted reports |
| `ENABLE_DOCUMENT_INTELLIGENCE` | Auto-generate insights after indexing |
| `ENABLE_REDIS_RATE_LIMIT` | Distributed rate limiting via Redis |
| `INGEST_QUEUE_ENABLED` | Durable RQ ingestion queue |

## Observability

- **Logs:** `backend/logs/backend.log` + stdout (`omni.http`, `omni.telemetry`, `omni.security`)
- **Metrics:** `api_usage`, `model_usage`, `token_usage` tables when `ENABLE_USAGE_TRACKING=true`
- **Tracing:** Optional LangSmith (`LANGCHAIN_TRACING_V2`)
- **Errors:** Optional Sentry (`SENTRY_DSN` backend, `NEXT_PUBLIC_SENTRY_DSN` frontend)

See also [monitoring/observability.md](./monitoring/observability.md).

## Related docs

- [API reference](./api-reference.md)
- [Deployment](./deployment.md)
- [Security](./security.md)
- [Agents](./agents.md)
