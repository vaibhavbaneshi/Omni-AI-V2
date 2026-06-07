import { sanitizeChatError } from "@/lib/user-facing-errors";
import {
  AUTH_EXPIRED_MESSAGE,
  getSession,
  handleAuthExpiration,
  persistSession,
} from "@/lib/auth";

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

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken() {
  const session = getSession();
  if (!session?.refreshToken) return null;

  if (!refreshPromise) {
    refreshPromise = fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: session.refreshToken }),
    })
      .then(async (response) => {
        if (!response.ok) return null;
        const body = (await response.json()) as {
          access_token?: string;
          refresh_token?: string;
        };
        if (!body.access_token || !body.refresh_token) return null;
        persistSession({
          ...session,
          token: body.access_token,
          refreshToken: body.refresh_token,
        });
        return body.access_token;
      })
      .catch(() => null)
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
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
  token?: string | null,
  retryAuth = true
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
    if (response.status === 401) {
      if (retryAuth && response.status === 401 && !path.startsWith("/auth/")) {
        const refreshedToken = await refreshAccessToken();
        if (refreshedToken) {
          return apiRequest<T>(path, options, refreshedToken, false);
        }
      }
      handleAuthExpiration(response.status, AUTH_EXPIRED_MESSAGE);
    }

    const message = response.status === 401 ? AUTH_EXPIRED_MESSAGE : detail;
    throw new ApiError(message, response.status, response.statusText);
  }

  if (body && typeof body.error === "string") {
    throw new ApiError(body.error, response.status);
  }

  return body as T;
}

export type AuthTokenResponse = {
  access_token: string;
  refresh_token?: string;
  token_type: string;
};

export async function logoutSession(refreshToken?: string | null) {
  return apiRequest<{ message: string }>(
    "/auth/logout",
    {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken || null }),
    },
    null,
    false
  );
}

