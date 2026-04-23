import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import { SiaErrorBanner } from "./SiaErrorBanner";

describe("SiaErrorBanner", () => {
  it("renders network copy with retry button + aria-live", () => {
    const onRetry = vi.fn();
    render(<SiaErrorBanner code="network" onRetry={onRetry} />);
    expect(
      screen.getByText(/연결이 끊겼어요/),
    ).toBeInTheDocument();
    const btn = screen.getByRole("button", { name: "다시" });
    expect(btn).toBeInTheDocument();
    fireEvent.click(btn);
    expect(onRetry).toHaveBeenCalledOnce();
    expect(screen.getByRole("alert")).toHaveAttribute("aria-live", "polite");
  });

  it("hides retry button for auth (재로그인 필요)", () => {
    render(<SiaErrorBanner code="auth" onRetry={() => undefined} />);
    expect(screen.getByText(/로그인이 만료됐어요/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "다시" })).toBeNull();
  });

  it("hides retry button for expired (세션 종료, 자동 이동)", () => {
    render(<SiaErrorBanner code="expired" onRetry={() => undefined} />);
    expect(screen.getByText(/대화 시간이 끝났어요/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "다시" })).toBeNull();
  });
});
