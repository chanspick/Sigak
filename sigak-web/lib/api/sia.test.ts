import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";

import { SiaApiError, startSiaChat } from "./sia";

// global fetch mock
function mockFetch(
  status: number,
  body: unknown,
  opts: { throwType?: "network" | "abort" } = {},
) {
  globalThis.fetch = vi.fn(async () => {
    if (opts.throwType === "network") {
      throw new TypeError("Failed to fetch");
    }
    if (opts.throwType === "abort") {
      const err = new DOMException("aborted", "AbortError");
      throw err;
    }
    return new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  }) as typeof fetch;
}

describe("lib/api/sia error classification", () => {
  const originalFetch = globalThis.fetch;
  beforeEach(() => {
    // auth.getToken 이 null 반환하도록 Bearer 부착 생략
    vi.stubGlobal("localStorage", {
      getItem: () => null,
      setItem: () => undefined,
      removeItem: () => undefined,
    });
  });
  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.unstubAllGlobals();
  });

  it("maps 401 → SiaApiError(code='auth')", async () => {
    mockFetch(401, { detail: "expired" });
    await expect(startSiaChat()).rejects.toSatisfy(
      (e: unknown) =>
        e instanceof SiaApiError && e.code === "auth" && e.status === 401,
    );
  });

  it("maps 410 → SiaApiError(code='expired')", async () => {
    mockFetch(410, { detail: "session expired" });
    await expect(startSiaChat()).rejects.toSatisfy(
      (e: unknown) =>
        e instanceof SiaApiError && e.code === "expired" && e.status === 410,
    );
  });

  it("maps 500 → SiaApiError(code='server')", async () => {
    mockFetch(500, { detail: "oops" });
    await expect(startSiaChat()).rejects.toSatisfy(
      (e: unknown) =>
        e instanceof SiaApiError && e.code === "server" && e.status === 500,
    );
  });

  it("maps fetch TypeError → SiaApiError(code='network')", async () => {
    mockFetch(0, null, { throwType: "network" });
    await expect(startSiaChat()).rejects.toSatisfy(
      (e: unknown) => e instanceof SiaApiError && e.code === "network",
    );
  });
});
