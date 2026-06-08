"use client";

import { useEffect, useState } from "react";
import { Bot, Clock, Loader2 } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { listAgentTraces, type AgentTraceRecord } from "@/lib/api";

type AgentTracesPanelProps = {
  token?: string | null;
};

export function AgentTracesPanel({ token }: AgentTracesPanelProps) {
  const [traces, setTraces] = useState<AgentTraceRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    listAgentTraces(token, 8)
      .then(setTraces)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load traces."))
      .finally(() => setLoading(false));
  }, [token]);

  return (
    <Card className="rounded-lg border-white/10 bg-card/65 shadow-premium">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Bot className="size-5 text-primary" />
          Agent Traces
        </CardTitle>
        <CardDescription>Recent multi-agent planner → specialist → critic runs</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        {loading && (
          <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" />
            Loading traces…
          </div>
        )}
        {error && <p className="text-sm text-destructive">{error}</p>}
        {!loading && !error && traces.length === 0 && (
          <p className="py-4 text-sm text-muted-foreground">
            No multi-agent runs yet. Use multi-agent mode in chat or POST /agents/multi-agent.
          </p>
        )}
        {traces.map((trace) => (
          <div
            key={trace.id}
            className="rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2.5"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="truncate text-sm font-medium">{trace.query}</p>
              <Badge variant="outline" className="border-white/10 text-[10px] capitalize">
                {trace.status}
              </Badge>
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-3 text-[11px] text-muted-foreground">
              <span className="inline-flex items-center gap-1">
                <Clock className="size-3" />
                {trace.latency_ms != null ? `${trace.latency_ms}ms` : "—"}
              </span>
              <span>{trace.agent_steps?.length ?? 0} agent steps</span>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
