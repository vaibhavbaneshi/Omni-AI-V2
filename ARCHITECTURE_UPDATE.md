# Architecture Update — Phases M–P

**Alembic head:** `20260608_0016`

---

## System overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Next.js Frontend                         │
│  /chat  /agents  /connectors  /marketplace  /research  /graph   │
└────────────────────────────┬────────────────────────────────────┘
                             │ HttpOnly cookies + CSRF
┌────────────────────────────▼────────────────────────────────────┐
│                      FastAPI Application                         │
│  ┌─────────────┐ ┌──────────────┐ ┌────────────┐ ┌────────────┐ │
│  │ app/agents  │ │ app/connectors│ │app/research│ │ marketplace│ │
│  └──────┬──────┘ └──────┬───────┘ └─────┬──────┘ └─────┬──────┘ │
│         │               │               │              │         │
│  ┌──────▼───────────────▼───────────────▼──────────────▼──────┐ │
│  │ app/agent (orchestrator, multi-agent, research_agent)       │ │
│  └──────┬─────────────────────────────────────────────────────┘ │
│         │ RAG · GraphRAG · hybrid search · web search           │
└─────────┼─────────────────────────────────────────────────────┘
          │
    ┌─────▼─────┐  ┌──────────┐  ┌─────────┐  ┌──────────────┐
    │ PostgreSQL │  │ ChromaDB │  │ Redis/RQ │  │ External APIs │
    └────────────┘  └──────────┘  └─────────┘  └──────────────┘
```

---

## New modules

### `app/agents/` (Phase M)

| Component | Role |
|-----------|------|
| `registry.py` | Agent type catalog + handler dispatch |
| `lifecycle.py` | CRUD, pause/resume, scheduling metadata |
| `executor.py` | Run agents, persist executions, notify |
| `scheduler.py` | Next-run computation, RQ registration |
| `memory.py` | Goals, plans, observations, outputs |
| `handlers/` | research, document_monitor, github_monitor, custom |

### `app/connectors/` (Phase N)

| Component | Role |
|-----------|------|
| `base.py` | Connector interface |
| `sync_engine.py` | Connection CRUD, sync runs, status |
| `indexing.py` | Shared document ingestion from connector content |
| `github.py`, `notion.py`, … | Provider implementations |
| `credential_crypto.py` | Fernet encryption at rest |

### `app/research/` (Phase O)

| Stage | Module |
|-------|--------|
| Planning | `planner.py` |
| Retrieval | `multi_hop.py` |
| Verification | `verification.py` |
| Contradiction | `contradiction.py` |
| Synthesis | `report_generator.py` |
| Export | `export.py` |
| Orchestration | `pipeline.py` |

### `app/marketplace/` (Phase P)

- Built-in templates seeded at startup
- Install creates `autonomous_agents` linked via `marketplace_installs`

---

## Database additions (0016)

| Table | Purpose |
|-------|---------|
| `autonomous_agents` | User agent definitions + schedule |
| `agent_executions` | Run history, tokens, latency |
| `agent_memory_entries` | Goals, plans, observations |
| `notifications` | In-app alerts |
| `connector_connections` | Encrypted per-user connector creds |
| `connector_sync_runs` | Sync history |
| `marketplace_templates` | Public agent templates |
| `marketplace_template_versions` | Version history |
| `marketplace_installs` | User installs + favorites |

---

## Background jobs

| Queue | Job | Trigger |
|-------|-----|---------|
| `ingest` | Document ingestion | Upload / connector sync |
| `agents` | `run_agent_job` | Schedule or manual run |

Worker: `app/worker.py` with `with_scheduler=True`

---

## Security

- Connector credentials encrypted via Fernet (derived from `JWT_SECRET_KEY`)
- OAuth-only auth unchanged (Phase L)
- CSRF on mutating cookie-authenticated requests
- RBAC admin paths for audit/platform analytics

---

## Caching

- Redis namespaces: `retrieval`, `embedding`, `graph_rag`, `research`
- Connector sync does not bypass upload security pipeline

---

## Intentional non-changes

- **LangGraph:** not introduced; custom orchestrator retained
- **Team ACLs:** deferred; user-scoped data model unchanged
