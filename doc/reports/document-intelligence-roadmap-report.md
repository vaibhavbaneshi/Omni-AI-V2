# AI Document Intelligence Platform Roadmap Report

Generated: 2026-06-06

## Executive Summary

Omni AI already has the foundation of a production document intelligence platform: authenticated uploads, parsing for common document formats, session-scoped RAG, background indexing via FastAPI background tasks, progress polling, retrieval orchestration, analytics, safe error handling, and an evaluation scaffold.

This implementation pass strengthened the source attribution layer, which is a prerequisite for trustworthy multi-document RAG, conversational follow-ups, and document intelligence workflows. Uploaded PDFs now preserve page metadata during ingestion, chunks receive stable chunk identifiers, retrieved context is citation-prefixed, and source cards expose `[S#]`, page, and chunk references to users.

## Phase Audit

### Phase 1: Document Pipeline Validation

Current coverage:

- Upload validation exists in `backend/app/core/upload_validation.py`.
- Supported formats include PDF, TXT, Markdown, and DOCX.
- Temporary file storage, malware scanning hook, and audit logging exist.
- Ingestion stages are tracked through `queued`, `loading`, `chunking`, `embedding`, `vector_store`, `finalizing`, `ready`, and `failed`.
- Structured ingestion timing exists through `IngestionContext`.
- Frontend polls document status and detects stale indexing.

Gaps:

- No dedicated end-to-end validation command that uploads sample PDF/DOCX/TXT files and verifies Chroma retrieval.
- Large-file testing exists conceptually but should be formalized as benchmark tests.
- Multiple-file upload is supported through repeated uploads, but there is no batch-upload API.

Implemented in this pass:

- Added page-aware document loading API while preserving the old `load_document()` contract.
- Added tests for loader metadata contract.

### Phase 2: RAG Evaluation Framework

Current coverage:

- `backend/evaluation` contains RAG metrics and exporters.
- `doc/evaluation/rag-evaluation.md` documents evaluation concepts.
- Existing metrics include answer relevance, context precision/recall, hallucination heuristic, latency-adjacent usage tracking, and response quality.

Gaps:

- Evaluation dashboard is not yet exposed in the frontend.
- Upload/parsing/retrieval/benchmark test directories are not separated as requested by the roadmap.
- No scheduled benchmark runner.

Recommended next implementation:

- Add a CLI benchmark script that runs fixed document fixtures through upload, indexing, retrieval, and answer generation.
- Persist benchmark results to JSON and surface them in the analytics dashboard.

### Phase 3: Source Citations

Current coverage:

- Retrieval sources are streamed to the frontend.
- Source cards can display source chunks.

Gaps before this pass:

- Source metadata was not normalized.
- PDF page numbers were not preserved during chunking.
- No stable citation ID existed for answers.
- The prompt did not require `[S#]` citations.

Implemented in this pass:

- Added `backend/app/services/citation_service.py`.
- Added normalized fields: `citation_id`, `document_name`, `page_number`, `chunk_id`, and `source_reference`.
- Added citation-prefixed context chunks such as `[S1] Document: AWS_Architecture.pdf | Page: 12 | Chunk: 47`.
- Updated the answer prompt to cite factual claims using `[S#]`.
- Updated frontend source cards to display citation references.

### Phase 4: Multi-Document RAG

Current coverage:

- Session-scoped retrieval already searches all documents attached to the chat.
- Chroma metadata includes user, workspace, collection, session, document, and chunk identity.
- Retrieval uses semantic search, BM25, and optional reranking.

Gaps:

- Cross-document comparison should explicitly group and rank evidence by document.
- Context fusion does not yet produce a structured per-document evidence plan.
- Deduplication exists at chunking time, but retrieved evidence deduplication should be metadata-aware.

Recommended next implementation:

- Add a retrieval result fusion layer that ranks by document coverage, chunk relevance, and diversity.
- Add comparison prompts that force per-document contrast tables.

### Phase 5: Chat With Documents

Current coverage:

- Chat sessions, message persistence, session uploads, conversation summary, memory, and retrieval orchestration exist.
- Follow-up questions can use prior history and summary in `build_stream_prompt`.

Gaps:

- Follow-up resolution is implicit. There is no query rewriting step like “Expand point 3” → standalone retrieval query.
- Context window management is prompt-size based rather than budget-aware by source type.

Recommended next implementation:

- Add a query contextualizer before retrieval.
- Track source references used in prior assistant messages so follow-ups can rehydrate the same evidence.

### Phase 6: Document Intelligence

Current coverage:

- Summarization tool exists.
- Prompt formatting improvements support structured summaries.

Gaps:

- No dedicated document intelligence API for executive summaries, topics, mind maps, knowledge graphs, FAQs, action items, or key takeaways.
- No persisted analysis artifacts.
- Neo4j integration is not scaffolded.

