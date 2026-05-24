const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
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
      `Request failed (${response.status})`;
    throw new ApiError(detail, response.status);
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

export async function loginWithCredentials(email: string, password: string) {
  const body = new URLSearchParams({
    username: email,
    password,
  });

  return apiRequest<AuthTokenResponse>("/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: body.toString(),
  });
}

export async function registerAccount({
  username,
  email,
  password,
}: {
  username: string;
  email: string;
  password: string;
}) {
  const params = new URLSearchParams({
    username,
    email,
    password,
  });

  return apiRequest<{ message: string }>(`/register?${params.toString()}`, {
    method: "POST",
  });
}

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
  collectionId?: number | null
) {
  const formData = new FormData();
  formData.append("file", file);
  const params = new URLSearchParams();

  if (collectionId) {
    params.set("collection_id", String(collectionId));
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
  chunks_created: number;
};

export async function listDocuments(token?: string | null) {
  return apiRequest<{ documents: DocumentRecord[] }>("/documents", {}, token);
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

export async function createChatSession(title: string, token?: string | null) {
  const params = new URLSearchParams({ title });
  return apiRequest<ChatSessionRecord>(
    `/sessions?${params.toString()}`,
    {
      method: "POST",
    },
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
};

export type ChatStreamEvent =
  | ({ type: "meta" } & StreamMeta)
  | { type: "status"; phase: string; message: string; tool?: string }
  | { type: "error"; message: string }
  | { type: "token"; content: string }
  | { type: "done" };

export async function streamChat({
  query,
  sessionId,
  mode,
  collectionId,
  token,
  onEvent,
}: {
  query: string;
  sessionId: number;
  mode?: string;
  collectionId?: number | null;
  token?: string | null;
  onEvent: (event: ChatStreamEvent) => void;
}) {
  const params = new URLSearchParams({
    query,
    session_id: String(sessionId),
    mode: mode || "research",
  });

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
  });

  if (!response.ok || !response.body) {
    const body = await parseResponseBody(response);
    const detail =
      (typeof body?.detail === "string" && body.detail) ||
      `Request failed (${response.status})`;
    throw new ApiError(detail, response.status);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
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

export { API_BASE };
