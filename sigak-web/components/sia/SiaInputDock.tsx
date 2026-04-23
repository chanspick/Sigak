"use client";

/**
 * SiaInputDock — Phase H 주관식 입력 Dock.
 *
 * 디자인 출처:
 *   chat_design/ui_kits/sia/index.html `.input-dock` (pill 회색 input + round send).
 *
 * Phase H 변경 (디자인 kit 대비):
 *   - <input type="text"> → <textarea> auto-grow (최대 4줄).
 *   - send 버튼 아이콘 금지 → 텍스트 "보내기" (사용자 지시).
 *   - IME 조합 중 Enter 차단 (한국어 입력 필수 처리).
 *   - 선택지 버튼 / 카드 일체 없음. 100% 주관식.
 *
 * 접근성:
 *   - textarea aria-label: "Sia에게 답하기"
 *   - send 버튼 aria-label: "전송"
 *   - 키보드 only 동작 완전 지원 (Enter 전송, Shift+Enter 줄바꿈)
 */
import { useRef, useState, type KeyboardEvent, type ChangeEvent } from "react";

export interface SiaInputDockProps {
  onSend: (text: string) => Promise<void>;
  disabled?: boolean;
  placeholder?: string;
  /** 최대 문자 수 — native maxLength 로 clipping. 기본 500. */
  maxLength?: number;
}

const DEFAULT_PLACEHOLDER = "Sia에게 답하기";
const SENDING_PLACEHOLDER = "Sia가 생각하는 중...";
const DEFAULT_MAX_LENGTH = 500;

// Auto-grow 계산. 14px 폰트 + leading 1.5 = ~22px line-height.
const LINE_HEIGHT_PX = 22;
const MAX_LINES = 4;
const MIN_HEIGHT_PX = 44;
const MAX_HEIGHT_PX = LINE_HEIGHT_PX * MAX_LINES; // 88

export function SiaInputDock({
  onSend,
  disabled = false,
  placeholder = DEFAULT_PLACEHOLDER,
  maxLength = DEFAULT_MAX_LENGTH,
}: SiaInputDockProps) {
  const ref = useRef<HTMLTextAreaElement | null>(null);
  const [value, setValue] = useState("");
  const [isComposing, setIsComposing] = useState(false);
  const [isSending, setIsSending] = useState(false);

  const busy = disabled || isSending;
  const placeholderText = busy ? SENDING_PLACEHOLDER : placeholder;
  const canSend = !busy && value.trim().length > 0;

  function adjustHeight() {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    const next = Math.min(Math.max(el.scrollHeight, MIN_HEIGHT_PX), MAX_HEIGHT_PX);
    el.style.height = `${next}px`;
  }

  function handleChange(e: ChangeEvent<HTMLTextAreaElement>) {
    setValue(e.target.value);
    adjustHeight();
  }

  async function submit() {
    if (busy) return;
    const trimmed = value.trim();
    if (!trimmed) return;
    setIsSending(true);
    try {
      await onSend(trimmed);
      setValue("");
      const el = ref.current;
      if (el) el.style.height = `${MIN_HEIGHT_PX}px`;
    } finally {
      setIsSending(false);
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (isComposing) return;
    if (e.key !== "Enter") return;
    if (e.shiftKey) return;
    e.preventDefault();
    void submit();
  }

  return (
    <div
      className="sticky bottom-0 flex items-end gap-[8px] border-t border-[var(--color-line)] bg-[var(--color-paper)] px-[20px] pt-[12px] pb-[20px]"
      data-testid="sia-input-dock"
    >
      <textarea
        ref={ref}
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        onCompositionStart={() => setIsComposing(true)}
        onCompositionEnd={() => setIsComposing(false)}
        disabled={busy}
        maxLength={maxLength}
        rows={1}
        placeholder={placeholderText}
        aria-label="Sia에게 답하기"
        className="flex-1 resize-none rounded-[22px] bg-[#F4F4F5] px-[16px] py-[11px] text-[14px] leading-[1.5] text-black outline-none placeholder:text-black/40 disabled:opacity-60"
        style={{
          minHeight: MIN_HEIGHT_PX,
          maxHeight: MAX_HEIGHT_PX,
          letterSpacing: "-0.005em",
          caretColor: "#000",
        }}
      />
      <button
        type="button"
        onClick={() => {
          void submit();
        }}
        disabled={!canSend}
        aria-label="전송"
        className={
          "h-[44px] shrink-0 rounded-full px-[18px] text-[14px] font-semibold tracking-[0.3px] transition-opacity " +
          (canSend
            ? "bg-black text-[var(--color-paper)] hover:opacity-90"
            : "border border-[var(--color-line-strong)] bg-transparent text-black/30")
        }
      >
        보내기
      </button>
    </div>
  );
}
