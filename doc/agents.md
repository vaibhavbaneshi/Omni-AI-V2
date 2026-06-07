# OmniAI Agents

OmniAI uses a tool-calling orchestrator for in-chat routing and formal agent APIs for long-running workflows.

## Agent stack

```
User query
    │
    ▼
AgentOrchestrator.plan()          ← intent detection, mode, attachments
    │
    ├── retrieval (RAG)           ← hybrid search + rerank + citations
    ├── web_search                ← Tavily / Serper
    ├── document-analysis agent   ← Phase A insights
    ├── research agent            ← iterative retrieval + web + report
    ├── memory / calculator / summarizer
    │
    ▼
stream_response() or agent API response
```

**Code locations:**

| Component | Path |
|-----------|------|
| Orchestrator | `backend/app/agent/orchestrator.py` |
| Tool registry | `backend/app/agent/tools.py` |
| Chat integration | `backend/app/services/tool_agent.py` |
| Research agent | `backend/app/agent/research_agent.py` |
| Document analysis | `backend/app/agent/document_analysis_agent.py` |
| Formal APIs | `backend/app/api/agent_routes.py` |

---

## In-chat routing (orchestrator)

The orchestrator inspects the user query, chat mode, session attachments, and feature flags to pick a strategy:

| Strategy | When |
|----------|------|
| `hybrid-rerank` | Default document Q&A |
| `multi-document` | Comparison queries across session uploads |
| `web-rag-hybrid` | Needs external/web context |
| `document-analysis-agent` | Explicit insight/FAQ requests |
| `research-agent` | Deep research mode (`deep-research` or `ENABLE_DEEP_RESEARCH`) |

Stream metadata (`type: meta`) exposes `tool`, `strategy`, `agent`, `sources`, `report_id`, and `document_analysis` to the frontend.

### Feature flags

```env
ENABLE_AGENT_WORKFLOWS=true    # Master switch for /agents APIs
ENABLE_DEEP_RESEARCH=false     # Research agent (chat + API)
ENABLE_QUERY_REWRITING=true    # Follow-up query expansion
ENABLE_DOCUMENT_INTELLIGENCE=false  # Post-index insight generation
```

---

## Research agent

**Purpose:** Multi-iteration research with hybrid retrieval, web search, and a persisted structured report.

**Flow:**

1. `ResearchAgent.run()` loops up to `max_iterations` (default 3).
2. Each iteration: retrieve internal chunks → optional web search → accumulate evidence.
3. LLM synthesizes JSON report (title, executive summary, key findings, sources, open questions).
4. Report saved to `research_reports` table.

**API:**

```http
POST /agents/research
Content-Type: application/json
Authorization: Bearer <token>

{
  "query": "Compare vector databases for RAG",
  "session_id": 42,
  "workspace_id": "default",
  "max_iterations": 3
}
```

```http
GET /agents/research/{report_id}
```

Requires `ENABLE_AGENT_WORKFLOWS=true` and `ENABLE_DEEP_RESEARCH=true`.

**Chat integration:** Set mode to `deep-research` or enable deep research globally; orchestrator routes to research agent and returns `report_id` in stream meta.

---

## Document analysis agent

**Purpose:** Generate or reuse Phase A document insights (summary, FAQs, action items, metadata) for session uploads.

**Flow:**

1. Detect document-analysis intent ("generate FAQs", "summarize uploaded document", …).
2. List ready documents in the session.
3. Call `document_intelligence_service.generate_document_insights()` per document (or load cached).
4. Format grouped context for the LLM or API response.

**API:**

```http
POST /agents/document-analysis
Content-Type: application/json

{
  "session_id": 42,
  "document_id": 7,
  "workspace_id": "default",
  "force": false
}
```

Response includes `status`, `documents[]` with insight IDs, and `context_preview`.

**Related insight API:**

- `GET /documents/{id}/insights`
- `POST /documents/{id}/insights/generate`

---

## Tools

Registered in the orchestrator:

| Tool | Module | Role |
|------|--------|------|
| `retrieval` | `app/tools/retrieval.py` | Hybrid RAG with query rewriting |
| `web_search` | `app/tools/web_search_tool.py` | External search |
| `memory` | `app/tools/memory.py` | User long-term memory |
| `calculator` | `app/tools/calculator.py` | Safe math evaluation |
| `summarizer` | `app/tools/summarizer.py` | Conversation compression |

---

## Advanced RAG (Phase B)

Agents and retrieval share:

- **Query contextualizer** — rewrites follow-ups using chat history (`query_contextualizer_service.py`).
- **Weighted hybrid search** — semantic + BM25 via RRF (`hybrid_search.py`, env weights).
- **Multi-document service** — groups chunks by `document_id` for comparison prompts.

---

## Frontend indicators

Chat UI reads stream `meta` events to show:

- Agent badge (`research`, `document-analysis`)
- Source citations and `source_groups`
- `report_id` link for research reports
- Document analysis status

---

## Testing

```bash
cd backend
pytest tests/test_agents.py tests/test_advanced_rag.py tests/test_platform_services.py -q
```

Key scenarios: research report persistence, document analysis context formatting, orchestrator routing, API 403 when flags disabled.

---

## Related docs

- [Architecture](./architecture.md)
- [API reference](./api-reference.md)
- [Document intelligence roadmap](./reports/document-intelligence-roadmap-report.md)
