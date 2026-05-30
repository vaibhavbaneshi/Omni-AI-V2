const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  statusText?: string;

  constructor(message: string, status: number, statusText?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.statusText = statusText;
  }
}

async function parseResponseBody(response: Response) {
  const text = await response.text();
  if (!text) return null;

  try {
    return JSON.parse(text) as Record<string, unknown>;
  } catch {
    return { detail: text };
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null
): Promise<T> {
  const headers = new Headers(options.headers);

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  if (
    options.body &&
    !(options.body instanceof FormData) &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  const body = await parseResponseBody(response);

  if (!response.ok) {
    const detail =
      (typeof body?.detail === "string" && body.detail) ||
      (typeof body?.error === "string" && body.error) ||
      (typeof body?.message === "string" && body.message) ||
      `Request failed (${response.status} ${response.statusText})`;
    const message =
      response.status === 401
        ? "Authentication failed. Please sign in again."
        : detail;
    throw new ApiError(message, response.status, response.statusText);
  }

  if (body && typeof body.error === "string") {
    throw new ApiError(body.error, response.status);
  }

  return body as T;
}

export type AuthTokenResponse = {
  access_token: string;
  token_type: string;
};

export type UploadDocumentResponse = {
  message: string;
  filename: string;
  chunks_created: number;
  collection_id: number;
  document_id: number;
};

export async function uploadDocument(
  file: File,
  token?: string | null,
  options?: {
    collectionId?: number | null;
    sessionId?: number | null;
  }
) {
  const formData = new FormData();
  formData.append("file", file);
  const params = new URLSearchParams();

  if (options?.collectionId) {
    params.set("collection_id", String(options.collectionId));
  }
  if (options?.sessionId) {
    params.set("session_id", String(options.sessionId));
  }

  return apiRequest<UploadDocumentResponse>(
    `/upload${params.size ? `?${params.toString()}` : ""}`,
    {
      method: "POST",
      body: formData,
    },
    token
  );
}

export type DocumentRecord = {
  id: number;
  filename: string;
  size: number;
  updated_at: number;
  collection_id: number;
  session_id?: number | null;
  chunks_created: number;
};

export async function listDocuments(
  token?: string | null,
  options?: { sessionId?: number | null; collectionId?: number | null }
) {
  const params = new URLSearchParams();
  if (options?.sessionId) {
    params.set("session_id", String(options.sessionId));
  }
  if (options?.collectionId) {
    params.set("collection_id", String(options.collectionId));
  }
  const suffix = params.size ? `?${params.toString()}` : "";
  return apiRequest<{ documents: DocumentRecord[] }>(`/documents${suffix}`, {}, token);
}

export async function deleteDocument(filename: string, token?: string | null) {
  return apiRequest<{ message: string; filename: string }>(
    `/documents/${encodeURIComponent(filename)}`,
    {
      method: "DELETE",
    },
    token
  );
}

export type DocumentCollection = {
  id: number;
  name: string;
  workspace_id: string;
  created_at?: string | null;
};

export async function listCollections(token?: string | null) {
  return apiRequest<{ collections: DocumentCollection[] }>("/collections", {}, token);
}

export async function createCollection(name: string, token?: string | null) {
  const params = new URLSearchParams({ name });
  return apiRequest<DocumentCollection>(
    `/collections?${params.toString()}`,
    {
      method: "POST",
    },
    token
  );
}

export type ChatSessionRecord = {
  id: number;
  title: string;
};

export type ChatMessageRecord = {
  id: number;
  session_id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string | null;
};

export async function listChatSessions(token?: string | null) {
  return apiRequest<ChatSessionRecord[]>("/sessions", {}, token);
}

export async function createChatSession(
  firstMessage: string,
  token?: string | null,
  options?: { title?: string }
) {
  const params = new URLSearchParams();
  if (options?.title) {
    params.set("title", options.title);
  }
  if (firstMessage.trim()) {
    params.set("first_message", firstMessage.trim());
  }
  return apiRequest<ChatSessionRecord>(
    `/sessions?${params.toString()}`,
    {
      method: "POST",
    },
    token
  );
}

export async function updateChatSessionTitle(
  sessionId: number,
  title: string,
  token?: string | null
) {
  const params = new URLSearchParams({ title });
  return apiRequest<ChatSessionRecord>(
    `/sessions/${sessionId}?${params.toString()}`,
    { method: "PATCH" },
    token
  );
}

export async function deleteChatSession(sessionId: number, token?: string | null) {
  return apiRequest<{ message: string; session_id: number }>(
    `/sessions/${sessionId}`,
    { method: "DELETE" },
    token
  );
}

export async function getChatSessionMessages(sessionId: number, token?: string | null) {
  return apiRequest<ChatMessageRecord[]>(`/sessions/${sessionId}/messages`, {}, token);
}

export type StreamSource = {
  title: string;
  source: string;
  chunk: string;
  score?: number | null;
  strategy?: string;
  url?: string;
  type?: "document" | "web" | "memory";
  metadata?: Record<string, unknown>;
};

export type StreamMeta = {
  tool?: string;
  strategy?: string;
  mode?: string;
  route?: {
    strategy?: string;
    tools?: string[];
    reason?: string;
    status?: string;
    web_status?: string;
    web_error?: string | null;
  };
  tools?: Array<{
    name: string;
    confidence?: number;
    latency_ms?: number;
    error?: string | null;
    metadata?: Record<string, unknown>;
  }>;
  traces?: Array<{
    phase: string;
    status: string;
    message: string;
    tool?: string | null;
    latency_ms?: number | null;
    metadata?: Record<string, unknown>;
  }>;
  sources?: StreamSource[];
  source_groups?: {
    documents?: StreamSource[];
    web?: StreamSource[];
    memory?: StreamSource[];
  };
  memory?: {
    conversation_history?: boolean;
    summary?: boolean;
  };
  model?: {
    id: string;
    provider: string;
    model_name: string;
    display_name: string;
    routing_reason: string;
  };
};

export type ModelDefinition = {
  id: string;
  name: string;
  provider: string;
  model_name: string;
  description: string;
  roles: string[];
  badge?: string | null;
  available: boolean;
};

export type ModelsResponse = {
  routing_enabled: boolean;
  models: ModelDefinition[];
};

export async function fetchModels() {
  return apiRequest<ModelsResponse>("/models");
}

export type ChatStreamEvent =
  | ({ type: "meta" } & StreamMeta)
  | { type: "status"; phase: string; message: string; tool?: string }
  | { type: "error"; message: string }
  | { type: "cancelled"; message: string }
  | { type: "token"; content: string }
  | { type: "title"; session_id: number; title: string }
  | { type: "done" };

export async function streamChat({
  query,
  sessionId,
  mode,
  model,
  collectionId,
  token,
  signal,
  onEvent,
}: {
  query: string;
  sessionId: number;
  mode?: string;
  model?: string;
  collectionId?: number | null;
  token?: string | null;
  signal?: AbortSignal;
  onEvent: (event: ChatStreamEvent) => void;
}) {
  const params = new URLSearchParams({
    query,
    session_id: String(sessionId),
    mode: mode || "research",
  });

  if (model) {
    params.set("model", model);
  }

  if (collectionId) {
    params.set("collection_id", String(collectionId));
  }

  const headers = new Headers();

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE}/chat-stream?${params.toString()}`, {
    method: "POST",
    headers,
    signal,
  });

  if (!response.ok || !response.body) {
    const raw = await response.text();
    let detail = `Request failed (${response.status} ${response.statusText})`;

    if (raw) {
      for (const line of raw.split("\n")) {
        if (!line.trim()) continue;
        try {
          const event = JSON.parse(line) as { type?: string; message?: string };
          if (event.type === "error" && event.message) {
            detail = event.message;
            break;
          }
        } catch {
          // ignore malformed lines
        }
      }

      if (detail.startsWith("Request failed")) {
        try {
          const body = JSON.parse(raw) as Record<string, unknown>;
          if (typeof body.detail === "string") {
            detail = body.detail;
          }
        } catch {
          // keep default detail
        }
      }
    }

    const message =
      response.status === 401
        ? "Authentication failed. Please sign in again."
        : detail;
    throw new ApiError(message, response.status, response.statusText);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    if (signal?.aborted) {
      throw new DOMException("The stream was aborted.", "AbortError");
    }

    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.trim()) continue;

      try {
        onEvent(JSON.parse(line) as ChatStreamEvent);
      } catch {
        onEvent({ type: "token", content: line });
      }
    }

    if (done) break;
  }

  if (buffer.trim()) {
    try {
      onEvent(JSON.parse(buffer) as ChatStreamEvent);
    } catch {
      onEvent({ type: "token", content: buffer });
    }
  }
}

export type MemoryRecord = {
  id: number;
  category: string;
  content: string;
  importance: number;
  created_at?: string | null;
  updated_at?: string | null;
};

export async function listMemories(token?: string | null) {
  return apiRequest<{ memories: MemoryRecord[] }>("/memory", {}, token);
}

export async function createMemory(
  content: string,
  token?: string | null,
  options?: {
    category?: string;
    importance?: number;
  }
) {
  const params = new URLSearchParams({
    content,
    category: options?.category || "preference",
    importance: String(options?.importance ?? 0.5),
  });

  return apiRequest<MemoryRecord>(
    `/memory?${params.toString()}`,
    {
      method: "POST",
    },
    token
  );
}

export async function deleteMemory(memoryId: number, token?: string | null) {
  return apiRequest<{ message: string }>(
    `/memory/${memoryId}`,
    {
      method: "DELETE",
    },
    token
  );
}

export type OAuthProviders = {
  github: boolean;
  google: boolean;
};

export async function getOAuthProviders() {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), 8000);

  try {
    return await apiRequest<OAuthProviders>("/auth/providers", {
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError(
        `Cannot reach the API at ${API_BASE}. Start the backend and verify NEXT_PUBLIC_API_URL.`,
        0
      );
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export function getOAuthStartUrl(provider: "github" | "google", nextPath = "/dashboard") {
  const params = new URLSearchParams({ next: nextPath });
  return `${API_BASE}/auth/${provider}?${params.toString()}`;
}

export type AnalyticsModelBreakdown = {
  model: string;
  tokens: number;
  calls: number;
  share_pct: number;
};

export type AnalyticsDailyTokens = {
  date: string;
  tokens: number;
};

export type AnalyticsOverview = {
  scope: "user" | "platform";
  period_days: number;
  users: {
    sessions?: number;
    messages?: number;
    api_requests?: number;
    total_users?: number;
    active_users_24h?: number;
    active_users_period?: number;
  };
  ai: {
    total_tokens: number;
    avg_latency_ms: number;
    model_breakdown: AnalyticsModelBreakdown[];
    daily_tokens: AnalyticsDailyTokens[];
    total_chats?: number;
    total_messages?: number;
    endpoint_latency?: Array<{ path: string; avg_latency_ms: number; requests: number }>;
  };
  rag: {
    uploads: number;
    ingestion_runs: number;
    total_chunks?: number;
  };
};

export async function getAnalyticsOverview(token?: string | null, days = 30) {
  return apiRequest<AnalyticsOverview>(`/analytics/overview?days=${days}`, {}, token);
}

export async function getPlatformAnalytics(token?: string | null, days = 30) {
  return apiRequest<AnalyticsOverview>(`/analytics/platform?days=${days}`, {}, token);
}

export { API_BASE };
