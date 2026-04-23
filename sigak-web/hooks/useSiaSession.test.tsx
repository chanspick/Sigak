import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";

import { useSiaSession } from "./useSiaSession";
import * as siaApi from "@/lib/api/sia";
import { SiaApiError } from "@/lib/api/sia";

function resolved<T>(v: T): Promise<T> {
  return Promise.resolve(v);
}

describe("useSiaSession", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("calls startSiaChat on mount and transitions booting → ready", async () => {
    const start = vi.spyOn(siaApi, "startSiaChat").mockImplementation(() =>
      resolved({
        sessionId: "s1",
        openingMessage: "정세현님, Sia 예요.",
        turnCount: 0,
      }),
    );

    const { result } = renderHook(() => useSiaSession());
    expect(result.current.status).toBe("booting");

    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });
    expect(start).toHaveBeenCalledOnce();
    expect(result.current.status).toBe("ready");
    expect(result.current.sessionId).toBe("s1");
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].role).toBe("sia");
  });

  it("send appends optimistic user message + assistant response", async () => {
    vi.spyOn(siaApi, "startSiaChat").mockImplementation(() =>
      resolved({ sessionId: "s1", openingMessage: "오프닝.", turnCount: 0 }),
    );
    vi.spyOn(siaApi, "sendSiaMessage").mockImplementation(() =>
      resolved({
        sessionId: "s1",
        assistantMessage: "좋은 답이에요.",
        turnCount: 1,
        isComplete: false,
      }),
    );
    const { result } = renderHook(() => useSiaSession());
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });
    await act(async () => {
      await result.current.send("세련된 인상");
      await vi.advanceTimersByTimeAsync(100);
    });
    expect(result.current.messages).toHaveLength(3); // opening + user + assistant
    expect(result.current.messages[1].role).toBe("user");
    expect(result.current.messages[1].content).toBe("세련된 인상");
    expect(result.current.messages[2].role).toBe("sia");
    expect(result.current.turnCount).toBe(1);
  });

  it("transitions to error on send failure and allows resetError", async () => {
    vi.spyOn(siaApi, "startSiaChat").mockImplementation(() =>
      resolved({ sessionId: "s1", openingMessage: "오프닝.", turnCount: 0 }),
    );
    vi.spyOn(siaApi, "sendSiaMessage").mockImplementation(() =>
      Promise.reject(new SiaApiError("server", 500)),
    );
    const { result } = renderHook(() => useSiaSession());
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });
    await act(async () => {
      await result.current.send("test");
      await vi.advanceTimersByTimeAsync(100);
    });
    expect(result.current.status).toBe("error");
    expect(result.current.errorCode).toBe("server");
    act(() => result.current.resetError());
    expect(result.current.status).toBe("ready");
    expect(result.current.errorCode).toBeNull();
  });

  it("transitions to completed when server returns isComplete=true", async () => {
    vi.spyOn(siaApi, "startSiaChat").mockImplementation(() =>
      resolved({ sessionId: "s1", openingMessage: "오프닝.", turnCount: 0 }),
    );
    vi.spyOn(siaApi, "sendSiaMessage").mockImplementation(() =>
      resolved({
        sessionId: "s1",
        assistantMessage: "마지막 인사예요.",
        turnCount: 14,
        isComplete: true,
      }),
    );
    const { result } = renderHook(() => useSiaSession());
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });
    await act(async () => {
      await result.current.send("마무리");
      await vi.advanceTimersByTimeAsync(100);
    });
    expect(result.current.status).toBe("completed");
    expect(result.current.reportId).toBe("s1");
  });

  it("countdown ticks 1s per interval in ready state", async () => {
    vi.spyOn(siaApi, "startSiaChat").mockImplementation(() =>
      resolved({ sessionId: "s1", openingMessage: "오프닝.", turnCount: 0 }),
    );
    const { result } = renderHook(() => useSiaSession());
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });
    const initial = result.current.countdownSeconds;
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(result.current.countdownSeconds).toBe(initial - 3);
  });

  it("auto-ends on countdown expiry with reason='timeout'", async () => {
    vi.spyOn(siaApi, "startSiaChat").mockImplementation(() =>
      resolved({ sessionId: "s1", openingMessage: "오프닝.", turnCount: 0 }),
    );
    const end = vi.spyOn(siaApi, "endSiaChat").mockImplementation(() =>
      resolved({
        sessionId: "s1",
        messagesPersisted: 3,
        extractionQueued: true,
      }),
    );
    const { result } = renderHook(() => useSiaSession());
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });
    // 300s 경과 — 만료
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300_000);
      await vi.advanceTimersByTimeAsync(100);
    });
    expect(end).toHaveBeenCalledWith({
      sessionId: "s1",
      reason: "timeout",
    });
    expect(result.current.status).toBe("completed");
  });

  it("treats expired SiaApiError as graceful completion (not error)", async () => {
    vi.spyOn(siaApi, "startSiaChat").mockImplementation(() =>
      resolved({ sessionId: "s1", openingMessage: "오프닝.", turnCount: 0 }),
    );
    vi.spyOn(siaApi, "sendSiaMessage").mockImplementation(() =>
      Promise.reject(new SiaApiError("expired", 410)),
    );
    const { result } = renderHook(() => useSiaSession());
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });
    await act(async () => {
      await result.current.send("test");
      await vi.advanceTimersByTimeAsync(100);
    });
    expect(result.current.status).toBe("completed");
    expect(result.current.errorCode).toBeNull();
  });
});
