"use client";

import { useState } from "react";
import { BookOpen, FileDown, Loader2, Search } from "lucide-react";
import { BackButton } from "@/components/navigation/back-button";
import { useRequireAuth } from "@/lib/auth";
import { downloadResearchExport, getResearchReport, runResearchReport, type ResearchReportRecord } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";

export default function ResearchPage() {
  const { ready, authenticated } = useRequireAuth();
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<ResearchReportRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState<"markdown" | "pdf" | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  const handleRun = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setReport(null);
    setExportError(null);
    try {
      const created = await runResearchReport({ query: query.trim(), max_iterations: 3 });
      const full = await getResearchReport(created.id);
      setReport(full);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Research failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format: "markdown" | "pdf") => {
    if (!report?.id) return;
    setExporting(format);
    setExportError(null);
    try {
      await downloadResearchExport(report.id, format);
    } catch (err) {
      setExportError(err instanceof Error ? err.message : "Export failed.");
    } finally {
      setExporting(null);
    }
  };

  if (!ready || !authenticated) return <div className="min-h-screen bg-background" />;

  return (
    <div className="min-h-screen bg-background px-4 py-8">
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold flex items-center gap-2">
              <BookOpen className="size-6 text-primary" />
              Deep Research
            </h1>
            <p className="text-sm text-muted-foreground mt-1">Plan → evidence → verification → report</p>
          </div>
          <BackButton variant="outline" />
        </div>
        <Card className="border-white/10 bg-card/65">
          <CardHeader><CardTitle>Research query</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <Textarea value={query} onChange={(e) => setQuery(e.target.value)} placeholder="What should we research?" rows={4} />
            <Button onClick={() => void handleRun()} disabled={loading || !query.trim()}>
              {loading ? <Loader2 className="size-4 animate-spin mr-2" /> : <Search className="size-4 mr-2" />}
              Run research
            </Button>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </CardContent>
        </Card>
        {report && (
          <Card className="border-white/10 bg-card/65">
            <CardHeader>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <CardTitle>{report.report?.title || report.query}</CardTitle>
                  <p className="text-xs text-muted-foreground">Status: {report.status}</p>
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={exporting !== null}
                    onClick={() => void handleExport("markdown")}
                    aria-label="Export MD"
                  >
                    {exporting === "markdown" ? <Loader2 className="size-4 animate-spin" /> : <FileDown className="size-4 mr-1" />}
                    Export MD
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={exporting !== null}
                    onClick={() => void handleExport("pdf")}
                    aria-label="Export PDF"
                  >
                    {exporting === "pdf" ? <Loader2 className="size-4 animate-spin" /> : <FileDown className="size-4 mr-1" />}
                    Export PDF
                  </Button>
                </div>
              </div>
              {exportError && <p className="text-sm text-destructive mt-2">{exportError}</p>}
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              {report.report?.executive_summary && (
                <section>
                  <h3 className="font-medium mb-1">Executive summary</h3>
                  <p className="text-muted-foreground">{report.report.executive_summary}</p>
                </section>
              )}
              {report.report?.key_findings?.length ? (
                <section>
                  <h3 className="font-medium mb-1">Key findings</h3>
                  <ul className="list-disc pl-5 space-y-1 text-muted-foreground">
                    {report.report.key_findings.map((item) => <li key={item}>{item}</li>)}
                  </ul>
                </section>
              ) : null}
              {report.report?.verification && (
                <section>
                  <h3 className="font-medium mb-1">Verification</h3>
                  <pre className="rounded bg-white/5 p-3 text-xs overflow-x-auto">{JSON.stringify(report.report.verification, null, 2)}</pre>
                </section>
              )}
              {report.traces?.length ? (
                <section>
                  <h3 className="font-medium mb-1">Research steps</h3>
                  <pre className="rounded bg-white/5 p-3 text-xs overflow-x-auto">{JSON.stringify(report.traces, null, 2)}</pre>
                </section>
              ) : null}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
