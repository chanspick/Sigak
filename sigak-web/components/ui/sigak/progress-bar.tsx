// SIGAK MVP v1.2 — ProgressBar
// 2px sage 진행바 + 좌측 라벨 + 우측 퍼센트.
// Source: refactor/analyzing-screen.jsx ProgressBar (0..100).

interface ProgressBarProps {
  /** 0..100 정수 권장. */
  pct: number;
  /** 좌측 라벨. 기본 "PROGRESS". */
  label?: string;
  /** 퍼센트 숨김. 기본 false. */
  hideValue?: boolean;
  className?: string;
}

export function ProgressBar({
  pct,
  label = "PROGRESS",
  hideValue = false,
  className,
}: ProgressBarProps) {
  const clamped = Math.max(0, Math.min(100, Math.round(pct)));
  return (
    <div className={className}>
      <div className="mb-2 flex items-baseline justify-between">
        <span
          className="font-display font-medium text-mute"
          style={{ fontSize: 10, letterSpacing: "0.22em" }}
        >
          {label}
        </span>
        {!hideValue && (
          <span
            className="font-mono text-ink tabular-nums"
            style={{ fontSize: 11, letterSpacing: "0.04em" }}
          >
            {String(clamped).padStart(3, " ")}%
          </span>
        )}
      </div>
      <div className="h-[2px] w-full" style={{ background: "rgba(15,15,14,0.08)" }}>
        <div
          className="h-full bg-sage transition-[width] duration-[260ms] ease-out"
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}
