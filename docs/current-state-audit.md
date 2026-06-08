# OmniAI Current State Audit

**Date:** 2026-05-25  
**Lead architect review** — baseline before Phases G–K  
**Sources:** Full repo scan, `doc/implementation-plan.md`, `doc/phases-a-f-implementation-plan.md`, `doc/reports/document-intelligence-roadmap-report.md`, `doc/reports/omniai-repository-audit-2026-05-25.md`

---

## 1. Existing Features (verified in code)

| Domain | Features |
|--------|----------|
| **Auth** | OAuth GitHub/Google, JWT access + refresh rotation, session registry, `/users/me` |
| **Chat** | NDJSON streaming, modes, model selection, orchestrator routing, citations |
| **Sessions** | CRUD, pin/folder, title refine, message history |
| **Documents** | Upload, validation, RQ/background indexing, collections, session scope |
| **RAG** | Hybrid search, rerank, query rewriting, multi-doc comparison path |
| **Intelligence** | `document_insights` table, generate API, workspace UI sheet |
| **Agents** | Research + document-analysis agents, `/agents/*` |
| **Workspace** | Folders, collections, global search |
| **Analytics** | DB metrics, admin API, Recharts dashboard |
| **Evaluation** | Backend runner, metrics, admin API, CI smoke |
| **Security** | Rate limits, audit logs, headers, abuse detection, upload validation |
| **Ops** | Sentry, LangSmith env, migrations, Railway scripts, health probes |

---

## 2. Completed Roadmap Items

### Original phases (A–F + 1–7)
- Phases 1–4, 6–7: largely complete per `doc/implementation-plan.md`
- Phases A–E: complete per `doc/phases-a-f-implementation-plan.md`
- Phase F: partial (Sentry yes; 80% coverage gate not met)

### Document intelligence (partial A + roadmap Phase 3)
- Citation service, page metadata, `[S#]` prompts
- Persisted insights (summary, FAQs, actions, metadata)
- Chroma fallback when upload file cleaned post-index

---

## 3. Partially Implemented Features

| Feature | Gap |
|---------|-----|
| Session expiration UX | Redirect exists; toast + error flash before redirect |
| Chat delete | Optimistic UI; stale `listChatSessions` can restore deleted chat |
| Upload | Session ref desync after `local-*` → backend promotion |
| Response formatting | Prompt-driven; streaming parses incomplete Markdown |
| Document intelligence | Auto-gen off (`ENABLE_DOCUMENT_INTELLIGENCE=false`); no timeline/entity tables |
| Auth | `auth_routes.py` missing — OAuth-only |
| Research agent | `ENABLE_DEEP_RESEARCH=false` |
| Malware scan | No-op hook |
| Billing | Mock invoices |
| Performance | In-memory retrieval cache only |
| Testing | 78.3% coverage; no frontend tests |

---

## 4. Missing Features (G–K scope)

| Phase | Missing |
|-------|---------|
| **G** | Toast on expiry, delete race fix, upload first-try fix, response formatter layer |
| **H** | `document_timeline`, `document_entities` tables, timeline extraction, entity normalization, auto insights default |
| **I** | Knowledge graph (Neo4j/NetworkX), GraphRAG, graph UI |
| **J** | Multi-agent LangGraph/CrewAI, planner/critic flow, agent dashboard |
| **K** | Deep research reports, workspace connectors, RBAC, audit center UI |
| **Cross-cutting** | Redis embedding cache, 90% coverage, full doc set under `docs/` |

---

## 5. Technical Debt

- Monolithic `frontend/app/chat/page.tsx` (~1900 lines)
- Large `upload_routes.py`
- `.coveragerc` omits core modules (`chat_routes`, `rag_service`, `upload_routes`)
- Stale planning docs (Phase A marked in progress)
- Root `README.md` stub
- DuckDuckGo HTML scraping for web search
- OAuth tokens in callback URL

---

## 6. Security Gaps

| Severity | Item |
|----------|------|
| Critical | No email/password API (`auth_routes.py` absent) |
| High | Malware scanner noop; OAuth token in URL |
| Medium | Prompt injection log-only; in-memory rate limit fallback |
| Low | No CSRF (acceptable for Bearer API) |

Controls in place: JWT, CORS validation, upload validation, audit logs, Markdown `skipHtml`, user-scoped Chroma.

---

## 7. Performance Bottlenecks

1. Chroma on local disk (ephemeral without volume)
2. In-memory retrieval cache (`retrieval_cache.py`)
3. API + RQ worker in one Railway container
4. CrossEncoder reranker RAM
5. Sync SQLAlchemy

---

## 8. Database Schema Review

**Migrations:** 12 through `20260605_0012` (workspace folders)

| Table | Purpose |
|-------|---------|
| `users`, `user_settings`, `user_sessions` | Auth + preferences |
| `chat_sessions`, `messages`, `conversation_summaries` | Chat |
| `documents`, `document_collections` | Uploads |
| `document_insights` | Intelligence JSON payload |
| `chat_folders` | Workspace organization |
| `research_reports` | Research agent output |
| `api_usage`, `model_usage`, `token_usage` | Analytics |
| `security_audit_logs` | Security audit |
| `user_memories` | Long-term memory facts |

**Gaps for G–K:** `document_timeline`, `document_entities`, RBAC roles, knowledge graph nodes/edges, agent trace tables.

---

## 9. API Review

**Mounted routers** (`main.py`): user, chat, upload, session, oauth, memory, evaluation, analytics, model, settings, queue, insights, agents, folders, search.

**Gaps:** `/graph/*`, multi-agent trace APIs, connector webhooks, RBAC middleware, batch upload.

**Health:** `/health/live`, `/health/ready`, `/health/migrations` — production-ready pattern.

---

## 10. Frontend Review

| Area | Status |
|------|--------|
| Chat UI | Feature-rich; needs stability fixes (G) |
| Workspace sheet | Collections + intelligence (recent) |
| Dashboard | Real analytics via `useAnalytics` |
| Settings | Profile, 2FA, billing mock |
| Auth pages | OAuth only |
| Tests | None |
| Toast system | Missing |

---

## Roadmap Completion %

| Track | % |
|-------|---|
| Phases 1–7 (original) | **~82%** |
| Phases A–F | **~88%** |
| Document intelligence roadmap | **~65%** |
| Phases G–K (not started) | **~5%** (issues identified) |
| **Overall platform** | **~78%** |

---

## Recommended Implementation Order

1. **Phase G** — Production stabilization (session, delete, upload, formatter) ← **NOW**
2. **Phase H** — Document Intelligence 2.0 (timeline, entities, auto-gen) ← **NOW**
3. **Phase I** — Knowledge graph foundation (NetworkX + optional Neo4j)
4. **Phase J** — Multi-agent orchestration (LangGraph)
5. **Phase K** — Deep research + RBAC + audit center + connectors
6. **Cross-cutting** — Redis caches, security hardening, 90% tests, `docs/` refresh

---

## Phase G–K execution status

| Phase | Status | Notes |
|-------|--------|-------|
| G | ✅ Complete (2026-05-25) | Session toast, delete race, upload fix, response formatter |
| H | ✅ Complete (2026-05-25) | Timeline/entity tables, auto insights, UI |
| I | ✅ Complete (2026-05-25) | Graph service, GraphRAG, `/graph/*`, workspace Graph tab |
| J | ✅ Complete (2026-05-25) | Multi-agent platform, traces API, dashboard panel |
| K | ✅ Complete (2026-05-25) | RBAC, audit/connectors API, deep research verification |

*Update this table as phases complete.*
