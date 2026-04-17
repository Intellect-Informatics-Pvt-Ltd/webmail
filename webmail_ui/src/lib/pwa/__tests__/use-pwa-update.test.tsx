/**
 * Unit tests — usePWAUpdate hook
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

// ── Mock registerSW ───────────────────────────────────────────────────────────

let capturedOptions: {
  onNeedRefresh?: () => void;
  onOfflineReady?: () => void;
  onMessage?: (d: unknown) => void;
} = {};

const mockUpdateSW = vi.fn().mockResolvedValue(undefined);

vi.mock("../register", () => ({
  registerSW: vi.fn((opts: typeof capturedOptions) => {
    capturedOptions = opts;
    return mockUpdateSW;
  }),
}));

describe("usePWAUpdate", () => {
  beforeEach(() => {
    capturedOptions = {};
    mockUpdateSW.mockClear();
  });

  it("starts with needsRefresh=false and isOfflineReady=false", async () => {
    const { usePWAUpdate } = await import("../use-pwa-update");
    const { result } = renderHook(() => usePWAUpdate());
    expect(result.current.needsRefresh).toBe(false);
    expect(result.current.isOfflineReady).toBe(false);
  });

  it("sets needsRefresh=true when onNeedRefresh is called", async () => {
    const { usePWAUpdate } = await import("../use-pwa-update");
    const { result } = renderHook(() => usePWAUpdate());

    act(() => {
      capturedOptions.onNeedRefresh?.();
    });

    expect(result.current.needsRefresh).toBe(true);
  });

  it("sets isOfflineReady=true when onOfflineReady is called", async () => {
    const { usePWAUpdate } = await import("../use-pwa-update");
    const { result } = renderHook(() => usePWAUpdate());

    act(() => {
      capturedOptions.onOfflineReady?.();
    });

    expect(result.current.isOfflineReady).toBe(true);
  });

  it("dismissUpdate sets needsRefresh back to false", async () => {
    const { usePWAUpdate } = await import("../use-pwa-update");
    const { result } = renderHook(() => usePWAUpdate());

    act(() => capturedOptions.onNeedRefresh?.());
    expect(result.current.needsRefresh).toBe(true);

    act(() => result.current.dismissUpdate());
    expect(result.current.needsRefresh).toBe(false);
  });

  it("updateSW calls the underlying updateSW function", async () => {
    const { usePWAUpdate } = await import("../use-pwa-update");
    const { result } = renderHook(() => usePWAUpdate());

    await act(async () => {
      await result.current.updateSW(true);
    });

    expect(mockUpdateSW).toHaveBeenCalledWith(true);
  });

  it("forwards SW messages to the onSWMessage callback", async () => {
    const onMsg = vi.fn();
    const { usePWAUpdate } = await import("../use-pwa-update");
    renderHook(() => usePWAUpdate(onMsg));

    act(() => {
      capturedOptions.onMessage?.({ type: "DELTA_SYNC_REQUESTED" });
    });

    expect(onMsg).toHaveBeenCalledWith({ type: "DELTA_SYNC_REQUESTED" });
  });
});
