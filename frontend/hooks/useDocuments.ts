import { useCallback, useEffect, useRef, useState } from "react";
import {
  createCollection,
  deleteDocumentById,
  getDocumentStatus,
  indexingStageLabel,
  isDocumentFailed,
  isDocumentIndexing,
  isDocumentReady,
  listCollections,
  listDocuments,
  uploadDocument,
  ApiError,
  type DocumentCollection,
  type DocumentRecord,
} from "@/lib/api";
import { isBackendSessionId } from "@/lib/chat-sessions";
import {
  isSupportedUploadFilename,
  SUPPORTED_UPLOADS_LABEL,
} from "@/lib/supported-uploads";
import { sanitizeApiError } from "@/lib/user-facing-errors";

const MAX_UPLOAD_BYTES = 20 * 1024 * 1024;
const STALE_INDEXING_MS = 15 * 60 * 1000;

function belongsToSession(document: DocumentRecord, sessionId: number | null): boolean {
  if (!sessionId) return false;
  return document.session_id === sessionId;
}

function applyStatusUpdate(document: DocumentRecord, update: Awaited<ReturnType<typeof getDocumentStatus>>): DocumentRecord {
  if (update.status === "failed") {
    return {
      ...document,
      status: "failed",
      indexing_stage: "failed",
      indexing_error: update.indexing_error,
      chunks_created: update.chunks_created,
      embeddings_completed: update.embeddings_completed,
    };
  }
  if (update.status === "ready" || update.chunks_created > 0) {
    return {
      ...document,
      chunks_created: update.chunks_created,
      embeddings_completed: update.embeddings_completed,
      indexing_stage: "ready",
      status: "ready",
    };
  }
  return {
    ...document,
    chunks_created: update.chunks_created,
    embeddings_completed: update.embeddings_completed,
    indexing_stage: update.indexing_stage,
    indexing_error: update.indexing_error,
    elapsed_seconds: update.elapsed_seconds,
    stale: update.stale,
    stale_message: update.stale_message,
    status: "indexing",
  };
}

