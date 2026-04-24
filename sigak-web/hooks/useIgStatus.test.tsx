import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { act, renderHook } from "@testing-library/react";

import * as onboardingApi from "@/lib/api/onboarding";
import { ApiError } from "@/lib/api/fetch";
import type { IgStatusResponse } from "@/lib/types/mvp";

import { useIgStatus } from "./useIgStatus";


function makeResp(overrides: Partial<IgStatusResponse> = {}): IgStatusResponse {
  return {
    status: "pending",
    preview_urls: [],
    username: null,
    analyzed: false,
    ...overrides,
  };
}


/** 한 tick (비동기 resolve + timer advance) 진행. */
async function advance(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}


/** 초기 마운트 후 첫 tick (즉시 실행) resolve 기다림. */
async function flushInitialTick() {
  await act(async () => {
    // microtask 3회 정도 flush — fetch resolve + setState 처리
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
  });
}


beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});


describe("useIgStatus", () => {
  it("transitions pending → pending_vision → success across ticks", async () => {
    const responses = [
      makeResp({ status: "pending" }),
      makeResp({
        status: "pending_vision",
        preview_urls: ["https://cdn/1.jpg", "https://cdn/2.jpg"],
        username: "xhan0_0",
      }),
      makeResp({
        status: "success",
        preview_urls: ["https://cdn/1.jpg", "https://cdn/2.jpg"],
        username: "xhan0_0",
        analyzed: true,
      }),
    ];
    let idx = 0;
    vi.spyOn(onboardingApi, "getIgStatus").mockImplementation(() => {
      const resp = responses[Math.min(idx, responses.length - 1)];
      idx++;
      return Promise.resolve(resp);
    });

    const { result } = renderHook(() =>
      useIgStatus({ intervalMs: 1000, maxAttempts: 10 }),
    );

    await flushInitialTick();
    expect(result.current.status).toBe("pending");

    await advance(1000);
    expect(result.current.status).toBe("pending_vision");
    expect(result.current.previewUrls).toEqual([
      "https://cdn/1.jpg",
      "https://cdn/2.jpg",
    ]);
    expect(result.current.username).toBe("xhan0_0");

    await advance(1000);
    expect(result.current.status).toBe("success");
    expect(result.current.analyzed).toBe(true);
    expect(result.current.isTerminal).toBe(true);
  });

  it("stops polling on terminal status", async () => {
    const spy = vi.spyOn(onboardingApi, "getIgStatus").mockResolvedValue(
      makeResp({ status: "success", analyzed: true }),
    );

    const { result } = renderHook(() =>
      useIgStatus({ intervalMs: 500, maxAttempts: 10 }),
    );

    await flushInitialTick();
    expect(result.current.isTerminal).toBe(true);

    const callsBefore = spy.mock.calls.length;
    await advance(5000);
    expect(spy.mock.calls.length).toBe(callsBefore);
  });

  it("classifies 401 as auth error", async () => {
    vi.spyOn(onboardingApi, "getIgStatus").mockRejectedValue(
      new ApiError(401, "Unauthorized"),
    );

    const { result } = renderHook(() =>
      useIgStatus({ intervalMs: 500, maxAttempts: 10 }),
    );
    await flushInitialTick();
    expect(result.current.error).toBe("auth");
  });

  it("classifies network error (TypeError)", async () => {
    vi.spyOn(onboardingApi, "getIgStatus").mockRejectedValue(
      new TypeError("fetch failed"),
    );

    const { result } = renderHook(() =>
      useIgStatus({ intervalMs: 500, maxAttempts: 10 }),
    );
    await flushInitialTick();
    expect(result.current.error).toBe("network");
  });

  it("sets timeout error after maxAttempts", async () => {
    vi.spyOn(onboardingApi, "getIgStatus").mockResolvedValue(
      makeResp({ status: "pending" }),
    );

    const { result } = renderHook(() =>
      useIgStatus({ intervalMs: 100, maxAttempts: 3 }),
    );

    await flushInitialTick();   // attempt 1
    await advance(100);         // attempt 2
    await advance(100);         // attempt 3
    await advance(100);         // attempt 4 → timeout
    expect(result.current.error).toBe("timeout");
  });

  it("does not poll when disabled", async () => {
    const spy = vi.spyOn(onboardingApi, "getIgStatus");

    renderHook(() => useIgStatus({ enabled: false }));

    await advance(5000);
    expect(spy).not.toHaveBeenCalled();
  });
});
