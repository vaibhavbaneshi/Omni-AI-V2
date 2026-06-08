# OmniAI Repository Audit — Review & Planning Document

**Generated:** 2026-05-25  
**Purpose:** Review current state, track gaps, and plan next work  
**Scope:** Full repo (`backend/`, `frontend/`, `doc/`, `eval/`, CI, deployment)  
**Method:** Static analysis — no code was modified for this audit

---

## How to use this document

1. Read **Executive Summary** and **Priority Matrix** first.
2. Use **Feature Inventory** to confirm what ships today vs what is stubbed.
3. Use **Phase Completion** to align sprint planning with original roadmap.
4. Track fixes in **Open Issues & Bugs** — check off as resolved.
5. Copy items from **Recommended Next Priorities** into your issue tracker or sprint board.

---

## Executive Summary

OmniAI is a **production-capable RAG chat platform**: FastAPI + Next.js + PostgreSQL + ChromaDB + optional Redis/RQ.

| Area | Assessment |
|------|------------|
| Core chat + streaming | ✅ Strong |
| Document upload + RAG + citations | ✅ Strong |
| Workspace (collections, folders, search) | ✅ Strong |
| Analytics + evaluation (backend) | ✅ Strong |
| Document intelligence | ⚠️ Implemented, auto-gen off by default |
| Auth | ⚠️ OAuth only — `auth_routes.py` missing |
| Testing | ⚠️ 78.3% coverage, 2 failing tests, no frontend tests |
| Documentation | ⚠️ Good `doc/` tree, root README is a stub |
| Performance / ops hardening | ⚠️ Partial (RQ yes; distributed cache no) |

**Overall maturity:** ~**75–80%** of documented production plan implemented.

**Test run at audit time:** 189 tests, **187 passed**, **2 failed**, **78.30%** coverage (gate: 80% in `backend/pytest.ini`).

**Alembic head:** `20260605_0012` (`workspace_folders.py`)

---

## Priority Matrix (start here)

### P1 — Must do before trusting production

| # | Item | Why | Key files |
|---|------|-----|-----------|
| 1 | **Resolve auth gap** | `backend/app/api/auth_routes.py` is **missing**; only OAuth works | `oauth_routes.py`, `login/page.tsx`, `main.py` |
| 2 | **Fix CI** | 2 Sentry tests fail; coverage below 80% | `tests/test_platform_services.py`, `pytest.ini` |
| 3 | **Verify deploy health** | Migrations, Redis worker, persistent Chroma/uploads | `railway_migrate.sh`, `railway_web_and_worker.sh`, `/health/ready` |
| 4 | **Ship recent fixes** | Doc intelligence Chroma fallback, simple-query routing, cleaner UI | `document_intelligence_service.py`, `conversation_heuristics.py`, `workspace-context-sheet.tsx` |

### P2 — Should do next sprint

| # | Item | Why |
|---|------|-----|
| 5 | Enable `ENABLE_DOCUMENT_INTELLIGENCE=true` after validation | Auto insights after upload |
| 6 | Integration tests for insights, agents, folders, search | Gaps in API test coverage |
| 7 | Real malware scanner in `file_scanner.py` | Currently no-op hook |
| 8 | Complete README + developer onboarding | Root README is one line |
| 9 | Redis-backed retrieval cache | Today: in-memory only |
| 10 | Benchmark CLI + eval widgets on dashboard | Roadmap gap |

### P3 — Nice to have

| # | Item |
|---|------|
| 11 | Batch upload API |
| 12 | Knowledge graph / timeline extraction |
| 13 | Image/vision analysis (or remove UI claim) |
| 14 | HttpOnly cookie auth redesign |
| 15 | Split Railway API vs worker services |
| 16 | Frontend component / E2E tests |
| 17 | Prometheus `/metrics` endpoint |

---

## Feature Inventory

