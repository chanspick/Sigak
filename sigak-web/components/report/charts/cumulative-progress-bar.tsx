// 누적 진행 바 — 카테고리 내 각 액션이 목표 delta에 기여하는 비율을 스택형으로 표시
// 프리미엄 컨설팅 리포트 스타일: 세그먼트 구분 + 총합 마커 + 요약 텍스트

interface ProgressSegment {
  /** 액션 이름 */
  label: string;
  /** 이 액션이 target_delta에 기여하는 절대값 */
  contribution: number;
}

interface CumulativeProgressBarProps {
  /** 목표 delta 값 (분모) */
  targetDelta: number;
  /** 각 액션의 기여 세그먼트 */
  segments: ProgressSegment[];
}

// 불투명도 단계 — 프리미엄 구분감: 채운/중간/연한
const OPACITY_STEPS = [1.0, 0.6, 0.35, 0.25, 0.18, 0.12];

export function CumulativeProgressBar({
  targetDelta,
  segments,
}: CumulativeProgressBarProps) {
  if (targetDelta <= 0) return null;

  // 각 세그먼트의 퍼센트 계산
  const segmentsWithPercent = segments.map((s) => ({
    ...s,
    percent: Math.min((s.contribution / targetDelta) * 100, 100),
  }));

  const totalContribution = segments.reduce(
    (sum, s) => sum + s.contribution,
    0
  );
  const totalPercent = Math.min(
    Math.round((totalContribution / targetDelta) * 100),
    100
  );

  // 누적 위치 계산 (총합 마커용)
  const totalWidthPercent = Math.min(
    (totalContribution / targetDelta) * 100,
    100
  );

  return (
    <div className="w-full">
      {/* 총합 퍼센트 라벨 — 바 위에 위치 */}
      <div className="relative h-4 mb-1">
        <div
          className="absolute -translate-x-1/2"
          style={{ left: `${totalWidthPercent}%` }}
        >
          <span className="text-[10px] font-semibold tabular-nums text-[var(--color-fg)]">
            {totalPercent}%
          </span>
        </div>
      </div>

      {/* 누적 바 — 8px 높이로 프리미엄 느낌 */}
      <div className="relative">
        <div className="w-full h-[8px] bg-[var(--color-border)] rounded-full overflow-hidden flex">
          {segmentsWithPercent.map((seg, idx) => (
            <div
              key={seg.label}
              className="h-full first:rounded-l-full last:rounded-r-full relative"
              style={{
                width: `${seg.percent}%`,
                backgroundColor: "var(--color-fg)",
                opacity: OPACITY_STEPS[idx] ?? 0.12,
                // 세그먼트 사이 미세한 구분선
                borderRight:
                  idx < segmentsWithPercent.length - 1
                    ? "1px solid var(--color-bg)"
                    : "none",
              }}
              title={`${seg.label}: ${Math.round(seg.percent)}%`}
            />
          ))}
        </div>

        {/* 총합 위치에 수직 마커 라인 */}
        <div
          className="absolute top-[-2px] w-[1.5px] h-[12px] bg-[var(--color-fg)]"
          style={{ left: `${totalWidthPercent}%`, marginLeft: "-0.75px" }}
        />
      </div>

      {/* 세그먼트별 라벨 (충분히 넓을 때만 표시) */}
      {segmentsWithPercent.length <= 4 && (
        <div className="flex mt-1.5 gap-px">
          {segmentsWithPercent.map((seg, idx) => (
            <div
              key={seg.label}
              className="text-[8px] text-[var(--color-muted)] truncate"
              style={{ width: `${seg.percent}%`, minWidth: 0 }}
            >
              {seg.percent > 12 && (
                <span className="tabular-nums opacity-70">
                  {Math.round(seg.percent)}%
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* 요약 텍스트 — 트래킹 넓은 소문자 스타일 */}
      <p className="text-[10px] text-[var(--color-muted)] mt-2 tabular-nums tracking-[0.5px]">
        {segments.length}개 액션 &rarr; {totalPercent}% 달성
      </p>
    </div>
  );
}

// 개별 추천의 기여 퍼센트를 인라인으로 보여주는 보조 컴포넌트
export function ContributionBadge({
  contribution,
  targetDelta,
}: {
  contribution: number;
  targetDelta: number;
}) {
  if (targetDelta <= 0 || contribution <= 0) return null;
  const percent = Math.round((contribution / targetDelta) * 100);

  return (
    <span className="inline-flex items-center px-1.5 py-0.5 text-[10px] tabular-nums text-[var(--color-muted)] border border-[var(--color-border)] rounded">
      {percent}%
    </span>
  );
}
