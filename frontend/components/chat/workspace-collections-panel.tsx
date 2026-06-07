"use client";

import { useState } from "react";
import { FolderPlus, Loader2, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { DocumentCollection } from "@/lib/api";
import {
  createCollection,
  deleteCollection,
  moveDocumentToCollection,
  updateCollection,
} from "@/lib/api";

type WorkspaceCollectionsPanelProps = {
  token?: string | null;
  collections: DocumentCollection[];
  activeCollectionId: number | null;
  documents: Array<{ id: number; filename: string; collection_id?: number }>;
  onRefresh: () => Promise<unknown>;
  onSelectCollection: (collectionId: number) => void;
};

export function WorkspaceCollectionsPanel({
  token,
  collections,
  activeCollectionId,
  documents,
  onRefresh,
  onSelectCollection,
}: WorkspaceCollectionsPanelProps) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const runAction = async (action: () => Promise<void>) => {
    if (!token) return;
    setBusy(true);
    setMessage(null);
    try {
      await action();
      await onRefresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Collection action failed.");
    } finally {
      setBusy(false);
    }
  };

  const handleCreate = () => {
    const name = window.prompt("Collection name")?.trim();
    if (!name) return;
    void runAction(async () => {
      const created = await createCollection(name, token);
      onSelectCollection(created.id);
    });
  };

  const handleRename = (collection: DocumentCollection) => {
    const name = window.prompt("Rename collection", collection.name)?.trim();
    if (!name || name === collection.name) return;
    void runAction(async () => {
      await updateCollection(collection.id, name, token);
    });
  };

  const handleDelete = (collection: DocumentCollection) => {
    if (collection.name === "Default") return;
    if (!window.confirm(`Delete collection “${collection.name}”? Documents move to Default.`)) return;
    void runAction(async () => {
      await deleteCollection(collection.id, token);
    });
  };

  const handleMoveDocument = (documentId: number) => {
    if (!activeCollectionId) return;
    void runAction(async () => {
      await moveDocumentToCollection(documentId, activeCollectionId, token);
    });
  };

  if (collections.length === 0) {
    return null;
  }

  return (
    <div className="mb-3 rounded-xl border border-white/5 bg-white/[0.015] px-3 py-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground/60">
          <FolderPlus className="size-3.5" />
          Collections
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 px-2 text-[11px]"
          disabled={busy || !token}
          onClick={handleCreate}
        >
          New
        </Button>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {collections.map((collection) => (
          <button
            key={collection.id}
            type="button"
            className={`rounded-full border px-2.5 py-1 text-[10px] transition-colors ${
              activeCollectionId === collection.id
                ? "border-primary/30 bg-primary/10 text-primary"
                : "border-white/10 bg-white/[0.03] text-muted-foreground hover:text-foreground"
            }`}
            onClick={() => onSelectCollection(collection.id)}
            onDoubleClick={() => handleRename(collection)}
          >
            {collection.name}
            {typeof collection.document_count === "number" ? ` (${collection.document_count})` : ""}
          </button>
        ))}
        {busy && <Loader2 className="size-3.5 animate-spin text-primary" />}
      </div>
      {documents.length > 0 && activeCollectionId && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {documents.slice(0, 4).map((document) => (
            <button
              key={document.id}
              type="button"
              className="rounded-md border border-white/10 px-2 py-1 text-[10px] text-muted-foreground hover:text-foreground"
              disabled={busy}
              onClick={() => handleMoveDocument(document.id)}
            >
              Move {document.filename} here
            </button>
          ))}
        </div>
      )}
      {collections
        .filter((collection) => collection.name !== "Default")
        .slice(0, 3)
        .map((collection) => (
          <button
            key={`delete-${collection.id}`}
            type="button"
            className="mt-2 inline-flex items-center gap-1 text-[10px] text-muted-foreground/60 hover:text-destructive"
            disabled={busy}
            onClick={() => handleDelete(collection)}
          >
            <Trash2 className="size-3" />
            Delete {collection.name}
          </button>
        ))}
      {message && <p className="mt-2 text-[10px] text-destructive">{message}</p>}
    </div>
  );
}
