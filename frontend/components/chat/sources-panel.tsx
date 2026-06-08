"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Brain, FileText, Globe } from "lucide-react";
import type { StreamSource } from "@/lib/api";

export type SourceCitation = StreamSource & {
  url?: string;
};

type SourcesPanelProps = {
  sources: SourceCitation[];
  embedded?: boolean;
};

export function SourcesPanel({ sources, embedded = false }: SourcesPanelProps) {
  if (sources.length === 0) return null;

  const webSources = sources.filter((source) => source.type === "web");
  const memorySources = sources.filter((source) => source.type === "memory");
  const documentSources = sources.filter((source) => source.type !== "web" && source.type !== "memory");

  return (
    <div className={embedded ? "space-y-3" : "space-y-3"}>
      <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1 scrollbar-thin">
        {sources.map((source, index) => (
          <SourceCard key={`${source.source}-${index}`} source={source} index={index} />
        ))}
      </div>
      <SourceChunks
        documentSources={documentSources}
        webSources={webSources}
        memorySources={memorySources}
      />
    </div>
  );
}

function SourceChunks({
  documentSources,
  webSources,
  memorySources,
}: {
  documentSources: SourceCitation[];
  webSources: SourceCitation[];
  memorySources: SourceCitation[];
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div>
      <button
        type="button"
        className="text-[11px] font-medium text-muted-foreground/70 transition-colors hover:text-foreground"
        onClick={() => setExpanded((value) => !value)}
      >
        {expanded ? "Hide retrieved chunks" : "View retrieved chunks"}
      </button>
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-2 space-y-2">
              {[
                { label: "Workspace documents", items: documentSources },
                { label: "Live web", items: webSources },
                { label: "Memory", items: memorySources },
              ].map(
                (group) =>
                  group.items.length > 0 && (
                    <div key={group.label} className="space-y-2">
                      <p className="px-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground/45">
                        {group.label}
                      </p>
                      {group.items.map((source, index) => (
                        <div
                          key={`${source.source}-chunk-${index}`}
                          className="rounded-xl border border-white/5 bg-[#050505] p-3 shadow-inner"
                        >
                          <div className="mb-2 flex items-center justify-between gap-3 text-[10px] text-muted-foreground/55">
                            <span className="truncate font-medium">{source.title || source.source}</span>
                            {typeof source.score === "number" && (
                              <span>{Math.round(source.score * 100)}% match</span>
                            )}
                          </div>
                          <p className="line-clamp-5 text-[12px] leading-relaxed text-muted-foreground/80">
                            {source.chunk}
                          </p>
                        </div>
                      ))}
                    </div>
                  )
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function SourceCard({ source, index }: { source: SourceCitation; index: number }) {
  const metadata = source.metadata || {};
  const citationId = typeof metadata.citation_id === "string" ? metadata.citation_id : `S${index + 1}`;
  const pageNumber =
    typeof metadata.page_number === "number" || typeof metadata.page_number === "string"
      ? metadata.page_number
      : null;
  const chunkId = typeof metadata.chunk_id === "string" ? metadata.chunk_id : null;
  const sourceReference =
    typeof metadata.source_reference === "string" ? metadata.source_reference : null;

  const body = (
    <div className="group/source flex w-[190px] shrink-0 flex-col justify-between gap-2 rounded-xl border border-white/5 bg-[#050505] px-3 py-2.5 shadow-inner transition-colors hover:bg-white/[0.03]">
      <div className="flex items-center gap-2">
        <div className="flex size-5 shrink-0 items-center justify-center rounded-md bg-white/10">
          {source.type === "web" ? (
            <Globe className="size-3 text-cyan-200 transition-colors group-hover/source:text-foreground" />
          ) : source.type === "memory" ? (
            <Brain className="size-3 text-emerald-200 transition-colors group-hover/source:text-foreground" />
          ) : (
            <FileText className="size-3 text-primary transition-colors group-hover/source:text-foreground" />
          )}
        </div>
        <span className="truncate text-[10px] text-muted-foreground/60">
          [{citationId}] {source.source || source.title || `Source ${index + 1}`}
        </span>
      </div>
      <span className="line-clamp-2 text-[12px] font-medium leading-snug text-foreground/85 transition-colors group-hover/source:text-foreground">
        {source.title || source.source || `Retrieved chunk ${index + 1}`}
      </span>
      {(sourceReference || pageNumber || chunkId) && (
        <span className="truncate text-[10px] text-muted-foreground/45">
          {sourceReference ||
            `${pageNumber ? `Page ${pageNumber}` : ""}${pageNumber && chunkId ? " · " : ""}${chunkId ? `Chunk ${chunkId}` : ""}`}
        </span>
      )}
      <div className="flex items-center justify-between text-[10px] text-muted-foreground/45">
        <span>
          {source.type === "web" ? "live web" : source.type === "memory" ? "memory" : source.strategy || "retrieval"}
        </span>
        {typeof source.score === "number" && <span>{Math.round(source.score * 100)}%</span>}
      </div>
    </div>
  );

  if (!source.url) return body;

  return (
    <a href={source.url} target="_blank" rel="noopener noreferrer">
      {body}
    </a>
  );
}

export function sourcesSummary(sources: SourceCitation[]): string {
  const web = sources.filter((s) => s.type === "web").length;
  const docs = sources.filter((s) => s.type !== "web" && s.type !== "memory").length;
  const memory = sources.filter((s) => s.type === "memory").length;
  const parts: string[] = [];
  if (web) parts.push(`${web} web`);
  if (docs) parts.push(`${docs} doc${docs === 1 ? "" : "s"}`);
  if (memory) parts.push(`${memory} memory`);
  return parts.join(" · ") || `${sources.length} source${sources.length === 1 ? "" : "s"}`;
}
