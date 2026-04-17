/**
 * PSense Mail — Typed API client.
 *
 * Wraps `fetch` with:
 *  - Auth header injection (Bearer token from localStorage / future KeyCloak)
 *  - X-Correlation-ID (random UUID per request)
 *  - Idempotency-Key support (caller-supplied or auto-generated for mutations)
 *  - X-Account-Id header for multi-account context
 *  - Standard error envelope decoding into typed ApiError throws
 *
 * All hooks and services import from here — never call `fetch` directly.
 */

// ── Error types ───────────────────────────────────────────────────────────────

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;
  readonly correlationId: string | null;
  readonly retryable: boolean;

  constructor(
    status: number,
    code: string,
    message: string,
    details: Record<string, unknown> = {},
    correlationId: string | null = null,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.correlationId = correlationId;
    this.retryable = status >= 500 || status === 429;
  }

  get isNotFound() { return this.status === 404; }
  get isConflict() { return this.status === 409; }
  get isConcurrencyError() { return this.code === "CONCURRENCY_ERROR"; }
  get isUnauthorized() { return this.status === 401; }
  get isForbidden() { return this.status === 403; }
  get isRateLimited() { return this.status === 429; }
}

// ── Config ────────────────────────────────────────────────────────────────────

const BASE_URL = (
  typeof import.meta !== "undefined"
    ? (import.meta.env?.VITE_API_BASE_URL as string | undefined)
    : undefined
) ?? "http://localhost:8000";

function generateUUID(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback for environments without crypto.randomUUID
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

// ── Request context ───────────────────────────────────────────────────────────

let _accountId: string | null = null;
let _authToken: string | null = null;

/** Set the active account ID (call after account selection). */
export function setActiveAccount(accountId: string): void {
  _accountId = accountId;
}

/** Set the auth bearer token (call after login). */
export function setAuthToken(token: string | null): void {
  _authToken = token;
}

/** Get the stored auth token. */
export function getAuthToken(): string | null {
  return _authToken;
}

// ── Core fetch wrapper ────────────────────────────────────────────────────────

export interface ApiRequestOptions extends RequestInit {
  /** If true and method is POST/PATCH/DELETE, an Idempotency-Key is auto-generated. */
  idempotent?: boolean;
  /** Explicit idempotency key (overrides auto-generation). */
  idempotencyKey?: string;
  /** Expected entity version for optimistic concurrency (adds If-Match header). */
  expectedVersion?: number;
  /** Skip the auth header (used for public endpoints). */
  anonymous?: boolean;
}

export async function apiFetch<T = unknown>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const {
    idempotent = false,
    idempotencyKey,
    expectedVersion,
    anonymous = false,
    ...fetchOptions
  } = options;

  const correlationId = generateUUID();
  const method = (fetchOptions.method ?? "GET").toUpperCase();
  const isMutation = ["POST", "PATCH", "PUT", "DELETE"].includes(method);

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Correlation-ID": correlationId,
    ...(fetchOptions.headers as Record<string, string> | undefined),
  };

  if (!anonymous && _authToken) {
    headers["Authorization"] = `Bearer ${_authToken}`;
  }

  if (_accountId) {
    headers["X-Account-Id"] = _accountId;
  }

  if (isMutation && (idempotent || idempotencyKey)) {
    headers["Idempotency-Key"] = idempotencyKey ?? generateUUID();
  }

  if (expectedVersion !== undefined) {
    headers["If-Match"] = String(expectedVersion);
  }

  const url = `${BASE_URL}${path}`;

  let response: Response;
  try {
    response = await fetch(url, {
      ...fetchOptions,
      headers,
    });
  } catch (networkError) {
    throw new ApiError(0, "NETWORK_ERROR", `Network error: ${networkError}`, {}, correlationId);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  let body: unknown;
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    body = await response.json();
  } else {
    body = await response.text();
  }

  if (!response.ok) {
    const errBody = body as {
      error?: string;
      code?: string;
      details?: Record<string, unknown>;
      correlation_id?: string;
    };
    throw new ApiError(
      response.status,
      errBody.code ?? "UNKNOWN_ERROR",
      errBody.error ?? response.statusText,
      errBody.details ?? {},
      errBody.correlation_id ?? correlationId,
    );
  }

  return body as T;
}

// ── Typed convenience methods ─────────────────────────────────────────────────

export const api = {
  get: <T>(path: string, options?: ApiRequestOptions) =>
    apiFetch<T>(path, { ...options, method: "GET" }),

  post: <T>(path: string, body: unknown, options?: ApiRequestOptions) =>
    apiFetch<T>(path, {
      ...options,
      method: "POST",
      body: JSON.stringify(body),
      idempotent: options?.idempotent ?? true,
    }),

  patch: <T>(path: string, body: unknown, options?: ApiRequestOptions) =>
    apiFetch<T>(path, {
      ...options,
      method: "PATCH",
      body: JSON.stringify(body),
      idempotent: options?.idempotent ?? true,
    }),

  delete: <T = void>(path: string, options?: ApiRequestOptions) =>
    apiFetch<T>(path, {
      ...options,
      method: "DELETE",
      idempotent: options?.idempotent ?? true,
    }),
};

// ── Query string builder ──────────────────────────────────────────────────────

export function buildQueryString(params: Record<string, string | number | boolean | null | undefined>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== null && v !== undefined && v !== "");
  if (!entries.length) return "";
  const qs = entries.map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`).join("&");
  return `?${qs}`;
}
