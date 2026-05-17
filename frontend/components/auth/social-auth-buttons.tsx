"use client";

import { useEffect, useState } from "react";
import { Code2, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import { API_BASE, getOAuthProviders, getOAuthStartUrl } from "@/lib/api";

type SocialAuthButtonsProps = {
  nextPath?: string;
  disabled?: boolean;
  onError?: (message: string) => void;
  onClearError?: () => void;
};

export function SocialAuthButtons({
  nextPath = "/dashboard",
  disabled = false,
  onError,
  onClearError,
}: SocialAuthButtonsProps) {
  const [providers, setProviders] = useState({ github: false, google: false });
  const [ready, setReady] = useState(false);
  const [loadingProvider, setLoadingProvider] = useState<"github" | "google" | null>(null);
  const [inlineError, setInlineError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const result = await getOAuthProviders();
        if (!cancelled) {
          setProviders(result);
        }
      } catch {
        if (!cancelled) {
          setProviders({ github: false, google: false });
        }
      } finally {
        if (!cancelled) {
          setReady(true);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const reportError = (message: string) => {
    setInlineError(message);
    onError?.(message);
  };

  const handleSocialLogin = (provider: "github" | "google") => {
    if (disabled || loadingProvider) return;

    onClearError?.();
    setInlineError(null);
    setLoadingProvider(provider);

    const targetUrl = getOAuthStartUrl(provider, nextPath);

    if (!API_BASE) {
      reportError("API URL is not configured. Set NEXT_PUBLIC_API_URL in the frontend environment.");
      setLoadingProvider(null);
      return;
    }

    // Redirect immediately — do not block on a providers preflight request.
    window.location.href = targetUrl;
  };

  const isBusy = disabled || Boolean(loadingProvider);

  return (
    <div className="space-y-2 mb-6">
      <div className="grid grid-cols-2 gap-3">
        <Button
          type="button"
          variant="outline"
          className="w-full bg-white/[0.02] border-white/5 hover:bg-white/5 hover:text-foreground transition-colors text-[13px] h-9"
          disabled={isBusy}
          title={
            ready && !providers.github
              ? "GitHub OAuth may not be configured on the server"
              : undefined
          }
          onClick={() => handleSocialLogin("github")}
        >
          <Code2 className="size-4 mr-2 opacity-70" />
          {loadingProvider === "github" ? "Redirecting..." : "GitHub"}
        </Button>
        <Button
          type="button"
          variant="outline"
          className="w-full bg-white/[0.02] border-white/5 hover:bg-white/5 hover:text-foreground transition-colors text-[13px] h-9"
          disabled={isBusy}
          title={
            ready && !providers.google
              ? "Google OAuth may not be configured on the server"
              : undefined
          }
          onClick={() => handleSocialLogin("google")}
        >
          <Globe className="size-4 mr-2 opacity-70" />
          {loadingProvider === "google" ? "Redirecting..." : "Google"}
        </Button>
      </div>

      {inlineError && (
        <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-[12px] text-destructive">
          {inlineError}
        </p>
      )}

      {ready && !providers.github && !providers.google && (
        <p className="text-[11px] text-muted-foreground/70">
          Social sign-in requires OAuth keys in the backend `.env`. Restart the API after adding them.
        </p>
      )}
    </div>
  );
}
