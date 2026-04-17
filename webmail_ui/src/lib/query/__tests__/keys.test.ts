/**
 * Unit tests — query key factories
 */

import { describe, it, expect } from "vitest";
import { keys, type KeyContext } from "../keys";

const ctx: KeyContext = { tenantId: "t1", accountId: "acc1" };
const ctx2: KeyContext = { tenantId: "t2", accountId: "acc2" };

describe("query keys", () => {
  describe("messages", () => {
    it("all key is scoped to tenant + account", () => {
      const k = keys.messages.all(ctx);
      expect(k).toEqual(["t1", "acc1", "messages"]);
    });

    it("list key includes params", () => {
      const k = keys.messages.list(ctx, { folderId: "inbox", view: "all" });
      expect(k[0]).toBe("t1");
      expect(k[2]).toBe("messages");
      expect(k[3]).toBe("list");
      expect(k[4]).toMatchObject({ folderId: "inbox" });
    });

    it("detail key includes id", () => {
      const k = keys.messages.detail(ctx, "msg-001");
      expect(k).toContain("msg-001");
      expect(k).toContain("detail");
    });

    it("different contexts produce different keys", () => {
      expect(keys.messages.all(ctx)).not.toEqual(keys.messages.all(ctx2));
    });
  });

  describe("threads", () => {
    it("all key is tenant + account scoped", () => {
      expect(keys.threads.all(ctx)).toEqual(["t1", "acc1", "threads"]);
    });

    it("detail key includes thread id", () => {
      expect(keys.threads.detail(ctx, "th-1")).toContain("th-1");
    });
  });

  describe("folders", () => {
    it("list and counts keys start with the same base", () => {
      const base = keys.folders.all(ctx);
      const list = keys.folders.list(ctx);
      const counts = keys.folders.counts(ctx);
      expect(list.slice(0, base.length)).toEqual(base);
      expect(counts.slice(0, base.length)).toEqual(base);
    });
  });

  describe("preferences", () => {
    it("detail key is tenant + account scoped", () => {
      expect(keys.preferences.detail(ctx)).toEqual(["t1", "acc1", "preferences"]);
    });
  });

  describe("search", () => {
    it("results key includes params", () => {
      const k = keys.search.results(ctx, { q: "hello" });
      expect(k).toContain("search");
      expect(k[k.length - 1]).toMatchObject({ q: "hello" });
    });
  });

  describe("key hierarchy — invalidation coverage", () => {
    it("list key starts with all key (enables wildcard invalidation)", () => {
      const all = keys.messages.all(ctx);
      const list = keys.messages.list(ctx, {});
      expect(list.slice(0, all.length)).toEqual(all);
    });

    it("detail key starts with all key", () => {
      const all = keys.messages.all(ctx);
      const detail = keys.messages.detail(ctx, "id-1");
      expect(detail.slice(0, all.length)).toEqual(all);
    });
  });
});
