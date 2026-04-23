import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { SiaDots } from "./SiaDots";

describe("SiaDots", () => {
  it("renders as a status region with accessible label", () => {
    render(<SiaDots />);
    const region = screen.getByRole("status");
    expect(region).toHaveAttribute("aria-label", "Sia 응답 준비 중");
  });

  it("renders 3 dots with bounce animation classes + staggered delays", () => {
    const { container } = render(<SiaDots />);
    const dots = container.querySelectorAll("span.sia-dot");
    expect(dots).toHaveLength(3);
    expect(dots[1].className).toContain("sia-dot-2");
    expect(dots[2].className).toContain("sia-dot-3");
  });
});
