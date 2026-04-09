// 2D 갭 산점도 — 고정 축: X=형태(Shape), Y=연령대(Age), 점 크기=존재감(Volume)
// 쿼드런트 배경 + 미세 격자 + 현재(더블 링) → 추구(글로우 원) 방향 화살표
// 프리미엄 컨설팅 리포트 스타일

interface AestheticMap {
  current: { x: number; y: number; size: number };
  aspiration: { x: number; y: number; size: number };
  x_axis: { name_kr: string; low: string; high: string; low_en: string; high_en: string };
  y_axis: { name_kr: string; low: string; high: string; low_en: string; high_en: string };
  size_axis: { name_kr: string; low: string; high: string };
  quadrants: { top_left: string; top_right: string; bottom_left: string; bottom_right: string };
  description?: string;
}

interface GapScatterPlotProps {
  aestheticMap: AestheticMap;
  gapMagnitude?: number;
}

// 값 → SVG 좌표 변환 (클램프 -1~+1)
function toSvg(
  val: number,
  size: number,
  padding: number,
  invert = false
): number {
  const clamped = Math.max(-1, Math.min(1, val ?? 0));
  const normalized = (clamped + 1) / 2; // 0~1
  const range = size - 2 * padding;
  return invert
    ? size - padding - normalized * range
    : padding + normalized * range;
}

// 클램프된 원본 값 반환
function clampVal(val: number): number {
  return Math.max(-1, Math.min(1, val ?? 0));
}

