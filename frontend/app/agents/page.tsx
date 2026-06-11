"use client";

import { useCallback, useEffect, useState } from "react";
import { Bot, Loader2, Pause, Play, Plus, Trash2 } from "lucide-react";
import { BackButton } from "@/components/navigation/back-button";
import { useRequireAuth } from "@/lib/auth";
import {
  createAutonomousAgent,
  deleteAutonomousAgent,
  listAutonomousAgents,
  pauseAutonomousAgent,
  resumeAutonomousAgent,
  runAutonomousAgent,
  type AutonomousAgentRecord,
} from "@/lib/api";
import { formatFutureRun, formatPastRun } from "@/lib/format-relative-time";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

function agentDisplayStatus(agent: AutonomousAgentRecord): "idle" | "running" | "error" | "paused" {
  if (agent.status === "paused") return "paused";
  const runtime = (agent.config?.runtime_status as string | undefined) ?? "idle";
  if (runtime === "error") return "error";
  if (runtime === "running") return "running";
  return "idle";
}

const statusStyles: Record<string, string> = {
  idle: "border-emerald-300/20 bg-emerald-400/10 text-emerald-200",
  running: "border-primary/20 bg-primary/10 text-primary",
  error: "border-destructive/20 bg-destructive/10 text-destructive",
  paused: "border-amber-300/20 bg-amber-400/10 text-amber-200",
};

export default function AgentsPage() {
  const { ready, authenticated } = useRequireAuth();
  const [agents, setAgents] = useState<AutonomousAgentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listAutonomousAgents();
      setAgents(data.agents);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load agents.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (ready && authenticated) void load();
  }, [ready, authenticated, load]);

  const handleCreate = async () => {
    if (!name.trim()) return;
    setError(null);
    try {
      await createAutonomousAgent({
        name: name.trim(),
        agent_type: "document_monitor",
        schedule_kind: "daily",
        config: { stale_days: 14 },
      });
      setName("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed.");
    }
  };

  const withBusy = async (id: number, action: () => Promise<unknown>) => {
    setBusyId(id);
    try {
      await action();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed.");
    } finally {
      setBusyId(null);
    }
  };

  if (!ready || !authenticated) return <div className="min-h-screen bg-background" />;

  return (
    <div className="min-h-screen bg-background px-4 py-8">
      <div className="mx-auto max-w-4xl space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold flex items-center gap-2">
              <Bot className="size-6 text-primary" />
              Agent Workspace
            </h1>
            <p className="text-sm text-muted-foreground mt-1">Create, schedule, and monitor autonomous agents</p>
          </div>
          <BackButton variant="outline" />
        </div>

        <Card className="border-white/10 bg-card/65">
          <CardHeader><CardTitle>Create document monitor</CardTitle></CardHeader>
          <CardContent className="flex gap-2">
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Agent name" />
            <Button onClick={() => void handleCreate()} disabled={!name.trim()}>
              <Plus className="size-4 mr-1" /> Create
            </Button>
          </CardContent>
        </Card>

        {error && <p className="text-sm text-destructive">{error}</p>}

        {loading ? (
          <div className="flex justify-center py-12"><Loader2 className="size-6 animate-spin text-muted-foreground" /></div>
        ) : (
          <div className="space-y-3">
            {agents.map((agent) => {
              const displayStatus = busyId === agent.id ? "running" : agentDisplayStatus(agent);
              return (
                <Card key={agent.id} className="border-white/10 bg-card/65">
                  <CardContent className="py-4 flex items-center justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <p className="font-medium">{agent.name}</p>
                        <Badge variant="outline" className={cn("text-[10px] capitalize", statusStyles[displayStatus])}>
                          {displayStatus}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {agent.agent_type} · schedule: {agent.schedule_kind}
                      </p>
                      {agent.next_run_at && (
                        <p className="text-xs text-muted-foreground">{formatFutureRun(agent.next_run_at)}</p>
                      )}
                      <p className="text-xs text-muted-foreground">{formatPastRun(agent.last_run_at)}</p>
                      {typeof agent.config?.last_error === "string" && displayStatus === "error" && (
                        <p className="text-xs text-destructive">{agent.config.last_error}</p>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" disabled={busyId === agent.id} onClick={() => void withBusy(agent.id, () => runAutonomousAgent(agent.id))}>
                        {busyId === agent.id ? <Loader2 className="size-4 animate-spin" /> : <Play className="size-4" />}
                      </Button>
                      {agent.status === "paused" ? (
                        <Button size="sm" variant="outline" onClick={() => void withBusy(agent.id, () => resumeAutonomousAgent(agent.id))}>
                          <Play className="size-4" />
                        </Button>
                      ) : (
                        <Button size="sm" variant="outline" onClick={() => void withBusy(agent.id, () => pauseAutonomousAgent(agent.id))}>
                          <Pause className="size-4" />
                        </Button>
                      )}
                      <Button size="sm" variant="destructive" onClick={() => void withBusy(agent.id, () => deleteAutonomousAgent(agent.id))}>
                        <Trash2 className="size-4" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
            {!agents.length && <p className="text-sm text-muted-foreground">No agents yet. Create one or install from the marketplace.</p>}
          </div>
        )}
      </div>
    </div>
  );
}
