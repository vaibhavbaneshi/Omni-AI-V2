# OmniAI Phases A–F — Implementation Plan

**Last updated:** 2026-06-03  
**Principle:** Extend existing infrastructure; do not rebuild working systems.

---

## Existing assets to reuse

| Capability | Location |
|------------|----------|
| Document upload + indexing | `upload_routes.py`, `ingestion_service.py`, RQ queue |
| Text extraction | `document_loaders.py` |
| Hybrid retrieval | `hybrid_search.py`, `reranker_service.py` |
| Citations | `citation_service.py` |
| LLM calls | `llm_invoke.py`, `model_router.py` |
| Agents | `agent/orchestrator.py`, `tools/*` |
| Collections | `DocumentCollection` model, `/collections` API |
| Analytics / eval | `analytics_service.py`, `evaluation/runner.py` |
| Security | `sanitize.py`, `upload_validation.py`, `security_audit_service.py` |
| Chat UI | `frontend/app/chat/page.tsx`, `useDocuments`, `MarkdownMessage` |

---

## Phase A — Document Intelligence (IN PROGRESS)

### Deliverables
- [x] Plan
- [ ] `document_insights` table (JSON payload: summary, FAQs, action items, keywords/topics/entities/dates/stats)
- [ ] `document_intelligence_service.py` — load doc text, LLM structured JSON, persist
- [ ] `GET/POST /documents/{id}/insights` API
- [ ] Optional post-index generation (`ENABLE_DOCUMENT_INTELLIGENCE`)
- [ ] Frontend `DocumentInsightsPanel` in chat when document ready
- [ ] Tests

### Files (new/modified)
- `backend/app/models/document_insight.py`
- `backend/alembic/versions/20260603_0010_document_insights.py`
- `backend/app/schemas/document_insight_schemas.py`
- `backend/app/services/document_intelligence_service.py`
- `backend/app/api/insights_routes.py`
- `frontend/hooks/useDocumentInsights.ts`
- `frontend/components/chat/document-insights-panel.tsx`

---

## Phase B — Advanced RAG (COMPLETED)

| Item | Reuse | Work |
|------|-------|------|
| Query rewriting | `conversation_service`, `llm_invoke` | `query_contextualizer_service.py`; wired in `retrieval_tool` / `rag_service` |
| Hybrid retrieval | `hybrid_search.py` | Weighted RRF merge + `benchmark_hybrid_retrieval` in `evaluation/runner.py` |
| Multi-doc analysis | Session-scoped retrieval | `multi_document_service.py` — group by `document_id`, comparison prompts |

---

## Phase C — AI Agents

| Agent | Reuse | Work |
|-------|-------|------|
| Research | `research_workflow.py`, orchestrator | Formalize as `ResearchAgent` workflow with report artifact |
| Document analysis | Phase A service | `DocumentAnalysisAgent` — chain: load → insights → persist (automate Phase A steps) |

---

## Phase D — Knowledge Workspace

| Item | Reuse | Work |
|------|-------|------|
| Folders | Client-only pins in chat | `chat_folders` table or `ChatSession.folder_id`; API + persist sidebar |
| Collections | `DocumentCollection` | DELETE/PATCH collections, move documents, collection UI |
| Global search | PostgreSQL full-text | `search_service.py` — messages, documents, insights; `GET /search?q=` |

---

## Phase E — Security Completion

| Item | Status | Work |
|------|--------|------|
| Redis rate limit | In-memory only | `RedisRateLimitMiddleware` using existing `redis_client.py` |
| Request validation | Partial (query params) | Pydantic bodies for chat/upload |
| Upload validation | Done | Extend tests |
| Abuse detection | Prompt injection only | Rate-limit + audit patterns |
| Security tests | Partial | `tests/integration/test_security_integration.py` |

---

## Phase F — Platform Quality

| Item | Work |
|------|------|
| Sentry | `sentry-sdk` in `main.py` + Next.js `instrumentation.ts` |
| Testing 80%+ | Expand integration tests per module |
| Docs | `doc/architecture.md`, `doc/api-reference.md`, `doc/deployment.md`, `doc/security.md`, `doc/agents.md` |

---

## Execution order

1. **Phase A** (this sprint) — persisted insights + UI
2. **Phase B** — query rewriting + multi-doc grouping
3. **Phase C** — agent workflows wrapping A + B
4. **Phase D** — workspace + search
5. **Phase E** — Redis rate limits + validation
6. **Phase F** — Sentry, coverage, docs

Each phase: migration → service → API → frontend → tests → build verify.
