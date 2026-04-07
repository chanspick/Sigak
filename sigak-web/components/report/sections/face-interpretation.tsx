// 얼굴 구조 심층 해석 섹션 (standard 잠금)
// 프리미엄 컨설팅 리포트 스타일: 피처 카드 + 분포 바 + 과학적 백분위 표기
// 블러 시: overall_impression 선명, 상세 해석 블러

import { DistributionBar } from "@/components/report/charts/distribution-bar";

interface FeatureInterpretation {
  feature: string;
  label: string;
  value: number;
  unit: string;
  percentile: number;
  range_label: string;
  interpretation: string;
  min_label?: string;
  max_label?: string;
}

interface FaceInterpretationContent {
  overall_impression: string;
  feature_interpretations: FeatureInterpretation[];
  harmony_note: string;
  distinctive_points: string[];
}

interface FaceInterpretationProps {
  content: FaceInterpretationContent;
  locked: boolean;
}

// 수치 포맷
function formatValue(value: number | undefined, unit: string): string {
  if (value == null) return "";
  const formatted = value >= 1 ? value.toFixed(1) : value.toFixed(3);
  return `${formatted}${unit}`;
}

// 얼굴 구조 심층 해석 — 프리미엄 레이아웃
export function FaceInterpretation({
  content,
  locked,
}: FaceInterpretationProps) {
  return (
    <section className="py-10 border-b border-[var(--color-border)]">
      {/* 섹션 헤더 */}
      <h2 className="text-[11px] font-semibold tracking-[3px] uppercase text-[var(--color-muted)] mb-8">
        FACE INTERPRETATION
      </h2>

      {/* 전체 인상 요약 — 항상 선명 */}
      <p className="text-lg leading-relaxed font-serif mb-10">
        {content.overall_impression}
      </p>

      {/* 상세 해석 영역 — 잠금 시 블러 */}
      <div className={locked ? "select-none" : ""}>
        <div className="relative">
          {/* ─── 특징별 해석 카드 ─── */}
          <div className="grid grid-cols-1 gap-0 mb-10">
            {content.feature_interpretations.map((fi, idx) => (
              <div
                key={fi.feature}
                className={`py-5 ${idx < content.feature_interpretations.length - 1 ? "border-b border-[var(--color-border)] border-opacity-40" : ""}`}
              >
                {/* 상단: 라벨 태그 + 값 배지 + P백분위 */}
                <div className="flex items-center gap-2.5 flex-wrap mb-3">
                  {/* 라벨 태그 — 깔끔한 필 스타일 */}
                  <span className="shrink-0 px-2.5 py-1 text-[11px] font-semibold tracking-[1px] border border-[var(--color-fg)] rounded-full">
                    {fi.label}
                  </span>
                  {/* 수치 + 단위 — 아웃라인 배지 (대비 보장) */}
                  <span className="px-2 py-0.5 text-[13px] font-semibold tabular-nums text-[var(--color-fg)] border border-[var(--color-border)] rounded">
                    {formatValue(fi.value, fi.unit)}
                  </span>
                  {/* 범위 라벨 (예: 하위 5%, 상위 38%) */}
                  <span className="text-[11px] text-[var(--color-muted)] tracking-[0.3px]">
                    {fi.range_label}
                  </span>
                </div>

                {/* 분포 위치 바 */}
                {fi.min_label && fi.max_label && (
                  <div className="mb-3">
                    <DistributionBar
                      percentile={fi.percentile}
                      minLabel={fi.min_label}
                      maxLabel={fi.max_label}
                    />
                  </div>
                )}

                {/* 해석 텍스트 — 들여쓰기된 본문 */}
                <p className="text-[13px] leading-relaxed text-[var(--color-fg)] pl-1">
                  {fi.interpretation}
                </p>
              </div>
            ))}
          </div>

          {/* ─── 특징적 포인트 ─── */}
          <div className="mb-8">
            <h3 className="text-[11px] font-semibold tracking-[2px] uppercase text-[var(--color-muted)] mb-3">
              DISTINCTIVE POINTS
            </h3>
            <div className="flex flex-wrap gap-2">
              {content.distinctive_points.map((point) => (
                <span
                  key={point}
                  className="px-3 py-1.5 text-[13px] bg-[var(--color-fg)] text-[var(--color-bg)] rounded-full"
                >
                  {point}
                </span>
              ))}
            </div>
          </div>

          {/* ─── 조화 노트 ─── */}
          <div className="pt-5 border-t border-[var(--color-border)]">
            <p className="text-[13px] italic text-[var(--color-muted)] leading-relaxed">
              {content.harmony_note}
            </p>
          </div>

          {/* 블러 오버레이 */}
          {locked && (
            <div className="absolute inset-0 blur-overlay blur-fade-out rounded-lg" />
          )}
        </div>
      </div>
    </section>
  );
}
