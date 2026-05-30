import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  getAnalyticsOverview,
  getPlatformAnalytics,
  listChatSessions,
  type AnalyticsOverview,
  type ChatSessionRecord,
} from "@/lib/api";

export function useAnalytics(token?: string | null, days = 30) {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [platform, setPlatform] = useState<AnalyticsOverview | null>(null);
  const [sessions, setSessions] = useState<ChatSessionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!token) {
      setOverview(null);
      setPlatform(null);
      setSessions([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const [overviewResult, sessionResult] = await Promise.all([
        getAnalyticsOverview(token, days),
        listChatSessions(token),
      ]);
      setOverview(overviewResult);
      setSessions(sessionResult);

      try {
        const platformResult = await getPlatformAnalytics(token, days);
        setPlatform(platformResult);
      } catch (err) {
        if (!(err instanceof ApiError && err.status === 403)) {
          throw err;
        }
        setPlatform(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load analytics.");
    } finally {
      setLoading(false);
    }
  }, [days, token]);

  useEffect(() => {
    refresh().catch(() => undefined);
  }, [refresh]);

  return { overview, platform, sessions, loading, error, refresh };
}

export function formatCount(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return String(value);
}
