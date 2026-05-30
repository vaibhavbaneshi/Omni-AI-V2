import { useRef, useState } from "react";
import { clearSession } from "@/lib/auth";
import {
  ApiError,
  streamChat,
  type ChatStreamEvent,
  type StreamMeta,
  type StreamSource,
} from "@/lib/api";

export function useChatStream() {
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [streamingMeta, setStreamingMeta] = useState<StreamMeta | null>(null);
  const [streamStatus, setStreamStatus] = useState<ChatStreamEvent | null>(null);
  const [streamError, setStreamError] = useState<string | null>(null);
  const contentRef = useRef("");
  const metaRef = useRef<StreamMeta | null>(null);
  const sourcesRef = useRef<StreamSource[]>([]);
  const titleRef = useRef<{ session_id: number; title: string } | null>(null);

  const start = async ({
    query,
    sessionId,
    mode,
    collectionId,
    token,
    onTitle,
  }: {
    query: string;
    sessionId: number;
    mode?: string;
    collectionId?: number | null;
    token?: string | null;
    onTitle?: (payload: { session_id: number; title: string }) => void;
  }) => {
    setIsStreaming(true);
    setStreamingContent("");
    setStreamingMeta(null);
    setStreamStatus(null);
    setStreamError(null);
    contentRef.current = "";
    metaRef.current = null;
    sourcesRef.current = [];
    titleRef.current = null;

    try {
      await streamChat({
        query,
        sessionId,
        mode,
        collectionId,
        token,
        onEvent: (event) => {
          if (event.type === "status") {
            setStreamStatus(event);
            return;
          }

          if (event.type === "error") {
            setStreamError(event.message);
            return;
          }

          if (event.type === "meta") {
            metaRef.current = event;
            sourcesRef.current = event.sources || [];
            setStreamingMeta(event);
            return;
          }

          if (event.type === "title") {
            titleRef.current = { session_id: event.session_id, title: event.title };
            onTitle?.({ session_id: event.session_id, title: event.title });
            return;
          }

          if (event.type === "token") {
            contentRef.current += event.content;
            setStreamingContent((current) => current + event.content);
          }
        },
      });

      return {
        content: contentRef.current,
        meta: metaRef.current,
        sources: sourcesRef.current,
        title: titleRef.current,
      };
    } catch (error) {
      const errAny = error as { status?: number; statusText?: string; message?: string };
      if (errAny?.status) {
        console.error("streamChat error:", errAny.status, errAny.statusText, errAny.message || errAny);
      } else {
        console.error("streamChat error:", error);
      }

      const message =
        error instanceof ApiError && error.status === 401
          ? "Session expired or invalid. Please sign in again."
          : error instanceof Error
          ? error.message
          : "The response stream failed.";

      if (error instanceof ApiError && error.status === 401) {
        clearSession();
      }

      setStreamError(message);
      throw error;
    } finally {
      setIsStreaming(false);
      setStreamingContent("");
      setStreamingMeta(null);
      setStreamStatus(null);
    }
  };

  return {
    isStreaming,
    streamingContent,
    streamingMeta,
    streamStatus,
    streamError,
    setStreamError,
    start,
  };
}