export function useDocuments(token?: string | null, sessionId?: string | null) {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [collections, setCollections] = useState<DocumentCollection[]>([]);
  const [activeCollectionId, setActiveCollectionId] = useState<number | null>(null);
  const [status, setStatus] = useState<"idle" | "uploading" | "indexing" | "success" | "error">(
    "idle"
  );
  const [message, setMessage] = useState<string | null>(null);
  const [uploadTargetSessionId, setUploadTargetSessionId] = useState<number | null>(null);

  const numericSessionId =
    sessionId && isBackendSessionId(sessionId) ? Number(sessionId) : null;

  const currentSessionIdRef = useRef<number | null>(numericSessionId);
  const pollTimerRef = useRef<number | null>(null);
  const indexingStartedAtRef = useRef<number | null>(null);

  useEffect(() => {
    currentSessionIdRef.current = numericSessionId;
  }, [numericSessionId]);

  const refresh = useCallback(async (sessionIdOverride?: number | null) => {
    const scopedSessionId = sessionIdOverride ?? numericSessionId;
    if (!token || !scopedSessionId) {
      if (scopedSessionId === numericSessionId) {
        setDocuments([]);
      }
      return [];
    }

    const [documentResult, collectionResult] = await Promise.all([
      listDocuments(token, { sessionId: scopedSessionId }),
      listCollections(token),
    ]);

    const scopedDocuments = documentResult.documents.filter((document) =>
      belongsToSession(document, scopedSessionId)
    );

    if (scopedSessionId === numericSessionId) {
      setDocuments(scopedDocuments);
      setCollections(collectionResult.collections);

      if (!activeCollectionId && collectionResult.collections.length > 0) {
        setActiveCollectionId(collectionResult.collections[0].id);
      }
    }

    return scopedDocuments;
  }, [activeCollectionId, numericSessionId, token]);

  useEffect(() => {
    setDocuments([]);
    setStatus("idle");
    setMessage(null);
    indexingStartedAtRef.current = null;

    if (pollTimerRef.current) {
      window.clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }

    if (!token || !numericSessionId) return;

    const id = window.setTimeout(() => {
      refresh().catch(() => undefined);
    }, 0);

    return () => window.clearTimeout(id);
  }, [numericSessionId, token, refresh]);

  const pollIndexingDocuments = useCallback(async () => {
    if (!token || !numericSessionId) return;

    const pending = documents.filter(
      (document) => isDocumentIndexing(document) && belongsToSession(document, numericSessionId)
    );
    if (pending.length === 0) {
      return;
    }

    setStatus("indexing");

    const updates = await Promise.all(
      pending.map(async (document) => {
        try {
          return await getDocumentStatus(document.id, token);
        } catch (error) {
          if (error instanceof ApiError && error.status === 404) {
            return { id: document.id, missing: true as const };
          }
          return null;
        }
      })
    );

    let becameReady = false;
    let becameFailed = false;
    let progressMessage = "";

    setDocuments((current) => {
      const next = current
        .filter((document) => belongsToSession(document, numericSessionId))
        .flatMap((document) => {
          const update = updates.find((item) => item && "id" in item && item.id === document.id);
          if (!update) return [document];
          if ("missing" in update && update.missing) {
            becameFailed = true;
            return [];
          }
          if (!update || !("status" in update)) return [document];

          const merged = applyStatusUpdate(document, update);
          if (merged.status === "ready") becameReady = true;
          if (merged.status === "failed") becameFailed = true;
          if (merged.status === "indexing") {
            progressMessage = update.stale_message
              ? update.stale_message
              : `${merged.filename}: ${indexingStageLabel(merged)}`;
          }
          return [merged];
        });
      return next;
    });

    if (currentSessionIdRef.current !== numericSessionId) {
      return;
    }

    if (becameReady) {
      setMessage("Document ready in this chat.");
      setStatus("success");
      setUploadTargetSessionId(null);
      indexingStartedAtRef.current = null;
      return;
    }

    if (becameFailed) {
      setMessage("Document indexing failed. Check backend logs or try uploading again.");
      setStatus("error");
      setUploadTargetSessionId(null);
      indexingStartedAtRef.current = null;
      return;
    }

    if (progressMessage) {
      setMessage(progressMessage);
    } else {
      const names = pending.map((document) => document.filename).join(", ");
      setMessage(`Indexing ${names}...`);
    }

    if (
      indexingStartedAtRef.current &&
      Date.now() - indexingStartedAtRef.current > STALE_INDEXING_MS
    ) {
      setStatus("error");
      setMessage(
        "Indexing is taking longer than expected. Check Railway backend logs for [EMBEDDING_*] or [ERROR] entries."
      );
    }
  }, [documents, numericSessionId, token]);

  useEffect(() => {
    const hasPendingForSession = documents.some(
      (document) => isDocumentIndexing(document) && belongsToSession(document, numericSessionId)
    );

    if (!token || !numericSessionId || !hasPendingForSession) {
      if (pollTimerRef.current) {
        window.clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
      return;
    }

    pollIndexingDocuments().catch(() => undefined);

    if (!pollTimerRef.current) {
      pollTimerRef.current = window.setInterval(() => {
        pollIndexingDocuments().catch(() => undefined);
      }, 1200);
    }

    return () => {
      if (pollTimerRef.current) {
        window.clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, [documents, numericSessionId, pollIndexingDocuments, token]);

  const upload = async (file: File, options?: { sessionId?: number | null }) => {
    const targetSessionId = options?.sessionId ?? numericSessionId;
    if (!targetSessionId) {
      const errorMessage = "Start or select a chat before uploading a document.";
      setStatus("error");
      setMessage(errorMessage);
      throw new Error(errorMessage);
    }
    if (!isSupportedUploadFilename(file.name)) {
      const errorMessage = `Unsupported file type. Supported formats: ${SUPPORTED_UPLOADS_LABEL}.`;
      setStatus("error");
      setMessage(errorMessage);
      throw new Error(errorMessage);
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      const errorMessage = `File exceeds the ${Math.floor(MAX_UPLOAD_BYTES / (1024 * 1024))}MB limit.`;
      setStatus("error");
      setMessage(errorMessage);
      throw new Error(errorMessage);
    }

    setUploadTargetSessionId(targetSessionId);
    indexingStartedAtRef.current = Date.now();
    currentSessionIdRef.current = targetSessionId;

    const viewingTargetSession = numericSessionId === targetSessionId;
    if (viewingTargetSession) {
      setStatus("uploading");
      setMessage("Uploading file...");
    }

    const validCollectionId =
      activeCollectionId && collections.some((item) => item.id === activeCollectionId)
        ? activeCollectionId
        : null;

    try {
      const result = await uploadDocument(file, token, {
        collectionId: validCollectionId,
        sessionId: targetSessionId,
      });

      const latestDocuments = await refresh(targetSessionId);
      const uploadedDocument =
        latestDocuments?.find((document) => document.id === result.document_id) ?? {
          id: result.document_id,
          filename: result.filename,
          size: file.size,
          updated_at: Date.now() / 1000,
          collection_id: result.collection_id,
          session_id: targetSessionId,
          chunks_created: result.chunks_created,
          indexing_stage: result.indexing ? "queued" : "ready",
          status: result.indexing ? ("indexing" as const) : ("ready" as const),
        };

      if (viewingTargetSession) {
        setDocuments((current) => {
          const scoped = current.filter(
            (document) =>
              belongsToSession(document, targetSessionId) && document.id !== uploadedDocument.id
          );
          return [uploadedDocument, ...scoped];
        });
      }

      if (result.indexing || uploadedDocument.chunks_created === 0) {
        if (viewingTargetSession) {
          setStatus("indexing");
          setMessage(`${result.filename}: Queued for indexing...`);
        }
        return { ...result, indexing: true };
      }

      if (viewingTargetSession) {
        setStatus("success");
        setMessage(`${result.message} (${result.chunks_created} chunks indexed)`);
        setUploadTargetSessionId(null);
        indexingStartedAtRef.current = null;
      }
      return result;
    } catch (error) {
      if (numericSessionId === targetSessionId) {
        setStatus("error");
        setMessage(
          sanitizeApiError(error instanceof ApiError ? error.message : undefined, {
            fallback: "Upload failed. Please try again.",
            status: error instanceof ApiError ? error.status : undefined,
          })
        );
      }
      setUploadTargetSessionId(null);
      indexingStartedAtRef.current = null;
      throw error;
    }
  };

  const remove = async (documentId: number) => {
    setDocuments((current) => current.filter((document) => document.id !== documentId));
    await deleteDocumentById(documentId, token);
    await refresh();
  };

  const addCollection = async (name: string) => {
    const collection = await createCollection(name, token);
    await refresh();
    setActiveCollectionId(collection.id);
    return collection;
  };

  const readyDocuments = documents.filter(isDocumentReady);
  const indexingDocuments = documents.filter(isDocumentIndexing);
  const failedDocuments = documents.filter(isDocumentFailed);
  const isUploadActiveForSession =
    uploadTargetSessionId !== null &&
    uploadTargetSessionId === numericSessionId &&
    (status === "uploading" || status === "indexing");

  return {
    documents,
    readyDocuments,
    indexingDocuments,
    failedDocuments,
    collections,
    activeCollectionId,
    setActiveCollectionId,
    status,
    message,
    isUploadActiveForSession,
    setStatus,
    setMessage,
    refresh,
    upload,
    remove,
    addCollection,
  };
}
