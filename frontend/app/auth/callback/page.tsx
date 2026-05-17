"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, Sparkles } from "lucide-react";
import { createSession } from "@/lib/auth";

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [message, setMessage] = useState("Completing sign-in...");

  useEffect(() => {
    const error = searchParams.get("error");
    const token = searchParams.get("token");
    const email = searchParams.get("email");
    const name = searchParams.get("name");
    const username = searchParams.get("username");
    const next = searchParams.get("next") || "/dashboard";

    if (error) {
      setMessage(error);
      const timeout = window.setTimeout(() => {
        router.replace(`/login?error=${encodeURIComponent(error)}`);
      }, 2500);
      return () => window.clearTimeout(timeout);
    }

    if (!token || !email) {
      setMessage("Invalid authentication response.");
      const timeout = window.setTimeout(() => {
        router.replace("/login");
      }, 2500);
      return () => window.clearTimeout(timeout);
    }

    createSession({
      email,
      name: name || email.split("@")[0],
      username: username || email,
      token,
    });

    router.replace(next.startsWith("/") ? next : "/dashboard");
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
