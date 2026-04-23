/**
 * SiaProgressBar — TopBar 하단 1px hairline 진행도.
 *
 * Phase H ⑤.
 * - 높이 1px 고정. 디자인 원칙 "no progress label" 준수 (숫자 0).
 * - 배경: `var(--color-line)` (rgba 0.10). 진행 fill: `var(--color-ink)` (검정).
 * - width 300ms ease 전환 — 디자인 motion 규칙 (ease-out 전용) 준수.
 * - role="progressbar" + aria-label 로 스크린 리더 호환.
 */

export interface SiaProgressBarProps {
  /** 0-100. 범위 밖 입력은 clamp. */
  percent: number;
}

export function SiaProgressBar({ percent }: SiaProgressBarProps) {
  const clamped = Math.max(0, Math.min(100, Number.isFinite(percent) ? percent : 0));
  return (
    <div
      className="h-[1px] w-full bg-[var(--color-line)]"
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label="대화 진행도"
      data-testid="sia-progress-bar"
    >
      <div
        className="h-full bg-[var(--color-ink)] transition-[width] duration-300 ease-out"
        style={{ width: `${clamped}%` }}
        data-testid="sia-progress-fill"
      />
    </div>
  );
}
