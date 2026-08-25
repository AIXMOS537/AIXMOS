import { describe, it, expect } from "vitest";
import { sanitizeId, constantEq, safeHtmlEscape } from "../src/index.js";

describe("sanitizeId", () => {
  it("keeps a plain alphanumeric id unchanged", () => {
    expect(sanitizeId("jarvis")).toBe("jarvis");
    expect(sanitizeId("tank-up_v2")).toBe("tank-up_v2");
  });

  it("strips the XSS payload this function exists to close", () => {
    // The real attack this guards: agent = "<script>...</script>" ends up in a
    // KV stat key (stat:agent:<script>...>) that's later rendered via innerHTML
    // on the founder dashboard. sanitizeId must never let this through whole.
    expect(sanitizeId("<script>alert(1)</script>")).toBe("");
  });

  it("rejects non-string input", () => {
    expect(sanitizeId(undefined)).toBe("");
    expect(sanitizeId(null)).toBe("");
    expect(sanitizeId(123)).toBe("");
    expect(sanitizeId({})).toBe("");
  });

  it("rejects empty string and strings over 64 chars", () => {
    expect(sanitizeId("")).toBe("");
    expect(sanitizeId("a".repeat(65))).toBe("");
    expect(sanitizeId("a".repeat(64))).toBe("a".repeat(64));
  });

  it("rejects ids containing disallowed characters entirely, not partially", () => {
    // Regex is anchored (^...$), so a mixed string must be rejected outright,
    // not truncated to its valid prefix -- a truncating sanitizer would still
    // be exploitable via "validprefix<script>...".
    expect(sanitizeId("valid<script>")).toBe("");
    expect(sanitizeId("has space")).toBe("");
    expect(sanitizeId("has.dot")).toBe("");
  });
});

describe("safeHtmlEscape", () => {
  it("escapes all five HTML-significant characters", () => {
    expect(safeHtmlEscape(`&<>"'`)).toBe("&amp;&lt;&gt;&quot;&#39;");
  });

  it("neutralizes a script tag", () => {
    expect(safeHtmlEscape("<script>alert(1)</script>")).toBe(
      "&lt;script&gt;alert(1)&lt;/script&gt;"
    );
  });

  it("coerces non-strings instead of throwing", () => {
    expect(safeHtmlEscape(123)).toBe("123");
    expect(safeHtmlEscape(null)).toBe("null");
  });

  it("leaves plain text untouched", () => {
    expect(safeHtmlEscape("plain text 123")).toBe("plain text 123");
  });
});

describe("constantEq", () => {
  it("returns true for identical strings", async () => {
    expect(await constantEq("same-secret", "same-secret")).toBe(true);
  });

  it("returns false for different strings of the same length", async () => {
    expect(await constantEq("secret-aaaa", "secret-bbbb")).toBe(false);
  });

  it("returns false for different-length strings without throwing", async () => {
    expect(await constantEq("short", "a-lot-longer-string")).toBe(false);
  });

  it("returns false for non-string input instead of throwing", async () => {
    expect(await constantEq(undefined, "x")).toBe(false);
    expect(await constantEq("x", null)).toBe(false);
    expect(await constantEq(123, 123)).toBe(false);
  });

  it("is not fooled by a shared prefix", async () => {
    expect(await constantEq("prefix-secretA", "prefix-secretB")).toBe(false);
  });
});
