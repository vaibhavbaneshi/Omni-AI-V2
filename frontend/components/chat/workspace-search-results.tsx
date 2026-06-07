"use client";

import { FolderOpen, Loader2, Search } from "lucide-react";

import type { WorkspaceSearchResult } from "@/lib/api";

type WorkspaceSearchResultsProps = {
  query: string;
  results: WorkspaceSearchResult[];
  loading?: boolean;
  onSelect: (result: WorkspaceSearchResult) => void;
};

const TYPE_LABELS: Record<string, string> = {
  session: "Chat",
  message: "Message",
  document: "Document",
  insight: "Insight",
};

export function WorkspaceSearchResults({
  query,
  results,
  loading = false,
  onSelect,
}: WorkspaceSearchResultsProps) {
  if (query.trim().length < 2) {
    return null;
  }

  return (
    <div className="mt-2 rounded-lg border border-white/5 bg-white/[0.02] p-2 shadow-inner">
      <div className="mb-2 flex items-center gap-2 px-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground/60">
        <Search className="size-3" />
        <span>Workspace results</span>
        {loading && <Loader2 className="size-3 animate-spin" />}
      </div>
      {!loading && results.length === 0 && (
        <p className="px-1 py-1 text-[11px] text-muted-foreground/60">No matches for “{query}”.</p>
      )}
      <div className="max-h-44 space-y-1 overflow-y-auto">
        {results.map((result) => (
          <button
            key={`${result.type}-${result.id}-${result.session_id ?? "x"}`}
            type="button"
            className="flex w-full flex-col rounded-md px-2 py-1.5 text-left transition-colors hover:bg-white/[0.04]"
            onClick={() => onSelect(result)}
          >
            <div className="flex items-center gap-2">
              <span className="rounded-full border border-white/10 px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-muted-foreground/70">
                {TYPE_LABELS[result.type] || result.type}
              </span>
              <span className="truncate text-[11px] font-medium text-foreground/85">{result.title}</span>
            </div>
            {result.snippet && (
              <span className="mt-0.5 line-clamp-2 text-[10px] text-muted-foreground/60">{result.snippet}</span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
