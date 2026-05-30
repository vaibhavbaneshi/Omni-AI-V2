# Model routing

Phase 7 adds dynamic LLM selection while preserving backward compatibility with the single-provider `LLM_PROVIDER` default.

## How routing works

1. **User override** — If the client sends `model=<catalog-id>` on `/chat-stream`, that model is used when configured.
2. **Auto route** — When `model=auto` or omitted, `ModelRouter` picks a model from workspace mode and query shape.
3. **Fallback** — When `MODEL_ROUTING_ENABLED=false`, routing rules are skipped and the default Groq model is used (explicit `model` overrides still apply).

### Routing rules (when enabled)

| Signal | Model |
|--------|--------|
| `mode=coding` or coding-like query | DeepSeek Chat (if `DEEPSEEK_API_KEY` set) |
| `mode=research` / `analyst` or reasoning keywords | Llama 3.3 70B |
| Short query (≤80 chars) | Llama 3.1 8B Instant |
| Default | Llama 3.3 70B |

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `MODEL_ROUTING_ENABLED` | `true` | Toggle automatic routing |
| `GROQ_FAST_MODEL` | `llama-3.1-8b-instant` | Fast / short queries |
| `GROQ_REASONING_MODEL` | `llama-3.3-70b-versatile` | Research & reasoning |
| `GROQ_GEMMA_MODEL` | `gemma2-9b-it` | Optional Gemma route |
| `DEEPSEEK_API_KEY` | — | Enables DeepSeek for coding |
| `DEEPSEEK_MODEL` | `deepseek-chat` | DeepSeek model id |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | DeepSeek API base |

Existing `LLM_PROVIDER`, `GROQ_API_KEY`, and `GROQ_MODEL` remain the global fallback.

## API

- `GET /models` — catalog with availability flags
- `GET /models/route?mode=&query=&model_id=` — preview resolved route
- `POST /chat-stream?model=auto` — optional model override

Stream `meta` events include a `model` object:

```json
{
  "id": "deepseek-chat",
  "provider": "deepseek",
  "model_name": "deepseek-chat",
  "display_name": "DeepSeek Chat",
  "routing_reason": "coding_task"
}
```

## Frontend

- Chat model selector loads from `GET /models`
- Default model preference is stored in `localStorage` (`omniai.default_model_id`)
- Settings → AI Behavior uses the same catalog

## Railway / Vercel

No deploy changes required. Groq-only deploys work unchanged. Add `DEEPSEEK_API_KEY` when you want coding routes to use DeepSeek.
