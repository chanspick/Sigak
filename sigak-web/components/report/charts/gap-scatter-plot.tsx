// 2D 갭 산점도 — 고정 축: X=형태(Shape), Y=연령대(Age), 점 크기=존재감(Volume)
// 쿼드런트 배경 + 미세 격자 + 현재(더블 링) → 추구(글로우 원) 방향 화살표

interface AestheticMap {
  current: { x: number; y: number; size: number };
  aspiration: { x: number; y: number; size: number };
  trend?: { x: number; y: number; size: number } | null;
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
  padLeft: number,
  padRight: number,
  invert = false
): number {
  const clamped = Math.max(-1, Math.min(1, val ?? 0));
  const normalized = (clamped + 1) / 2;
  const range = size - padLeft - padRight;
  return invert
    ? size - padRight - normalized * range
    : padLeft + normalized * range;
}

// 클램프된 원본 값 반환
function clampVal(val: number): number {
  return Math.max(-1, Math.min(1, val ?? 0));
}

export function GapScatterPlot({
  aestheticMap,
  gapMagnitude,
}: GapScatterPlotProps) {
  const { current, aspiration, trend, x_axis, y_axis, size_axis, quadrants } = aestheticMap;

  const W = 340;
  const H = 370;
  // 비대칭 패딩: 좌(Y축 라벨), 우, 상, 하(X축 라벨)
  const padL = 56;
  const padR = 16;
  const padT = 16;
  const padB = 78;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;
  const centerX = padL + plotW / 2;
  const centerY = padT + plotH / 2;

  // X = shape, Y = age (inverted: Fresh at bottom, Mature at top)
  const cx = toSvg(current.x, W, padL, padR);
  const cy = toSvg(current.y, H, padT, padB, true);
  const ax = toSvg(aspiration.x, W, padL, padR);
  const ay = toSvg(aspiration.y, H, padT, padB, true);

  // 점 크기: volume [-1,1] → 반지름 [5,11]
  const currentRadius = 5 + ((clampVal(current.size) + 1) / 2) * 6;
  const aspirationRadius = 5 + ((clampVal(aspiration.size) + 1) / 2) * 6;

  // 화살표 끝점 (추구 원 가장자리에서 멈추도록 오프셋)
  const dx = ax - cx;
  const dy = ay - cy;
  const dist = Math.sqrt(dx * dx + dy * dy);
  const arrowEndX = dist > 10 ? ax - (dx / dist) * aspirationRadius : ax;
  const arrowEndY = dist > 10 ? ay - (dy / dist) * aspirationRadius : ay;
  const arrowStartX = dist > 10 ? cx + (dx / dist) * currentRadius : cx;
  const arrowStartY = dist > 10 ? cy + (dy / dist) * currentRadius : cy;

  // 0.5 간격 격자 (한글 라벨 공간 확보를 위해 줄임)
  const gridSteps = [-0.5, 0, 0.5];

  return (
    <div className="w-full max-w-[340px] mx-auto">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full h-auto"
        role="img"
        aria-label={`${x_axis.name_kr}(X)과 ${y_axis.name_kr}(Y) 축 갭 산점도`}
      >
        <defs>
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

        {/* ─── 쿼드런트 배경 ─── */}
        <rect x={padL} y={padT} width={plotW / 2} height={plotH / 2} fill="var(--color-fg)" opacity="0.015" />
        <rect x={centerX} y={padT} width={plotW / 2} height={plotH / 2} fill="var(--color-fg)" opacity="0.03" />
        <rect x={padL} y={centerY} width={plotW / 2} height={plotH / 2} fill="var(--color-fg)" opacity="0.03" />
        <rect x={centerX} y={centerY} width={plotW / 2} height={plotH / 2} fill="var(--color-fg)" opacity="0.015" />

        {/* 쿼드런트 라벨 */}
        <text x={padL + plotW * 0.25} y={padT + plotH * 0.12} fontSize="8" fill="var(--color-muted)" textAnchor="middle" opacity="0.35" letterSpacing="0.5">{quadrants.top_left}</text>
        <text x={centerX + plotW * 0.25} y={padT + plotH * 0.12} fontSize="8" fill="var(--color-muted)" textAnchor="middle" opacity="0.35" letterSpacing="0.5">{quadrants.top_right}</text>
        <text x={padL + plotW * 0.25} y={centerY + plotH * 0.38} fontSize="8" fill="var(--color-muted)" textAnchor="middle" opacity="0.35" letterSpacing="0.5">{quadrants.bottom_left}</text>
        <text x={centerX + plotW * 0.25} y={centerY + plotH * 0.38} fontSize="8" fill="var(--color-muted)" textAnchor="middle" opacity="0.35" letterSpacing="0.5">{quadrants.bottom_right}</text>

        {/* ─── 격자 ─── */}
        {gridSteps.map((step) => {
          const posX = toSvg(step, W, padL, padR);
          const posY = toSvg(step, H, padT, padB, true);
          const isCenter = step === 0;
          return (
            <g key={step}>
              <line x1={posX} y1={padT} x2={posX} y2={H - padB} stroke="var(--color-line)" strokeWidth={isCenter ? "0.75" : "0.3"} strokeDasharray={isCenter ? "none" : "1.5,3"} opacity={isCenter ? 0.6 : 0.35} />
              <line x1={padL} y1={posY} x2={W - padR} y2={posY} stroke="var(--color-line)" strokeWidth={isCenter ? "0.75" : "0.3"} strokeDasharray={isCenter ? "none" : "1.5,3"} opacity={isCenter ? 0.6 : 0.35} />
            </g>
          );
        })}

        {/* 외곽 프레임 */}
        <rect x={padL} y={padT} width={plotW} height={plotH} fill="none" stroke="var(--color-line)" strokeWidth="0.75" />

        {/* ─── X축 라벨 (하단) ─── */}
        <text x={padL} y={H - padB + 18} fontSize="10" fill="var(--color-muted)" textAnchor="start" opacity="0.6">{x_axis.low}</text>
        <text x={centerX} y={H - padB + 32} fontSize="11" fill="var(--color-fg)" textAnchor="middle" fontWeight="600" letterSpacing="2">{x_axis.name_kr}</text>
        <text x={W - padR} y={H - padB + 18} fontSize="10" fill="var(--color-muted)" textAnchor="end" opacity="0.6">{x_axis.high}</text>

        {/* ─── Y축 라벨 (좌측, rotate 사용 — writingMode 대신) ─── */}
        <text x={padL - 22} y={H - padB} fontSize="10" fill="var(--color-muted)" textAnchor="middle" opacity="0.6">{y_axis.low}</text>
        <text x={14} y={centerY} fontSize="11" fill="var(--color-fg)" textAnchor="middle" fontWeight="600" letterSpacing="2" transform={`rotate(-90, 14, ${centerY})`}>{y_axis.name_kr}</text>
        <text x={padL - 22} y={padT + 4} fontSize="10" fill="var(--color-muted)" textAnchor="middle" dominantBaseline="hanging" opacity="0.6">{y_axis.high}</text>

        {/* ─── 화살표: 현재 → 추구 ─── */}
        {dist > 12 && (
          <line
            x1={arrowStartX} y1={arrowStartY} x2={arrowEndX} y2={arrowEndY}
            stroke="var(--color-fg)" strokeWidth="1.2" strokeDasharray="3,2.5" opacity="0.55"
            markerEnd="url(#gap-arrowhead)"
          />
        )}

        {/* ─── 현재 위치 — 더블 링 ─── */}
        <circle cx={cx} cy={cy} r={currentRadius + 3} fill="none" stroke="var(--color-muted)" strokeWidth="0.5" opacity="0.3" filter="url(#current-shadow)" />
        <circle cx={cx} cy={cy} r={currentRadius} fill="var(--color-bg)" stroke="var(--color-muted)" strokeWidth="1.5" />

        {/* ─── 추구 위치 — 채운 원 + 글로우 ─── */}
        <circle cx={ax} cy={ay} r={aspirationRadius} fill="var(--color-fg)" filter="url(#aspiration-glow)" />
        <circle cx={ax} cy={ay} r={aspirationRadius} fill="var(--color-fg)" />

        {/* ─── 트렌드 방향 — 삼각형 (옵션) ─── */}
        {trend && (() => {
          const tx = toSvg(trend.x, W, padL, padR);
          const ty = toSvg(trend.y, H, padT, padB, true);
          const s = 6;
          const points = `${tx},${ty - s} ${tx - s * 0.87},${ty + s * 0.5} ${tx + s * 0.87},${ty + s * 0.5}`;
          return (
            <polygon
              points={points}
              fill="none"
              stroke="var(--color-fg)"
              strokeWidth="1.2"
              opacity="0.4"
              strokeDasharray="2,1.5"
            />
          );
        })()}
      </svg>

      {/* 범례 */}
      <div className="flex items-center justify-center gap-5 mt-2 text-[10px] tracking-[0.5px]">
        <div className="flex items-center gap-1.5 text-[var(--color-muted)]">
          <span className="inline-block w-2.5 h-2.5 rounded-full border-[1.5px] border-[var(--color-muted)] bg-[var(--color-bg)]" />
          <span>현재</span>
        </div>
        <div className="flex items-center gap-1.5 text-[var(--color-fg)]">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-[var(--color-fg)]" />
          <span className="font-medium">추구</span>
        </div>
        {trend && (
          <div className="flex items-center gap-1.5 text-[var(--color-muted)]">
            <span className="text-[9px]">&#9651;</span>
            <span>트렌드</span>
          </div>
        )}
        <div className="flex items-center gap-1.5 text-[var(--color-muted)]">
          <span className="text-[9px]">&#9679;</span>
          <span>점 크기 = {size_axis.name_kr}</span>
        </div>
      </div>
    </div>
  );
}
