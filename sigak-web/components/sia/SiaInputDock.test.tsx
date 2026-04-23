import { describe, it, expect, vi, beforeAll } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { SiaInputDock } from "./SiaInputDock";

// happy-dom: textarea scrollHeight 기본 0. auto-grow 테스트는 behavior 만 확인.
beforeAll(() => {
  // noop — 환경 보정 여지
});

describe("SiaInputDock", () => {
  function setup(overrides?: Partial<Parameters<typeof SiaInputDock>[0]>) {
    const onSend = vi.fn().mockResolvedValue(undefined);
    const utils = render(<SiaInputDock onSend={onSend} {...overrides} />);
    const textarea = screen.getByLabelText("Sia에게 답하기") as HTMLTextAreaElement;
    const button = screen.getByRole("button", { name: "전송" }) as HTMLButtonElement;
    return { onSend, textarea, button, ...utils };
  }

  it("disabled 상태에서 Enter 전송을 차단한다", () => {
    const { onSend, textarea } = setup({ disabled: true });
    fireEvent.change(textarea, { target: { value: "답변" } });
    fireEvent.keyDown(textarea, { key: "Enter" });
    expect(onSend).not.toHaveBeenCalled();
  });

  it("disabled 상태에서 placeholder 가 생각 중 카피로 바뀐다", () => {
    const { textarea } = setup({ disabled: true });
    expect(textarea.placeholder).toBe("Sia가 생각하는 중...");
  });

  it("Enter 로 전송하고 onSend 에 trim 된 값을 넘긴다", async () => {
    const { onSend, textarea } = setup();
    fireEvent.change(textarea, { target: { value: "  답변 내용  " } });
    fireEvent.keyDown(textarea, { key: "Enter" });
    await waitFor(() => expect(onSend).toHaveBeenCalledWith("답변 내용"));
  });

  it("Shift+Enter 는 전송하지 않는다 (줄바꿈 허용)", () => {
    const { onSend, textarea } = setup();
    fireEvent.change(textarea, { target: { value: "first" } });
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: true });
    expect(onSend).not.toHaveBeenCalled();
  });

  it("IME 조합 중 Enter 는 전송하지 않는다", () => {
    const { onSend, textarea } = setup();
    fireEvent.compositionStart(textarea);
    fireEvent.change(textarea, { target: { value: "안녕하세요" } });
    fireEvent.keyDown(textarea, { key: "Enter" });
    expect(onSend).not.toHaveBeenCalled();
  });

  it("IME 조합 종료 후 Enter 는 정상 전송", async () => {
    const { onSend, textarea } = setup();
    fireEvent.compositionStart(textarea);
    fireEvent.change(textarea, { target: { value: "안녕하세요" } });
    fireEvent.compositionEnd(textarea);
    fireEvent.keyDown(textarea, { key: "Enter" });
    await waitFor(() => expect(onSend).toHaveBeenCalledWith("안녕하세요"));
  });

  it("공백 only 는 전송하지 않는다", () => {
    const { onSend, textarea } = setup();
    fireEvent.change(textarea, { target: { value: "   \n   " } });
    fireEvent.keyDown(textarea, { key: "Enter" });
    expect(onSend).not.toHaveBeenCalled();
  });

  it("maxLength 가 native 속성으로 적용된다", () => {
    const { textarea } = setup({ maxLength: 5 });
    expect(textarea.maxLength).toBe(5);
  });

  it("전송 성공 후 입력창이 초기화된다", async () => {
    const { onSend, textarea } = setup();
    fireEvent.change(textarea, { target: { value: "hello" } });
    fireEvent.keyDown(textarea, { key: "Enter" });
    await waitFor(() => expect(onSend).toHaveBeenCalled());
    await waitFor(() => expect(textarea.value).toBe(""));
  });

  it("버튼 클릭 시에도 전송된다", async () => {
    const { onSend, textarea, button } = setup();
    fireEvent.change(textarea, { target: { value: "버튼 전송" } });
    fireEvent.click(button);
    await waitFor(() => expect(onSend).toHaveBeenCalledWith("버튼 전송"));
  });

  it("빈 값일 때 버튼은 disabled", () => {
    const { button } = setup();
    expect(button).toBeDisabled();
  });
});
