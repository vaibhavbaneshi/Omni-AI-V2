import { describe, expect, it, beforeEach } from "vitest";
import {
  AUTH_EXPIRED_MESSAGE,
  clearSession,
  createSession,
  getCsrfToken,
  getSession,
  isAuthenticated,
  persistSession,
} from "@/lib/auth";

describe("auth helpers", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    document.cookie = "";
  });

  it("returns null CSRF when no cookie", () => {
    expect(getCsrfToken()).toBeNull();
  });

  it("reads CSRF token from cookie", () => {
    document.cookie = "omniai_csrf=test-token-value";
    expect(getCsrfToken()).toBe("test-token-value");
  });

  it("creates and reads session profile with tokens", () => {
    createSession({
      email: "user@example.com",
      name: "User",
      token: "access-token",
      refreshToken: "refresh-token",
    });
    const session = getSession();
    expect(session?.email).toBe("user@example.com");
    expect(session?.token).toBe("access-token");
    expect(session?.refreshToken).toBe("refresh-token");
    expect(isAuthenticated()).toBe(true);
  });

  it("clears session on logout", () => {
    persistSession({
      email: "user@example.com",
      name: "User",
      username: "user@example.com",
      createdAt: new Date().toISOString(),
    });
    clearSession();
    expect(getSession()).toBeNull();
    expect(isAuthenticated()).toBe(false);
  });

  it("exports auth expired message", () => {
    expect(AUTH_EXPIRED_MESSAGE).toContain("expired");
  });
});
