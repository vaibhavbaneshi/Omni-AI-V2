"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Code2, Loader2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  disconnectGitHub,
  getGitHubConnectorAuthorizeUrl,
  getGitHubConnectorStatus,
  listGitHubRepos,
  syncGitHubRepo,
} from "@/lib/api";

type SyncResult = Awaited<ReturnType<typeof syncGitHubRepo>>;

function describeSyncResult(repoFullName: string, result: SyncResult): { kind: "success" | "error"; message: string } {
  if (result.status === "queued" && !result.files_indexed && !result.candidates_seen) {
    return {
      kind: "error",
      message:
        String(result.message ?? "") ||
        "GitHub sync hit a legacy admin stub endpoint. Redeploy the latest backend and try again.",
    };
  }

  const count = Number(result.files_indexed ?? 0);
  const candidates = Number(result.candidates_seen ?? 0);
  const tarballMembers = result.tarball_members;
  const skippedExtension = Number(result.skipped_extension ?? 0);

  if (count > 0) {
    return {
      kind: "success",
      message: `Synced ${count} file${count === 1 ? "" : "s"} from ${repoFullName}. Check the GitHub collection in Files.`,
    };
  }
  if (candidates > 0) {
    return {
      kind: "error",
      message: `Found ${candidates} source file${candidates === 1 ? "" : "s"} in ${repoFullName} but none were indexed. Check backend logs or reconnect GitHub with repo access.`,
    };
  }
  if (typeof tarballMembers === "number" && tarballMembers === 0) {
    return {
      kind: "error",
      message: `GitHub returned an empty archive for ${repoFullName}. Revoke Omni-AI in GitHub settings, reconnect, and sync again.`,
    };
  }
  if (skippedExtension > 0) {
    return {
      kind: "success",
      message: `Sync finished for ${repoFullName}, but no supported source files were found (${skippedExtension} files skipped by type). Supported: .js, .jsx, .ts, .tsx, .py, .md, etc.`,
    };
  }
  return {
    kind: "error",
    message: `Sync finished for ${repoFullName} with 0 indexed files. Revoke Omni-AI in GitHub settings, reconnect with repository access, then sync again.`,
  };
}

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
  const [hasRepoScope, setHasRepoScope] = useState(true);
  const [revokeUrl, setRevokeUrl] = useState<string | null>(null);
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
      setHasRepoScope(status.has_repo_scope !== false);
      setRevokeUrl(status.revoke_url ?? null);
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
            const candidates = Number(repo?.candidates_seen ?? 0);
            if (count > 0) {
              setSuccess(
                `Synced ${count} file${count === 1 ? "" : "s"} from ${repoFullName}. Check the GitHub collection in Files.`
              );
            } else if (candidates > 0) {
              setError(
                `Found ${candidates} source files in ${repoFullName} but indexing failed. Check backend logs or reconnect GitHub.`
              );
            } else {
              setSuccess(
                `Sync finished for ${repoFullName}, but no indexable source files were found. Reconnect GitHub if this repo is private.`
              );
            }
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
      const { authorize_url, revoke_url } = await getGitHubConnectorAuthorizeUrl(token, "/chat");
      if (revoke_url) {
        setRevokeUrl(revoke_url);
      }
      window.location.href = authorize_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start GitHub authorization.");
    }
  };

  const handleDisconnect = async () => {
    setError(null);
    setSuccess(null);
    try {
      await disconnectGitHub(token);
      setConnected(false);
      setGithubLogin(null);
      setRepos([]);
      setSuccess("GitHub disconnected. Your app login is unchanged — reconnect anytime from here.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to disconnect GitHub.");
    }
  };

  const handleSync = async (repoFullName: string) => {
    setSyncing(repoFullName);
    setError(null);
    setSuccess(null);
    try {
      const result = await syncGitHubRepo(repoFullName, token);
      if (result.status === "queued") {
        setError(
          String(result.message ?? "GitHub sync was queued on a legacy endpoint and did not run. Redeploy the backend.")
        );
        await load();
        return;
      }
      if (result.status === "running") {
        setSuccess(result.message ?? "Sync already in progress for this repository.");
        pollUntilSettled(repoFullName);
        return;
      }
      if (result.status === "unchanged") {
        setSuccess(`Already up to date (${result.files_indexed ?? 0} indexed files).`);
      } else {
        const feedback = describeSyncResult(repoFullName, result);
        if (feedback.kind === "error") {
          setError(feedback.message);
        } else if ((result.files_indexed ?? 0) > 0) {
          setSuccess(
            `${feedback.message} Indexing runs in the background — open Files → GitHub to browse (40 at a time).`
          );
        } else {
          setSuccess(feedback.message);
        }
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
              ? "GitHub may skip the permission screen if Omni-AI is already authorized. Revoke the app in GitHub settings first if sync fails."
              : "Authorize GitHub to list and sync your repositories (repo scope required)."}
          </p>
          {revokeUrl && (
            <p className="mb-4 text-[11px] text-muted-foreground/70">
              Already authorized?{" "}
              <a
                href={revokeUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-foreground underline underline-offset-2"
              >
                Revoke Omni-AI in GitHub
              </a>{" "}
              first, then connect again.
            </p>
          )}
          <Button type="button" size="sm" onClick={() => void handleConnect()}>
            Connect GitHub
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-[12px] text-muted-foreground">
            Connected as <span className="text-foreground font-medium">@{githubLogin}</span>
            {" · "}
            Stays linked to your account after logout. Use Disconnect to remove GitHub access.
          </p>
          {!hasRepoScope && revokeUrl && (
            <p className="rounded-lg border border-amber-400/30 bg-amber-400/10 px-3 py-2 text-[12px] text-amber-100">
              Repository access is missing.{" "}
              <a href={revokeUrl} target="_blank" rel="noopener noreferrer" className="underline underline-offset-2">
                Revoke Omni-AI in GitHub
              </a>
              , reconnect, and approve repository access.
            </p>
          )}
          <div className="flex justify-end">
            <Button
              type="button"
              size="sm"
              variant="ghost"
              className="h-7 text-[11px] text-muted-foreground hover:text-destructive"
              onClick={() => void handleDisconnect()}
            >
              Disconnect GitHub
            </Button>
          </div>
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
