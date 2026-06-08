const ACTIVE_CHAT_STORAGE_KEY = "omni-ai-active-chat";

export function readStoredActiveChatId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const value = window.sessionStorage.getItem(ACTIVE_CHAT_STORAGE_KEY);
    return value?.trim() || null;
  } catch {
    return null;
  }
}

export function storeActiveChatId(chatId: string | null) {
  if (typeof window === "undefined") return;
  try {
    if (!chatId) {
      window.sessionStorage.removeItem(ACTIVE_CHAT_STORAGE_KEY);
      return;
    }
    window.sessionStorage.setItem(ACTIVE_CHAT_STORAGE_KEY, chatId);
  } catch {
    // ignore storage failures
  }
}

export function clearStoredActiveChatId() {
  storeActiveChatId(null);
}

/** Keep the browser address bar on a single clean path — no session ids in the URL. */
export function syncChatPath() {
  if (typeof window === "undefined") return;
  const target = "/chat";
  if (window.location.pathname !== target) {
    window.history.replaceState(null, "", target);
    return;
  }
  if (window.location.search) {
    window.history.replaceState(null, "", target);
  }
}
