import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError,
  generateDocumentInsights,
  getDocumentInsights,
  type DocumentInsightRecord,
} from "@/lib/api";

const POLL_MS = 2500;
const MAX_POLLS = 48;

export function useDocumentInsights(
  documentId: number | null | undefined,
  token?: string | null
) {
  const [insights, setInsights] = useState<DocumentInsightRecord | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);

  const clearPoll = useCallback(() => {
    if (pollRef.current) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const refresh = useCallback(async () => {
    if (!token || !documentId) {
      setInsights(null);
      return null;
    }

    setLoading(true);
    setError(null);

    try {
      const record = await getDocumentInsights(documentId, token);
      setInsights(record);
      return record;
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setInsights(null);
        return null;
      }
      setError(err instanceof Error ? err.message : "Could not load document insights.");
      return null;
    } finally {
      setLoading(false);
    }
  }, [documentId, token]);

  useEffect(() => {
    clearPoll();
    setInsights(null);
    setError(null);

    if (!token || !documentId) return;

    refresh().catch(() => undefined);

    return clearPoll;
  }, [clearPoll, documentId, refresh, token]);

  const pollUntilReady = useCallback(() => {
    clearPoll();
    let attempts = 0;

    pollRef.current = window.setInterval(() => {
      attempts += 1;
      refresh()
        .then((record) => {
          if (!record) return;
          if (record.status === "ready" || record.status === "failed") {
            setGenerating(false);
            clearPoll();
          }
        })
        .catch(() => undefined);

      if (attempts >= MAX_POLLS) {
        setGenerating(false);
        clearPoll();
      }
    }, POLL_MS);
  }, [clearPoll, refresh]);

  const generate = useCallback(
    async (options?: { force?: boolean }) => {
      if (!token || !documentId) return;

      setGenerating(true);
      setError(null);

      try {
        const result = await generateDocumentInsights(documentId, token, options);
        if (result.status === "ready") {
          await refresh();
          setGenerating(false);
          return;
        }
        pollUntilReady();
      } catch (err) {
        setGenerating(false);
        setError(err instanceof Error ? err.message : "Could not generate insights.");
      }
    },
    [documentId, pollUntilReady, refresh, token]
  );

  return {
    insights,
    loading,
    generating,
    error,
    refresh,
    generate,
  };
}
