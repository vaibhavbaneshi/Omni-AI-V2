"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Cable, Loader2, RefreshCw } from "lucide-react";
import { useRequireAuth } from "@/lib/auth";
import { connectConnectorHub, getConnectorHubStatus, syncConnectorHub } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type ConnectorRow = Record<string, unknown> & {
  id?: string;
  label?: string;
  connected?: boolean;
  document_count?: number;
  last_sync_at?: string | null;
};

export default function ConnectorsPage() {
  const { ready, authenticated } = useRequireAuth();
  const [connectors, setConnectors] = useState<ConnectorRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [notionToken, setNotionToken] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getConnectorHubStatus();
      setConnectors(data.connectors as ConnectorRow[]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load connectors.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (ready && authenticated) void load();
  }, [ready, authenticated, load]);

  const handleSync = async (connectorType: string) => {
    setSyncing(connectorType);
    setError(null);
    try {
      await syncConnectorHub(connectorType);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed.");
    } finally {
      setSyncing(null);
    }
  };

  const connectNotion = async () => {
    if (!notionToken.trim()) return;
    setError(null);
    try {
      await connectConnectorHub("notion", { api_token: notionToken.trim() });
      setNotionToken("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Notion connect failed.");
    }
  };

  if (!ready || !authenticated) return <div className="min-h-screen bg-background" />;

  return (
    <div className="min-h-screen bg-background px-4 py-8">
      <div className="mx-auto max-w-4xl space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold flex items-center gap-2">
              <Cable className="size-6 text-primary" />
              Connectors
            </h1>
            <p className="text-sm text-muted-foreground mt-1">Connect sources and sync into your knowledge hub</p>
          </div>
          <Link href="/dashboard"><Button variant="outline" size="sm">Dashboard</Button></Link>
        </div>

        <Card className="border-white/10 bg-card/65">
          <CardHeader><CardTitle>Connect Notion</CardTitle></CardHeader>
          <CardContent className="flex gap-2">
            <Input type="password" value={notionToken} onChange={(e) => setNotionToken(e.target.value)} placeholder="Notion integration token" />
            <Button onClick={() => void connectNotion()} disabled={!notionToken.trim()}>Connect</Button>
          </CardContent>
        </Card>

        {error && <p className="text-sm text-destructive">{error}</p>}

        {loading ? (
          <Loader2 className="size-6 animate-spin mx-auto text-muted-foreground" />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {connectors.map((row) => {
              const id = String(row.id ?? "");
              return (
                <Card key={id} className="border-white/10 bg-card/65">
                  <CardHeader>
                    <CardTitle className="text-base">{String(row.label ?? id)}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 text-sm">
                    <p className="text-muted-foreground">
                      {row.connected ? "Connected" : "Not connected"} · {Number(row.document_count ?? 0)} docs
                    </p>
                    {row.last_sync_at && <p className="text-xs text-muted-foreground">Last sync: {new Date(String(row.last_sync_at)).toLocaleString()}</p>}
                    {id === "github" ? (
                      <Link href="/chat"><Button size="sm" variant="outline">Open GitHub panel</Button></Link>
                    ) : (
                      <Button size="sm" variant="outline" disabled={!row.connected || syncing === id} onClick={() => void handleSync(id)}>
                        {syncing === id ? <Loader2 className="size-4 animate-spin mr-1" /> : <RefreshCw className="size-4 mr-1" />}
                        Sync
                      </Button>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
