# OmniAI

Production RAG chat platform with OAuth-only authentication, document intelligence, knowledge graphs, and multi-agent research.

## Stack

- **Backend:** FastAPI, PostgreSQL, ChromaDB, Redis/RQ
- **Frontend:** Next.js, TypeScript
- **Auth:** Google + GitHub OAuth (HttpOnly cookies)

## Quick start

```bash
# Backend
cd backend
cp .env.example .env
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
pnpm install
pnpm dev
```

Set `NEXT_PUBLIC_API_URL=http://localhost:8000` and configure OAuth keys in `backend/.env`.

## Authentication

OmniAI is **OAuth-only**. Sign in at `/login` with Google or GitHub. Tokens are stored in **HttpOnly cookies** — never in URLs or localStorage.

## Key features

- Streaming chat with RAG citations
- Document upload with quarantine + security scanning
- Document intelligence (summaries, FAQs, timeline, entities)
- Knowledge graph + GraphRAG
- Multi-agent platform with trace dashboard
- Deep research reports with verification
- GitHub connector (repo sync)
- RBAC + audit center (admin UI)

## Admin routes

| Route | Purpose |
|-------|---------|
| `/admin/audit` | Audit center dashboard |
| `/admin/rbac` | Role assignment |
| `/research` | Deep research UI |

## Documentation

- [Architecture](docs/architecture.md)
- [Deployment](docs/deployment.md)
- [Security](docs/security.md)
- [Connectors](docs/connectors.md)
- [Phase L report](docs/phase-l-implementation-report.md)

## License

Proprietary — OmniAI
