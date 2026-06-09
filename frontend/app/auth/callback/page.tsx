"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, Sparkles } from "lucide-react";
import { createSession } from "@/lib/auth";
import { fetchAuthSession } from "@/lib/api";
import { sanitizeAuthError } from "@/lib/user-facing-errors";

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [message, setMessage] = useState("Completing sign-in...");

  useEffect(() => {
    const error = searchParams.get("error");
    const next = searchParams.get("next") || "/dashboard";
    const status = searchParams.get("status");
    const legacyToken = searchParams.get("token");
    const legacyEmail = searchParams.get("email");

    if (error) {
      const safeError = sanitizeAuthError(error);
      setMessage(safeError);
      const timeout = window.setTimeout(() => {
        router.replace(`/login?error=${encodeURIComponent(safeError)}`);
      }, 2500);
      return () => window.clearTimeout(timeout);
    }

    if (legacyToken && legacyEmail) {
      createSession({
        email: legacyEmail,
        name: searchParams.get("name") || legacyEmail.split("@")[0] || "User",
        username: searchParams.get("username") || legacyEmail,
      });
      router.replace(next.startsWith("/") ? next : "/dashboard");
      return;
    }

    if (status === "ok" || legacyToken) {
      fetchAuthSession()
        .then((profile) => {
          createSession({
            email: profile.email,
            name: profile.name || profile.username,
            username: profile.username,
          });
          router.replace(next.startsWith("/") ? next : "/dashboard");
        })
        .catch(() => {
          const signInError = "Sign-in could not be completed. Please try again.";
          setMessage(signInError);
          router.replace(`/login?error=${encodeURIComponent(signInError)}`);
        });
      return;
    }

    setMessage("Invalid authentication response.");
    router.replace("/login");
  }, [router, searchParams]);

  return (
    <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
      <Loader2 className="size-4 animate-spin text-primary" />
      <span>{message}</span>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <div className="min-h-dvh flex items-center justify-center bg-[#050505] p-6">
      <div className="w-full max-w-sm rounded-3xl border border-white/5 bg-white/[0.02] p-8 text-center shadow-premium backdrop-blur-2xl">
        <div className="mx-auto mb-4 flex size-12 items-center justify-center rounded-xl bg-primary/10 border border-primary/20">
          <Sparkles className="size-5 text-primary" />
        </div>
        <Suspense
          fallback={
            <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin text-primary" />
              <span>Completing sign-in...</span>
            </div>
          }
        >
          <AuthCallbackContent />
        </Suspense>
      </div>
    </div>
  );
}
