/**
 * SiaBubble — Sia / user / list 버블 렌더링 (D6 정적 포팅).
 *
 * 디자인 출처: chat_design/ui_kits/sia/index.html `.b.ai` / `.me .b` / `.list-line`
 *
 * Variants (마케터 랜딩_1815 ChatDemo 정합):
 *   sia  : 좌측 정렬, cream 배경 (--color-bubble-ai = #FAF6F0), 하단 좌측 각진 꼬리
 *   user : 우측 정렬, warm dark (--color-bubble-user = #2D2D2D) + 흰 텍스트
 *   list : sia variant + white-space pre-wrap 으로 하이픈 리스트 보존 렌더
 *
 * Max width 규칙 (D6 스펙):
 *   sia / list : 85%
 *   user       : 75%
 */
import type { ReactNode } from "react";

export type SiaBubbleVariant = "sia" | "user" | "list";

export interface SiaBubbleProps {
  variant: SiaBubbleVariant;
  children: ReactNode;
  /** 새로 공개된 버블에 진입 애니메이션 적용. stagger reveal 에서만 true. */
  animateIn?: boolean;
}

const BASE =
  "px-[14px] py-[11px] text-[14px] leading-[1.5] font-[var(--font-sans)]";

/** variant 별 정적 클래스. Tailwind JIT 가 purge 안 하도록 명시 전개. */
const VARIANT_CLASS: Record<SiaBubbleVariant, string> = {
  sia:
    "self-start bg-[var(--color-bubble-ai)] text-[var(--color-ink)] " +
    "rounded-tl-[16px] rounded-tr-[16px] rounded-br-[16px] rounded-bl-[4px] " +
    "max-w-[85%]",
  list:
    "self-start bg-[var(--color-bubble-ai)] text-[var(--color-ink)] " +
    "rounded-tl-[16px] rounded-tr-[16px] rounded-br-[16px] rounded-bl-[4px] " +
    "max-w-[85%] whitespace-pre-wrap",
  user:
    "self-end bg-[var(--color-bubble-user)] text-white " +
    "rounded-tl-[16px] rounded-tr-[16px] rounded-br-[4px] rounded-bl-[16px] " +
    "max-w-[75%]",
};

export function SiaBubble({ variant, children, animateIn = false }: SiaBubbleProps) {
  const anim = animateIn ? " animate-bubble-in" : "";
  return (
    <div
      className={`${BASE} ${VARIANT_CLASS[variant]}${anim}`}
      style={{ letterSpacing: "-0.005em" }}
      data-variant={variant}
    >
      {children}
    </div>
  );
}
