// SIGAK MVP v1.2 — SageFrame
// Sage 색상 모서리 tick 프레임. "선택된 hero 순간"에만 사용(sparingly).
// Source: refactor/shared.jsx SageFrame.

import type { ReactNode } from "react";

interface SageFrameProps {
  children: ReactNode;
  /** 내부 padding (px). 기본 8. */
  inset?: number;
  /** tick 가로/세로 길이 (px). 기본 14. */
  tick?: number;
  /** stroke 두께 (px). 기본 1. */
  weight?: number;
  className?: string;
}

export function SageFrame({
  children,
  inset = 8,
  tick = 14,
  weight = 1,
  className,
}: SageFrameProps) {
  const sage = "var(--color-sage)";
  return (
    <div
      className={className}
      style={{ position: "relative", padding: inset }}
    >
      {/* TL */}
      <span style={{ position: "absolute", left: 0, top: 0, width: tick, height: weight, background: sage }} />
      <span style={{ position: "absolute", left: 0, top: 0, width: weight, height: tick, background: sage }} />
      {/* TR */}
      <span style={{ position: "absolute", right: 0, top: 0, width: tick, height: weight, background: sage }} />
      <span style={{ position: "absolute", right: 0, top: 0, width: weight, height: tick, background: sage }} />
      {/* BL */}
      <span style={{ position: "absolute", left: 0, bottom: 0, width: tick, height: weight, background: sage }} />
      <span style={{ position: "absolute", left: 0, bottom: 0, width: weight, height: tick, background: sage }} />
      {/* BR */}
      <span style={{ position: "absolute", right: 0, bottom: 0, width: tick, height: weight, background: sage }} />
      <span style={{ position: "absolute", right: 0, bottom: 0, width: weight, height: tick, background: sage }} />

      <div style={{ position: "relative" }}>{children}</div>
    </div>
  );
}