| Feature | Status | Evidence |
|---------|--------|----------|
| JWT authentication | ✅ Complete | `auth_service.py`, `security.py`, auth tests |
| Email/password login/register API | ❌ Missing | `auth_routes.py` absent; `user_routes.py` only has `/users/me` |
| OAuth (GitHub/Google) | ✅ Complete | `oauth_routes.py`, `social-auth-buttons.tsx` |
| JWT refresh + session registry | ✅ Complete | `/auth/refresh`, `UserSessionRecord` |
| Chat sessions + messages | ✅ Complete | `session_routes.py`, migrations through `0012` |
| Streaming chat (NDJSON) | ✅ Complete | `/chat-stream`, `useChatStream.ts`, disconnect handling |
| Legacy `/chat` | ✅ Complete | Not deprecated |
| User memory (facts) | ✅ Complete | `memory_routes.py`, `useMemory.ts` |
| Conversation summarization | ✅ Complete | `memory_summary_service.py` |
| Document upload | ✅ Complete | `upload_routes.py`, `upload_validation.py` |
| Document indexing pipeline | ✅ Complete | `ingestion_service.py`, RQ worker, progress stages |
| Embeddings | ✅ Complete | `embedding_service.py` |
| Chroma vector store | ✅ Complete | `chroma_client.py`, `documents_services.py` |
| Hybrid RAG (semantic + BM25) | ✅ Complete | `hybrid_search.py` |
| Reranking | ✅ Complete (optional) | `reranker_service.py`, `ENABLE_RERANKER` |
| Citations `[S#]` | ✅ Complete | `citation_service.py`, `sources-panel.tsx` |
| Query contextualization | ✅ Complete (flagged) | `query_contextualizer_service.py`, `ENABLE_QUERY_REWRITING` |
| Multi-document retrieval | ⚠️ Partial | `multi_document_service.py` (~44% coverage) |
| Web search | ✅ Complete | `web_search_tool.py` (DDG/Tavily/Serper) |
| Agent orchestration | ✅ Complete | `orchestrator.py`, `tool_agent.py` |
| Research agent | ⚠️ Partial | `research_agent.py`; `ENABLE_DEEP_RESEARCH=false` default |
| Document analysis agent | ✅ Complete | `document_analysis_agent.py`, `/agents/document-analysis` |
| Document intelligence (persisted) | ⚠️ Partial | `document_insights` table + API + UI; auto-gen off; Chroma fallback added |
| Collections | ✅ Complete | `/collections` CRUD, workspace panel |
| Chat folders + pins | ✅ Complete | `folder_routes.py`, migration `0012` |
| Global workspace search | ✅ Complete | `search_routes.py`, sidebar results UI |
| Analytics API | ✅ Complete | `analytics_routes.py`, `analytics_service.py` |
| Analytics dashboard UI | ✅ Complete | `dashboard/page.tsx`, Recharts |
| Evaluation pipeline (backend) | ✅ Complete | `backend/evaluation/`, `/evaluation/run` |
| Evaluation dashboard UI | ❌ Missing | No frontend `/evaluation` usage |
| Multi-model routing | ✅ Complete | `model_router.py`, `/models`, settings UI |
| Redis | ⚠️ Partial | docker-compose + `redis_client.py`; optional |
| RQ ingestion workers | ✅ Complete | `worker.py`, `ingestion_queue.py`, Railway script |
| Rate limiting | ✅ Complete | Redis or in-memory middleware |
| Security headers + audit log | ✅ Complete | `production.py`, `security_audit_service.py` |
| Prompt injection detection | ⚠️ Partial | Logs/sanitizes; does not block by default |
| Malware scanning | ⚠️ Partial | No-op hook in `file_scanner.py` |
| 2FA (TOTP) | ✅ Complete | Settings routes + `pyotp` in `settings_service.py` |
| Billing | ⚠️ Mock | Seeded demo invoices; no Stripe |
| Password reset | ❌ Missing | `forgot-password/page.tsx` redirects to login |
| Image analysis | ❌ Missing | UI suggests it; no vision API |
| Sentry | ⚠️ Partial | Wired; 2 unit tests failing |
| LangSmith | ⚠️ Partial | Env supported; default off |
| Usage/token tracking | ✅ Complete | `usage_tracking_service.py`, `llm_invoke.py` |
| CI | ⚠️ Partial | Backend pytest only; no frontend job |
| Root README | ❌ Stub | One-line title only |

