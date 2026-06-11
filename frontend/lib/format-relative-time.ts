const UNITS: Array<[Intl.RelativeTimeFormatUnit, number]> = [
  ["year", 60 * 60 * 24 * 365],
  ["month", 60 * 60 * 24 * 30],
  ["week", 60 * 60 * 24 * 7],
  ["day", 60 * 60 * 24],
  ["hour", 60 * 60],
  ["minute", 60],
  ["second", 1],
];

export function formatRelativeTime(value?: string | null, now = Date.now()): string {
  if (!value) return "—";
  const timestamp = new Date(value).getTime();
  if (Number.isNaN(timestamp)) return "—";

  const diffSeconds = Math.round((timestamp - now) / 1000);
  const formatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

  for (const [unit, secondsInUnit] of UNITS) {
    if (Math.abs(diffSeconds) >= secondsInUnit || unit === "second") {
      const amount = Math.round(diffSeconds / secondsInUnit);
      return formatter.format(amount, unit);
    }
  }
  return "—";
}

export function formatFutureRun(value?: string | null): string {
  if (!value) return "Not scheduled";
  const timestamp = new Date(value).getTime();
  if (Number.isNaN(timestamp)) return "Not scheduled";
  const diffMs = timestamp - Date.now();
  if (diffMs <= 0) return "due now";
  return `runs ${formatRelativeTime(value)}`;
}

export function formatPastRun(value?: string | null): string {
  if (!value) return "never ran";
  return `last ran ${formatRelativeTime(value)}`;
}
