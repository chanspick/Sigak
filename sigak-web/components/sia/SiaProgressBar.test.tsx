import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { SiaProgressBar } from "./SiaProgressBar";

describe("SiaProgressBar", () => {
  it("percent=0 은 fill width 0%", () => {
    render(<SiaProgressBar percent={0} />);
    const fill = screen.getByTestId("sia-progress-fill") as HTMLDivElement;
    expect(fill.style.width).toBe("0%");
  });

  it("percent=50 은 fill width 50%", () => {
    render(<SiaProgressBar percent={50} />);
    const fill = screen.getByTestId("sia-progress-fill") as HTMLDivElement;
    expect(fill.style.width).toBe("50%");
  });

  it("percent=100 은 fill width 100%", () => {
    render(<SiaProgressBar percent={100} />);
    const fill = screen.getByTestId("sia-progress-fill") as HTMLDivElement;
    expect(fill.style.width).toBe("100%");
  });

  it("fill 이 width 전환 transition 클래스를 가진다", () => {
    render(<SiaProgressBar percent={42} />);
    const fill = screen.getByTestId("sia-progress-fill") as HTMLDivElement;
    // Tailwind transition-[width] duration-300 ease-out 은 className 상에 보존됨.
    expect(fill.className).toMatch(/transition-\[width\]/);
    expect(fill.className).toMatch(/duration-300/);
    expect(fill.className).toMatch(/ease-out/);
  });

  it("범위 밖 입력은 clamp (>100 → 100, <0 → 0, NaN → 0)", () => {
    const { rerender } = render(<SiaProgressBar percent={150} />);
    let fill = screen.getByTestId("sia-progress-fill") as HTMLDivElement;
    expect(fill.style.width).toBe("100%");

    rerender(<SiaProgressBar percent={-20} />);
    fill = screen.getByTestId("sia-progress-fill") as HTMLDivElement;
    expect(fill.style.width).toBe("0%");

    rerender(<SiaProgressBar percent={Number.NaN} />);
    fill = screen.getByTestId("sia-progress-fill") as HTMLDivElement;
    expect(fill.style.width).toBe("0%");
  });

  it("role=progressbar + aria-valuenow 동기화", () => {
    render(<SiaProgressBar percent={45} />);
    const bar = screen.getByRole("progressbar");
    expect(bar.getAttribute("aria-valuenow")).toBe("45");
    expect(bar.getAttribute("aria-valuemin")).toBe("0");
    expect(bar.getAttribute("aria-valuemax")).toBe("100");
  });
});
