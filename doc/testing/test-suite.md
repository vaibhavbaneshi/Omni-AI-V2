# Testing Guide

Phase 5 test suite for OmniAI backend.

## Stack

- **pytest** — test runner
- **pytest-asyncio** — async test support
- **pytest-cov** — coverage reports
- **httpx** — HTTP client (via Starlette TestClient)
- **factory-boy** — model factories for integration tests

## Run locally

```bash
cd backend
pip install -r requirements-dev.txt
pytest -q
```

With coverage:

```bash
pytest --cov=app --cov=evaluation --cov-report=term-missing
```

## Test layout

| Path | Scope |
|------|--------|
| `tests/conftest.py` | SQLite in-memory DB, auth fixtures |
| `tests/factories.py` | User, ChatSession, Message factories |
| `tests/integration/` | API integration tests (auth, chat, sessions, memory, upload, health) |
| `tests/test_*.py` | Unit tests for services and core modules |

## Integration test database

Tests use **SQLite in-memory** with dependency override on `get_db`. No PostgreSQL required for CI.

`ENABLE_USAGE_TRACKING=false` in tests avoids analytics writes during middleware runs.

## Coverage policy

Coverage target ramps toward **80%**:

| Milestone | `fail_under` |
|-----------|----------------|
| Phase 5 (current) | 45% |
| Next increment | 60% |
| Target | 80% |

Heavy modules omitted from coverage denominator:

- `app/rag/*` (legacy CLI scripts)
- `app/main.py` (startup wiring)

## Areas covered

- **Auth** — JWT validation, `/users/me`
- **Chat** — `/chat-stream` NDJSON (mocked LLM/agent), legacy `/chat`
- **Sessions** — create, list, messages, rename, delete
- **Memory** — CRUD `/memory`
- **Upload** — TXT validation + mocked ingestion
- **Health** — liveness + deep readiness
- **Evaluation** — metrics + admin gate (unit)

## Related

- [Implementation plan](../implementation-plan.md)
- [Auth tests](./testing/auth-tests.md)
