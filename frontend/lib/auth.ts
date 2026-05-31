"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

export type OmniSession = {
  name: string;
  email: string;
  username: string;
  token: string;
  refreshToken?: string;
  createdAt: string;
};

const SESSION_KEY = "omni-ai-session";
const AUTH_EXPIRED_KEY = "omni-ai-auth-expired";
const AUTH_EXPIRED_MESSAGE = "Your session has expired. Please sign in again.";
const AUTH_STORAGE_KEY_PATTERNS = [/^omni-ai-session$/, /auth/i, /token/i];

export { AUTH_EXPIRED_MESSAGE };

export function getSession(): OmniSession | null {
  if (typeof window === "undefined") return null;

  try {
    const raw = window.localStorage.getItem(SESSION_KEY);
    if (!raw) return null;

    const parsed = JSON.parse(raw) as Partial<OmniSession>;
    if (!parsed.token || !parsed.email) {
      window.localStorage.removeItem(SESSION_KEY);
      return null;
    }

    return {
      name: parsed.name || parsed.email.split("@")[0] || "User",
      email: parsed.email,
      username: parsed.username || parsed.email,
      token: parsed.token,
      refreshToken: parsed.refreshToken,
      createdAt: parsed.createdAt || new Date().toISOString(),
    };
  } catch {
    window.localStorage.removeItem(SESSION_KEY);
    return null;
  }
}

export function isAuthenticated() {
  return Boolean(getSession()?.token);
}

export function persistSession(session: OmniSession) {
  if (typeof window === "undefined") return session;
  window.sessionStorage.removeItem(AUTH_EXPIRED_KEY);
  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  window.dispatchEvent(new Event("omni-auth-changed"));
  return session;
}

export function createSession({
  name,
  email,
  username,
  token,
  refreshToken,
}: {
  name?: string;
  email: string;
  username?: string;
  token: string;
  refreshToken?: string | null;
}) {
  const session: OmniSession = {
    name: name?.trim() || email.split("@")[0] || "User",
    email,
    username: username || email,
    token,
    refreshToken: refreshToken || undefined,
    createdAt: new Date().toISOString(),
  };

  return persistSession(session);
}

export function clearSession() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(SESSION_KEY);
  window.dispatchEvent(new Event("omni-auth-changed"));
}

function clearAuthStorage() {
  if (typeof window === "undefined") return;

  for (const storage of [window.localStorage, window.sessionStorage]) {
    for (const key of Object.keys(storage)) {
      if (AUTH_STORAGE_KEY_PATTERNS.some((pattern) => pattern.test(key))) {
        storage.removeItem(key);
      }
    }
  }

  document.cookie.split(";").forEach((cookie) => {
    const name = cookie.split("=")[0]?.trim();
    if (!name) return;
    document.cookie = `${name}=; Max-Age=0; path=/`;
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
  });
}

export function clearAuthState() {
  if (typeof window === "undefined") return;
  clearAuthStorage();
  window.localStorage.removeItem(SESSION_KEY);
  window.dispatchEvent(new Event("omni-auth-changed"));
}

export function consumeAuthExpiredMessage() {
  if (typeof window === "undefined") return null;
  const message = window.sessionStorage.getItem(AUTH_EXPIRED_KEY);
  if (message) {
    window.sessionStorage.removeItem(AUTH_EXPIRED_KEY);
  }
  return message;
}

export function handleAuthExpiration(status?: number, message = AUTH_EXPIRED_MESSAGE) {
  if (typeof window === "undefined" || (status !== 401 && status !== 403)) return false;

  const pathname = window.location.pathname;
  clearAuthState();
  window.sessionStorage.setItem(AUTH_EXPIRED_KEY, message);

  if (pathname === "/login") {
    window.dispatchEvent(new Event("omni-auth-expired"));
    return true;
  }

  if (pathname.startsWith("/auth/callback")) {
    window.location.replace(`/login?error=${encodeURIComponent(message)}`);
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

  return { session, ready, authenticated: Boolean(session?.token) };
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
    const next =
      new URLSearchParams(window.location.search).get("redirect") || defaultPath;
    const id = window.setTimeout(() => {
      setRedirect(next);
    }, 0);

    return () => window.clearTimeout(id);
  }, [defaultPath]);

  useEffect(() => {
    if (state.ready && state.authenticated) {
      router.replace(redirect);
    }
  }, [redirect, router, state.authenticated, state.ready]);

  return { ...state, redirect };
}