export function GapScatterPlot({
  aestheticMap,
  gapMagnitude,
}: GapScatterPlotProps) {
  const { current, aspiration, x_axis, y_axis, size_axis, quadrants } = aestheticMap;

  // 넓은 사이즈 (320 max-width 기준)
  const size = 320;
  const pad = 48; // 축 라벨 공간 확보
  const plotSize = size - 2 * pad;
  const center = size / 2;

  // X = shape, Y = age (inverted: Fresh at bottom, Mature at top)
  const cx = toSvg(current.x, size, pad);
  const cy = toSvg(current.y, size, pad, true);
  const ax = toSvg(aspiration.x, size, pad);
  const ay = toSvg(aspiration.y, size, pad, true);

  // 점 크기: volume [-1,1] → 반지름 [5,11]
  const currentRadius = 5 + ((clampVal(current.size) + 1) / 2) * 6;
  const aspirationRadius = 5 + ((clampVal(aspiration.size) + 1) / 2) * 6;

  // 화살표 끝점 (추구 원 가장자리에서 멈추도록 오프셋)
  const dx = ax - cx;
  const dy = ay - cy;
  const dist = Math.sqrt(dx * dx + dy * dy);
  const arrowEndX = dist > 10 ? ax - (dx / dist) * aspirationRadius : ax;
  const arrowEndY = dist > 10 ? ay - (dy / dist) * aspirationRadius : ay;
  // 화살표 시작점 (현재 원 가장자리에서 출발)
  const arrowStartX = dist > 10 ? cx + (dx / dist) * currentRadius : cx;
  const arrowStartY = dist > 10 ? cy + (dy / dist) * currentRadius : cy;

  // 0.25 간격 격자 위치 계산
  const gridSteps = [-0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75];

  return (
    <div className="w-full max-w-[340px] mx-auto">
      <svg
        viewBox={`0 0 ${size} ${size}`}
        className="w-full h-auto"
        role="img"
        aria-label={`${x_axis.name_kr}(X)과 ${y_axis.name_kr}(Y) 축 갭 산점도`}
      >
        <defs>
          {/* 화살표 마커 — 더 정제된 형태 */}
          <marker
            id="gap-arrowhead"
            markerWidth="8"
            markerHeight="6"
            refX="7"
            refY="3"
            orient="auto"
          >
            <path
              d="M0,0.5 L7,3 L0,5.5 L1.5,3 Z"
              fill="var(--color-fg)"
              opacity="0.7"
            />
          </marker>
          {/* 현재 위치 더블 링 효과용 */}
          <filter id="current-shadow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceAlpha" stdDeviation="1.5" />
            <feOffset dx="0" dy="0" />
            <feComponentTransfer>
              <feFuncA type="linear" slope="0.15" />
            </feComponentTransfer>
            <feMerge>
              <feMergeNode />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          {/* 추구 위치 글로우 효과 */}
          <filter id="aspiration-glow" x="-80%" y="-80%" width="260%" height="260%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="blur" />
            <feComponentTransfer in="blur">
              <feFuncA type="linear" slope="0.2" />
            </feComponentTransfer>
            <feMerge>
              <feMergeNode />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* ─── 쿼드런트 배경 (4개 영역, 미세한 밝기 차이) ─── */}
        {/* 좌상 */}
        <rect
          x={pad}
          y={pad}
          width={plotSize / 2}
          height={plotSize / 2}
          fill="var(--color-fg)"
          opacity="0.015"
        />
        {/* 우상 */}
        <rect
          x={center}
          y={pad}
          width={plotSize / 2}
          height={plotSize / 2}
          fill="var(--color-fg)"
          opacity="0.03"
        />
        {/* 좌하 */}
        <rect
          x={pad}
          y={center}
          width={plotSize / 2}
          height={plotSize / 2}
          fill="var(--color-fg)"
          opacity="0.03"
        />
        {/* 우하 */}
        <rect
          x={center}
          y={center}
          width={plotSize / 2}
          height={plotSize / 2}
          fill="var(--color-fg)"
          opacity="0.015"
        />

        {/* 쿼드런트 라벨 (매우 연하게) */}
        <text
          x={pad + plotSize * 0.25}
          y={pad + plotSize * 0.15}
          fontSize="7"
          fill="var(--color-muted)"
          textAnchor="middle"
          opacity="0.4"
          letterSpacing="0.5"
        >
          {quadrants.top_left}
        </text>
        <text
          x={center + plotSize * 0.25}
          y={pad + plotSize * 0.15}
          fontSize="7"
          fill="var(--color-muted)"
          textAnchor="middle"
          opacity="0.4"
          letterSpacing="0.5"
        >
          {quadrants.top_right}
        </text>
        <text
          x={pad + plotSize * 0.25}
          y={center + plotSize * 0.35}
          fontSize="7"
          fill="var(--color-muted)"
          textAnchor="middle"
          opacity="0.4"
          letterSpacing="0.5"
        >
          {quadrants.bottom_left}
        </text>
        <text
          x={center + plotSize * 0.25}
          y={center + plotSize * 0.35}
          fontSize="7"
          fill="var(--color-muted)"
          textAnchor="middle"
          opacity="0.4"
          letterSpacing="0.5"
        >
          {quadrants.bottom_right}
        </text>

        {/* ─── 미세 점선 격자 (0.25 간격) ─── */}
        {gridSteps.map((step) => {
          const pos = toSvg(step, size, pad);
          const posY = toSvg(step, size, pad, true);
          const isCenter = step === 0;
          return (
            <g key={step}>
              {/* 수직선 */}
              <line
                x1={pos}
                y1={pad}
                x2={pos}
                y2={size - pad}
                stroke="var(--color-border)"
                strokeWidth={isCenter ? "0.75" : "0.3"}
                strokeDasharray={isCenter ? "none" : "1.5,3"}
                opacity={isCenter ? 0.6 : 0.35}
              />
              {/* 수평선 */}
              <line
                x1={pad}
                y1={posY}
                x2={size - pad}
                y2={posY}
                stroke="var(--color-border)"
                strokeWidth={isCenter ? "0.75" : "0.3"}
                strokeDasharray={isCenter ? "none" : "1.5,3"}
                opacity={isCenter ? 0.6 : 0.35}
              />
            </g>
          );
        })}

        {/* 외곽 프레임 */}
        <rect
          x={pad}
          y={pad}
          width={plotSize}
          height={plotSize}
          fill="none"
          stroke="var(--color-border)"
          strokeWidth="0.75"
        />

        {/* ─── X축 라벨 (하단, 플롯 영역 바깥) ─── */}
        <text
          x={pad}
          y={size - 14}
          fontSize="8.5"
          fill="var(--color-muted)"
          textAnchor="start"
          letterSpacing="0.3"
        >
          {x_axis.low}
        </text>
        <text
          x={center}
          y={size - 6}
          fontSize="9"
          fill="var(--color-fg)"
          textAnchor="middle"
          fontWeight="600"
          letterSpacing="1"
        >
          {x_axis.name_kr}
        </text>
        {/* X축 방향 화살표 */}
        <line
          x1={center + 20}
          y1={size - 9}
          x2={center + 32}
          y2={size - 9}
          stroke="var(--color-muted)"
          strokeWidth="0.6"
          markerEnd="url(#gap-arrowhead)"
          opacity="0.4"
        />
        <text
          x={size - pad}
          y={size - 14}
          fontSize="8.5"
          fill="var(--color-muted)"
          textAnchor="end"
          letterSpacing="0.3"
        >
          {x_axis.high}
        </text>

        {/* ─── Y축 라벨 (좌측, 플롯 영역 바깥) ─── */}
        <text
          x={14}
          y={size - pad}
          fontSize="8.5"
          fill="var(--color-muted)"
          textAnchor="middle"
          letterSpacing="0.3"
        >
          {y_axis.low}
        </text>
        <text
          x={14}
          y={center + 3}
          fontSize="9"
          fill="var(--color-fg)"
          textAnchor="middle"
          fontWeight="600"
          letterSpacing="1"
          writingMode="vertical-rl"
          transform={`rotate(180, 14, ${center})`}
        >
          {y_axis.name_kr}
        </text>
        <text
          x={14}
          y={pad + 4}
          fontSize="8.5"
          fill="var(--color-muted)"
          textAnchor="middle"
          letterSpacing="0.3"
        >
          {y_axis.high}
        </text>

        {/* ─── 화살표: 현재 → 추구 (그라데이션 느낌의 실선) ─── */}
        {dist > 12 && (
          <line
            x1={arrowStartX}
            y1={arrowStartY}
            x2={arrowEndX}
            y2={arrowEndY}
            stroke="var(--color-fg)"
            strokeWidth="1.2"
            strokeDasharray="3,2.5"
            opacity="0.55"
            markerEnd="url(#gap-arrowhead)"
          />
        )}

        {/* ─── 현재 위치 — 더블 링 (크기 = volume 기반) ─── */}
        <circle
          cx={cx}
          cy={cy}
          r={currentRadius + 3}
          fill="none"
          stroke="var(--color-muted)"
          strokeWidth="0.5"
          opacity="0.3"
          filter="url(#current-shadow)"
        />
        <circle
          cx={cx}
          cy={cy}
          r={currentRadius}
          fill="var(--color-bg)"
          stroke="var(--color-muted)"
          strokeWidth="1.5"
        />
        {/* ─── 추구 위치 — 채운 원 + 글로우 (크기 = volume 기반) ─── */}
        <circle
          cx={ax}
          cy={ay}
          r={aspirationRadius}
          fill="var(--color-fg)"
          filter="url(#aspiration-glow)"
        />
        <circle
          cx={ax}
          cy={ay}
          r={aspirationRadius}
          fill="var(--color-fg)"
        />
      </svg>

      {/* 범례 — 깔끔한 하단 범례 */}
      <div className="flex items-center justify-center gap-6 mt-2 text-[10px] tracking-[0.5px]">
        <div className="flex items-center gap-1.5 text-[var(--color-muted)]">
          <span className="inline-block w-2.5 h-2.5 rounded-full border-[1.5px] border-[var(--color-muted)] bg-[var(--color-bg)]" />
          <span>현재</span>
        </div>
        <div className="flex items-center gap-1.5 text-[var(--color-fg)]">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-[var(--color-fg)]" />
          <span className="font-medium">추구</span>
        </div>
        <div className="flex items-center gap-1.5 text-[var(--color-muted)]">
          <span className="text-[9px]">&#9679;</span>
          <span>점 크기 = {size_axis.name_kr}</span>
        </div>
      </div>
    </div>
  );
}
