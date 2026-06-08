# Connectors

## GitHub (implemented)

### Setup

1. Use existing `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` (same as login OAuth)
2. Authorize connector: `GET /connectors/github/authorize` (requires login)
3. List repos: `GET /connectors/github/repos`
4. Sync repo: `POST /connectors/github/sync`

### Sync behavior

- Creates **GitHub** collection in workspace
- Indexes README, markdown, source, docs (size-capped)
- Incremental sync via commit SHA comparison
- Files queued for RQ ingestion

### Supported file types

`.md`, `.markdown`, `.txt`, `.py`, `.js`, `.ts`, `.tsx`, `.json`, `.yaml`, `.yml`, `.rst`, `.html`

## Stubs (not implemented)

| Connector | Status |
|-----------|--------|
| Notion | Stub |
| Confluence | Stub |
| Slack | Stub |
