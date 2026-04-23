import { describe, expect, it, vi, beforeAll } from "vitest";
import { render, screen } from "@testing-library/react";

import { SiaStream, parseSiaMessage } from "./SiaStream";
import type { SiaTurn } from "@/lib/types/sia.legacy";

// happy-dom scrollTo 미구현 — stub
beforeAll(() => {
  Element.prototype.scrollTo = vi.fn();
});

describe("parseSiaMessage", () => {
  it("splits single line by sentence terminators", () => {
    const result = parseSiaMessage("안녕하세요. Sia입니다.");
    expect(result).toEqual([
      { type: "text", content: "안녕하세요." },
      { type: "text", content: "Sia입니다." },
    ]);
  });

  it("groups consecutive hyphen lines into a single list bubble", () => {
    const result = parseSiaMessage(
      [
        "피드를 분석했습니다.",
        "- 쿨뮤트 68%",
        "- 채도 감소 추세",
        "- 측면 > 정면",
        "한 문장으로 요약합니다.",
      ].join("\n"),
    );
    expect(result).toEqual([
      { type: "text", content: "피드를 분석했습니다." },
      {
        type: "list",
        content: "- 쿨뮤트 68%\n- 채도 감소 추세\n- 측면 > 정면",
      },
      { type: "text", content: "한 문장으로 요약합니다." },
    ]);
  });

  it("trims blank lines and preserves question mark as sentence terminator", () => {
    const result = parseSiaMessage(
      "\n어떠세요? 다음 질문입니다.\n\n- 옵션 1",
    );
    expect(result).toEqual([
      { type: "text", content: "어떠세요?" },
      { type: "text", content: "다음 질문입니다." },
      { type: "list", content: "- 옵션 1" },
    ]);
  });
});

describe("SiaStream", () => {
  it("renders assistant turn with bubbles parsed from content", () => {
    const messages: SiaTurn[] = [
      {
        role: "sia",
        content: "안녕하세요.\n- 쿨뮤트 68%\n- 채도 감소",
      },
    ];
    render(<SiaStream messages={messages} />);

    expect(screen.getByText("안녕하세요.")).toBeInTheDocument();
    // 리스트는 단일 버블로 한 번만 렌더
    const listBubble = screen.getByText(/쿨뮤트 68%/);
    expect(listBubble.textContent).toContain("- 채도 감소");
    expect(listBubble).toHaveAttribute("data-variant", "list");
  });

  it("renders user turn as a single user bubble (no parsing)", () => {
    const messages: SiaTurn[] = [
      { role: "user", content: "세련되고 거리감 있는 인상" },
    ];
    render(<SiaStream messages={messages} />);

    const el = screen.getByText("세련되고 거리감 있는 인상");
    expect(el).toHaveAttribute("data-variant", "user");
  });

  it("renders SiaDots when pending prop is true", () => {
    render(<SiaStream messages={[]} pending />);
    expect(screen.getByRole("status")).toHaveAttribute(
      "aria-label",
      "Sia 응답 준비 중",
    );
  });

  it("does not render SiaDots when pending is false (default)", () => {
    render(<SiaStream messages={[{ role: "sia", content: "Hi." }]} />);
    expect(screen.queryByRole("status")).toBeNull();
  });
});
