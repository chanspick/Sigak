// SIGAK MVP v1.2 (Rebrand) — PrimaryButton
//
// Active: 검정 bg + 베이지 텍스트, border 없음, 높이 56, border-radius 0.
// Inactive: 투명 bg + 검정 1px 0.15 opacity 테두리, opacity 0.3.
// 폰트: Pretendard 14px weight 600, letterSpacing 0.5px.
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
  // showArrow prop 소비만 (렌더에 영향 없음)
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
        width: "100%",
        height: 56,
        background: ready ? "var(--color-ink)" : "transparent",
        color: ready ? "var(--color-paper)" : "var(--color-ink)",
        border: ready ? "none" : "1px solid rgba(0, 0, 0, 0.15)",
        borderRadius: 0,
        fontFamily: "var(--font-sans)",
        fontSize: 14,
        fontWeight: 600,
        letterSpacing: "0.5px",
        opacity: ready ? 1 : 0.3,
        cursor: ready ? "pointer" : "default",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        ...style,
      }}
    >
      <span>{ready ? children : (disabledLabel ?? children)}</span>
    </button>
  );
}
