import { useCallback, useEffect, useRef, useState } from "react";
import {
  createCollection,
  deleteDocumentById,
  getDocumentStatus,
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

function belongsToSession(document: DocumentRecord, sessionId: number | null): boolean {
  if (!sessionId) return false;
  return document.session_id === sessionId;
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

  useEffect(() => {
    currentSessionIdRef.current = numericSessionId;
  }, [numericSessionId]);

  const refresh = useCallback(async () => {
    if (!token || !numericSessionId) {
      setDocuments([]);
      return [];
    }

    const [documentResult, collectionResult] = await Promise.all([
      listDocuments(token, { sessionId: numericSessionId }),
      listCollections(token),
    ]);

    const scopedDocuments = documentResult.documents.filter((document) =>
      belongsToSession(document, numericSessionId)
    );

    setDocuments(scopedDocuments);
    setCollections(collectionResult.collections);

    if (!activeCollectionId && collectionResult.collections.length > 0) {
      setActiveCollectionId(collectionResult.collections[0].id);
    }

    return scopedDocuments;
  }, [activeCollectionId, numericSessionId, token]);

  useEffect(() => {
    setDocuments([]);
    setStatus("idle");
    setMessage(null);

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
      if (status === "indexing" && uploadTargetSessionId === numericSessionId) {
        setStatus("success");
      }
      return;
    }

    if (uploadTargetSessionId !== numericSessionId) {
      return;
    }

    setStatus("indexing");

    const updates = await Promise.all(
      pending.map(async (document) => {
        try {
          return await getDocumentStatus(document.id, token);
        } catch {
          return null;
        }
      })
    );

    let becameReady = false;

    setDocuments((current) =>
      current
        .filter((document) => belongsToSession(document, numericSessionId))
        .map((document) => {
          const update = updates.find((item) => item?.id === document.id);
          if (!update) return document;
          if (update.status === "ready" || update.chunks_created > 0) {
            becameReady = true;
            return {
              ...document,
              chunks_created: update.chunks_created,
              status: "ready" as const,
            };
          }
          return document;
        })
    );

    if (currentSessionIdRef.current !== numericSessionId) {
      return;
    }

    if (becameReady) {
      const readyCount = documents.filter(
        (document) => isDocumentReady(document) && belongsToSession(document, numericSessionId)
      ).length;
      setMessage(`${readyCount || 1} document${readyCount === 1 ? "" : "s"} ready in this chat.`);
      setStatus("success");
      setUploadTargetSessionId(null);
    } else {
      const names = pending.map((document) => document.filename).join(", ");
      setMessage(`Indexing ${names}...`);
    }
  }, [documents, numericSessionId, status, token, uploadTargetSessionId]);

  useEffect(() => {
    if (!token || !numericSessionId || documents.every(isDocumentReady)) {
      if (pollTimerRef.current) {
        window.clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
      return;
    }

    const hasPendingForSession = documents.some(
      (document) => isDocumentIndexing(document) && belongsToSession(document, numericSessionId)
    );
    if (!hasPendingForSession) {
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

    const showProgressForTarget = currentSessionIdRef.current === targetSessionId;
    if (showProgressForTarget) {
      setStatus("uploading");
      setMessage(null);
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

      if (currentSessionIdRef.current !== targetSessionId) {
        return { ...result, indexing: result.indexing ?? result.chunks_created === 0 };
      }

      const latestDocuments = await refresh();
      const uploadedDocument =
        latestDocuments?.find((document) => document.id === result.document_id) ?? {
          id: result.document_id,
          filename: result.filename,
          size: file.size,
          updated_at: Date.now() / 1000,
          collection_id: result.collection_id,
          session_id: targetSessionId,
          chunks_created: result.chunks_created,
          status: result.indexing ? ("indexing" as const) : ("ready" as const),
        };

      setDocuments((current) => {
        const scoped = current.filter(
          (document) =>
            belongsToSession(document, targetSessionId) && document.id !== uploadedDocument.id
        );
        return [uploadedDocument, ...scoped];
      });

      if (result.indexing || uploadedDocument.chunks_created === 0) {
        setStatus("indexing");
        setMessage(`Indexing ${result.filename}...`);
        return { ...result, indexing: true };
      }

      setStatus("success");
      setMessage(`${result.message} (${result.chunks_created} chunks indexed)`);
      setUploadTargetSessionId(null);
      return result;
    } catch (error) {
      if (currentSessionIdRef.current === targetSessionId) {
        setStatus("error");
        setMessage(
          sanitizeApiError(error instanceof ApiError ? error.message : undefined, {
            fallback: "Upload failed. Please try again.",
            status: error instanceof ApiError ? error.status : undefined,
          })
        );
      }
      setUploadTargetSessionId(null);
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
  const isUploadActiveForSession =
    uploadTargetSessionId !== null &&
    uploadTargetSessionId === numericSessionId &&
    (status === "uploading" || status === "indexing");

  return {
    documents,
    readyDocuments,
    indexingDocuments,
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
