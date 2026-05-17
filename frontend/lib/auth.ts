"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

export type OmniSession = {
  name: string;
  email: string;
  token: string;
  createdAt: string;
};

const SESSION_KEY = "omni-ai-session";

export function getSession(): OmniSession | null {
  if (typeof window === "undefined") return null;

  try {
    const raw = window.localStorage.getItem(SESSION_KEY);
    return raw ? (JSON.parse(raw) as OmniSession) : null;
  } catch {
    window.localStorage.removeItem(SESSION_KEY);
    return null;
  }
}

export function isAuthenticated() {
  return Boolean(getSession()?.token);
}

export function createSession({
  name = "John Doe",
  email,
}: {
  name?: string;
  email: string;
}) {
  const session: OmniSession = {
    name,
    email,
    token: `demo-${crypto.randomUUID()}`,
    createdAt: new Date().toISOString(),
  };

  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  window.dispatchEvent(new Event("omni-auth-changed"));
  return session;
}

export function clearSession() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(SESSION_KEY);
  window.dispatchEvent(new Event("omni-auth-changed"));
}

export function getInitials(name?: string) {
  return (name || "John Doe")
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export function useSession() {
  const [session, setSession] = useState<OmniSession | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const sync = () => {
      setSession(getSession());
      setReady(true);
    };

    sync();
    window.addEventListener("storage", sync);
    window.addEventListener("omni-auth-changed", sync);

    return () => {
      window.removeEventListener("storage", sync);
      window.removeEventListener("omni-auth-changed", sync);
    };
  }, []);

  return { session, ready, authenticated: Boolean(session?.token) };
}

export function useRequireAuth() {
  const router = useRouter();
  const pathname = usePathname();
  const state = useSession();

  useEffect(() => {
    if (!state.ready || state.authenticated) return;
    router.replace(`/login?redirect=${encodeURIComponent(pathname || "/dashboard")}`);
  }, [pathname, router, state.authenticated, state.ready]);

  return state;
}

export function useAuthRedirect(defaultPath = "/dashboard") {
  const router = useRouter();
  const state = useSession();
  const redirect =
    typeof window === "undefined"
      ? defaultPath
      : new URLSearchParams(window.location.search).get("redirect") || defaultPath;

  useEffect(() => {
    if (state.ready && state.authenticated) {
      router.replace(redirect);
    }
  }, [redirect, router, state.authenticated, state.ready]);

  return { ...state, redirect };
}
