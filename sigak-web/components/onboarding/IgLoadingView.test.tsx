import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import type { UseIgStatusResult } from "@/hooks/useIgStatus";

import { IgLoadingView } from "./IgLoadingView";


function makeResult(
  overrides: Partial<UseIgStatusResult> = {},
): UseIgStatusResult {
  return {
    status: "pending",
    previewUrls: [],
    username: null,
    analyzed: false,
    isTerminal: false,
    error: null,
    elapsedSeconds: 0,
    attempts: 0,
    ...overrides,
  };
}


describe("IgLoadingView", () => {
  it("renders pending heading with generic label when no username", () => {
    render(<IgLoadingView result={makeResult({ status: "pending" })} />);
    expect(
      screen.getByTestId("ig-loading-heading").textContent,
    ).toContain("피드 찾고 있어요");
  });

  it("renders pending_vision heading with username", () => {
    render(
      <IgLoadingView
        result={makeResult({
          status: "pending_vision",
          username: "xhan0_0",
          previewUrls: ["https://cdn/1.jpg"],
        })}
      />,
    );
    const heading = screen.getByTestId("ig-loading-heading").textContent ?? "";
    expect(heading).toContain("@xhan0_0");
    expect(heading).toContain("살피고 있어요");
  });

  it("shows skeleton grid when no previewUrls", () => {
    render(<IgLoadingView result={makeResult({ status: "pending" })} />);
    expect(screen.getByTestId("ig-skeleton-grid")).toBeInTheDocument();
    expect(screen.queryByTestId("ig-preview-grid")).toBeNull();
  });

  it("shows preview grid when previewUrls present", () => {
    render(
      <IgLoadingView
        result={makeResult({
          status: "pending_vision",
          previewUrls: [
            "https://cdn/1.jpg",
            "https://cdn/2.jpg",
            "https://cdn/3.jpg",
          ],
        })}
      />,
    );
    expect(screen.getByTestId("ig-preview-grid")).toBeInTheDocument();
    expect(screen.queryByTestId("ig-skeleton-grid")).toBeNull();
  });

  it("shows progress hint after 15s", () => {
    render(
      <IgLoadingView
        result={makeResult({
          status: "pending_vision",
          elapsedSeconds: 20,
        })}
      />,
    );
    expect(screen.getByTestId("ig-progress-hint").textContent).toBe(
      "곧 끝나요",
    );
  });

  it("shows different progress hint after 45s", () => {
    render(
      <IgLoadingView
        result={makeResult({
          status: "pending_vision",
          elapsedSeconds: 50,
        })}
      />,
    );
    expect(screen.getByTestId("ig-progress-hint").textContent).toBe(
      "조금만 더요",
    );
  });

  it("hides progress hint before 15s", () => {
    render(
      <IgLoadingView
        result={makeResult({
          status: "pending_vision",
          elapsedSeconds: 5,
        })}
      />,
    );
    expect(screen.queryByTestId("ig-progress-hint")).toBeNull();
  });

  it("renders success heading with preview", () => {
    render(
      <IgLoadingView
        result={makeResult({
          status: "success",
          isTerminal: true,
          previewUrls: ["https://cdn/1.jpg"],
          analyzed: true,
          username: "xhan0_0",
        })}
      />,
    );
    expect(
      screen.getByTestId("ig-loading-heading").textContent,
    ).toContain("다 봤어요");
  });

  it("renders private account fallback copy", () => {
    render(
      <IgLoadingView
        result={makeResult({ status: "private", isTerminal: true })}
      />,
    );
    expect(
      screen.getByTestId("ig-loading-heading").textContent,
    ).toContain("비공개");
    expect(
      screen.getByTestId("ig-loading-subcopy").textContent,
    ).toContain("괜찮아요");
  });

  it("renders failed fallback copy", () => {
    render(
      <IgLoadingView
        result={makeResult({ status: "failed", isTerminal: true })}
      />,
    );
    expect(
      screen.getByTestId("ig-loading-heading").textContent,
    ).toContain("못 가져왔어요");
  });

  it("renders error banner with retry CTA", () => {
    const onRetry = vi.fn();
    render(
      <IgLoadingView
        result={makeResult({ status: "pending", error: "timeout" })}
        onRetry={onRetry}
      />,
    );
    expect(screen.getByTestId("ig-error-banner")).toBeInTheDocument();
    const btn = screen.getByRole("button", { name: "다시 시도" });
    fireEvent.click(btn);
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("calls onContinue when CTA clicked on terminal status", () => {
    const onContinue = vi.fn();
    render(
      <IgLoadingView
        result={makeResult({ status: "success", isTerminal: true })}
        onContinue={onContinue}
      />,
    );
    const btn = screen.getByTestId("ig-continue-cta");
    fireEvent.click(btn);
    expect(onContinue).toHaveBeenCalledTimes(1);
  });

  it("preview grid caps at 6 thumbnails", () => {
    const urls = Array.from({ length: 10 }).map((_, i) => `https://cdn/${i}.jpg`);
    const { container } = render(
      <IgLoadingView
        result={makeResult({
          status: "pending_vision",
          previewUrls: urls,
        })}
      />,
    );
    const imgs = container.querySelectorAll("img");
    expect(imgs.length).toBe(6);
  });
});
