"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Activity, Loader2, Download } from "lucide-react";
import { BackButton } from "@/components/navigation/back-button";
import { useRequireAuth } from "@/lib/auth";
import { getAuditEvents, getAuditOverview, API_BASE } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function AuditCenterPage() {
  const { ready, authenticated } = useRequireAuth();
  const [overview, setOverview] = useState<Record<string, unknown> | null>(null);
  const [events, setEvents] = useState<Array<Record<string, unknown>>>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authenticated) return;
    Promise.all([
      getAuditOverview(30),
      getAuditEvents({ days: 30, limit: 50, action_prefix: filter || undefined }),
    ])
      .then(([ov, ev]) => {
        setOverview(ov);
        setEvents(ev.events);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load audit data."))
      .finally(() => setLoading(false));
  }, [authenticated, filter]);

  if (!ready || !authenticated) return <div className="min-h-screen bg-background" />;

  return (
    <div className="min-h-screen bg-background px-4 py-8">
      <div className="mx-auto max-w-5xl space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold flex items-center gap-2">
              <Activity className="size-6 text-primary" />
              Audit Center
            </h1>
            <p className="text-sm text-muted-foreground mt-1">Security events, uploads, agent runs</p>
          </div>
          <div className="flex gap-2">
            <a href={`${API_BASE}/audit/export?days=30`} target="_blank" rel="noreferrer">
              <Button variant="outline" size="sm"><Download className="size-4 mr-1" />Export CSV</Button>
            </a>
            <Link href="/admin/rbac"><Button variant="outline" size="sm">RBAC</Button></Link>
            <BackButton variant="outline" />
          </div>
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
        {loading ? (
          <div className="flex gap-2 text-sm text-muted-foreground"><Loader2 className="size-4 animate-spin" />Loading…</div>
        ) : (
          <>
            <div className="grid gap-3 sm:grid-cols-3">
              {[
                ["Uploads", (overview?.uploads as { total?: number })?.total ?? 0],
                ["Agent traces", (overview?.agent_traces as { total?: number })?.total ?? 0],
                ["Security events", (overview?.security_events as { total?: number })?.total ?? 0],
              ].map(([label, value]) => (
                <Card key={label as string} className="border-white/10 bg-card/65">
                  <CardContent className="p-4">
                    <p className="text-xs text-muted-foreground">{label}</p>
                    <p className="text-2xl font-semibold">{value}</p>
                  </CardContent>
                </Card>
              ))}
            </div>
            <Card className="border-white/10 bg-card/65">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Events</CardTitle>
                <input
                  className="h-8 rounded-md border border-white/10 bg-background px-2 text-xs"
                  placeholder="Filter by action prefix"
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                />
              </CardHeader>
              <CardContent className="space-y-2 max-h-96 overflow-y-auto">
                {events.map((event) => (
                  <div key={String(event.id)} className="rounded-md border border-white/5 px-3 py-2 text-xs">
                    <p className="font-medium">{String(event.action)}</p>
                    <p className="text-muted-foreground">user {String(event.user_id ?? "—")} · {String(event.created_at ?? "")}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}
