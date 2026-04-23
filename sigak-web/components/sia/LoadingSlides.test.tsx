import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";

import { LoadingSlides } from "./LoadingSlides";

describe("LoadingSlides", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("advances through 5 slides and stops at last", () => {
    render(<LoadingSlides />);
    // 슬라이드 1
    expect(screen.getByText(/피드를 다시 보고 있어요/)).toBeInTheDocument();
    // 3초마다 다음 슬라이드
    act(() => void vi.advanceTimersByTime(3000));
    expect(screen.getByText(/관찰을 조립하는 중이에요/)).toBeInTheDocument();
    act(() => void vi.advanceTimersByTime(3000));
    expect(screen.getByText(/톤을 정돈하는 중이에요/)).toBeInTheDocument();
    act(() => void vi.advanceTimersByTime(3000));
    expect(screen.getByText(/문장을 고르는 중이에요/)).toBeInTheDocument();
    act(() => void vi.advanceTimersByTime(3000));
    expect(screen.getByText(/거의 다 왔어요/)).toBeInTheDocument();
  });

  it("invokes onComplete after final slide timer", async () => {
    const onComplete = vi.fn();
    render(<LoadingSlides onComplete={onComplete} />);
    // 5 슬라이드 × 3초 = 15초. fake timer + setIndex 사이클이
    // 한 advance call 안에 다 처리되도록 async + 단계 분할.
    for (let i = 0; i < 5; i += 1) {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(3000);
      });
    }
    expect(onComplete).toHaveBeenCalledOnce();
  });
});
