/**
 * Unit tests — API client
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { ApiError, api, buildQueryString, setAuthToken, setActiveAccount } from "../client";

const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

function makeResponse(body: unknown, status = 200) {
  return {
    ok: status < 400,
    status,
    headers: { get: (_: string) => "application/json" },
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
  } as unknown as Response;
}

describe("API client", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    setAuthToken(null);
    setActiveAccount("");
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("api.get", () => {
    it("makes a GET request and returns parsed body", async () => {
      mockFetch.mockResolvedValueOnce(makeResponse({ items: [], next_cursor: null }));
      const result = await api.get<{ items: never[] }>("/api/v1/messages");
      expect(result.items).toEqual([]);
      expect(mockFetch).toHaveBeenCalledOnce();
      const [, options] = mockFetch.mock.calls[0];
      expect(options.method).toBe("GET");
    });

    it("includes Authorization header when token is set", async () => {
      setAuthToken("test-token");
      mockFetch.mockResolvedValueOnce(makeResponse({}));
      await api.get("/api/v1/messages");
      const [, options] = mockFetch.mock.calls[0];
      expect(options.headers["Authorization"]).toBe("Bearer test-token");
    });

    it("includes X-Account-Id when account is set", async () => {
      setActiveAccount("acc-123");
      mockFetch.mockResolvedValueOnce(makeResponse({}));
      await api.get("/api/v1/messages");
      const [, options] = mockFetch.mock.calls[0];
      expect(options.headers["X-Account-Id"]).toBe("acc-123");
    });

    it("includes X-Correlation-ID in every request", async () => {
      mockFetch.mockResolvedValueOnce(makeResponse({}));
      await api.get("/api/v1/messages");
      const [, options] = mockFetch.mock.calls[0];
      expect(options.headers["X-Correlation-ID"]).toMatch(/[0-9a-f-]{36}/);
    });
  });

  describe("api.post", () => {
    it("makes a POST with JSON body", async () => {
      mockFetch.mockResolvedValueOnce(makeResponse({ ok: true }));
      await api.post("/api/v1/drafts", { subject: "Hello" });
      const [, options] = mockFetch.mock.calls[0];
      expect(options.method).toBe("POST");
      expect(JSON.parse(options.body)).toEqual({ subject: "Hello" });
    });

    it("adds Idempotency-Key header on POST by default", async () => {
      mockFetch.mockResolvedValueOnce(makeResponse({}));
      await api.post("/api/v1/drafts", {});
      const [, options] = mockFetch.mock.calls[0];
      expect(options.headers["Idempotency-Key"]).toBeDefined();
    });

    it("uses caller-supplied idempotencyKey", async () => {
      mockFetch.mockResolvedValueOnce(makeResponse({}));
      await api.post("/api/v1/drafts", {}, { idempotencyKey: "my-key" });
      const [, options] = mockFetch.mock.calls[0];
      expect(options.headers["Idempotency-Key"]).toBe("my-key");
    });

    it("adds If-Match header when expectedVersion is provided", async () => {
      mockFetch.mockResolvedValueOnce(makeResponse({}));
      await api.post("/api/v1/messages/actions", {}, { expectedVersion: 5 });
      const [, options] = mockFetch.mock.calls[0];
      expect(options.headers["If-Match"]).toBe("5");
    });
  });

  describe("error handling", () => {
    it("throws ApiError with structured data on 4xx", async () => {
      const errBody = { error: "Not found", code: "NOT_FOUND", details: { resource: "Message" } };
      // Each call needs its own mock return value
      mockFetch
        .mockResolvedValueOnce(makeResponse(errBody, 404))
        .mockResolvedValueOnce(makeResponse(errBody, 404));
      await expect(api.get("/api/v1/messages/bad-id")).rejects.toThrow(ApiError);
      await expect(api.get("/api/v1/messages/bad-id")).rejects.toMatchObject({
        status: 404,
        code: "NOT_FOUND",
      });
    });

    it("marks 429 and 5xx errors as retryable", async () => {
      mockFetch.mockResolvedValueOnce(makeResponse({ error: "Rate limited", code: "RATE_LIMITED" }, 429));
      try {
        await api.get("/api/v1/messages");
      } catch (e) {
        expect((e as ApiError).retryable).toBe(true);
      }
    });

    it("marks 4xx (non-429) errors as non-retryable", async () => {
      mockFetch.mockResolvedValueOnce(makeResponse({ error: "Bad request", code: "VALIDATION_ERROR" }, 400));
      try {
        await api.get("/api/v1/messages");
      } catch (e) {
        expect((e as ApiError).retryable).toBe(false);
      }
    });

    it("throws ApiError with NETWORK_ERROR code on network failure", async () => {
      mockFetch.mockRejectedValueOnce(new TypeError("Failed to fetch"));
      await expect(api.get("/api/v1/messages")).rejects.toMatchObject({ code: "NETWORK_ERROR" });
    });
  });

  describe("buildQueryString", () => {
    it("builds a query string from non-null entries", () => {
      const qs = buildQueryString({ folder_id: "inbox", limit: 50, sort_order: "desc" });
      expect(qs).toBe("?folder_id=inbox&limit=50&sort_order=desc");
    });

    it("omits null and undefined values", () => {
      const qs = buildQueryString({ a: "x", b: null, c: undefined, d: "y" });
      expect(qs).toBe("?a=x&d=y");
    });

    it("returns empty string for empty params", () => {
      expect(buildQueryString({})).toBe("");
    });

    it("encodes special characters", () => {
      const qs = buildQueryString({ q: "hello world" });
      expect(qs).toContain("hello%20world");
    });
  });
});
