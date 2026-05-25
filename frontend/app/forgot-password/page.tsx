"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function ForgotPasswordPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/login");
  }, [router]);

  return (
    <div className="min-h-dvh flex items-center justify-center bg-[#050505] p-4 text-muted-foreground">
      <div className="flex flex-col items-center gap-2">
        <span className="size-6 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
        <p className="text-sm">Redirecting to login...</p>
      </div>
    </div>
  );
}
