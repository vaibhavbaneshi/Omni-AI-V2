import { useRef, useState } from "react";
import {
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

  const start = async ({
    query,
    sessionId,
    mode,
    collectionId,
    token,
  }: {
    query: string;
    sessionId: number;
    mode?: string;
    collectionId?: number | null;
    token?: string | null;
  }) => {
    setIsStreaming(true);
    setStreamingContent("");
    setStreamingMeta(null);
    setStreamStatus(null);
    setStreamError(null);
    contentRef.current = "";
    metaRef.current = null;
    sourcesRef.current = [];

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
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : "The response stream failed.";
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