---

## Phase Completion (original 10-phase plan)

Source: `doc/implementation-plan.md`

| Phase | Name | Completion | Notes |
|-------|------|------------|-------|
| 1 | Observability | **~90%** | Analytics tables, `llm_invoke`, trace middleware; no Prometheus |
| 2 | Streaming | **~85%** | NDJSON + cancellation; legacy `/chat` remains |
| 3 | Memory | **~95%** | Summaries, windowing, delete, pin/folder |
| 4 | Evaluation | **~85%** | Backend complete; no eval UI |
| 5 | Testing | **~75%** | 78.3% coverage; 2 failures; large omit list in `.coveragerc` |
| 6 | Analytics | **~90%** | API + Recharts dashboard |
| 7 | Multi-model routing | **~95%** | ModelRouter + UI |
| 8 | Security | **~85%** | Redis limiter, audit, schemas; scanner noop |
| 9 | Performance | **~55%** | RQ yes; no async SQLAlchemy; in-memory retrieval cache |
| 10 | Documentation | **~65%** | Good `doc/`; missing README, rag-architecture, schema docs |

---

## Phases A–F (extended roadmap)

Source: `doc/phases-a-f-implementation-plan.md`

| Phase | Doc says | Actual | Completion |
|-------|----------|--------|------------|
| A | Document Intelligence — IN PROGRESS | Code + migration + API + UI exist | **~85%** |
| B | Advanced RAG — COMPLETE | Query rewriting, multi-doc, hybrid benchmarks | **~90%** |
| C | AI Agents — COMPLETE | Research + document-analysis agents | **~85%** |
| D | Knowledge Workspace — COMPLETE | Folders, collections, search | **~95%** |
| E | Security Completion — COMPLETE | Redis rate limit, abuse detection, tests | **~85%** |
| F | Platform Quality — COMPLETE | Sentry wired; coverage gate not met | **~70%** |

**Action:** Update `phases-a-f-implementation-plan.md` — Phase A checklist is stale (items are largely done).

---

## Document Intelligence Roadmap

Source: `doc/reports/document-intelligence-roadmap-report.md`

| Capability | Status |
|------------|--------|
| Upload pipeline | ✅ Complete |
| Citation system | ✅ Complete |
| Multi-document retrieval | ⚠️ Partial |
| Document chat (session-scoped) | ✅ Complete |
| Executive summaries | ✅ Complete |
| FAQ generation | ✅ Complete |
| Action item extraction | ✅ Complete |
| Topic extraction | ⚠️ Partial (LLM list, not clustering) |
| Timeline extraction | ❌ Missing |
| Cross-document comparison | ⚠️ Partial |
| Knowledge graph / Neo4j | ❌ Missing |
| Mind maps | ❌ Missing |
| Persisted insights table | ✅ Complete |
| Auto insights after upload | ⚠️ Off (`ENABLE_DOCUMENT_INTELLIGENCE=false`) |
| Post-index file cleanup | ⚠️ Fixed via Chroma fallback (deploy required) |
| Batch multi-file upload API | ❌ Missing |
| E2E validation CLI | ❌ Missing |
| Eval dashboard (frontend) | ❌ Missing |

---

## Security Findings

| Severity | Finding | Recommendation |
|----------|---------|----------------|
| **Critical** | `auth_routes.py` deleted — OAuth-only | Restore credential auth OR document OAuth-only and remove dead UI/docs |
| **High** | OAuth tokens in callback URL | Move to HttpOnly cookies (future) |
| **High** | Malware scanner is no-op | Integrate ClamAV or managed scanner |
| **High** | Admin access open in non-prod when allowlist empty | Set `EVAL_ADMIN_EMAILS` / `ANALYTICS_ADMIN_EMAILS` in staging |
| **Medium** | Prompt injection logged, not blocked | OK for chat; add hard-block option for sensitive deployments |
| **Medium** | In-memory rate limit without Redis | Require `ENABLE_REDIS_RATE_LIMIT=true` + `REDIS_URL` in prod |
| **Medium** | JWT in localStorage (SPA) | Standard SPA risk; consider cookie auth |
| **Low** | No CSRF | Acceptable for Bearer API |
| **Low** | Mock billing | Label clearly in UI/docs |

