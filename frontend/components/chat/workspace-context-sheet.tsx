"use client";

import { useEffect, useState } from "react";
import { FileIcon, FolderOpen, Loader2, Sparkles, UploadCloud, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DocumentInsightsPanel } from "@/components/chat/document-insights-panel";
import { GitHubConnectorPanel } from "@/components/chat/github-connector-panel";
import { KnowledgeGraphPanel } from "@/components/chat/knowledge-graph-panel";
import { WorkspaceCollectionsPanel } from "@/components/chat/workspace-collections-panel";
import type {
  DocumentCollection,
  DocumentInsightRecord,
  DocumentRecord,
} from "@/lib/api";
import { indexingStageLabel } from "@/lib/api";

export type WorkspaceContextTab = "files" | "collections" | "insights" | "graph" | "connectors";

type WorkspaceContextSheetProps = {
  token?: string | null;
  collections: DocumentCollection[];
  activeCollectionId: number | null;
  documents: DocumentRecord[];
  readyDocuments: DocumentRecord[];
  indexingDocuments: DocumentRecord[];
  activeDocumentId: number | null;
  insightDocument: DocumentRecord | null;
  documentInsights: DocumentInsightRecord | null;
  insightsLoading?: boolean;
  insightsGenerating?: boolean;
  insightsError?: string | null;
  onRefresh: () => Promise<unknown>;
  onSelectCollection: (collectionId: number) => void;
  onSelectDocument: (documentId: number) => void;
  onGenerateInsights: (options?: { force?: boolean }) => void;
  onDeleteDocument?: (documentId: number, filename: string) => void;
  deletingDocumentId?: number | null;
  onAttachClick?: () => void;
  uploadBusy?: boolean;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  defaultTab?: WorkspaceContextTab;
  showTrigger?: boolean;
  sessionId?: number | null;
};

