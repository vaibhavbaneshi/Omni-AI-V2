"use client";

import type { ComponentType } from "react";
import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  BookOpen,
  ChevronDown,
  Database,
  FileText,
  FlaskConical,
  Loader2,
  Search,
  ShieldCheck,
  Sparkles,
  Wrench,
} from "lucide-react";
import type { StreamMeta } from "@/lib/api";
import { SourcesPanel, sourcesSummary, type SourceCitation } from "@/components/chat/sources-panel";

type MessageContextBarProps = {
  meta?: StreamMeta | null;
  sources?: SourceCitation[];
  memoryFacts?: string[];
  live?: boolean;
};

export function MessageContextBar({
  meta,
  sources = [],
  memoryFacts = [],
  live = false,
}: MessageContextBarProps) {
  const [open, setOpen] = useState(false);
  const hasSources = sources.length > 0;
  const hasMeta = Boolean(
    meta?.tool ||
      meta?.strategy ||
      meta?.route?.status ||
      meta?.agent ||
      meta?.mode ||
      memoryFacts.length > 0
  );

  if (!hasSources && !hasMeta) return null;

  const tool = meta?.tool || "rag";
  const toolLabel =
    tool === "calculator" || meta?.route?.tools?.includes("calculator")
      ? "Calculator"
      : meta?.route?.tools?.includes("web_search")
        ? meta?.route?.tools?.includes("vector_retrieval")
          ? "Web + documents"
          : "Web search"
        : tool === "web_search"
          ? "Web search"
          : "Document search";

  const summaryParts: string[] = [];
  if (hasMeta) summaryParts.push(live ? `Using ${toolLabel}` : toolLabel);
  if (hasSources) summaryParts.push(sourcesSummary(sources));

  return (
    <div className="mb-3">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="inline-flex max-w-full items-center gap-2 rounded-full border border-white/8 bg-white/[0.02] px-3 py-1.5 text-left text-[11px] font-medium text-muted-foreground/80 shadow-inner transition-colors hover:border-white/12 hover:bg-white/[0.04] hover:text-foreground"
        aria-expanded={open}
      >
        {live ? (
          <Loader2 className="size-3.5 shrink-0 animate-spin text-primary" />
        ) : hasSources ? (
          <BookOpen className="size-3.5 shrink-0 text-primary/80" />
        ) : (
          <Wrench className="size-3.5 shrink-0 text-primary/80" />
        )}
        <span className="truncate">{summaryParts.join(" · ")}</span>
        <ChevronDown
          className={`size-3.5 shrink-0 text-muted-foreground/60 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-3 space-y-3 rounded-xl border border-white/5 bg-white/[0.015] p-3">
              {hasMeta && (
                <div className="flex flex-wrap items-center gap-2">
                  <MetaPill
                    icon={live ? Loader2 : Wrench}
                    iconClassName={live ? "animate-spin text-primary" : "text-primary"}
                    label={live ? `Using ${toolLabel}` : `Used ${toolLabel}`}
                  />
                  {meta?.strategy && (
                    <MetaPill icon={Database} iconClassName="text-blue-400" label={meta.strategy} />
                  )}
                  {meta?.route?.status && (
                    <MetaPill icon={Search} iconClassName="text-cyan-300" label={`Search ${meta.route.status}`} />
                  )}
                  {meta?.agent === "research" && meta?.report_id && (
                    <MetaPill
                      icon={FlaskConical}
                      iconClassName="text-violet-200"
                      label={`Research report #${meta.report_id}`}
                      className="border-violet-400/20 bg-violet-500/10 text-violet-200"
                    />
                  )}
                  {meta?.agent === "document-analysis" && (
                    <MetaPill
                      icon={FileText}
                      iconClassName="text-emerald-200"
                      label={`Document analysis${meta.document_analysis?.length ? ` (${meta.document_analysis.length})` : ""}`}
                      className="border-emerald-400/20 bg-emerald-500/10 text-emerald-200"
                    />
                  )}
                  {meta?.mode && (
                    <MetaPill icon={Sparkles} iconClassName="text-violet-300" label={`${meta.mode} mode`} />
                  )}
                  <MetaPill
                    icon={ShieldCheck}
                    iconClassName="text-emerald-300"
                    label={`Memory ${meta?.memory?.conversation_history || memoryFacts.length > 0 ? "available" : "ready"}`}
                  />
                  {memoryFacts.slice(0, 2).map((fact) => (
                    <span
                      key={fact}
                      className="rounded-full border border-primary/15 bg-primary/5 px-2.5 py-1 text-[10px] font-medium text-primary/90"
                    >
                      {fact}
                    </span>
                  ))}
                </div>
              )}
              {hasSources && <SourcesPanel sources={sources} embedded />}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function MetaPill({
  icon: Icon,
  label,
  iconClassName,
  className,
}: {
  icon: ComponentType<{ className?: string }>;
  label: string;
  iconClassName?: string;
  className?: string;
}) {
  return (
    <div
      className={`flex items-center gap-2 rounded-full border border-white/5 bg-white/[0.02] px-3 py-1.5 text-[11px] font-medium text-muted-foreground/80 shadow-inner ${className || ""}`}
    >
      <Icon className={`size-3.5 ${iconClassName || ""}`} />
      <span>{label}</span>
    </div>
  );
}