**Controls in place:** JWT + refresh rotation, CORS validation, upload validation, security headers, audit logs, Markdown `skipHtml`, user-scoped Chroma queries.

Docs: `doc/security.md`, `SECURITY.md`

---

## Open Issues & Bugs

Use as a checklist — mark `[x]` when fixed.

- [ ] **`auth_routes.py` missing** — no email/password API
- [ ] **CI:** 2 failing Sentry tests (`test_platform_services.py`)
- [ ] **CI:** Coverage 78.3% vs 80% gate
- [ ] **Production migrations** — ensure head `20260605_0012` applied (`/health/migrations`)
- [ ] **Document intelligence** — deploy Chroma fallback for deleted upload files
- [ ] **Research mode verbosity** — deploy `conversation_heuristics.py` + orchestrator `direct-chat`
- [ ] **OAuth-only login/register pages** — no credential form (by design or gap?)
- [ ] **Forgot password** — redirects to login only
- [ ] **“Analyze an image”** — chat empty state promises feature that does not exist
- [ ] **Chroma/uploads on Railway** — need persistent volume or data loss on redeploy
- [ ] **Planning doc drift** — Phase A marked in progress in `phases-a-f-implementation-plan.md`
- [ ] **Root README** — empty stub

---

## Architecture Snapshot

```
Frontend (Next.js)
    │  HTTPS + JWT Bearer + NDJSON stream
    ▼
FastAPI (main.py)
    │  Trace → Rate limit → Security headers
    ├── PostgreSQL (users, sessions, messages, documents, insights, analytics, audit)
    ├── ChromaDB (embeddings, session-scoped retrieval)
    ├── Redis (optional: RQ queue + rate limits)
    └── LLM providers (Groq / OpenAI / Ollama / DeepSeek)
         ▲
    RQ Worker (app/worker.py) — document ingestion
```

**Deployment:** `Dockerfile`, `railway.toml` (`/health/ready`), `docker-compose.yml`, `scripts/railway_web_and_worker.sh` (API + worker in one container).

**Scalability bottlenecks:**
1. Chroma on local disk per instance
2. In-memory retrieval cache (not shared)
3. API + worker share one container’s CPU/RAM
4. Reranker + local embeddings are RAM-heavy

**Technical debt hotspots:**
- `frontend/app/chat/page.tsx` (~1900 lines)
- `backend/app/api/upload_routes.py` (large)
- `.coveragerc` omits core paths (`chat_routes`, `rag_service`, `upload_routes`, etc.)
- DuckDuckGo HTML scraping for web search

---

## Testing Audit

| Area | Status |
|------|--------|
| Backend unit tests | 44 files under `backend/tests/` |
| Backend integration | 10 files, ~52 tests (auth, chat, sessions, memory, upload, health, security, settings, models, evaluation) |
| Coverage (measured) | **78.30%** on `app` + `evaluation` (many modules omitted) |
| Failing tests | 2 — Sentry init tests in `test_platform_services.py` |
| API routes without integration tests | Agents, insights, folders, search, queue admin |
| Frontend tests | **None** (`package.json` has no test script) |
| E2E (Playwright/Cypress) | **None** |

**CI:** `.github/workflows/ci.yml` — backend pytest + eval smoke only.

---

## Documentation Audit

| Document | Status |
|----------|--------|
| `README.md` | ❌ Stub |
| `doc/architecture.md` | ✅ Good |
| `doc/api-reference.md` | ✅ Good |
| `doc/deployment.md` | ✅ Good |
| `doc/security.md` | ✅ Good |
| `doc/agents.md` | ✅ Good |
| `doc/implementation-plan.md` | ⚠️ Partially stale |
| `doc/phases-a-f-implementation-plan.md` | ⚠️ Phase A stale |
| `doc/testing/*` | ✅ Good |
| `doc/sprint1/*` | ✅ Good |
| Missing (per original plan) | `doc/rag-architecture.md`, `doc/database-schema.md`, `doc/environment.md`, `doc/development.md` |

