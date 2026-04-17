/**
 * Unit tests — SW registration helpers
 *
 * workbox-window is mocked entirely (no real SW environment in jsdom).
 *
 * IMPORTANT: vi.restoreAllMocks() must NOT be used here because Vitest v3
 * treats it as vi.resetAllMocks() for vi.fn() instances, which wipes mock
 * implementations (including the Workbox constructor) between tests.
 * Instead we use vi.clearAllMocks() (history only) + explicit re-init.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";

// ── vi.hoisted: vars are available inside the vi.mock factory (hoisted) ───────

const mocks = vi.hoisted(() => ({
  wbRegister: vi.fn().mockResolvedValue(undefined),
  wbAddEventListener: vi.fn(),
  wbGetSW: vi.fn().mockReturnValue(null),
  messageSW: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("workbox-window", () => ({
  Workbox: vi.fn().mockImplementation(() => ({
    register: mocks.wbRegister,
    addEventListener: mocks.wbAddEventListener,
    getSW: mocks.wbGetSW,
  })),
  messageSW: mocks.messageSW,
}));

// ── Environment polyfills (jsdom lacks these) ─────────────────────────────────

const swStub = {
  register: vi.fn().mockResolvedValue({}),
  addEventListener: vi.fn(),
  controller: null,
  ready: Promise.resolve({} as ServiceWorkerRegistration),
};

Object.defineProperty(navigator, "serviceWorker", {
  value: swStub,
  configurable: true,
  writable: true,
});

(globalThis as Record<string, unknown>).Notification = {
  requestPermission: vi.fn().mockResolvedValue("default"),
  permission: "default",
};

(window as Record<string, unknown>).PushManager = {};

// ── Helpers ───────────────────────────────────────────────────────────────────

function getCapturedHandler(eventName: string): ((...args: unknown[]) => void) | undefined {
  const call = mocks.wbAddEventListener.mock.calls.find((c) => c[0] === eventName);
  return call ? (call[1] as (...args: unknown[]) => void) : undefined;
}

// ── registerSW tests ──────────────────────────────────────────────────────────

describe("registerSW", () => {
  beforeEach(() => {
    // Clear call history only — do NOT reset implementations.
    vi.clearAllMocks();
    // Re-apply default implementations that vi.clearAllMocks doesn't touch,
    // but safety-restore in case any test called mockImplementationOnce.
    mocks.wbRegister.mockResolvedValue(undefined);
    mocks.messageSW.mockResolvedValue(undefined);
  });

  it("returns a function (updateSW)", async () => {
    const { registerSW } = await import("../register");
    const updateSW = registerSW({});
    expect(typeof updateSW).toBe("function");
  });

  it("registers Workbox event listeners for message, waiting, activated, registered", async () => {
    const { registerSW } = await import("../register");
    registerSW({});

    const events = mocks.wbAddEventListener.mock.calls.map((c) => c[0] as string);
    expect(events).toContain("message");
    expect(events).toContain("waiting");
    expect(events).toContain("activated");
    expect(events).toContain("registered");
  });

  it("calls onNeedRefresh when the 'waiting' event fires", async () => {
    const onNeedRefresh = vi.fn();
    const { registerSW } = await import("../register");
    registerSW({ onNeedRefresh });

    const handler = getCapturedHandler("waiting");
    expect(handler).toBeDefined();
    handler!();
    expect(onNeedRefresh).toHaveBeenCalledOnce();
  });

  it("calls onOfflineReady when 'activated' fires with isUpdate=false (first install)", async () => {
    const onOfflineReady = vi.fn();
    const { registerSW } = await import("../register");
    registerSW({ onOfflineReady });

    const handler = getCapturedHandler("activated");
    expect(handler).toBeDefined();
    handler!({ isUpdate: false });
    expect(onOfflineReady).toHaveBeenCalledOnce();
  });

  it("does NOT call onOfflineReady on a re-activation (isUpdate=true)", async () => {
    const onOfflineReady = vi.fn();
    const { registerSW } = await import("../register");
    registerSW({ onOfflineReady });

    const handler = getCapturedHandler("activated");
    expect(handler).toBeDefined();
    handler!({ isUpdate: true });
    expect(onOfflineReady).not.toHaveBeenCalled();
  });

  it("calls onRegistered when 'registered' fires with a registration", async () => {
    const onRegistered = vi.fn();
    const fakeReg = {} as ServiceWorkerRegistration;
    const { registerSW } = await import("../register");
    registerSW({ onRegistered });

    const handler = getCapturedHandler("registered");
    expect(handler).toBeDefined();
    handler!({ registration: fakeReg });
    expect(onRegistered).toHaveBeenCalledWith(fakeReg);
  });

  it("forwards SW messages to the onMessage callback", async () => {
    const onMessage = vi.fn();
    const { registerSW } = await import("../register");
    registerSW({ onMessage });

    const handler = getCapturedHandler("message");
    expect(handler).toBeDefined();
    handler!({ data: { type: "DELTA_SYNC_REQUESTED" } });
    expect(onMessage).toHaveBeenCalledWith({ type: "DELTA_SYNC_REQUESTED" });
  });

  it("calls onRegisterError when wb.register() rejects", async () => {
    mocks.wbRegister.mockRejectedValueOnce(new Error("SW registration failed"));
    const onRegisterError = vi.fn();
    const { registerSW } = await import("../register");
    registerSW({ onRegisterError });

    // document.readyState === 'complete' in jsdom, so register fires synchronously.
    await new Promise((r) => setTimeout(r, 0));
    expect(onRegisterError).toHaveBeenCalledWith(expect.any(Error));
  });

  it("returns a no-op updateSW when serviceWorker API is absent", async () => {
    const orig = navigator.serviceWorker;
    Object.defineProperty(navigator, "serviceWorker", { value: undefined, configurable: true });

    const { registerSW } = await import("../register");
    const updateSW = registerSW({});
    await expect(updateSW()).resolves.not.toThrow();

    Object.defineProperty(navigator, "serviceWorker", { value: orig, configurable: true });
  });
});

// ── requestBackgroundSync tests ───────────────────────────────────────────────

describe("requestBackgroundSync", () => {
  it("resolves silently when `sync` API is absent on the SW registration", async () => {
    // swStub.ready resolves with a plain object — no `sync` property.
    swStub.ready = Promise.resolve({} as ServiceWorkerRegistration);

    const { requestBackgroundSync } = await import("../register");
    await expect(requestBackgroundSync("test-tag")).resolves.not.toThrow();
  });

  it("resolves silently when serviceWorker API is absent", async () => {
    const orig = navigator.serviceWorker;
    Object.defineProperty(navigator, "serviceWorker", { value: undefined, configurable: true });

    const { requestBackgroundSync } = await import("../register");
    await expect(requestBackgroundSync("test-tag")).resolves.not.toThrow();

    Object.defineProperty(navigator, "serviceWorker", { value: orig, configurable: true });
  });
});

// ── subscribeToPush tests ─────────────────────────────────────────────────────

describe("subscribeToPush", () => {
  it("returns null when PushManager is not in window", async () => {
    const origPM = (window as Record<string, unknown>).PushManager;
    delete (window as Record<string, unknown>).PushManager;

    const { subscribeToPush } = await import("../register");
    expect(await subscribeToPush("fake-key")).toBeNull();

    (window as Record<string, unknown>).PushManager = origPM;
  });

  it("returns null when notification permission is denied", async () => {
    (window as Record<string, unknown>).PushManager = {};
    (globalThis.Notification as Record<string, unknown>).requestPermission = vi
      .fn()
      .mockResolvedValue("denied");

    const { subscribeToPush } = await import("../register");
    expect(await subscribeToPush("fake-key")).toBeNull();
  });
});
