"use client";

import { useCallback, useEffect, useRef, useState } from "react";
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
  onDocumentsRefresh?: () => Promise<unknown>;
};

export function GitHubConnectorPanel({
  token,
  embedded = false,
  onDocumentsRefresh,
}: GitHubConnectorPanelProps) {
  const [connected, setConnected] = useState(false);
  const [githubLogin, setGithubLogin] = useState<string | null>(null);
  const [statusSignedInWithGitHub, setStatusSignedInWithGitHub] = useState(false);
  const [repos, setRepos] = useState<Array<Record<string, unknown>>>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const pollTimerRef = useRef<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const status = await getGitHubConnectorStatus(token);
      setConnected(status.connected);
      setGithubLogin(status.github_login ?? null);
      setStatusSignedInWithGitHub(Boolean(status.signed_in_with_github));
      if (status.connected) {
        const data = await listGitHubRepos(token);
        setRepos(data.repositories);
        return data.repositories;
      }
      setRepos([]);
      return [];
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load GitHub connector.");
      return [];
    } finally {
      setLoading(false);
    }
  }, [token]);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      window.clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const pollUntilSettled = useCallback(
    (repoFullName: string) => {
      stopPolling();
      let attempts = 0;
      pollTimerRef.current = window.setInterval(() => {
        attempts += 1;
        void load().then((nextRepos) => {
          const repo = nextRepos.find((item) => String(item.full_name) === repoFullName);
          const syncStatus = String(repo?.sync_status ?? "");
          if (syncStatus === "complete") {
            stopPolling();
            setSyncing(null);
            const count = Number(repo?.files_indexed ?? 0);
            setSuccess(
              count > 0
                ? `Synced ${count} file${count === 1 ? "" : "s"} from ${repoFullName}. Check the GitHub collection in Files.`
                : `Sync finished for ${repoFullName}, but no indexable source files were found. Try a repo with .js, .jsx, .ts, .md, or .py files outside node_modules.`
            );
            void onDocumentsRefresh?.();
          } else if (syncStatus === "failed") {
            stopPolling();
            setSyncing(null);
            setError(
              String(repo?.sync_error ?? "GitHub sync failed. Try reconnecting GitHub and sync again.")
            );
          } else if (attempts >= 30) {
            stopPolling();
            setSyncing(null);
            setSuccess("Sync is still running. Refresh again in a moment.");
          }
        });
      }, 2000);
    },
    [load, onDocumentsRefresh, stopPolling]
  );

  useEffect(() => {
    void load();
    return () => stopPolling();
  }, [load, stopPolling]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("github") === "connected") {
      void load();
      params.delete("github");
      const suffix = params.size ? `?${params.toString()}` : "";
      window.history.replaceState({}, "", `${window.location.pathname}${suffix}`);
    }
  }, [load]);

  const handleConnect = async () => {
    setError(null);
    setSuccess(null);
    try {
      const { authorize_url } = await getGitHubConnectorAuthorizeUrl(token, "/chat");
      window.location.href = authorize_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start GitHub authorization.");
    }
  };

  const handleSync = async (repoFullName: string) => {
    setSyncing(repoFullName);
    setError(null);
    setSuccess(null);
    try {
      const result = await syncGitHubRepo(repoFullName, token);
      if (result.status === "running") {
        setSuccess(result.message ?? "Sync started. This may take a minute for larger repositories.");
        pollUntilSettled(repoFullName);
        return;
      }
            if (result.status === "unchanged") {
        setSuccess(`Already up to date (${result.files_indexed ?? 0} indexed files).`);
      } else {
        const count = result.files_indexed ?? 0;
        setSuccess(
          count > 0
            ? `Synced ${count} file${count === 1 ? "" : "s"} from ${repoFullName}.`
            : `Sync finished for ${repoFullName}, but no indexable source files were found. Supported: code and docs in folders like frontend/ or backend/ (.js, .jsx, .ts, .py, .md, etc.). node_modules and build folders are skipped.`
        );
      }
      await load();
      await onDocumentsRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed.");
    } finally {
      if (!pollTimerRef.current) {
        setSyncing(null);
      }
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

      {success && (
        <p className="rounded-lg border border-emerald-400/30 bg-emerald-400/10 px-3 py-2 text-[12px] text-emerald-100">
          {success}
        </p>
      )}

      {!connected ? (
        <div className="rounded-xl border border-dashed border-white/10 bg-white/[0.02] px-4 py-6 text-center">
          <p className="text-[13px] font-medium">Not connected</p>
          <p className="mt-1 text-[12px] text-muted-foreground/60 mb-4">
            {statusSignedInWithGitHub
              ? "Your GitHub sign-in will be linked automatically after you sign in again. You can also connect manually below."
              : "Authorize GitHub to list and sync your repositories."}
          </p>
          <Button type="button" size="sm" onClick={() => void handleConnect()}>
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
            const syncStatus = String(repo.sync_status ?? "not_synced");
            return (
              <div
                key={fullName}
                className="flex items-center justify-between gap-2 rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2"
              >
                <div className="min-w-0">
                  <p className="truncate text-[13px] font-medium">{fullName}</p>
                  <p className="text-[11px] text-muted-foreground capitalize">
                    {syncStatus.replace(/_/g, " ")}
                    {syncStatus === "complete" && typeof repo.files_indexed === "number"
                      ? ` · ${repo.files_indexed} files`
                      : ""}
                  </p>
                </div>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="h-7 shrink-0 text-[11px]"
                  disabled={syncing === fullName || syncStatus === "running"}
                  onClick={() => void handleSync(fullName)}
                >
                  {syncing === fullName || syncStatus === "running" ? (
                    <Loader2 className="size-3 animate-spin" />
                  ) : (
                    "Sync"
                  )}
                </Button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
