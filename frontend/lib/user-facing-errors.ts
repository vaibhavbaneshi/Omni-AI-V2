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
];

export function sanitizeAuthError(raw: string | null | undefined): string {
  if (!raw?.trim()) {
    return "Sign-in failed. Please try again.";
  }

  const message = raw.trim();
  const lower = message.toLowerCase();

  if (INTERNAL_MARKERS.some((marker) => lower.includes(marker))) {
    return "Sign-in is temporarily unavailable. Please try again in a moment.";
  }

  if (message.length > 180) {
    return "Sign-in failed. Please try again.";
  }

  return message;
}
