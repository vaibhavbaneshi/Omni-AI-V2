# Upload & Indexing Pipeline — Debugging Report

## A. Current Architecture

| Layer | Technology | Role |
|-------|------------|------|
| Frontend | Next.js (`app/chat/page.tsx`, `hooks/useDocuments.ts`) | Upload UI, polling, per-session document list |
| API | FastAPI (`app/api/upload_routes.py`) | Upload, list, status, delete |
| Storage | Temp dir (`tempfile.mkdtemp`) | File bytes until indexing completes |
| Metadata | PostgreSQL `documents` table | `chunks_created`, `indexing_stage`, progress |
| Background work | FastAPI `BackgroundTasks` | Runs `ingest_document_record()` after HTTP response |
| Loader | `app/services/document_loaders.py` | PDF, DOCX, TXT, CSV, XLSX extraction |
| Chunker | `documents_services.chunk_text()` | LangChain `RecursiveCharacterTextSplitter` |
| Embeddings | `app/services/embedding_service.py` | OpenAI / HuggingFace API / local PyTorch |
| Vector store | ChromaDB (`app/core/chroma_client.py`) | `PersistentClient` at `CHROMA_DB_PATH` |
| Status | `GET /documents/{id}/status` | Polled every 1.2s by frontend |

**No separate queue** (Redis/Celery). Indexing runs in-process via FastAPI background tasks on the same Railway dyno.

---

## B. End-to-End Flow Diagram

```
User selects file
       ↓
chat/page.tsx → processSelectedFile()
       ↓
ensureBackendChat() → POST /sessions (if needed)
       ↓
useDocuments.upload() → uploadDocument() → POST /upload?session_id=N
       ↓
upload_routes.upload_document()
  ├─ validate_document_upload()
  ├─ scan_uploaded_file()
  ├─ write temp file
  ├─ INSERT documents (indexing_stage=queued, chunks_created=0)
  └─ BackgroundTasks.add_task(ingest_document_record, document_id)
       ↓
HTTP 200 { indexing: true, document_id }
       ↓
Frontend polls GET /documents/{id}/status every 1.2s
       ↓
ingest_document_record()  [background]
  ├─ stage: loading   → load_document()
  ├─ stage: chunking  → chunk_text()
  ├─ stage: embedding → encode_texts() [HF/OpenAI/local]
  ├─ stage: vector_store → collection.add() [Chroma]
  ├─ stage: finalizing → chunks_created=N, indexing_stage=ready
  └─ delete temp file
       ↓
Status poll sees status=ready → UI shows ready chip
```

---

## C. Exact Call Chain

### Frontend
```
frontend/app/chat/page.tsx
  processSelectedFile()
    → ensureBackendChat()
    → useDocuments.upload()                    [hooks/useDocuments.ts]
      → uploadDocument()                       [lib/api.ts]
        → POST /upload?session_id={id}
      → refresh() → GET /documents?session_id={id}
      → setInterval pollIndexingDocuments()
        → getDocumentStatus() → GET /documents/{id}/status
```

### Backend upload
```
app/api/upload_routes.py
  upload_document()
    → validate_document_upload()               [app/core/upload_validation.py]
    → scan_uploaded_file()                     [app/services/file_scanner.py]
    → DocumentRecord INSERT
    → background_tasks.add_task(ingest_document_record, id)
```

### Backend indexing
```
app/services/ingestion_service.py
  ingest_document_record(document_id)
    → app/services/documents_services.py
        process_document(db, telemetry)
          → load_document()                    [app/services/document_loaders.py]
          → chunk_text()
          → store_chunks()
            → encode_texts()                   [app/services/embedding_service.py]
            → get_or_create_collection().add() [app/core/chroma_client.py]
    → mark_indexing_ready()                    [app/services/indexing_progress.py]
```

---

## D. Where the Process Stops (Observed Failure Modes)

