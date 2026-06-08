"use client";

import { useEffect, useState } from "react";
import { AlertCircle, X } from "lucide-react";
import { consumeAuthExpiredMessage } from "@/lib/auth";

export function AuthExpiredToast() {
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const expired = consumeAuthExpiredMessage();
    if (expired) {
      setMessage(expired);
      return;
    }

    const onExpired = () => {
      setMessage("Your session has expired. Please sign in again.");
    };

    window.addEventListener("omni-auth-expired", onExpired);
    return () => window.removeEventListener("omni-auth-expired", onExpired);
  }, []);

  if (!message) return null;

  return (
    <div
      role="status"
      className="fixed left-1/2 top-4 z-[100] flex w-[min(92vw,420px)] -translate-x-1/2 items-start gap-2 rounded-xl border border-amber-400/30 bg-[#14120b]/95 px-4 py-3 text-[13px] text-amber-50 shadow-lg backdrop-blur-md"
    >
      <AlertCircle className="mt-0.5 size-4 shrink-0 text-amber-300" />
      <div className="min-w-0 flex-1">
        <p className="font-medium text-amber-100">Session expired</p>
        <p className="mt-0.5 text-[12px] text-amber-50/85">{message}</p>
      </div>
      <button
        type="button"
        className="rounded-md p-1 text-amber-200/70 hover:bg-white/5 hover:text-amber-50"
        onClick={() => setMessage(null)}
        aria-label="Dismiss"
      >
        <X className="size-3.5" />
      </button>
    </div>
  );
}
