// 2D 갭 산점도 — 가장 큰 delta 두 축을 X/Y로 사용
// 쿼드런트 배경 + 미세 격자 + 현재(더블 링) → 추구(글로우 원) 방향 화살표
// 프리미엄 컨설팅 리포트 스타일

interface Coordinates {
  structure: number;
  impression: number;
  maturity: number;
  intensity: number;
}

// 축 한글 라벨 — coordinate.py의 AXES 정의와 일치
// -1 = minLabel, +1 = maxLabel
const AXIS_META: Record<
  string,
  { label: string; minLabel: string; maxLabel: string }
> = {
  structure: { label: "라인", minLabel: "둥근", maxLabel: "각진" },
  impression: { label: "인상", minLabel: "온화한", maxLabel: "선명한" },
  maturity: { label: "분위기", minLabel: "프레시", maxLabel: "성숙한" },
  intensity: { label: "존재감", minLabel: "절제된", maxLabel: "화려한" },
};

// 한국어 형용사 → "~고" 연결형 (ㅂ불규칙 등 직접 매핑)
const CONNECTIVE_MAP: Record<string, string> = {
  "둥근": "둥글고",
  "각진": "각지고",
  "온화한": "온화하고",
  "선명한": "선명하고",
  "프레시": "프레시하고",
  "성숙한": "성숙하고",
  "절제된": "절제되고",
  "화려한": "화려하고",
};

// 쿼드런트 라벨 조합 — 한글 자연어
function getQuadrantLabels(
  xMeta: { minLabel: string; maxLabel: string },
  yMeta: { minLabel: string; maxLabel: string }
) {
  const join = (a: string, b: string) => {
    const connA = CONNECTIVE_MAP[a] ?? `${a}하고`;
    return `${connA} ${b}`;
  };
  return {
    topLeft: join(yMeta.maxLabel, xMeta.minLabel),
    topRight: join(yMeta.maxLabel, xMeta.maxLabel),
    bottomLeft: join(yMeta.minLabel, xMeta.minLabel),
    bottomRight: join(yMeta.minLabel, xMeta.maxLabel),
  };
}

interface GapScatterPlotProps {
  current: Coordinates;
  aspiration: Coordinates;
  gapMagnitude?: number;
}

// delta가 가장 큰 두 축 선택
function pickTopTwoAxes(
  current: Coordinates,
  aspiration: Coordinates
): [string, string] {
  const axes = Object.keys(current) as (keyof Coordinates)[];
  const sorted = axes
    .map((key) => ({
      key,
      delta: Math.abs(aspiration[key] - current[key]),
    }))
    .sort((a, b) => b.delta - a.delta);
  return [sorted[0].key, sorted[1].key];
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
  current,
  aspiration,
  gapMagnitude,
}: GapScatterPlotProps) {
  const [xAxis, yAxis] = pickTopTwoAxes(current, aspiration);
  const xMeta = AXIS_META[xAxis];
  const yMeta = AXIS_META[yAxis];
  const quadLabels = getQuadrantLabels(xMeta, yMeta);

  // 넓은 사이즈 (320 max-width 기준)
  const size = 320;
  const pad = 48; // 축 라벨 공간 확보
  const plotSize = size - 2 * pad;
  const center = size / 2;

  const cx = toSvg(current[xAxis as keyof Coordinates], size, pad);
  const cy = toSvg(current[yAxis as keyof Coordinates], size, pad, true);
  const ax = toSvg(aspiration[xAxis as keyof Coordinates], size, pad);
  const ay = toSvg(aspiration[yAxis as keyof Coordinates], size, pad, true);

  // 원본 클램프 값 (좌표 라벨용)
  const cxVal = clampVal(current[xAxis as keyof Coordinates]);
  const cyVal = clampVal(current[yAxis as keyof Coordinates]);
  const axVal = clampVal(aspiration[xAxis as keyof Coordinates]);
  const ayVal = clampVal(aspiration[yAxis as keyof Coordinates]);

  // 화살표 끝점 (원 가장자리에서 멈추도록 오프셋)
  const dx = ax - cx;
  const dy = ay - cy;
  const dist = Math.sqrt(dx * dx + dy * dy);
  const arrowEndX = dist > 10 ? ax - (dx / dist) * 9 : ax;
  const arrowEndY = dist > 10 ? ay - (dy / dist) * 9 : ay;
  // 화살표 시작점 (현재 원 가장자리에서 출발)
  const arrowStartX = dist > 10 ? cx + (dx / dist) * 9 : cx;
  const arrowStartY = dist > 10 ? cy + (dy / dist) * 9 : cy;

  // 중간점 (갭 라벨 배치용)
  const midX = (cx + ax) / 2;
  const midY = (cy + ay) / 2;

  // 0.25 간격 격자 위치 계산
  const gridSteps = [-0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75];

  return (
    <div className="w-full max-w-[340px] mx-auto">
      <svg
        viewBox={`0 0 ${size} ${size}`}
        className="w-full h-auto"
        role="img"
        aria-label={`${xMeta.label}(X)과 ${yMeta.label}(Y) 축 갭 산점도`}
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
          {quadLabels.topLeft}
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
          {quadLabels.topRight}
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
          {quadLabels.bottomLeft}
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
          {quadLabels.bottomRight}
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
          {xMeta.minLabel}
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
          {xMeta.label}
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
          {xMeta.maxLabel}
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
          {yMeta.minLabel}
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
          {yMeta.label}
        </text>
        <text
          x={14}
          y={pad + 4}
          fontSize="8.5"
          fill="var(--color-muted)"
          textAnchor="middle"
          letterSpacing="0.3"
        >
          {yMeta.maxLabel}
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

        {/* ─── 현재 위치 — 더블 링 (빈 원 + 외곽 링) ─── */}
        <circle
          cx={cx}
          cy={cy}
          r="9"
          fill="none"
          stroke="var(--color-muted)"
          strokeWidth="0.5"
          opacity="0.3"
          filter="url(#current-shadow)"
        />
        <circle
          cx={cx}
          cy={cy}
          r="6"
          fill="var(--color-bg)"
          stroke="var(--color-muted)"
          strokeWidth="1.5"
        />
        {/* ─── 추구 위치 — 채운 원 + 글로우 ─── */}
        <circle
          cx={ax}
          cy={ay}
          r="7"
          fill="var(--color-fg)"
          filter="url(#aspiration-glow)"
        />
        <circle
          cx={ax}
          cy={ay}
          r="7"
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
      </div>
    </div>
  );
}