export type UploadDocumentResponse = {
  message: string;
  filename: string;
  chunks_created: number;
  collection_id: number;
  document_id: number;
  indexing?: boolean;
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

  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), 120_000);

  try {
    return await apiRequest<UploadDocumentResponse>(
      `/upload${params.size ? `?${params.toString()}` : ""}`,
      {
        method: "POST",
        body: formData,
        signal: controller.signal,
      },
      token
    );
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError(
        "Upload timed out. Try a smaller file or check that the backend is running.",
        408
      );
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export type DocumentIndexingStage =
  | "queued"
  | "loading"
  | "chunking"
  | "embedding"
  | "vector_store"
  | "finalizing"
  | "ready"
  | "failed";

export const INDEXING_STAGE_LABELS: Record<DocumentIndexingStage, string> = {
  queued: "Queued for indexing...",
  loading: "Loading document...",
  chunking: "Chunking text...",
  embedding: "Generating embeddings...",
  vector_store: "Storing vectors...",
  finalizing: "Finalizing...",
  ready: "Ready",
  failed: "Indexing failed",
};

export type DocumentRecord = {
  id: number;
  filename: string;
  size: number;
  updated_at: number;
  collection_id: number;
  session_id?: number | null;
  chunks_created: number;
  embeddings_completed?: number;
  indexing_stage?: DocumentIndexingStage;
  indexing_error?: string | null;
  elapsed_seconds?: number | null;
  stale?: boolean;
  stale_message?: string;
  status?: "indexing" | "ready" | "failed";
};

export function isDocumentReady(document: DocumentRecord): boolean {
  return document.status === "ready" || document.indexing_stage === "ready" || document.chunks_created > 0;
}

export function isDocumentFailed(document: DocumentRecord): boolean {
  return document.status === "failed" || document.indexing_stage === "failed";
}

export function isDocumentIndexing(document: DocumentRecord): boolean {
  return !isDocumentReady(document) && !isDocumentFailed(document);
}

export function indexingStageLabel(document: DocumentRecord): string {
  if (isDocumentFailed(document)) {
    return document.indexing_error || INDEXING_STAGE_LABELS.failed;
  }
  const stage = document.indexing_stage || "queued";
  return INDEXING_STAGE_LABELS[stage] || INDEXING_STAGE_LABELS.queued;
}

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

export async function getDocumentStatus(documentId: number, token?: string | null) {
  return apiRequest<{
    id: number;
    filename: string;
    chunks_created: number;
    embeddings_completed: number;
    indexing_stage: DocumentIndexingStage;
    indexing_error?: string | null;
    elapsed_seconds?: number | null;
    stale?: boolean;
    stale_message?: string;
    status: "indexing" | "ready" | "failed";
  }>(`/documents/${documentId}/status`, {}, token);
}

export async function waitForDocumentIndexed(
  documentId: number,
  token?: string | null,
  maxWaitMs = 180_000
) {
  const started = Date.now();
  let delayMs = 750;

  while (Date.now() - started < maxWaitMs) {
    const document = await getDocumentStatus(documentId, token);
    if (document.status === "ready" || document.chunks_created > 0) {
      return document;
    }
    await new Promise((resolve) => window.setTimeout(resolve, delayMs));
    delayMs = Math.min(delayMs + 250, 2000);
  }

  throw new ApiError(
    "Document indexing is taking longer than expected. It will keep processing in the background.",
    408
  );
}

export async function deleteDocumentById(documentId: number, token?: string | null) {
  return apiRequest<{ message: string; filename: string; document_id: number }>(
    `/documents/id/${documentId}`,
    {
      method: "DELETE",
    },
    token
  );
}

export type ExecutiveSummarySection = {
  overview: string;
  key_findings: string[];
  important_points: string[];
  risks: string[];
  recommendations: string[];
};

export type DocumentFaqItem = {
  question: string;
  answer: string;
};

export type DocumentActionItem = {
  task: string;
  deadline?: string | null;
  owner?: string | null;
};

export type DocumentMetadataInsights = {
  keywords: string[];
  topics: string[];
  entities: string[];
  important_dates: string[];
  statistics: string[];
};

export type DocumentInsightPayload = {
  executive_summary: ExecutiveSummarySection;
  faqs: DocumentFaqItem[];
  action_items: DocumentActionItem[];
  metadata_insights: DocumentMetadataInsights;
};

export type DocumentInsightRecord = {
  document_id: number;
  status: "pending" | "processing" | "ready" | "failed" | string;
  model?: string | null;
  error_message?: string | null;
  payload?: DocumentInsightPayload | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export async function getDocumentInsights(documentId: number, token?: string | null) {
  return apiRequest<DocumentInsightRecord>(`/documents/${documentId}/insights`, {}, token);
}

export async function generateDocumentInsights(
  documentId: number,
  token?: string | null,
  options?: { force?: boolean }
) {
  const params = new URLSearchParams();
  if (options?.force) {
    params.set("force", "true");
  }
  const suffix = params.size ? `?${params.toString()}` : "";
  return apiRequest<{ document_id: number; status: string; message: string }>(
    `/documents/${documentId}/insights/generate${suffix}`,
    { method: "POST" },
    token
  );
}

export async function deleteDocument(
  filename: string,
  token?: string | null,
  options?: { sessionId?: number | null }
) {
  const params = new URLSearchParams();
  if (options?.sessionId) {
    params.set("session_id", String(options.sessionId));
  }
  const suffix = params.size ? `?${params.toString()}` : "";
  return apiRequest<{ message: string; filename: string; document_id?: number }>(
    `/documents/${encodeURIComponent(filename)}${suffix}`,
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
  id?: number;
  session_id?: number;
  title: string;
};

export function normalizeChatSessionRecord(
  record: ChatSessionRecord
): { id: number; title: string } {
  const id = record.id ?? record.session_id;
  if (typeof id !== "number" || !Number.isFinite(id) || id <= 0) {
    throw new ApiError("Invalid chat session returned by the server.", 500);
  }
  return {
    id,
    title: record.title || "New Chat",
  };
}

export type ChatMessageRecord = {
  id: number;
  session_id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string | null;
};

export async function listChatSessions(token?: string | null) {
  const records = await apiRequest<ChatSessionRecord[]>("/sessions", {}, token);
  return records.map(normalizeChatSessionRecord);
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
  ).then(normalizeChatSessionRecord);
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
  retryAuth = true,
}: {
  query: string;
  sessionId: number;
  mode?: string;
  model?: string;
  collectionId?: number | null;
  token?: string | null;
  signal?: AbortSignal;
  onEvent: (event: ChatStreamEvent) => void;
  retryAuth?: boolean;
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

    if (response.status === 401) {
      if (retryAuth && response.status === 401) {
        const refreshedToken = await refreshAccessToken();
        if (refreshedToken) {
          return streamChat({
            query,
            sessionId,
            mode,
            model,
            collectionId,
            token: refreshedToken,
            signal,
            onEvent,
            retryAuth: false,
          });
        }
      }
      handleAuthExpiration(response.status, AUTH_EXPIRED_MESSAGE);
    }

    throw new ApiError(
      sanitizeChatError(
        response.status === 401 ? AUTH_EXPIRED_MESSAGE : detail,
        { status: response.status }
      ),
      response.status,
      response.statusText
    );
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

export type WorkspaceSession = {
  id: number;
  device_label: string;
  ip_address?: string | null;
  created_at?: string | null;
  last_active_at?: string | null;
  is_current: boolean;
};

export type WorkspaceSettings = {
  profile: {
    id: number;
    username: string;
    email: string;
    first_name: string;
    last_name: string;
    bio: string;
    avatar_url?: string | null;
    display_name: string;
    oauth_provider?: string | null;
    has_password: boolean;
    password_changed_at?: string | null;
    totp_enabled: boolean;
    created_at?: string | null;
  };
  security: {
    totp_enabled: boolean;
    has_password: boolean;
    password_changed_at?: string | null;
    sessions: WorkspaceSession[];
  };
  preferences: {
    default_model: string;
    response_style: string;
    system_prompt: string;
    web_search_enabled: boolean;
    code_execution_enabled: boolean;
    streaming_enabled: boolean;
    theme: string;
    font_size: string;
    compact_mode: boolean;
    email_notifications: boolean;
    product_updates: boolean;
    usage_alerts: boolean;
  };
  api: {
    key: {
      prefix?: string | null;
      created_at?: string | null;
      last_used_at?: string | null;
      active: boolean;
    };
    rate_limits: {
      requests_per_minute: number;
      tokens_per_minute: number;
      max_upload_bytes: number;
    };
    webhook: {
      url: string;
      events: string[];
      enabled: boolean;
    };
  };
  billing: {
    plan: string;
    status: string;
    amount_cents: number;
    billing_cycle: string;
    next_billing_date?: string | null;
    payment_method_brand?: string | null;
    payment_method_last4?: string | null;
    cancel_at_period_end: boolean;
    usage: {
      messages: { used: number; limit: number; percent: number };
      api_calls: { used: number; limit: number; percent: number };
      storage_gb: { used: number; limit: number; percent: number };
      tokens: number;
    };
    invoices: Array<{
      id: number;
      date: string;
      amount: string;
      amount_cents: number;
      status: string;
      description: string;
    }>;
  };
};

export async function getWorkspaceSettings(token?: string | null) {
  return apiRequest<WorkspaceSettings>("/settings", {}, token);
}

export async function updateWorkspaceProfile(
  payload: {
    first_name: string;
    last_name: string;
    email: string;
    bio: string;
  },
  token?: string | null
) {
  return apiRequest<WorkspaceSettings["profile"]>(
    "/settings/profile",
    { method: "PATCH", body: JSON.stringify(payload) },
    token
  );
}

export async function uploadWorkspaceAvatar(file: File, token?: string | null) {
  const formData = new FormData();
  formData.append("file", file);
  return apiRequest<{ avatar_url: string }>(
    "/settings/avatar",
    { method: "POST", body: formData },
    token
  );
}

export async function changeWorkspacePassword(
  payload: {
    current_password?: string;
    new_password: string;
    confirm_password: string;
  },
  token?: string | null
) {
  return apiRequest<{ message: string }>(
    "/settings/password",
    { method: "POST", body: JSON.stringify(payload) },
    token
  );
}

export async function setupTwoFactor(token?: string | null) {
  return apiRequest<{ secret: string; provisioning_uri: string; issuer: string }>(
    "/settings/2fa/setup",
    {},
    token
  );
}

export async function enableTwoFactor(code: string, token?: string | null) {
  return apiRequest<{ message: string; totp_enabled: boolean }>(
    "/settings/2fa/enable",
    { method: "POST", body: JSON.stringify({ code }) },
    token
  );
}

export async function disableTwoFactor(
  payload: { code: string; password?: string },
  token?: string | null
) {
  return apiRequest<{ message: string; totp_enabled: boolean }>(
    "/settings/2fa/disable",
    { method: "POST", body: JSON.stringify(payload) },
    token
  );
}

export async function revokeWorkspaceSession(sessionId: number, token?: string | null) {
  return apiRequest<{ message: string }>(
    `/settings/sessions/${sessionId}`,
    { method: "DELETE" },
    token
  );
}

export async function revokeOtherWorkspaceSessions(token?: string | null) {
  return apiRequest<{ message: string; revoked: number }>(
    "/settings/sessions/revoke-others",
    { method: "POST" },
    token
  );
}

export async function updateWorkspacePreferences(
  payload: WorkspaceSettings["preferences"],
  token?: string | null
) {
  return apiRequest<WorkspaceSettings["preferences"]>(
    "/settings/preferences",
    { method: "PATCH", body: JSON.stringify(payload) },
    token
  );
}

export async function regenerateWorkspaceApiKey(token?: string | null) {
  return apiRequest<{ api_key: string; prefix: string; created_at?: string; message: string }>(
    "/settings/api-key/regenerate",
    { method: "POST" },
    token
  );
}

export async function updateWorkspaceWebhook(
  payload: WorkspaceSettings["api"]["webhook"],
  token?: string | null
) {
  return apiRequest<WorkspaceSettings["api"]["webhook"]>(
    "/settings/webhook",
    { method: "PUT", body: JSON.stringify(payload) },
    token
  );
}

export async function changeWorkspaceBillingPlan(plan: "free" | "pro", token?: string | null) {
  return apiRequest<WorkspaceSettings["billing"]>(
    "/settings/billing/plan",
    { method: "POST", body: JSON.stringify({ plan }) },
    token
  );
}

export async function cancelWorkspaceSubscription(token?: string | null) {
  return apiRequest<{ message: string }>("/settings/billing/cancel", { method: "POST" }, token);
}

export async function downloadWorkspaceInvoice(invoiceId: number, token?: string | null) {
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE}/settings/billing/invoices/${invoiceId}/download`, {
    headers,
  });
  if (!response.ok) {
    throw new ApiError("Failed to download invoice", response.status, response.statusText);
  }
  return response.text();
}

export async function deleteWorkspaceAccount(confirmation: string, token?: string | null) {
  return apiRequest<{ message: string }>(
    "/settings/account",
    { method: "DELETE", body: JSON.stringify({ confirmation }) },
    token
  );
}

export { API_BASE };
