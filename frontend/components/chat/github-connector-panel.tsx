"use client";

import { useCallback, useEffect, useState } from "react";
import { Code2, Loader2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  getGitHubConnectorAuthorizeUrl,
  getGitHubConnectorStatus,
  listGitHubRepos,
  syncGitHubRepo,
} from "@/lib/api";

type GitHubConnectorPanelProps = {
  token?: string | null;
  sessionId?: number | null;
  embedded?: boolean;
};

export function GitHubConnectorPanel({
  token,
  sessionId,
  embedded = false,
}: GitHubConnectorPanelProps) {
  const [connected, setConnected] = useState(false);
  const [githubLogin, setGithubLogin] = useState<string | null>(null);
  const [repos, setRepos] = useState<Array<Record<string, unknown>>>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const status = await getGitHubConnectorStatus(token);
      setConnected(status.connected);
      setGithubLogin(status.github_login ?? null);
      if (status.connected) {
        const data = await listGitHubRepos(token);
        setRepos(data.repositories);
      } else {
        setRepos([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load GitHub connector.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleConnect = () => {
    window.location.href = getGitHubConnectorAuthorizeUrl();
  };

  const handleSync = async (repoFullName: string) => {
    setSyncing(repoFullName);
    setError(null);
    try {
      await syncGitHubRepo(repoFullName, token, {
        sessionId: sessionId ?? undefined,
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed.");
    } finally {
      setSyncing(null);
    }
  };

  const wrapperClass = embedded ? "space-y-4" : "rounded-xl border border-white/10 bg-card/50 p-4 space-y-4";

  return (
    <div className={wrapperClass}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Code2 className="size-4 text-foreground" />
            <h3 className="text-[13px] font-semibold">GitHub Connector</h3>
          </div>
          <p className="mt-1 text-[12px] text-muted-foreground/70">
            Sync repositories into your workspace for RAG indexing.
          </p>
        </div>
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="h-7 gap-1.5 text-[11px]"
          onClick={() => void load()}
          disabled={loading}
        >
          {loading ? <Loader2 className="size-3 animate-spin" /> : <RefreshCw className="size-3" />}
          Refresh
        </Button>
      </div>

      {error && (
        <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-[12px] text-destructive">
          {error}
        </p>
      )}

      {!connected ? (
        <div className="rounded-xl border border-dashed border-white/10 bg-white/[0.02] px-4 py-6 text-center">
          <p className="text-[13px] font-medium">Not connected</p>
          <p className="mt-1 text-[12px] text-muted-foreground/60 mb-4">
            Authorize GitHub to list and sync your repositories.
          </p>
          <Button type="button" size="sm" onClick={handleConnect}>
            Connect GitHub
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-[12px] text-muted-foreground">
            Connected as <span className="text-foreground font-medium">@{githubLogin}</span>
          </p>
          {repos.length === 0 && !loading && (
            <p className="text-[12px] text-muted-foreground">No repositories found.</p>
          )}
          {repos.slice(0, 15).map((repo) => {
            const fullName = String(repo.full_name ?? "");
            return (
              <div
                key={fullName}
                className="flex items-center justify-between gap-2 rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2"
              >
                <div className="min-w-0">
                  <p className="truncate text-[13px] font-medium">{fullName}</p>
                  <p className="text-[11px] text-muted-foreground capitalize">
                    {String(repo.sync_status ?? "not_synced").replace(/_/g, " ")}
                  </p>
                </div>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="h-7 shrink-0 text-[11px]"
                  disabled={syncing === fullName}
                  onClick={() => void handleSync(fullName)}
                >
                  {syncing === fullName ? <Loader2 className="size-3 animate-spin" /> : "Sync"}
                </Button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
