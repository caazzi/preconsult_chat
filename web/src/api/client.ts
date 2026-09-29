// Same-origin API client for the SPA.
//
// Auth is the HttpOnly session cookie issued by POST /api/session/init (2.0c).
// The SPA never holds or sends an API key. `credentials: "include"` ensures the
// cookie rides every same-origin request. Error codes are the stable,
// machine-readable codes from core/errors.py (docs/api-contract.md).

export const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export function apiUrl(path: string): string {
  return `${API_BASE}/api${path}`;
}

/** Stable error codes surfaced by the backend (never renamed casually). */
export type ApiErrorCode =
  | "auth_failed"
  | "rate_limited"
  | "session_expired"
  | "validation_failed"
  | "redis_unavailable"
  | "redis_quota_exceeded"
  | "llm_unavailable"
  | "ai_upstream_error"
  | "service_unavailable"
  | "internal_error"
  | "network_error";

export class ApiError extends Error {
  readonly code: ApiErrorCode;
  readonly status: number;

  constructor(code: ApiErrorCode, status: number, message?: string) {
    super(message ?? code);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

function codeFromStatus(status: number): ApiErrorCode {
  switch (status) {
    case 403:
      return "auth_failed";
    case 404:
      return "session_expired";
    case 429:
      return "rate_limited";
    case 503:
      return "service_unavailable";
    case 502:
      return "ai_upstream_error";
    default:
      return "internal_error";
  }
}

/** Map an HTTP response to a typed error (or return it when ok). */
export async function throwIfError(resp: Response): Promise<void> {
  if (resp.ok) return;
  let code = codeFromStatus(resp.status);
  try {
    const body = await resp.clone().json();
    if (typeof body?.code === "string") code = body.code as ApiErrorCode;
  } catch {
    // Non-JSON body: fall back to the status-derived code.
  }
  throw new ApiError(code, resp.status);
}

export type FetchOptions = Omit<RequestInit, "credentials">;

/**
 * Perform a JSON API request with the session cookie attached. Callers handle
 * the typed ApiError; nothing here retries (the SSE path has its own handling).
 */
export async function apiFetch(
  path: string,
  options: FetchOptions = {},
): Promise<Response> {
  let resp: Response;
  try {
    resp = await fetch(apiUrl(path), {
      ...options,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(options.headers ?? {}),
      },
    });
  } catch {
    throw new ApiError("network_error", 0);
  }
  await throwIfError(resp);
  return resp;
}
