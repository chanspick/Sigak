// 분포 위치 마커 — 가우시안 실루엣 + 수직 마커 + 삼각형 틱
// 프리미엄 컨설팅 리포트 스타일: 과학적이면서 우아한 데이터 시각화

interface DistributionBarProps {
  /** 0~100 범위의 백분위 */
  percentile: number;
  /** 왼쪽 끝 라벨 (예: "날카로운 110도") */
  minLabel: string;
  /** 오른쪽 끝 라벨 (예: "둥근 150도") */
  maxLabel: string;
}

export function DistributionBar({
  percentile,
  minLabel,
  maxLabel,
}: DistributionBarProps) {
  // 마커 위치를 0~100% 범위로 클램프
  const pos = Math.max(0, Math.min(100, percentile));
  // SVG 내 마커 X 위치 (양쪽 4px 패딩)
  const markerX = 6 + (pos / 100) * 188;

  return (
    <div className="w-full">
      {/* SVG: 벨커브 실루엣 + 트랙 + 수직 마커 + 삼각형 틱 */}
      <svg
        viewBox="0 0 200 32"
        className="w-full h-auto"
        role="img"
        aria-label="분포 위치"
      >
        {/* ─── 가우시안 벨커브 실루엣 (부드러운 배경) ─── */}
        <path
          d={[
            "M2,26",
            "C20,26 35,25 50,22",
            "C65,19 80,12 100,8",
            "C120,12 135,19 150,22",
            "C165,25 180,26 198,26",
            "Z",
          ].join(" ")}
          fill="var(--color-fg)"
          opacity="0.035"
          stroke="none"
        />
        {/* 벨커브 상단 윤곽선 (미세) */}
        <path
          d={[
            "M2,26",
            "C20,26 35,25 50,22",
            "C65,19 80,12 100,8",
            "C120,12 135,19 150,22",
            "C165,25 180,26 198,26",
          ].join(" ")}
          fill="none"
          stroke="var(--color-line)"
          strokeWidth="0.5"
          opacity="0.5"
        />

        {/* ─── 트랙 바 (얇고 세련된 수평선) ─── */}
        <line
          x1="6"
          y1="22"
          x2="194"
          y2="22"
          stroke="var(--color-line)"
          strokeWidth="2"
          strokeLinecap="round"
        />

        {/* ─── 수직 마커 (2px 폭, 16px 높이) ─── */}
        <line
          x1={markerX}
          y1="9"
          x2={markerX}
          y2="25"
          stroke="var(--color-fg)"
          strokeWidth="2"
          strokeLinecap="round"
        />

        {/* ─── 삼각형 틱 마크 (마커 하단) ─── */}
        <polygon
          points={`${markerX - 3},28 ${markerX + 3},28 ${markerX},25`}
          fill="var(--color-fg)"
          opacity="0.6"
        />

        {/* 백분위 라벨 제거 — 슬라이더 위치만으로 표현 (Fix #12) */}
      </svg>

      {/* 양쪽 끝 라벨 — 미세한 페이드 효과를 위한 그라데이션 텍스트 */}
      <div className="flex items-start justify-between mt-1 px-0.5">
        <span className="text-[11px] leading-tight text-[var(--color-muted)] opacity-80">
          {minLabel}
        </span>
        <span className="text-[11px] leading-tight text-[var(--color-muted)] opacity-80 text-right">
          {maxLabel}
        </span>
      </div>
    </div>
  );
}
