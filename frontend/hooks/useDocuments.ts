import { useCallback, useEffect, useState } from "react";
import {
  createCollection,
  deleteDocument,
  listCollections,
  listDocuments,
  uploadDocument,
  type DocumentCollection,
  type DocumentRecord,
} from "@/lib/api";
import { isBackendSessionId } from "@/lib/chat-sessions";
import {
  isSupportedUploadFilename,
  SUPPORTED_UPLOADS_LABEL,
} from "@/lib/supported-uploads";

const MAX_UPLOAD_BYTES = 15 * 1024 * 1024;

export function useDocuments(token?: string | null, sessionId?: string | null) {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [collections, setCollections] = useState<DocumentCollection[]>([]);
  const [activeCollectionId, setActiveCollectionId] = useState<number | null>(null);
  const [status, setStatus] = useState<"idle" | "uploading" | "success" | "error">("idle");
  const [message, setMessage] = useState<string | null>(null);

  const numericSessionId =
    sessionId && isBackendSessionId(sessionId) ? Number(sessionId) : null;

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
    setDocuments([]);
    setStatus("idle");
    setMessage(null);

    const id = window.setTimeout(() => {
      refresh().catch(() => undefined);
    }, 0);

    return () => window.clearTimeout(id);
  }, [refresh, numericSessionId]);

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

    setStatus("uploading");
    setMessage(null);

    try {
      const result = await uploadDocument(file, token, {
        collectionId: activeCollectionId,
        sessionId,
      });
      setStatus("success");
      setMessage(`${result.message} (${result.chunks_created} chunks indexed)`);
      const documentResult = await listDocuments(token, { sessionId });
      setDocuments(documentResult.documents);
      return result;
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "Upload failed.");
      throw error;
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