Recommended next implementation:

- Add `DocumentInsight` model/table with insight type, source document, generated JSON payload, and provenance.
- Implement deterministic JSON-output prompts for executive summary, topics, action items, and graph triples.

### Phase 7: Production Hardening

Current coverage:

- Background processing exists through FastAPI `BackgroundTasks`.
- Structured ingestion logging, request logging, telemetry spans, token usage tracking, audit logs, upload validation, file scanning hook, prompt injection detection, caching, and safe errors exist.
- Metrics are available through analytics endpoints.

Gaps:

- FastAPI background tasks are not durable. A process restart can lose queued work.
- No Redis/Celery/RQ worker exists yet.
- Metrics are product analytics, not Prometheus-style operational metrics.
- Retry policies are limited.

Recommended queue choice:

- Use **RQ + Redis** for the next production step. It is simpler than Celery, adequate for document indexing jobs, supports retries, and is easier to operate for this codebase.
- Upgrade to Celery only if workflows become multi-step, scheduled, or require complex routing.

## Current Architecture Diagram

```text
Frontend
  |
  | upload / chat-stream / status polling
  v
FastAPI API
  |
  | auth, validation, file scan
  v
Temporary Upload Storage
  |
  v
FastAPI BackgroundTask or Sync Ingest
  |
  | parse -> chunk -> embed
  v
Chroma Vector Store
  |
  | retrieve + rerank
  v
LLM Provider
  |
  v
Streaming Answer + Sources
```

## Updated Architecture Diagram

```text
Frontend
  |
  | upload / chat / citations / progress
  v
FastAPI API
  |
  | auth, validation, audit, trace id
  v
Document Record + Durable Job Queue
  |
  v
Worker
  |
  | parse with page metadata
  | chunk with document/page/chunk IDs
  | embed with batch metrics
  v
Vector Store + Citation Metadata
  |
  | hybrid search -> rerank -> context fusion
  v
Citation-Normalized RAG Prompt
  |
  v
LLM Answer with [S#] Citations
  |
  v
Frontend Source Inspector
```

## Data Flow Diagram

```text
User File
  -> Upload Validation
  -> Malware Scan
  -> DocumentRecord
  -> Loader Parts
  -> Chunks + Metadata
  -> Embeddings
  -> Chroma
  -> Retrieval Sources
  -> Citation Normalizer
  -> Prompt Context
  -> Answer
  -> Source Cards
```

## Component Diagram

```text
Upload API
  - validation
  - audit log
  - document record

Ingestion Service
  - load_document_parts
  - chunk_document_parts
  - store_chunks
  - indexing progress

Retrieval Services
  - semantic search
  - BM25
  - reranker
  - citation normalization

Generation
  - prompt builder
  - LLM invoke
  - streaming route

Frontend
  - upload controls
  - progress polling
  - chat stream
  - source cards
```

## Sequence Diagram

```text
User -> Frontend: Upload PDF
Frontend -> API: POST /upload
API -> API: validate + scan
API -> DB: create DocumentRecord
API -> Worker: ingest document
Worker -> Loader: extract page-aware text
Worker -> Chunker: create chunks with metadata
Worker -> Embeddings: encode chunks
Worker -> Chroma: store vectors + metadata
User -> Frontend: Ask document question
Frontend -> API: POST /chat-stream
API -> Retrieval: hybrid search
Retrieval -> CitationService: normalize sources
API -> LLM: cited context prompt
LLM -> API: answer tokens with [S#]
API -> Frontend: tokens + source metadata
Frontend -> User: answer + clickable source cards
```

## Production Readiness Score

Current score: **72 / 100**

Strengths:

- Authenticated, user-scoped document handling.
- Session-scoped chat and document retrieval.
- Strong baseline upload validation and security hooks.
- Background indexing path and progress tracking.
- Observability and analytics foundation.
- Improved answer formatting and citation provenance.

Weaknesses:

- Background jobs are not durable.
- No formal benchmark dashboard.
- No persisted document intelligence artifacts.
- No query rewriting for follow-up document questions.
- No Prometheus/OpenTelemetry metrics endpoint.
- Batch multi-file upload is not implemented.

## Recommended Next Steps

1. Add RQ + Redis durable ingestion jobs with retries and dead-letter handling.
2. Add an end-to-end benchmark CLI using fixed PDF/DOCX/TXT fixtures.
3. Add a frontend evaluation dashboard for retrieval quality and latency.
4. Add query contextualization for conversational document follow-ups.
5. Add `DocumentInsight` persistence for summaries, topics, FAQs, action items, and graph triples.
6. Add source-context drawer navigation keyed by `document_id`, `page_number`, and `chunk_id`.
