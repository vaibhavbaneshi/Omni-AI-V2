"use client";

import { useEffect, useState } from "react";
import { Code2, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ApiError, getOAuthProviders, getOAuthStartUrl } from "@/lib/api";

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

  const handleSocialLogin = async (provider: "github" | "google") => {
    if (disabled || loadingProvider) return;

    setLoadingProvider(provider);
    onClearError?.();

    try {
      const latest = await getOAuthProviders();
      setProviders(latest);

      if (!latest[provider]) {
        const label = provider === "github" ? "GitHub" : "Google";
        onError?.(
          `${label} sign-in is not configured. Add ${label.toUpperCase()}_CLIENT_ID and ${label.toUpperCase()}_CLIENT_SECRET to the backend environment.`
        );
        return;
      }

      window.location.assign(getOAuthStartUrl(provider, nextPath));
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : "Unable to start social sign-in. Check that the backend is running.";
      onError?.(message);
    } finally {
      setLoadingProvider(null);
    }
  };

  const isBusy = disabled || Boolean(loadingProvider);

  return (
    <div className="grid grid-cols-2 gap-3 mb-6">
      <Button
        type="button"
        variant="outline"
        className="w-full bg-white/[0.02] border-white/5 hover:bg-white/5 hover:text-foreground transition-colors text-[13px] h-9"
        disabled={isBusy}
        title={ready && !providers.github ? "GitHub OAuth is not configured on the server" : undefined}
        onClick={() => handleSocialLogin("github")}
      >
        <Code2 className="size-4 mr-2 opacity-70" />
        {loadingProvider === "github" ? "Connecting..." : "GitHub"}
      </Button>
      <Button
        type="button"
        variant="outline"
        className="w-full bg-white/[0.02] border-white/5 hover:bg-white/5 hover:text-foreground transition-colors text-[13px] h-9"
        disabled={isBusy}
        title={ready && !providers.google ? "Google OAuth is not configured on the server" : undefined}
        onClick={() => handleSocialLogin("google")}
      >
        <Globe className="size-4 mr-2 opacity-70" />
        {loadingProvider === "google" ? "Connecting..." : "Google"}
      </Button>
    </div>
  );
}