export function WorkspaceContextSheet({
  token,
  collections,
  activeCollectionId,
  documents,
  readyDocuments,
  indexingDocuments,
  activeDocumentId,
  insightDocument,
  documentInsights,
  insightsLoading = false,
  insightsGenerating = false,
  insightsError,
  onRefresh,
  onSelectCollection,
  onSelectDocument,
  onGenerateInsights,
  onDeleteDocument,
  deletingDocumentId,
  onAttachClick,
  uploadBusy = false,
  open: controlledOpen,
  onOpenChange,
  defaultTab = "files",
  showTrigger = true,
  sessionId = null,
}: WorkspaceContextSheetProps) {
  const [internalOpen, setInternalOpen] = useState(false);
  const [tab, setTab] = useState<WorkspaceContextTab>(defaultTab);
  const open = controlledOpen ?? internalOpen;
  const setOpen = onOpenChange ?? setInternalOpen;

  useEffect(() => {
    if (open) {
      setTab(defaultTab);
    }
  }, [open, defaultTab]);

  const docCount = documents.length;
  const hasInsights =
    documentInsights?.status === "ready" && Boolean(documentInsights.payload);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      {showTrigger && (
        <SheetTrigger
          render={
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-8 gap-1.5 border-white/10 bg-white/[0.02] px-2.5 text-[11px] font-medium text-muted-foreground hover:text-foreground"
            />
          }
        >
          <FolderOpen className="size-3.5" />
          <span className="hidden sm:inline">Workspace</span>
          {docCount > 0 && (
            <span className="rounded-full bg-primary/15 px-1.5 py-0.5 text-[10px] text-primary">
              {docCount}
            </span>
          )}
        </SheetTrigger>
      )}

      <SheetContent side="right" className="w-full border-white/10 bg-[#0a0a0a] p-0 sm:max-w-md">
        <SheetHeader className="border-b border-white/5 px-4 py-4 pr-12">
          <SheetTitle className="text-base">Workspace</SheetTitle>
          <SheetDescription className="text-[12px]">
            Files, collections, and document intelligence for this chat.
          </SheetDescription>
        </SheetHeader>

        <Tabs value={tab} onValueChange={(value) => setTab(value as WorkspaceContextTab)} className="min-h-0 flex-1 gap-0">
          <div className="border-b border-white/5 px-4 py-2">
            <TabsList variant="line" className="h-9 w-full justify-start gap-4 bg-transparent p-0">
              <TabsTrigger value="files" className="h-8 px-0 text-[12px]">
                Files
              </TabsTrigger>
              <TabsTrigger value="collections" className="h-8 px-0 text-[12px]">
                Collections
              </TabsTrigger>
              <TabsTrigger value="insights" className="h-8 gap-1 px-0 text-[12px]">
                <Sparkles className="size-3" />
                Intelligence
                {hasInsights && <span className="size-1.5 rounded-full bg-primary" />}
              </TabsTrigger>
              <TabsTrigger value="graph" className="h-8 gap-1 px-0 text-[12px]">
                Graph
              </TabsTrigger>
              <TabsTrigger value="connectors" className="h-8 gap-1 px-0 text-[12px]">
                GitHub
              </TabsTrigger>
            </TabsList>
          </div>

          <ScrollArea className="h-[calc(100dvh-9.5rem)]">
            <TabsContent value="files" className="px-4 py-4">
              <div className="mb-4 flex items-center justify-between gap-2">
                <p className="text-[12px] text-muted-foreground/70">
                  {readyDocuments.length} ready
                  {indexingDocuments.length > 0 ? ` · ${indexingDocuments.length} indexing` : ""}
                </p>
                {onAttachClick && (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="h-7 gap-1.5 text-[11px]"
                    onClick={onAttachClick}
                    disabled={uploadBusy}
                  >
                    {uploadBusy ? (
                      <Loader2 className="size-3 animate-spin" />
                    ) : (
                      <UploadCloud className="size-3" />
                    )}
                    Upload
                  </Button>
                )}
              </div>

              {documents.length === 0 ? (
                <div className="rounded-xl border border-dashed border-white/10 bg-white/[0.02] px-4 py-8 text-center">
                  <UploadCloud className="mx-auto mb-2 size-5 text-muted-foreground/50" />
                  <p className="text-[13px] font-medium text-foreground/85">No files yet</p>
                  <p className="mt-1 text-[12px] text-muted-foreground/60">
                    Upload documents to scope answers to this conversation.
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {indexingDocuments.map((document) => (
                    <FileRow
                      key={`indexing-${document.id}`}
                      document={document}
                      indexing
                    />
                  ))}
                  {readyDocuments.map((document) => (
                    <FileRow
                      key={document.id}
                      document={document}
                      active={activeDocumentId === document.id}
                      deleting={deletingDocumentId === document.id}
                      onSelect={() => {
                        onSelectDocument(document.id);
                        setTab("insights");
                      }}
                      onDelete={
                        onDeleteDocument
                          ? () => onDeleteDocument(document.id, document.filename)
                          : undefined
                      }
                    />
                  ))}
                </div>
              )}
            </TabsContent>

            <TabsContent value="collections" className="px-4 py-4">
              <WorkspaceCollectionsPanel
                embedded
                token={token}
                collections={collections}
                activeCollectionId={activeCollectionId}
                documents={documents}
                onRefresh={onRefresh}
                onSelectCollection={onSelectCollection}
              />
            </TabsContent>

            <TabsContent value="insights" className="px-4 py-4">
              {insightDocument ? (
                <DocumentInsightsPanel
                  embedded
                  document={insightDocument}
                  insights={documentInsights}
                  loading={insightsLoading}
                  generating={insightsGenerating}
                  error={insightsError}
                  onGenerate={onGenerateInsights}
                  documents={readyDocuments}
                  activeDocumentId={activeDocumentId}
                  onSelectDocument={onSelectDocument}
                />
              ) : (
                <div className="rounded-xl border border-dashed border-white/10 bg-white/[0.02] px-4 py-8 text-center">
                  <Sparkles className="mx-auto mb-2 size-5 text-muted-foreground/50" />
                  <p className="text-[13px] font-medium text-foreground/85">No document selected</p>
                  <p className="mt-1 text-[12px] text-muted-foreground/60">
                    Upload a file, then open Intelligence to generate summaries and FAQs.
                  </p>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="mt-4 h-8 text-[11px]"
                    onClick={() => setTab("files")}
                  >
                    Go to Files
                  </Button>
                </div>
              )}
            </TabsContent>

            <TabsContent value="graph" className="px-4 py-4">
              <KnowledgeGraphPanel
                embedded
                token={token}
                documentId={activeDocumentId}
              />
            </TabsContent>

            <TabsContent value="connectors" className="px-4 py-4">
              <GitHubConnectorPanel embedded token={token} sessionId={sessionId} />
            </TabsContent>
          </ScrollArea>
        </Tabs>
      </SheetContent>
    </Sheet>
  );
}

function FileRow({
  document,
  indexing = false,
  active = false,
  deleting = false,
  onSelect,
  onDelete,
}: {
  document: DocumentRecord;
  indexing?: boolean;
  active?: boolean;
  deleting?: boolean;
  onSelect?: () => void;
  onDelete?: () => void;
}) {
  return (
    <div
      className={`flex items-center gap-3 rounded-xl border px-3 py-2.5 transition-colors ${
        active ? "border-primary/30 bg-primary/5" : "border-white/5 bg-white/[0.02]"
      }`}
    >
      {indexing ? (
        <Loader2 className="size-4 shrink-0 animate-spin text-primary" />
      ) : (
        <FileIcon className="size-4 shrink-0 text-blue-300" />
      )}
      <button
        type="button"
        className="min-w-0 flex-1 text-left"
        onClick={onSelect}
        disabled={indexing || !onSelect}
      >
        <p className="truncate text-[13px] font-medium text-foreground/90">
          {indexing ? indexingStageLabel(document) : document.filename}
        </p>
        {!indexing && (
          <p className="text-[11px] text-muted-foreground/55">
            {document.chunks_created ? `${document.chunks_created} chunks indexed` : "Ready"}
          </p>
        )}
      </button>
      {!indexing && onDelete && (
        <button
          type="button"
          className="flex size-7 shrink-0 items-center justify-center rounded-md text-muted-foreground/60 hover:bg-white/5 hover:text-foreground"
          onClick={onDelete}
          disabled={deleting}
          aria-label={`Remove ${document.filename}`}
        >
          {deleting ? <Loader2 className="size-3.5 animate-spin" /> : <X className="size-3.5" />}
        </button>
      )}
    </div>
  );
}
