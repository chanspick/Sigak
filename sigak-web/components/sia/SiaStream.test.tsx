import { describe, expect, it, vi, beforeAll } from "vitest";
import { act, render, screen } from "@testing-library/react";

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

  // ─────────────────────────────────────────────
  //  Stagger reveal — 새 turn 도착 시 순차 공개
  // ─────────────────────────────────────────────

  it("initial mount reveals all bubbles of existing assistant turn immediately", () => {
    const messages: SiaTurn[] = [
      { role: "sia", content: "첫 문장. 두 문장. 세 문장." },
    ];
    render(<SiaStream messages={messages} />);
    // 마운트 직후 세 버블 모두 보여야 함 (재진입 시 재애니메이션 금지)
    expect(screen.getByText("첫 문장.")).toBeInTheDocument();
    expect(screen.getByText("두 문장.")).toBeInTheDocument();
    expect(screen.getByText("세 문장.")).toBeInTheDocument();
    // stagger dots 없음
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("new assistant turn after mount triggers staggered reveal", () => {
    vi.useFakeTimers();
    const initial: SiaTurn[] = [{ role: "user", content: "안녕" }];
    const { rerender } = render(<SiaStream messages={initial} />);

    // 새 assistant 턴 3 문장 도착
    const next: SiaTurn[] = [
      { role: "user", content: "안녕" },
      { role: "sia", content: "첫째. 둘째. 셋째." },
    ];
    rerender(<SiaStream messages={next} />);

    // 직후: 아직 버블 0개 + SiaDots 표시 중
    expect(screen.queryByText("첫째.")).toBeNull();
    expect(screen.getByRole("status")).toBeInTheDocument();

    // DOTS_DURATION_MS=250 경과 → 첫 버블 공개
    act(() => {
      vi.advanceTimersByTime(250);
    });
    expect(screen.getByText("첫째.")).toBeInTheDocument();
    expect(screen.queryByText("둘째.")).toBeNull();

    // BUBBLE_INTERVAL_MS=500 경과 → 다시 dots 표시
    act(() => {
      vi.advanceTimersByTime(500);
    });
    expect(screen.getByRole("status")).toBeInTheDocument();

    // 250ms 더 → 둘째 공개
    act(() => {
      vi.advanceTimersByTime(250);
    });
    expect(screen.getByText("둘째.")).toBeInTheDocument();

    // 500ms 경과 → 다시 dots
    act(() => {
      vi.advanceTimersByTime(500);
    });
    expect(screen.getByRole("status")).toBeInTheDocument();

    // 250ms 더 → 셋째 공개 + stagger 완료
    act(() => {
      vi.advanceTimersByTime(250);
    });
    expect(screen.getByText("셋째.")).toBeInTheDocument();
    expect(screen.queryByRole("status")).toBeNull();

    vi.useRealTimers();
  });

  it("pending dots do not duplicate with stagger dots during reveal", () => {
    vi.useFakeTimers();
    const initial: SiaTurn[] = [{ role: "user", content: "hi" }];
    const { rerender } = render(<SiaStream messages={initial} pending />);

    // pending=true 이지만 staggerInProgress 아님 → pending dots 1개 표시
    expect(screen.getAllByRole("status")).toHaveLength(1);

    // 새 sia 턴 도착 (pending 유지) — stagger 시작
    rerender(
      <SiaStream
        messages={[
          ...initial,
          { role: "sia", content: "첫. 둘." },
        ]}
        pending
      />,
    );
    // stagger 진행 중엔 pending dots 숨김, stagger dots 만 1개
    expect(screen.getAllByRole("status")).toHaveLength(1);

    vi.useRealTimers();
  });
});