---

## API Surface (quick reference)

Routers mounted in `backend/app/main.py`:

| Prefix / area | Router file |
|---------------|-------------|
| `/users/me` | `user_routes.py` |
| `/chat`, `/chat-stream` | `chat_routes.py` |
| `/upload`, `/documents`, `/collections` | `upload_routes.py` |
| `/sessions` | `session_routes.py` |
| `/auth/*` | `oauth_routes.py` |
| `/memory` | `memory_routes.py` |
| `/evaluation` | `evaluation_routes.py` |
| `/analytics` | `analytics_routes.py` |
| `/models` | `model_routes.py` |
| `/settings` | `settings_routes.py` |
| `/admin/ingestion-queue` | `queue_routes.py` |
| `/documents/{id}/insights` | `insights_routes.py` |
| `/agents` | `agent_routes.py` |
| `/folders` | `folder_routes.py` |
| `/search` | `search_routes.py` |
| `/health/*` | `main.py` |

Full reference: `doc/api-reference.md`

---

## Environment flags (planning)

| Variable | Default | Effect |
|----------|---------|--------|
| `ENABLE_DOCUMENT_INTELLIGENCE` | `false` | Auto-generate insights after indexing |
| `ENABLE_DEEP_RESEARCH` | `false` | Research agent depth |
| `ENABLE_AGENT_WORKFLOWS` | `true` | `/agents/*` endpoints |
| `ENABLE_QUERY_REWRITING` | `true` | Follow-up query expansion |
| `INGEST_QUEUE_ENABLED` | `true` | RQ durable ingestion |
| `ENABLE_REDIS_RATE_LIMIT` | `true` | Distributed rate limits |
| `ENABLE_USAGE_TRACKING` | `true` | Analytics DB writes |
| `LANGCHAIN_TRACING_V2` | `false` | LangSmith |
| `MODEL_ROUTING_ENABLED` | `true` | Auto model selection |

Source: `backend/app/core/app_settings.py`, `doc/architecture.md`

---

## Suggested sprint plan (template)

### Sprint 1 — Production trust
- [ ] Auth decision + fix (restore routes or OAuth-only docs)
- [ ] Fix Sentry tests + coverage gate
- [ ] Deploy + verify migrations, Redis worker, health checks
- [ ] Deploy doc intelligence + conversation heuristics + UI sheet

### Sprint 2 — Quality & security
- [ ] Integration tests: insights, agents, folders, search
- [ ] Malware scanner integration
- [ ] README + `doc/development.md`
- [ ] Enable document intelligence in staging

### Sprint 3 — Platform polish
- [ ] Redis retrieval cache
- [ ] Benchmark CLI + dashboard widgets
- [ ] Split worker service (optional)
- [ ] Frontend smoke tests

---

## Key file index

| Topic | Path |
|-------|------|
| App entry | `backend/app/main.py` |
| Settings / flags | `backend/app/core/app_settings.py` |
| Chat streaming | `backend/app/api/chat_routes.py` |
| RAG | `backend/app/services/rag_service.py` |
| Orchestrator | `backend/app/agent/orchestrator.py` |
| Ingestion | `backend/app/services/ingestion_service.py` |
| RQ worker | `backend/app/worker.py` |
| Document intelligence | `backend/app/services/document_intelligence_service.py` |
| Citations | `backend/app/services/citation_service.py` |
| Security middleware | `backend/app/middleware/production.py` |
| Chat UI | `frontend/app/chat/page.tsx` |
| Stream hook | `frontend/hooks/useChatStream.ts` |
| API client | `frontend/lib/api.ts` |
| Migrations | `backend/alembic/versions/` |
| CI | `.github/workflows/ci.yml` |
| Railway deploy | `Dockerfile`, `railway.toml`, `backend/scripts/railway_web_and_worker.sh` |

---

## Revision log

| Date | Change |
|------|--------|
| 2026-05-25 | Initial audit document created |

---

*End of audit document. Update the Revision log when you complete priority items.*
