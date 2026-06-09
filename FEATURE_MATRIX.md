# OmniAI Feature Matrix

| Feature | Status | API | UI | Tests |
|---------|--------|-----|-----|-------|
| **Auth (OAuth-only)** | ✅ | `/auth/*` | `/login` | ✅ |
| **Streaming RAG chat** | ✅ | `/chat-stream` | `/chat` | ✅ |
| **Document upload + security** | ✅ | `/upload` | Chat workspace | ✅ |
| **Document intelligence** | ✅ | `/insights/*` | Workspace tab | ✅ |
| **Knowledge graph + GraphRAG** | ✅ | `/graph/*` | `/knowledge-graph` | ✅ |
| **Multi-agent platform** | ✅ | `/agents/multi-agent` | Dashboard traces | ✅ |
| **Deep research (Phase O)** | ✅ | `/research/*` | `/research` | ✅ |
| **Autonomous agents (Phase M)** | ✅ | `/agents/workspace/*` | `/agents` | ✅ |
| **Agent scheduling** | ✅ | RQ + inline | `/agents` | ✅ |
| **Agent memory** | ✅ | `/agents/workspace/{id}/memory` | — | ✅ |
| **Notifications** | ✅ | `/notifications` | — | Partial |
| **GitHub connector** | ✅ | `/connectors/github/*` + hub | `/connectors` | ✅ |
| **Notion connector** | ✅ | `/connectors/hub` | `/connectors` | ✅ |
| **Confluence connector** | ✅ | `/connectors/hub` | `/connectors` | — |
| **Google Drive connector** | ✅ | `/connectors/hub` | `/connectors` | — |
| **Dropbox connector** | ✅ | `/connectors/hub` | `/connectors` | — |
| **Enterprise search (source filter)** | ✅ | `/search?source=` | Chat search | — |
| **Agent marketplace (Phase P)** | ✅ | `/marketplace/*` | `/marketplace` | ✅ |
| **RBAC admin** | ✅ | `/audit/*` | `/admin/rbac` | ✅ |
| **Audit center** | ✅ | `/audit/*` | `/admin/audit` | ✅ |
| **Analytics + agent metrics** | ✅ | `/analytics/agents` | Dashboard | Partial |
| **Redis cache layer** | ✅ | `/analytics/cache` | — | ✅ |
| **LangGraph** | ❌ | — | — | — |
| **Team workspaces / ACLs** | ❌ | — | — | — |
| **Force-directed graph viz** | ❌ | — | List view only | — |
| **E2E Playwright** | ❌ | — | — | — |

**Legend:** ✅ Complete · Partial · ❌ Not implemented / deferred
