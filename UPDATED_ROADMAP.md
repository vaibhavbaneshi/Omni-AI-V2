# Updated Roadmap

**Last updated:** 2026-05-25  
**Current head:** `20260608_0016`

---

## Completed phases

| Phase | Name | Status |
|-------|------|--------|
| A–F | Core platform (RAG, chat, ingestion) | ✅ |
| G–K | Intelligence, graph, multi-agent, RBAC | ✅ |
| L | Production readiness & security | ✅ |
| **M** | **Autonomous agent workspace** | ✅ |
| **N** | **Enterprise knowledge hub** | ✅ |
| **O** | **Deep research mode** | ✅ |
| **P** | **Agent marketplace** | ✅ |

---

## Phase Q — Platform scale (proposed)

| Item | Priority |
|------|----------|
| Team workspaces + shared ACLs | P1 |
| OAuth callback UI for Google Drive / Dropbox | P1 |
| Notification bell in app shell | P2 |
| Force-directed knowledge graph visualization | P2 |
| LangGraph for complex multi-agent graphs | P3 |
| 90%+ test coverage + Playwright E2E | P2 |
| Prometheus metrics + Grafana dashboards | P2 |
| Connector webhooks (Notion/Slack live sync) | P2 |

---

## Phase R — Enterprise compliance (proposed)

| Item | Priority |
|------|----------|
| SOC2 audit logging enhancements | P1 |
| KMS-backed credential encryption | P1 |
| Data retention policies | P2 |
| SSO/SAML alongside OAuth | P2 |

---

## Phase S — AI platform (proposed)

| Item | Priority |
|------|----------|
| Custom model routing per agent | P2 |
| Agent-to-agent shared memory bus | P2 |
| Marketplace publisher workflow + revenue share | P3 |
| Public template API | P3 |

---

## Migration path

```bash
cd backend && alembic upgrade head
# Applies through 20260608_0016 (Phases M–P)
```

---

## Documentation index

| Doc | Purpose |
|-----|---------|
| [PHASE_COMPLETION_REPORT.md](PHASE_COMPLETION_REPORT.md) | M–P delivery summary |
| [ARCHITECTURE_UPDATE.md](ARCHITECTURE_UPDATE.md) | System design changes |
| [FEATURE_MATRIX.md](FEATURE_MATRIX.md) | Feature coverage table |
| [docs/architecture.md](docs/architecture.md) | Core architecture |
| [docs/security.md](docs/security.md) | Security controls |
| [docs/deployment.md](docs/deployment.md) | Deploy guide |
