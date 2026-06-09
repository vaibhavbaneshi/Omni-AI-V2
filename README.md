# OmniAI

<p align="center">
  <strong>Autonomous AI workspace + enterprise knowledge hub</strong><br/>
  OAuth-only · RAG · GraphRAG · Multi-agent · Deep research · Connectors · Marketplace
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="#features">Features</a> ·
  <a href="#deployment">Deployment</a> ·
  <a href="#security">Security</a> ·
  <a href="#roadmap">Roadmap</a>
</p>

---

## Overview

OmniAI is a production-grade AI workspace that combines **retrieval-augmented chat**, **autonomous agents**, **enterprise connectors**, and **verified deep research** in a single platform.

Built for engineers, teams, and operators who need more than a chat box: scheduled research, document monitoring, GitHub/Notion/Drive sync, knowledge graphs, and a marketplace of reusable agents.

> **Auth model:** OAuth-only (Google + GitHub). HttpOnly cookies + CSRF. No email/password.

---

## Architecture

```
                    ┌──────────────────┐
                    │   Next.js UI     │
                    │ chat · agents ·  │
                    │ connectors ·     │
                    │ marketplace      │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   FastAPI API    │
        ┌───────────┤ agents/connectors├───────────┐
        │           │ research/market  │           │
        │           └────────┬─────────┘           │
        │                    │                     │
   ┌────▼────┐         ┌─────▼─────┐        ┌─────▼─────┐
   │ Postgres│         │  Chroma   │        │ Redis/RQ  │
   └─────────┘         └───────────┘        └───────────┘
```

See [ARCHITECTURE_UPDATE.md](ARCHITECTURE_UPDATE.md) and [docs/architecture.md](docs/architecture.md).

---

## Features

| Capability | Description |
|------------|-------------|
| **Chat + RAG** | Streaming responses with hybrid retrieval and citations |
| **Autonomous agents** | Schedule research, doc monitoring, GitHub watches |
| **Deep research** | Plan → multi-hop retrieval → verification → report + export |
| **Connectors** | GitHub, Notion, Confluence, Google Drive, Dropbox |
| **Knowledge graph** | Entity extraction, GraphRAG, explorer UI |
| **Marketplace** | Install templates: research, code review, security audit, PM, … |
| **Admin** | RBAC, audit center, platform analytics |

Full matrix: [FEATURE_MATRIX.md](FEATURE_MATRIX.md)

---

## Quick start

### Prerequisites

- Python 3.11+, Node 20+, PostgreSQL, Redis (optional for queues/cache)

### Backend

```bash
cd backend
cp .env.example .env
pip install -r requirements.txt
alembic upgrade head    # → 20260608_0016
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_URL=http://localhost:8000` and OAuth keys in `backend/.env`.

### Tests

```bash
cd backend && pytest --cov=app -q
cd frontend && npm test
```

---

## Key routes

| Route | Purpose |
|-------|---------|
| `/login` | OAuth sign-in |
| `/chat` | Main workspace |
| `/agents` | Autonomous agent dashboard |
| `/connectors` | Connect & sync external sources |
| `/marketplace` | Browse & install agent templates |
| `/research` | Deep research reports |
| `/knowledge-graph` | Graph explorer |
| `/admin/audit` | Audit center |
| `/admin/rbac` | Role management |

---

## OAuth setup

1. Create Google OAuth client → redirect `http://localhost:8000/auth/google/callback`
2. Create GitHub OAuth app → callback `http://localhost:8000/auth/github/callback`
3. Set in `backend/.env`:

```env
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
FRONTEND_URL=http://localhost:3000
AUTH_COOKIE_ENABLED=true
```

---

## Connectors

| Connector | Connect via |
|-----------|-------------|
| GitHub | OAuth (`/connectors/github/authorize`) or hub |
| Notion | Integration token at `/connectors` |
| Confluence | Base URL + email + API token |
| Google Drive | OAuth access token via hub |
| Dropbox | OAuth access token via hub |

Details: [docs/connectors.md](docs/connectors.md)

---

## Agent system

- **Types:** research, document_monitor, github_monitor, custom
- **Scheduling:** manual, hourly, daily, weekly
- **Memory:** goals, plans, observations, outputs persisted per agent
- **Jobs:** Redis/RQ queue `agents` or inline execution

Install pre-built agents from `/marketplace` or create at `/agents`.

---

## Deep research

Pipeline: **Question → Planner → Multi-hop retrieval → Verification → Contradiction check → Synthesis**

- Export: `/research/reports/{id}/export/markdown` or `/pdf`
- API: `POST /research/run`

---

## Deployment

```bash
alembic upgrade head
# Railway: scripts/railway_web_and_worker.sh (API + RQ worker)
```

See [docs/deployment.md](docs/deployment.md).

---

## Security

- HttpOnly session cookies + CSRF middleware
- Upload quarantine, MIME/ZIP/PDF checks, optional ClamAV
- Encrypted connector credentials (Fernet)
- RBAC + audit logging

See [docs/security.md](docs/security.md) and [docs/security-audit-phase-l.md](docs/security-audit-phase-l.md).

---

## Performance

- Redis-backed retrieval, embedding, GraphRAG, and research caches
- Background ingestion via RQ
- Hybrid BM25 + vector search with optional reranker

---

## AI architecture

- **LLM routing:** Groq/OpenAI/Ollama via `model_router`
- **RAG:** Hybrid search → rerank → context injection
- **GraphRAG:** NetworkX neighborhood over extracted entities
- **Agents:** Custom orchestrator (not LangGraph) + specialist handlers
- **Observability:** LangSmith tracing (optional), Sentry, structured logs

---

## Roadmap

Phases **M–P complete**. Next: team workspaces, OAuth for Drive/Dropbox UI, graph visualization, E2E tests.

[UPDATED_ROADMAP.md](UPDATED_ROADMAP.md) · [PHASE_COMPLETION_REPORT.md](PHASE_COMPLETION_REPORT.md)

---

## Contributing

1. Fork and branch from `main`
2. Run `pytest` and `npm test`
3. Follow existing module layout (`app/agents`, `app/connectors`, …)
4. No placeholder/stub implementations in production paths

---

## License

Proprietary — OmniAI
