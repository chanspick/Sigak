// SIGAK MVP v1.2 — PrimaryButton
//
// 2026-04-26 마케터 정합: pill (radius 100) + ink/mist 분기.
//   Active   : ink bg + paper text, padding 17px 24px, fontSize 15
//   Disabled : --color-line-strong bg + #fff text (마케터 mist 정합)
// 모든 페이지 (aspiration[id], best-shot[id], onboarding/step) 자동 정합.
"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";

interface PrimaryButtonProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> {
  children: ReactNode;
  /** disabled 상태 텍스트 override. */
  disabledLabel?: ReactNode;
  /** 하위 호환: 무시됨 (신규 디자인엔 화살표 없음). */
  showArrow?: boolean;
}

export function PrimaryButton({
  children,
  disabledLabel,
  disabled,
  className,
  style,
  showArrow: _showArrow,
  ...rest
}: PrimaryButtonProps) {
  const ready = !disabled;
  return (
    <button
      {...rest}
      disabled={disabled}
      className={className}
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        width: "100%",
        padding: "17px 24px",
        background: ready ? "var(--color-ink)" : "var(--color-line-strong)",
        color: ready ? "var(--color-paper)" : "#fff",
        border: "none",
        borderRadius: 100,
        fontFamily: "var(--font-sans)",
        fontSize: 15,
        fontWeight: 600,
        letterSpacing: "-0.012em",
        cursor: ready ? "pointer" : "not-allowed",
        transition: "all 0.2s ease",
        ...style,
      }}
    >
      <span>{ready ? children : (disabledLabel ?? children)}</span>
    </button>
  );
}
