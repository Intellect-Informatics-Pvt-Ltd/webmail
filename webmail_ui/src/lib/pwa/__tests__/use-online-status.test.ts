/**
 * Unit tests — useOnlineStatus hook
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useOnlineStatus } from "../use-online-status";

// ── Setup ──────────────────────────────────────────────────────────────────────

function setOnlineState(online: boolean) {
  Object.defineProperty(navigator, "onLine", {
    configurable: true,
    get: () => online,
  });
}

function fireOnlineEvent(type: "online" | "offline") {
  window.dispatchEvent(new Event(type));
}

describe("useOnlineStatus", () => {
  beforeEach(() => {
    setOnlineState(true);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    setOnlineState(true);
  });

  it("initialises to online when navigator.onLine is true", () => {
    setOnlineState(true);
    const { result } = renderHook(() => useOnlineStatus());
    expect(result.current.isOnline).toBe(true);
    expect(result.current.isOffline).toBe(false);
  });

  it("initialises to offline when navigator.onLine is false", () => {
    setOnlineState(false);
    const { result } = renderHook(() => useOnlineStatus());
    expect(result.current.isOnline).toBe(false);
    expect(result.current.isOffline).toBe(true);
  });

  it("switches to offline when the offline event fires", () => {
    const { result } = renderHook(() => useOnlineStatus());
    expect(result.current.isOnline).toBe(true);

    act(() => fireOnlineEvent("offline"));

    expect(result.current.isOnline).toBe(false);
    expect(result.current.isOffline).toBe(true);
  });

  it("switches back to online when the online event fires", () => {
    setOnlineState(false);
    const { result } = renderHook(() => useOnlineStatus());
    expect(result.current.isOffline).toBe(true);

    act(() => fireOnlineEvent("online"));

    expect(result.current.isOnline).toBe(true);
    expect(result.current.isOffline).toBe(false);
  });

  it("updates the `since` timestamp on each change", () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useOnlineStatus());
    const initialSince = result.current.since;

    // Advance time so the next Date() call produces a different value
    vi.advanceTimersByTime(50);
    act(() => fireOnlineEvent("offline"));
    const offlineSince = result.current.since;
    expect(offlineSince).not.toBe(initialSince);

    vi.advanceTimersByTime(50);
    act(() => fireOnlineEvent("online"));
    const onlineSince = result.current.since;
    expect(onlineSince).not.toBe(offlineSince);

    vi.useRealTimers();
  });

  it("cleans up listeners on unmount", () => {
    const removeSpy = vi.spyOn(window, "removeEventListener");
    const { unmount } = renderHook(() => useOnlineStatus());
    unmount();
    expect(removeSpy).toHaveBeenCalledWith("online", expect.any(Function));
    expect(removeSpy).toHaveBeenCalledWith("offline", expect.any(Function));
  });

  it("handles multiple rapid online/offline toggles correctly", () => {
    const { result } = renderHook(() => useOnlineStatus());

    act(() => fireOnlineEvent("offline"));
    expect(result.current.isOffline).toBe(true);

    act(() => fireOnlineEvent("online"));
    expect(result.current.isOnline).toBe(true);

    act(() => fireOnlineEvent("offline"));
    expect(result.current.isOffline).toBe(true);

    act(() => fireOnlineEvent("online"));
    expect(result.current.isOnline).toBe(true);
  });
});
