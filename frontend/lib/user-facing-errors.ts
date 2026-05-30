const INTERNAL_MARKERS = [
  "sqlalchemy",
  "psycopg2",
  "postgresql",
  "[sql:",
  "undefinedtable",
  "relation ",
  "integrityerror",
  "operationalerror",
  "background on this error",
  "parameters:",
  "traceback",
  "stream_options",
  "completions.create",
  "unexpected keyword argument",
  "groq streaming failed",
  "openai streaming failed",
  "deepseek streaming failed",
  "llmprovidererror",
  "typeerror",
  "attributeerror",
  "keyerror",
  "failed to fetch",
  "networkerror",
];

const TECHNICAL_PREFIXES = [
  "groq streaming failed:",
  "openai streaming failed:",
  "deepseek streaming failed:",
  "error:",
  "exception:",
];

function looksInternal(message: string) {
  const lower = message.toLowerCase();
  return INTERNAL_MARKERS.some((marker) => lower.includes(marker));
}

function stripTechnicalPrefix(message: string) {
  let cleaned = message.trim();
  for (const prefix of TECHNICAL_PREFIXES) {
    if (cleaned.toLowerCase().startsWith(prefix)) {
      cleaned = cleaned.slice(prefix.length).trim();
    }
  }
  return cleaned;
}

export function sanitizeAuthError(raw: string | null | undefined): string {
  if (!raw?.trim()) {
    return "Sign-in failed. Please try again.";
  }

  const message = raw.trim();
  if (looksInternal(message)) {
    return "Sign-in is temporarily unavailable. Please try again in a moment.";
  }

  if (message.length > 180) {
    return "Sign-in failed. Please try again.";
  }

  return message;
}

export function sanitizeChatError(
  raw: string | null | undefined,
  options?: { status?: number }
): string {
  if (options?.status === 401) {
    return "Your session expired. Please sign in again.";
  }

  if (options?.status === 429) {
    return "Too many requests. Please wait a moment and try again.";
  }

  if (options?.status && options.status >= 500) {
    return "The AI service is temporarily unavailable. Please try again.";
  }

  if (!raw?.trim()) {
    return "We couldn't generate a response. Please try again.";
  }

  const message = stripTechnicalPrefix(raw);
  const lower = message.toLowerCase();

  if (looksInternal(message)) {
    return "We couldn't generate a response. Please try again.";
  }

  if (lower.includes("not configured") || lower.includes("api key")) {
    return "AI service is temporarily unavailable. Please try again later.";
  }

  if (lower.includes("rate limit") || lower.includes("too many requests")) {
    return "The AI service is busy. Please wait a moment and try again.";
  }

  if (lower.includes("session not found")) {
    return "This chat session is no longer available. Start a new chat.";
  }

  if (lower.includes("unknown model")) {
    return "That model isn't available right now. Try Auto Route or another model.";
  }

  if (message.length > 180) {
    return "Something went wrong while generating a response. Please try again.";
  }

  return message;
}

export function sanitizeApiError(
  raw: string | null | undefined,
  options?: { status?: number; fallback?: string }
): string {
  const fallback = options?.fallback || "Something went wrong. Please try again.";

  if (options?.status === 401) {
    return "Your session expired. Please sign in again.";
  }

  if (!raw?.trim()) {
    return fallback;
  }

  const message = raw.trim();
  if (looksInternal(message) || message.length > 180) {
    return fallback;
  }

  return message;
}
