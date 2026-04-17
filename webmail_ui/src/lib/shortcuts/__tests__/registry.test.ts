/**
 * Unit tests — shortcut registry
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  registerShortcut,
  unregisterShortcut,
  getShortcuts,
  getShortcutsByCategory,
  updateShortcut,
  subscribeToRegistry,
  attachGlobalListener,
  detachGlobalListener,
} from "../registry";

// Reset the internal map between tests by unregistering everything
function clearAll() {
  for (const s of getShortcuts()) unregisterShortcut(s.id);
}

describe("shortcut registry", () => {
  beforeEach(clearAll);

  it("registers a shortcut and retrieves it", () => {
    const handler = vi.fn();
    registerShortcut({ id: "test-a", keys: ["a"], scope: "global", handler, description: "Test A" });
    const all = getShortcuts();
    expect(all).toHaveLength(1);
    expect(all[0].id).toBe("test-a");
    expect(all[0].keys).toEqual(["a"]);
  });

  it("defaults enabled=true and category='General'", () => {
    registerShortcut({ id: "x", keys: ["x"], scope: "global", handler: vi.fn(), description: "X" });
    const [s] = getShortcuts();
    expect(s.enabled).toBe(true);
    expect(s.category).toBe("General");
  });

  it("unregisters a shortcut", () => {
    registerShortcut({ id: "y", keys: ["y"], scope: "global", handler: vi.fn(), description: "Y" });
    unregisterShortcut("y");
    expect(getShortcuts()).toHaveLength(0);
  });

  it("updateShortcut patches fields", () => {
    registerShortcut({ id: "u", keys: ["u"], scope: "global", handler: vi.fn(), description: "U" });
    updateShortcut("u", { enabled: false, description: "Updated" });
    const [s] = getShortcuts();
    expect(s.enabled).toBe(false);
    expect(s.description).toBe("Updated");
  });

  it("does not update a non-existent shortcut", () => {
    // Should not throw
    expect(() => updateShortcut("missing", { enabled: false })).not.toThrow();
  });

  it("groups shortcuts by category", () => {
    registerShortcut({ id: "m1", keys: ["m"], scope: "global", handler: vi.fn(), description: "M1", category: "Mail" });
    registerShortcut({ id: "m2", keys: ["n"], scope: "global", handler: vi.fn(), description: "M2", category: "Mail" });
    registerShortcut({ id: "g1", keys: ["g"], scope: "global", handler: vi.fn(), description: "G1" });

    const byCategory = getShortcutsByCategory();
    expect(byCategory["Mail"]).toHaveLength(2);
    expect(byCategory["General"]).toHaveLength(1);
  });

  it("notifies subscribers on register", () => {
    const listener = vi.fn();
    const unsub = subscribeToRegistry(listener);
    registerShortcut({ id: "sub", keys: ["s"], scope: "global", handler: vi.fn(), description: "S" });
    expect(listener).toHaveBeenCalledOnce();
    unsub();
  });

  it("notifies subscribers on unregister", () => {
    const listener = vi.fn();
    registerShortcut({ id: "sub2", keys: ["s2"], scope: "global", handler: vi.fn(), description: "S2" });
    const unsub = subscribeToRegistry(listener);
    unregisterShortcut("sub2");
    expect(listener).toHaveBeenCalledOnce();
    unsub();
  });

  it("unsubscribing stops notifications", () => {
    const listener = vi.fn();
    const unsub = subscribeToRegistry(listener);
    unsub();
    registerShortcut({ id: "after", keys: ["z"], scope: "global", handler: vi.fn(), description: "Z" });
    expect(listener).not.toHaveBeenCalled();
  });

  it("fires handler on matching keydown event", () => {
    const handler = vi.fn();
    registerShortcut({ id: "fire", keys: ["e"], scope: "global", handler, description: "Fire" });
    attachGlobalListener();

    const event = new KeyboardEvent("keydown", { key: "e", bubbles: true });
    window.dispatchEvent(event);

    expect(handler).toHaveBeenCalled();
    detachGlobalListener();
  });

  it("does not fire handler for non-matching key", () => {
    const handler = vi.fn();
    registerShortcut({ id: "no-fire", keys: ["e"], scope: "global", handler, description: "E" });
    attachGlobalListener();

    const event = new KeyboardEvent("keydown", { key: "r", bubbles: true });
    window.dispatchEvent(event);

    expect(handler).not.toHaveBeenCalled();
    detachGlobalListener();
  });

  it("does not fire disabled shortcuts", () => {
    const handler = vi.fn();
    registerShortcut({ id: "disabled", keys: ["q"], scope: "global", handler, description: "Q", enabled: false });
    attachGlobalListener();

    const event = new KeyboardEvent("keydown", { key: "q", bubbles: true });
    window.dispatchEvent(event);

    expect(handler).not.toHaveBeenCalled();
    detachGlobalListener();
  });
});
