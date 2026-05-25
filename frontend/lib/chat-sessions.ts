/** True when id is a persisted backend ChatSession primary key (not a local/demo id). */
export function isBackendSessionId(id: string | undefined | null): boolean {
  if (!id) return false;

  if (id.startsWith("local-")) return false;

  if (!/^\d+$/.test(id)) return false;

  const numeric = Number(id);
  // Real DB ids are small serials; Date.now() strings are ~1.7e12+ and must not be sent.
  return Number.isInteger(numeric) && numeric > 0 && numeric < 1_000_000_000;
}

export function toBackendSessionId(id: string): number | null {
  return isBackendSessionId(id) ? Number(id) : null;
}
