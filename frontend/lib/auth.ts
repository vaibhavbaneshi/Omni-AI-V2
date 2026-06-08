"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

export type OmniSession = {
  name: string;
  email: string;
  username: string;
  createdAt: string;
  /** @deprecated Auth uses HttpOnly cookies; kept for API compatibility */
  token?: string | null;
  refreshToken?: string | null;
};

const SESSION_KEY = "omni-ai-profile";
const AUTH_EXPIRED_KEY = "omni-ai-auth-expired";
const AUTH_EXPIRED_MESSAGE = "Your session has expired. Please sign in again.";

export { AUTH_EXPIRED_MESSAGE };

export function getCsrfToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|;\s*)omniai_csrf=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export function getSession(): OmniSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<OmniSession>;
    if (!parsed.email) return null;
    return {
      name: parsed.name || parsed.email.split("@")[0] || "User",
      email: parsed.email,
      username: parsed.username || parsed.email,
      createdAt: parsed.createdAt || new Date().toISOString(),
    };
  } catch {
    return null;
  }
}

export function isAuthenticated() {
  return Boolean(getSession()?.email);
}

export function persistSession(session: OmniSession) {
  if (typeof window === "undefined") return session;
  window.sessionStorage.removeItem(AUTH_EXPIRED_KEY);
  window.sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
  window.dispatchEvent(new Event("omni-auth-changed"));
  return session;
}

export function createSession({
  name,
  email,
  username,
}: {
  name?: string;
  email: string;
  username?: string;
}) {
  return persistSession({
    name: name?.trim() || email.split("@")[0] || "User",
    email,
    username: username || email,
    createdAt: new Date().toISOString(),
  });
}

export function clearSession() {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(SESSION_KEY);
  window.dispatchEvent(new Event("omni-auth-changed"));
}

export function clearAuthState() {
  clearSession();
}

export function consumeAuthExpiredMessage() {
  if (typeof window === "undefined") return null;
  const message = window.sessionStorage.getItem(AUTH_EXPIRED_KEY);
  if (message) window.sessionStorage.removeItem(AUTH_EXPIRED_KEY);
  return message;
}

export function handleAuthExpiration(status?: number, message = AUTH_EXPIRED_MESSAGE) {
  if (typeof window === "undefined" || status !== 401) return false;
  const pathname = window.location.pathname;
  clearAuthState();
  window.sessionStorage.setItem(AUTH_EXPIRED_KEY, message);
  if (pathname === "/login") {
    window.dispatchEvent(new Event("omni-auth-expired"));
    return true;
  }
  const redirect = pathname.startsWith("/login") ? "/dashboard" : pathname + window.location.search;
  window.location.replace(
    `/login?error=${encodeURIComponent(message)}&redirect=${encodeURIComponent(redirect)}`
  );
  return true;
}

export function getInitials(name?: string) {
  return (name || "User")
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

  return { session, ready, authenticated: Boolean(session?.email) };
}

export function useRequireAuth() {
  const router = useRouter();
  const pathname = usePathname();
  const state = useSession();

  useEffect(() => {
    if (!state.ready || state.authenticated) return;
    if (pathname === "/login") return;
    router.replace(`/login?redirect=${encodeURIComponent(pathname || "/dashboard")}`);
  }, [pathname, router, state.authenticated, state.ready]);

  return state;
}

export function useAuthRedirect(defaultPath = "/dashboard") {
  const router = useRouter();
  const state = useSession();
  const [redirect, setRedirect] = useState(defaultPath);

  useEffect(() => {
    const next = new URLSearchParams(window.location.search).get("redirect") || defaultPath;
    setRedirect(next);
  }, [defaultPath]);

  useEffect(() => {
    if (state.ready && state.authenticated) {
      router.replace(redirect);
    }
  }, [redirect, router, state.authenticated, state.ready]);

  return { ...state, redirect };
}
