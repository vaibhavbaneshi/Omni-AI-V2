# LangSmith Setup

LangSmith provides trace dashboards for LLM calls, RAG retrieval, and agent routing.

## 1. Create a LangSmith account

1. Sign up at [https://smith.langchain.com](https://smith.langchain.com)
2. Create an API key under **Settings → API Keys**
3. Create a project (e.g. `OmniAI-Production`)

## 2. Configure environment variables

### Local (`.env`)

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_...
LANGCHAIN_PROJECT=OmniAI
```

### Railway

Add the same variables in **Railway → Backend Service → Variables**:

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=<your-key>
LANGCHAIN_PROJECT=OmniAI-Production
```

Redeploy after saving. Tracing is **opt-in** — default is `LANGCHAIN_TRACING_V2=false`, so existing deployments are unaffected.

## 3. What gets traced

| Component | Trace name | When |
|-----------|------------|------|
| LLM generate | `omni.llm.generate` | Title, summary, legacy `/chat` |
| LLM stream | `omni.llm.stream` (spans) | `/chat-stream` responses |
| RAG retrieval | `retrieval.hybrid` | Hybrid search + rerank |
| Document ingest | `document.ingest` | File upload pipeline |
| Agent orchestrator | Various `traced_span` events | Route planning, tools |

Structured JSON logs also emit `llm.complete` events with latency and token counts regardless of LangSmith.

## 4. View traces

1. Open [https://smith.langchain.com](https://smith.langchain.com)
2. Select your project (`LANGCHAIN_PROJECT`)
3. Filter by run name or trace ID
4. Correlate with API responses using the `X-Trace-Id` response header

## 5. Troubleshooting

| Issue | Fix |
|-------|-----|
| No traces appearing | Confirm `LANGCHAIN_TRACING_V2=true` and API key is set |
| Traces delayed | LangSmith batches uploads; wait 30–60 seconds |
| Railway still not tracing | Redeploy backend after env change; check startup logs |
| Import errors | `langsmith` is in `requirements.txt` — rebuild Docker image |

## 6. Cost and privacy

- LangSmith stores prompts and completions when tracing is enabled
- Disable tracing in production if you handle sensitive documents
- Use separate projects for staging vs production
