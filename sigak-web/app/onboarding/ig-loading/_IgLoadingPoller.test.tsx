/**
 * _IgLoadingPoller — G3 자동 폴백 nav 검증.
 *
 * 사양:
 *   - 최종 상태 (success/private/failed/skipped) 도달 시 자동 /sia 진입
 *   - timeout 에러 도달 시에도 0.6s 후 자동 /sia 진입 (유저 액션 불필요)
 *   - 401 (auth) 는 /auth/login 리다이렉트
 */
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { act, render } from "@testing-library/react";

import type { UseIgStatusResult } from "@/hooks/useIgStatus";


const mockReplace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace, push: vi.fn(), back: vi.fn() }),
}));

let mockResult: UseIgStatusResult = {
  status: "pending",
  previewUrls: [],
  username: null,
  analyzed: false,
  isTerminal: false,
  error: null,
  elapsedSeconds: 0,
  attempts: 0,
};

vi.mock("@/hooks/useIgStatus", () => ({
  useIgStatus: () => mockResult,
}));

// dynamic import — mocks 등록 이후에 로드되도록.
async function loadPoller() {
  const mod = await import("./_IgLoadingPoller");
  return mod.IgLoadingPoller;
}

function setResult(next: Partial<UseIgStatusResult>): void {
  mockResult = { ...mockResult, ...next };
}


beforeEach(() => {
  vi.useFakeTimers();
  mockReplace.mockClear();
  mockResult = {
    status: "pending",
    previewUrls: [],
    username: null,
    analyzed: false,
    isTerminal: false,
    error: null,
    elapsedSeconds: 0,
    attempts: 0,
  };
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});


describe("_IgLoadingPoller auto-nav", () => {
  it("does not navigate while pending", async () => {
    const Poller = await loadPoller();
    render(<Poller onRetry={vi.fn()} />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(mockReplace).not.toHaveBeenCalled();
  });

  it("navigates to /sia after 600ms on terminal status (failed)", async () => {
    setResult({ status: "failed", isTerminal: true });
    const Poller = await loadPoller();
    render(<Poller onRetry={vi.fn()} />);

    // 200ms — 아직 nav 안 됨
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });
    expect(mockReplace).not.toHaveBeenCalled();

    // 600ms 도달 — nav 수행
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(mockReplace).toHaveBeenCalledWith("/sia");
  });

  it("navigates to /sia after 1200ms on success", async () => {
    setResult({ status: "success", isTerminal: true });
    const Poller = await loadPoller();
    render(<Poller onRetry={vi.fn()} />);

    // 700ms — 아직 (success 는 1200ms 대기)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(700);
    });
    expect(mockReplace).not.toHaveBeenCalled();

    // 1200ms 도달
    await act(async () => {
      await vi.advanceTimersByTimeAsync(600);
    });
    expect(mockReplace).toHaveBeenCalledWith("/sia");
  });

  it("G3 — navigates to /sia after 600ms on timeout error", async () => {
    // timeout 은 isTerminal=false 이지만 error="timeout" — 자동 nav 해야 함.
    setResult({ status: "pending", isTerminal: false, error: "timeout" });
    const Poller = await loadPoller();
    render(<Poller onRetry={vi.fn()} />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });
    expect(mockReplace).not.toHaveBeenCalled();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(mockReplace).toHaveBeenCalledWith("/sia");
  });

  it("G3 — timeout auto-nav fires before user can click retry (0.6s window)", async () => {
    // 사양: "다시 시도 버튼 누를 시간 (0.6s) 안에 자동 nav 수행"
    setResult({ status: "pending", isTerminal: false, error: "timeout" });
    const Poller = await loadPoller();
    render(<Poller onRetry={vi.fn()} />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(600);
    });
    // 정확히 600ms 시점에 nav 트리거
    expect(mockReplace).toHaveBeenCalledWith("/sia");
    expect(mockReplace).toHaveBeenCalledTimes(1);
  });

  it("redirects to /auth/login on auth error", async () => {
    setResult({ status: "pending", error: "auth" });
    const Poller = await loadPoller();
    render(<Poller onRetry={vi.fn()} />);

    // auth 는 useEffect 즉시 — delay 없음
    await act(async () => {
      await Promise.resolve();
    });
    expect(mockReplace).toHaveBeenCalledWith("/auth/login");
  });

  it("does not auto-nav on non-timeout errors (network/server)", async () => {
    setResult({ status: "pending", error: "network" });
    const Poller = await loadPoller();
    render(<Poller onRetry={vi.fn()} />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    // network / server 에러는 유저 retry 대기 — 자동 nav 안 함
    expect(mockReplace).not.toHaveBeenCalled();
  });
});
