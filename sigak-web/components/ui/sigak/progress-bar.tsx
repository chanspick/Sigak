// SIGAK MVP v1.2 (Rebrand) — ProgressBar
//
// 단순 1px 라인. 좌측 "진행" 라벨(sans 11px/1.5px) + 우측 serif tabular percentage.

interface ProgressBarProps {
  /** 0..100 정수. */
  pct: number;
  /** 좌측 라벨. 기본 "진행". */
  label?: string;
  /** 퍼센트 숨김. 기본 false. */
  hideValue?: boolean;
  className?: string;
}

export function ProgressBar({
  pct,
  label = "진행",
  hideValue = false,
  className,
}: ProgressBarProps) {
  const clamped = Math.max(0, Math.min(100, Math.round(pct)));
  return (
    <div className={className}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: 12,
        }}
      >
        <span
          className="font-sans uppercase"
          style={{
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: "1.5px",
            opacity: 0.4,
            color: "var(--color-ink)",
          }}
        >
          {label}
        </span>
        {!hideValue && (
          <span
            className="font-serif tabular-nums"
            style={{
              fontSize: 14,
              fontWeight: 400,
              color: "var(--color-ink)",
            }}
          >
            {String(clamped).padStart(3, " ")}%
          </span>
        )}
      </div>
      <div style={{ width: "100%", height: 1, background: "rgba(0, 0, 0, 0.1)" }}>
        <div
          style={{
            width: `${clamped}%`,
            height: "100%",
            background: "var(--color-ink)",
            transition: "width 0.2s ease",
          }}
        />
      </div>
    </div>
  );
}
