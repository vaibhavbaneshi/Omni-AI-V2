"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Loader2, Network, RefreshCw, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  buildKnowledgeGraph,
  getDocumentGraph,
  getGlobalGraph,
  searchKnowledgeGraph,
  type KnowledgeGraphData,
} from "@/lib/api";

type KnowledgeGraphPanelProps = {
  token?: string | null;
  documentId?: number | null;
  workspaceId?: string;
  embedded?: boolean;
};

export function KnowledgeGraphPanel({
  token,
  documentId,
  workspaceId = "default",
  embedded = false,
}: KnowledgeGraphPanelProps) {
  const [graph, setGraph] = useState<KnowledgeGraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const [building, setBuilding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const loadGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = documentId
        ? await getDocumentGraph(documentId, token)
        : await getGlobalGraph(workspaceId, token);
      setGraph(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load graph.");
      setGraph(null);
    } finally {
      setLoading(false);
    }
  }, [token, documentId, workspaceId]);

  useEffect(() => {
    void loadGraph();
  }, [loadGraph]);

  const handleBuild = async () => {
    if (!token) return;
    setBuilding(true);
    setError(null);
    try {
      await buildKnowledgeGraph(token, {
        workspaceId,
        documentId: documentId ?? undefined,
      });
      await loadGraph();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Graph build failed.");
    } finally {
      setBuilding(false);
    }
  };

  const handleSearch = async () => {
    if (!token || !searchQuery.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await searchKnowledgeGraph(searchQuery.trim(), token, workspaceId);
      setGraph(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Graph search failed.");
    } finally {
      setLoading(false);
    }
  };

  const nodeMap = useMemo(() => {
    const map = new Map<number, string>();
    for (const node of graph?.nodes ?? []) {
      map.set(node.id, node.name);
    }
    return map;
  }, [graph]);

  const wrapperClass = embedded ? "space-y-4" : "rounded-xl border border-white/10 bg-card/50 p-4 space-y-4";

  return (
    <div className={wrapperClass}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Network className="size-4 text-primary" />
            <h3 className="text-[13px] font-semibold text-foreground/90">Knowledge Graph</h3>
          </div>
          <p className="mt-1 text-[12px] text-muted-foreground/70">
            Entities and relationships extracted from document intelligence.
          </p>
        </div>
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="h-7 gap-1.5 text-[11px]"
          onClick={handleBuild}
          disabled={building || !token}
        >
          {building ? <Loader2 className="size-3 animate-spin" /> : <RefreshCw className="size-3" />}
          Rebuild
        </Button>
      </div>

      <div className="flex gap-2">
        <Input
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
          placeholder="Search entities…"
          className="h-8 text-[12px]"
          onKeyDown={(event) => {
            if (event.key === "Enter") void handleSearch();
          }}
        />
        <Button type="button" size="sm" variant="outline" className="h-8 px-2.5" onClick={() => void handleSearch()}>
          <Search className="size-3.5" />
        </Button>
      </div>

      {error && (
        <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-[12px] text-destructive">
          {error}
        </p>
      )}

      {loading && !graph && (
        <div className="flex items-center justify-center py-10 text-[12px] text-muted-foreground">
          <Loader2 className="mr-2 size-4 animate-spin" />
          Loading graph…
        </div>
      )}

      {!loading && graph && graph.nodes.length === 0 && (
        <div className="rounded-xl border border-dashed border-white/10 bg-white/[0.02] px-4 py-8 text-center">
          <Network className="mx-auto mb-2 size-5 text-muted-foreground/50" />
          <p className="text-[13px] font-medium text-foreground/85">No graph data yet</p>
          <p className="mt-1 text-[12px] text-muted-foreground/60">
            Generate document intelligence, then rebuild the graph.
          </p>
        </div>
      )}

      {graph && graph.nodes.length > 0 && (
        <div className="space-y-4">
          <div className="grid gap-2 sm:grid-cols-2">
            {graph.nodes.slice(0, 12).map((node) => (
              <div
                key={node.id}
                className="rounded-lg border border-white/5 bg-white/[0.03] px-3 py-2 ring-1 ring-white/5"
              >
                <p className="truncate text-[13px] font-medium">{node.name}</p>
                <p className="text-[11px] capitalize text-muted-foreground/60">{node.node_type}</p>
              </div>
            ))}
          </div>

          {graph.edges.length > 0 && (
            <div className="space-y-2">
              <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground/55">
                Relationships
              </p>
              <div className="max-h-48 space-y-1.5 overflow-y-auto">
                {graph.edges.slice(0, 20).map((edge) => (
                  <div
                    key={edge.id}
                    className="rounded-md bg-white/[0.02] px-2.5 py-1.5 text-[11px] text-muted-foreground"
                  >
                    <span className="text-foreground/85">{nodeMap.get(edge.source) ?? edge.source}</span>
                    <span className="mx-1.5 text-primary/80">→ {edge.relation_type.replace(/_/g, " ")} →</span>
                    <span className="text-foreground/85">{nodeMap.get(edge.target) ?? edge.target}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <p className="text-[11px] text-muted-foreground/50">
            {graph.nodes.length} nodes · {graph.edges.length} edges
          </p>
        </div>
      )}
    </div>
  );
}
