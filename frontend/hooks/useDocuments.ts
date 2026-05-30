import { useCallback, useEffect, useRef, useState } from "react";
import {
  createCollection,
  deleteDocument,
  listCollections,
  listDocuments,
  uploadDocument,
  waitForDocumentIndexed,
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

const MAX_UPLOAD_BYTES = 15 * 1024 * 1024;

export function useDocuments(token?: string | null, sessionId?: string | null) {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [collections, setCollections] = useState<DocumentCollection[]>([]);
  const [activeCollectionId, setActiveCollectionId] = useState<number | null>(null);
  const [status, setStatus] = useState<"idle" | "uploading" | "success" | "error">("idle");
  const [message, setMessage] = useState<string | null>(null);

  const numericSessionId =
    sessionId && isBackendSessionId(sessionId) ? Number(sessionId) : null;

  const uploadInProgressRef = useRef(false);

  const refresh = useCallback(async () => {
    if (!token) {
      setDocuments([]);
      return;
    }

    const [documentResult, collectionResult] = await Promise.all([
      listDocuments(token, { sessionId: numericSessionId }),
      listCollections(token),
    ]);

    setDocuments(documentResult.documents);
    setCollections(collectionResult.collections);

    if (!activeCollectionId && collectionResult.collections.length > 0) {
      setActiveCollectionId(collectionResult.collections[0].id);
    }
  }, [activeCollectionId, numericSessionId, token]);

  useEffect(() => {
    if (uploadInProgressRef.current) return;

    setDocuments([]);
    setStatus("idle");
    setMessage(null);

    const id = window.setTimeout(() => {
      refresh().catch(() => undefined);
    }, 0);

    return () => window.clearTimeout(id);
  }, [numericSessionId, token, refresh]);

  const upload = async (file: File, options?: { sessionId?: number | null }) => {
    const sessionId = options?.sessionId ?? numericSessionId;
    if (!sessionId) {
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

    uploadInProgressRef.current = true;
    setStatus("uploading");
    setMessage(null);

    const validCollectionId =
      activeCollectionId && collections.some((item) => item.id === activeCollectionId)
        ? activeCollectionId
        : null;

    try {
      const result = await uploadDocument(file, token, {
        collectionId: validCollectionId,
        sessionId,
      });

      if (result.indexing) {
        setMessage("Indexing document...");
        const indexed = await waitForDocumentIndexed(result.document_id, sessionId, token);
        setStatus("success");
        setMessage(
          `Document indexed successfully (${indexed.chunks_created} chunks indexed)`
        );
        refresh().catch(() => undefined);
        return { ...result, chunks_created: indexed.chunks_created, indexing: false };
      }

      setStatus("success");
      setMessage(`${result.message} (${result.chunks_created} chunks indexed)`);
      refresh().catch(() => undefined);
      return result;
    } catch (error) {
      setStatus("error");
      setMessage(
        sanitizeApiError(error instanceof ApiError ? error.message : undefined, {
          fallback: "Upload failed. Please try again.",
          status: error instanceof ApiError ? error.status : undefined,
        })
      );
      throw error;
    } finally {
      uploadInProgressRef.current = false;
    }
  };

  const remove = async (filename: string) => {
    await deleteDocument(filename, token);
    await refresh();
  };

  const addCollection = async (name: string) => {
    const collection = await createCollection(name, token);
    await refresh();
    setActiveCollectionId(collection.id);
    return collection;
  };

  return {
    documents,
    collections,
    activeCollectionId,
    setActiveCollectionId,
    status,
    message,
    setStatus,
    setMessage,
    refresh,
    upload,
    remove,
    addCollection,
  };
}
