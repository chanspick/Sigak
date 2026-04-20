// SIGAK MVP v1.2 — PhotoPlaceholder
// 결정적 seed 기반 paper-toned diagonal-stripe placeholder.
// 실제 업로드 전까지 stock 이미지 없이도 UI 검증 가능.
// Source: refactor/shared.jsx PhotoPlaceholder.

interface PhotoPlaceholderProps {
  seed?: number;
  /** aspectRatio. 예: "1/1", "4/5". 기본 "4/5". */
  ratio?: string;
  className?: string;
}

const TONES = [
  { bg: "#E6E2D6", stripe: "rgba(15,15,14,0.06)" },
  { bg: "#D8DDD0", stripe: "rgba(15,15,14,0.07)" },
  { bg: "#E2DCD0", stripe: "rgba(15,15,14,0.05)" },
  { bg: "#D0D6CB", stripe: "rgba(15,15,14,0.06)" },
  { bg: "#E8E3D5", stripe: "rgba(15,15,14,0.05)" },
  { bg: "#DCD7C8", stripe: "rgba(15,15,14,0.06)" },
  { bg: "#D5DBCC", stripe: "rgba(15,15,14,0.06)" },
  { bg: "#E0DBCD", stripe: "rgba(15,15,14,0.07)" },
  { bg: "#D2D8C9", stripe: "rgba(15,15,14,0.06)" },
  { bg: "#E4DFD1", stripe: "rgba(15,15,14,0.05)" },
  { bg: "#DEDACA", stripe: "rgba(15,15,14,0.06)" },
] as const;

export function PhotoPlaceholder({
  seed = 0,
  ratio = "4/5",
  className,
}: PhotoPlaceholderProps) {
  const t = TONES[((seed % TONES.length) + TONES.length) % TONES.length];
  const angle = 28 + ((seed * 13) % 24); // 28..52deg
  return (
    <div
      className={className}
      style={{
        width: "100%",
        aspectRatio: ratio,
        background: `repeating-linear-gradient(${angle}deg, ${t.bg} 0 14px, ${t.stripe} 14px 15px)`,
        position: "relative",
        overflow: "hidden",
      }}
    />
  );
}
