"use client";

import { Loader2, RefreshCw, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { DocumentInsightRecord, DocumentRecord } from "@/lib/api";

type DocumentInsightsPanelProps = {
  document: DocumentRecord | null;
  insights: DocumentInsightRecord | null;
  loading?: boolean;
  generating?: boolean;
  error?: string | null;
  onGenerate: (options?: { force?: boolean }) => void;
  embedded?: boolean;
  documents?: DocumentRecord[];
  activeDocumentId?: number | null;
  onSelectDocument?: (documentId: number) => void;
};

function BulletList({ items, emptyLabel }: { items: string[]; emptyLabel: string }) {
  if (!items.length) {
    return <p className="text-[12px] text-muted-foreground/60">{emptyLabel}</p>;
  }
  return (
    <ul className="list-disc space-y-1 pl-4 text-[12px] leading-relaxed text-foreground/85">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

export function DocumentInsightsPanel({
  document,
  insights,
  loading = false,
  generating = false,
  error,
  onGenerate,
  embedded = false,
  documents = [],
  activeDocumentId,
  onSelectDocument,
}: DocumentInsightsPanelProps) {
  if (!document) return null;

  const payload = insights?.payload;
  const isBusy = loading || generating || insights?.status === "processing";
  const hasInsights = insights?.status === "ready" && payload;

  return (
    <div className={embedded ? "space-y-3" : "mb-3 rounded-xl border border-white/5 bg-white/[0.02] p-3 sm:p-4"}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <div className="flex size-7 shrink-0 items-center justify-center rounded-lg border border-primary/20 bg-primary/10">
            <Sparkles className="size-3.5 text-primary" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-[12px] font-medium text-foreground/90">Document Intelligence</p>
            <p className="truncate text-[11px] text-muted-foreground/60">{document.filename}</p>
          </div>
        </div>
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="h-7 text-[11px]"
          disabled={isBusy}
          onClick={() => onGenerate({ force: Boolean(hasInsights) })}
        >
          {isBusy ? (
            <>
              <Loader2 className="size-3 animate-spin" />
              Analyzing...
            </>
          ) : hasInsights ? (
            <>
              <RefreshCw className="size-3" />
              Regenerate
            </>
          ) : (
            <>
              <Sparkles className="size-3" />
              Generate insights
            </>
          )}
        </Button>
      </div>

      {embedded && documents.length > 1 && onSelectDocument && (
        <div className="flex flex-wrap gap-1.5">
          {documents.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`rounded-full border px-2 py-0.5 text-[10px] transition-colors ${
                activeDocumentId === item.id
                  ? "border-primary/30 bg-primary/10 text-primary"
                  : "border-white/10 text-muted-foreground hover:text-foreground"
              }`}
              onClick={() => onSelectDocument(item.id)}
            >
              {item.filename}
            </button>
          ))}
        </div>
      )}

      {error && (
        <p className="mb-2 text-[11px] text-destructive">{error}</p>
      )}

      {!hasInsights && !isBusy && !error && (
        <p className="text-[12px] text-muted-foreground/70">
          Generate an executive summary, FAQs, action items, and extracted topics from this document.
        </p>
      )}

      {insights?.status === "failed" && insights.error_message && (
        <p className="text-[11px] text-destructive">{insights.error_message}</p>
      )}

      {hasInsights && payload && (
        <div className="space-y-4">
          <section>
            <h3 className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/70">
              Executive Summary
            </h3>
            <p className="text-[13px] leading-relaxed text-foreground/90">
              {payload.executive_summary.overview || "No overview available."}
            </p>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <div>
                <p className="mb-1 text-[11px] font-medium text-foreground/75">Key findings</p>
                <BulletList items={payload.executive_summary.key_findings} emptyLabel="None identified." />
              </div>
              <div>
                <p className="mb-1 text-[11px] font-medium text-foreground/75">Important points</p>
                <BulletList items={payload.executive_summary.important_points} emptyLabel="None identified." />
              </div>
              <div>
                <p className="mb-1 text-[11px] font-medium text-foreground/75">Risks</p>
                <BulletList items={payload.executive_summary.risks} emptyLabel="None identified." />
              </div>
              <div>
                <p className="mb-1 text-[11px] font-medium text-foreground/75">Recommendations</p>
                <BulletList items={payload.executive_summary.recommendations} emptyLabel="None identified." />
              </div>
            </div>
          </section>

          {payload.faqs.length > 0 && (
            <section>
              <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/70">
                FAQs
              </h3>
              <div className="space-y-2">
                {payload.faqs.map((faq) => (
                  <div key={faq.question} className="rounded-lg border border-white/5 bg-[#050505]/60 p-2.5">
                    <p className="text-[12px] font-medium text-foreground/90">{faq.question}</p>
                    <p className="mt-1 text-[12px] leading-relaxed text-muted-foreground/80">{faq.answer}</p>
                  </div>
                ))}
              </div>
            </section>
          )}

          {payload.action_items.length > 0 && (
            <section>
              <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/70">
                Action Items
              </h3>
              <div className="space-y-2">
                {payload.action_items.map((item) => (
                  <div key={`${item.task}-${item.deadline}-${item.owner}`} className="rounded-lg border border-white/5 px-2.5 py-2">
                    <p className="text-[12px] font-medium text-foreground/90">{item.task}</p>
                    <p className="mt-0.5 text-[11px] text-muted-foreground/70">
                      {[item.owner ? `Owner: ${item.owner}` : null, item.deadline ? `Due: ${item.deadline}` : null]
                        .filter(Boolean)
                        .join(" · ") || "No owner or deadline specified"}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          )}

          <section>
            <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/70">
              Document Insights
            </h3>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <p className="mb-1 text-[11px] font-medium text-foreground/75">Keywords</p>
                <BulletList items={payload.metadata_insights.keywords} emptyLabel="None extracted." />
              </div>
              <div>
                <p className="mb-1 text-[11px] font-medium text-foreground/75">Topics</p>
                <BulletList items={payload.metadata_insights.topics} emptyLabel="None extracted." />
              </div>
              <div>
                <p className="mb-1 text-[11px] font-medium text-foreground/75">Entities</p>
                <BulletList items={payload.metadata_insights.entities} emptyLabel="None extracted." />
              </div>
              <div>
                <p className="mb-1 text-[11px] font-medium text-foreground/75">Important dates</p>
                <BulletList items={payload.metadata_insights.important_dates} emptyLabel="None extracted." />
              </div>
              <div className="sm:col-span-2">
                <p className="mb-1 text-[11px] font-medium text-foreground/75">Statistics</p>
                <BulletList items={payload.metadata_insights.statistics} emptyLabel="None extracted." />
              </div>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
