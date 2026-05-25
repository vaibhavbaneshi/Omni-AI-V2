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
    <div className="space-y-3 mb-6">
      <Button
        type="button"
        variant="outline"
        className="w-full bg-white/[0.02] border-white/5 hover:bg-white/5 hover:text-foreground hover:border-white/10 transition-all text-[13px] h-11 flex items-center justify-center rounded-xl font-medium"
        disabled={isBusy}
        title={
          ready && !providers.google
            ? "Google OAuth may not be configured on the server"
            : undefined
        }
        onClick={() => handleSocialLogin("google")}
      >
        <svg className="size-4 mr-2.5" viewBox="0 0 24 24">
          <path
            fill="#EA4335"
            d="M5.266 9.765A7.077 7.077 0 0 1 12 4.909c1.69 0 3.218.6 4.418 1.582l3.51-3.51C17.642 1.091 14.964 0 12 0 7.33 0 3.305 2.688 1.341 6.614l3.925 3.15z"
          />
          <path
            fill="#4285F4"
            d="M23.773 12.273c0-.818-.073-1.609-.209-2.373H12v4.5h6.6a5.64 5.64 0 0 1-2.445 3.7l3.8 2.945c2.223-2.045 3.818-5.055 3.818-8.773z"
          />
          <path
            fill="#FBBC05"
            d="M5.266 14.235L1.341 17.38A11.968 11.968 0 0 0 12 24c3.082 0 5.955-1.009 8.164-2.736l-3.8-2.945a7.126 7.126 0 0 1-4.364 1.482c-2.909 0-5.436-1.955-6.314-4.59z"
          />
          <path
            fill="#34A853"
            d="M1.341 6.614A11.944 11.944 0 0 0 0 12c0 1.927.455 3.755 1.259 5.382l4.007-3.147C5.073 13.436 5 12.727 5 12c0-.818.118-1.609.341-2.386L1.341 6.614z"
          />
        </svg>
        {loadingProvider === "google" ? "Redirecting..." : "Continue with Google"}
      </Button>

      <Button
        type="button"
        variant="outline"
        className="w-full bg-white/[0.02] border-white/5 hover:bg-white/5 hover:text-foreground hover:border-white/10 transition-all text-[13px] h-11 flex items-center justify-center rounded-xl font-medium"
        disabled={isBusy}
        title={
          ready && !providers.github
            ? "GitHub OAuth may not be configured on the server"
            : undefined
        }
        onClick={() => handleSocialLogin("github")}
      >
        <svg className="size-4 mr-2.5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/>
        </svg>
        {loadingProvider === "github" ? "Redirecting..." : "Continue with GitHub"}
      </Button>

      {inlineError && (
        <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-[12px] text-destructive">
          {inlineError}
        </p>
      )}

      {ready && !providers.github && !providers.google && (
        <p className="text-[11px] text-muted-foreground/70 text-center mt-2">
          Social sign-in requires OAuth keys in the backend `.env`. Restart the API after adding them.
        </p>
      )}
    </div>
  );
}
