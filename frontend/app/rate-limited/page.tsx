"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Clock, ShieldAlert, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { sanitizeRateLimitError } from "@/lib/user-facing-errors";

function formatCountdown(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes <= 0) {
    return `${seconds}s`;
  }
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

function RateLimitedContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialRetryAfter = useMemo(() => {
    const parsed = Number.parseInt(searchParams.get("retry_after") || "60", 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 60;
  }, [searchParams]);

  const [remaining, setRemaining] = useState(initialRetryAfter);
  const message = sanitizeRateLimitError({ retryAfter: initialRetryAfter });

  useEffect(() => {
    setRemaining(initialRetryAfter);
  }, [initialRetryAfter]);

  useEffect(() => {
    if (remaining <= 0) return;
    const timer = window.setInterval(() => {
      setRemaining((current) => Math.max(0, current - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [remaining]);

  const canRetry = remaining <= 0;

  return (
    <div className="w-full max-w-md rounded-3xl border border-white/5 bg-white/[0.02] p-8 text-center shadow-premium backdrop-blur-2xl">
      <div className="mx-auto mb-5 flex size-14 items-center justify-center rounded-2xl border border-amber-400/20 bg-amber-400/10">
        <ShieldAlert className="size-6 text-amber-300" />
      </div>

      <h1 className="text-xl font-semibold tracking-tight text-foreground">Slow down for a moment</h1>
      <p className="mt-2 text-[13px] leading-relaxed text-muted-foreground/85">{message}</p>

      <div className="mt-6 rounded-2xl border border-white/5 bg-black/20 px-4 py-5">
        <div className="mx-auto mb-2 flex size-10 items-center justify-center rounded-full border border-white/10 bg-white/[0.03]">
          <Clock className="size-4 text-primary" />
        </div>
        <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground/70">Retry in</p>
        <p className="mt-1 font-mono text-3xl font-semibold tabular-nums text-foreground">
          {canRetry ? "Ready" : formatCountdown(remaining)}
        </p>
      </div>

      <div className="mt-6 flex flex-col gap-2">
        <Button
          type="button"
          className="h-11 rounded-xl"
          disabled={!canRetry}
          onClick={() => router.replace("/login")}
        >
          {canRetry ? "Back to sign in" : "Please wait..."}
        </Button>
        <Button asChild type="button" variant="ghost" className="h-10 rounded-xl text-[13px]">
          <Link href="/">Return home</Link>
        </Button>
      </div>

      <p className="mt-5 text-[11px] leading-relaxed text-muted-foreground/60">
        We limit sign-in attempts to protect your account. If this keeps happening, wait a few minutes or contact support.
      </p>
    </div>
  );
}

export default function RateLimitedPage() {
  return (
    <div className="min-h-dvh flex items-center justify-center bg-[#050505] p-6">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,oklch(0.25_0.08_280),transparent_50%)] opacity-40" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_100%,oklch(0.2_0.06_200),transparent_50%)] opacity-30" />
      </div>

      <div className="relative z-10 w-full flex flex-col items-center">
        <div className="mb-6 flex items-center gap-2 text-muted-foreground/70">
          <div className="flex size-8 items-center justify-center rounded-lg border border-primary/20 bg-primary/10">
            <Sparkles className="size-4 text-primary" />
          </div>
          <span className="text-[12px] font-medium tracking-wide">Omni AI</span>
        </div>

        <Suspense
          fallback={
            <div className="w-full max-w-md rounded-3xl border border-white/5 bg-white/[0.02] p-8 text-center text-sm text-muted-foreground">
              Loading...
            </div>
          }
        >
          <RateLimitedContent />
        </Suspense>
      </div>
    </div>
  );
}
