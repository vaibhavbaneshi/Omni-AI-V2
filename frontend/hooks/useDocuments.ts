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

export function useDocuments(token?: string | null) {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [collections, setCollections] = useState<DocumentCollection[]>([]);
  const [activeCollectionId, setActiveCollectionId] = useState<number | null>(null);
  const [status, setStatus] = useState<"idle" | "uploading" | "success" | "error">("idle");
  const [message, setMessage] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!token) return;

    const [documentResult, collectionResult] = await Promise.all([
      listDocuments(token),
      listCollections(token),
    ]);

    setDocuments(documentResult.documents);
    setCollections(collectionResult.collections);

    if (!activeCollectionId && collectionResult.collections.length > 0) {
      setActiveCollectionId(collectionResult.collections[0].id);
    }
  }, [activeCollectionId, token]);

  useEffect(() => {
    const id = window.setTimeout(() => {
      refresh().catch(() => undefined);
    }, 0);

    return () => window.clearTimeout(id);
  }, [refresh]);

  const upload = async (file: File) => {
    setStatus("uploading");
    setMessage(null);

    try {
      const result = await uploadDocument(file, token, activeCollectionId);
      setStatus("success");
      setMessage(`${result.message} (${result.chunks_created} chunks indexed)`);
      await refresh();
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