| Symptom | Likely stop point | Cause |
|---------|-------------------|-------|
| UI stuck "Indexing..." forever, `chunks_created=0` | Background task never ran or still running | Railway OOM kill, HF API hang, embedding batch loop |
| UI stuck after page refresh | Frontend polling gated incorrectly | **Fixed:** polling no longer requires `uploadTargetSessionId` |
| Status always `indexing`, backend silent | `ingest_document_record` exception | Missing HF token, rate limit, Chroma error — previously deleted row silently |
| 10+ minutes | `embedding` stage | HF Inference API cold start + 120s timeout × many batches |
| Never reaches `ready` | `chunks_created` never updated | Background task died when Railway restarted container |

---

## E. Root Causes Identified

1. **Frontend polling bug (critical)** — `pollIndexingDocuments()` returned early unless `uploadTargetSessionId === numericSessionId`. After refresh or session navigation, pending documents were never polled → infinite "Indexing".

2. **No granular progress** — Only `chunks_created > 0` marked complete. No stage field → UI could only show generic "Indexing file".

3. **Silent failure** — On ingestion error, document row was **deleted**. Frontend kept showing local indexing chip; API returned 404 on poll with no failed state.

4. **Embedding bottleneck (Railway)** — `EMBEDDING_PROVIDER=huggingface` with large files → many sequential API batches (32 texts × 120s timeout each). Can exceed 10 minutes legitimately or hang on 503.

5. **BackgroundTasks reliability** — Not durable across deploys/restarts. No external worker queue.

---

## F. Logs Added

Structured events via `app/services/ingestion_telemetry.py` (`omniai.ingestion` logger):

| Event | When |
|-------|------|
| `[UPLOAD_COMPLETE]` | Background ingest starts |
| `[LOADING_START/COMPLETE]` | Document text extraction |
| `[CHUNKING_START/COMPLETE]` | chunk_count |
| `[EMBEDDING_START/PROGRESS/COMPLETE/RETRY]` | Per batch, provider, duration |
| `[VECTOR_DB_INSERT_START/COMPLETE]` | Chroma batch |
| `[FINALIZING_START/COMPLETE]` | DB status → ready |
| `[INDEXING_COMPLETE]` | Success |
| `[SLOW_STAGE]` | Stage exceeds threshold (30s/60s) |
| `[ERROR]` | Exception with stack trace |

Railway: filter logs by `omniai.ingestion` or `[EMBEDDING`.

---

## G. Fixes Implemented

1. **DB progress columns** — migration `20260531_0007`: `indexing_stage`, `indexing_error`, `embeddings_completed`, timestamps.

2. **Stage updates** during ingest — loading → chunking → embedding → vector_store → finalizing → ready/failed.

3. **Failed state persisted** — row kept with `indexing_stage=failed` + error message (not deleted).

4. **Frontend polling fixed** — always polls pending docs for current session.

5. **Granular UI labels** — "Loading document...", "Generating embeddings...", etc.

6. **HF embedding retries** — 3 attempts with backoff on 503/429/timeout.

7. **Stale detection** — backend + frontend warn after 15 minutes.

8. **404 on poll** — removes ghost indexing chip from UI.

---

## H. Additional Recommendations

1. **Run migration on Railway** — `alembic upgrade head` (auto on startup).

2. **Prefer OpenAI embeddings** on Railway — faster and more reliable than HF Inference cold starts.

3. **Move to durable queue** — Celery/RQ + Redis so indexing survives restarts.

4. **Cap `INGEST_MAX_CHUNKS=150`** on production to limit embedding time.

5. **Monitor logs** — search for `[SLOW_STAGE]` or `[ERROR]` after failed uploads.

6. **Consider Chroma Cloud / pgvector** — reduce local disk + memory pressure on Railway.

---

## Quick Debug Checklist

```bash
# 1. Check document status
curl -H "Authorization: Bearer $TOKEN" \
  https://your-backend/documents/{document_id}/status

# 2. Railway logs
grep -E '\[EMBEDDING|ERROR|INDEXING|SLOW_STAGE\]' backend.log

# 3. Verify env
EMBEDDING_PROVIDER=huggingface|openai
HF_TOKEN or OPENAI_API_KEY set
INGEST_IN_BACKGROUND=true
```

Expected healthy status progression:
`queued → loading → chunking → embedding → vector_store → finalizing → ready`
