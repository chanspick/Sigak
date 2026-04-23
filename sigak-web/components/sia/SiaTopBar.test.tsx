import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { SiaTopBar } from "./SiaTopBar";

describe("SiaTopBar (integration)", () => {
  it("progress 와 countdown 이 동시에 렌더된다 (30초 이하 케이스)", () => {
    render(
      <SiaTopBar progressPercent={45} remainingSeconds={27} />,
    );
    // progress bar 는 항상 렌더
    expect(screen.getByTestId("sia-progress-bar")).toBeTruthy();
    const fill = screen.getByTestId("sia-progress-fill") as HTMLDivElement;
    expect(fill.style.width).toBe("45%");
    // countdown 은 30초 이하에서만 렌더
    expect(screen.getByTestId("sia-countdown").textContent).toBe("0:27");
  });

  it("30초 경계 전에는 countdown 숨김, 경계 후에는 노출", () => {
    const { rerender } = render(
      <SiaTopBar progressPercent={20} remainingSeconds={31} />,
    );
    expect(screen.queryByTestId("sia-countdown")).toBeNull();
    // progress 는 보인다
    expect(screen.getByTestId("sia-progress-bar")).toBeTruthy();

    rerender(<SiaTopBar progressPercent={22} remainingSeconds={30} />);
    expect(screen.getByTestId("sia-countdown")).toBeTruthy();
    expect(screen.getByTestId("sia-countdown").textContent).toBe("0:30");
  });
});
