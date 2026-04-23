import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { SiaCountdown } from "./SiaCountdown";

describe("SiaCountdown", () => {
  it("31초 이상은 숨김 (null 렌더)", () => {
    render(<SiaCountdown remainingSeconds={31} />);
    expect(screen.queryByTestId("sia-countdown")).toBeNull();
  });

  it("30초 이하는 노출 + warning 색", () => {
    render(<SiaCountdown remainingSeconds={30} />);
    const el = screen.getByTestId("sia-countdown");
    expect(el).toBeTruthy();
    expect(el.className).toMatch(/text-\[var\(--color-danger\)\]/);
    expect(el.className).toMatch(/animate-sia-countdown-pulse/);
  });

  it("0초 도달 시 onExpire 가 1회만 호출된다", () => {
    const onExpire = vi.fn();
    const { rerender } = render(
      <SiaCountdown remainingSeconds={5} onExpire={onExpire} />,
    );
    expect(onExpire).not.toHaveBeenCalled();

    rerender(<SiaCountdown remainingSeconds={0} onExpire={onExpire} />);
    expect(onExpire).toHaveBeenCalledTimes(1);

    // 동일 값으로 re-render 해도 재호출 없음
    rerender(<SiaCountdown remainingSeconds={0} onExpire={onExpire} />);
    expect(onExpire).toHaveBeenCalledTimes(1);
  });

  it("M:SS 포맷 정확 (0:27 / 0:05 / 0:00)", () => {
    const { rerender } = render(<SiaCountdown remainingSeconds={27} />);
    expect(screen.getByTestId("sia-countdown").textContent).toBe("0:27");

    rerender(<SiaCountdown remainingSeconds={5} />);
    expect(screen.getByTestId("sia-countdown").textContent).toBe("0:05");

    rerender(<SiaCountdown remainingSeconds={0} />);
    expect(screen.getByTestId("sia-countdown").textContent).toBe("0:00");
  });

  it("aria-live='polite' 속성 포함", () => {
    render(<SiaCountdown remainingSeconds={20} />);
    const el = screen.getByTestId("sia-countdown");
    expect(el.getAttribute("aria-live")).toBe("polite");
  });
});
