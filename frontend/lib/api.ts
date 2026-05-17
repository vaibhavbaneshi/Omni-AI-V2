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
  chunks_created: number;
};

export async function uploadDocument(file: File, token?: string | null) {
  const formData = new FormData();
  formData.append("file", file);

  return apiRequest<UploadDocumentResponse>(
    "/upload",
    {
      method: "POST",
      body: formData,
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
