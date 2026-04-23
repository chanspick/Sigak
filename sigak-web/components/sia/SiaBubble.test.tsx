import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { SiaBubble } from "./SiaBubble";

describe("SiaBubble", () => {
  it("renders sia variant with AI background + left-aligned self-start", () => {
    render(<SiaBubble variant="sia">안녕하세요.</SiaBubble>);
    const el = screen.getByText("안녕하세요.");
    expect(el).toHaveAttribute("data-variant", "sia");
    expect(el.className).toContain("self-start");
    expect(el.className).toContain("bg-[var(--color-bubble-ai)]");
  });

  it("renders user variant with user background + right-aligned self-end", () => {
    render(<SiaBubble variant="user">세련되고 거리감 있는 인상</SiaBubble>);
    const el = screen.getByText("세련되고 거리감 있는 인상");
    expect(el).toHaveAttribute("data-variant", "user");
    expect(el.className).toContain("self-end");
    expect(el.className).toContain("bg-[var(--color-bubble-user)]");
  });

  it("renders list variant preserving whitespace via whitespace-pre-wrap", () => {
    const multiLine = "- 쿨뮤트 68%\n- 채도 감소";
    render(<SiaBubble variant="list">{multiLine}</SiaBubble>);
    const el = screen.getByText(/쿨뮤트 68%/);
    expect(el).toHaveAttribute("data-variant", "list");
    expect(el.className).toContain("whitespace-pre-wrap");
    expect(el.textContent).toContain("- 채도 감소");
  });

  it("applies distinct max-width per variant (85% sia / 75% user)", () => {
    const { rerender } = render(<SiaBubble variant="sia">A</SiaBubble>);
    expect(screen.getByText("A").className).toContain("max-w-[85%]");

    rerender(<SiaBubble variant="user">B</SiaBubble>);
    expect(screen.getByText("B").className).toContain("max-w-[75%]");
  });
});
