// SIGAK MVP v1.2 — Medal + MedalLabel
// Gold / Silver / Bronze 14px 원형 메달 + 라벨.
// Source: refactor/result-screen.jsx Medal/MedalLabel.

export type MedalTier = "gold" | "silver" | "bronze";

const PALETTE: Record<MedalTier, { stroke: string; fill: string }> = {
  gold: { stroke: "var(--color-gold-stroke)", fill: "var(--color-gold-fill)" },
  silver: { stroke: "var(--color-silver-stroke)", fill: "var(--color-silver-fill)" },
  bronze: { stroke: "var(--color-bronze-stroke)", fill: "var(--color-bronze-fill)" },
};

const TIER_LABEL: Record<MedalTier, string> = {
  gold: "GOLD",
  silver: "SILVER",
  bronze: "BRONZE",
};

interface MedalProps {
  tier: MedalTier;
  /** 지름 (px). 기본 14. */
  size?: number;
}

export function Medal({ tier, size = 14 }: MedalProps) {
  const { stroke, fill } = PALETTE[tier];
  const r = (size - 1) / 2;
  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      aria-hidden
      style={{ display: "block" }}
    >
      <circle cx={size / 2} cy={size / 2} r={r} fill={fill} stroke={stroke} strokeWidth="1" />
    </svg>
  );
}

interface MedalLabelProps {
  tier: MedalTier;
  count?: number;
  className?: string;
}

export function MedalLabel({ tier, count, className }: MedalLabelProps) {
  return (
    <div
      className={className}
      style={{ display: "flex", alignItems: "center", gap: 8, lineHeight: 1 }}
    >
      <Medal tier={tier} />
      <span
        className="font-display font-medium uppercase text-ink"
        style={{ fontSize: 10, letterSpacing: "0.14em" }}
      >
        {TIER_LABEL[tier]}
      </span>
      {count != null && (
        <span
          className="font-display font-medium text-mute tabular-nums"
          style={{ fontSize: 10, letterSpacing: "0.04em" }}
        >
          · {count}
        </span>
      )}
    </div>
  );
}
