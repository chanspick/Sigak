// 얼굴 구조 심층 해석 섹션 (standard 잠금)
// 블러 시: overall_impression 선명, 상세 해석 블러
// 공개 시: 전체 해석 + 특징 카드 + 하모니 노트 표시

interface FeatureInterpretation {
  feature: string;
  label: string;
  interpretation: string;
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

// 얼굴 구조 심층 해석 - LLM이 raw 수치를 자연어로 해석한 결과
export function FaceInterpretation({ content, locked }: FaceInterpretationProps) {
  return (
    <section className="py-10 border-b border-[var(--color-border)]">
      {/* 섹션 헤더 */}
      <h2 className="text-xs font-semibold tracking-[3px] uppercase text-[var(--color-muted)] mb-6">
        FACE INTERPRETATION
      </h2>

      {/* 전체 인상 요약 - 항상 선명 */}
      <p className="text-lg leading-relaxed font-serif mb-8">
        {content.overall_impression}
      </p>

      {/* 상세 해석 영역 - 잠금 시 블러 */}
      <div className={locked ? "select-none" : ""}>
        <div className="relative">
          {/* 특징별 해석 카드 */}
          <div className="grid grid-cols-1 gap-4 mb-8">
            {content.feature_interpretations.map((fi) => (
              <div
                key={fi.feature}
                className="flex gap-4 items-start"
              >
                {/* 라벨 태그 */}
                <span className="shrink-0 mt-0.5 px-2.5 py-1 text-xs font-semibold tracking-[1px] border border-[var(--color-fg)] rounded-full">
                  {fi.label}
                </span>
                {/* 해석 텍스트 */}
                <p className="text-sm leading-relaxed text-[var(--color-fg)]">
                  {fi.interpretation}
                </p>
              </div>
            ))}
          </div>

          {/* 특징적 포인트 */}
          <div className="mb-6">
            <h3 className="text-xs font-semibold tracking-[2px] uppercase text-[var(--color-muted)] mb-3">
              DISTINCTIVE POINTS
            </h3>
            <div className="flex flex-wrap gap-2">
              {content.distinctive_points.map((point) => (
                <span
                  key={point}
                  className="px-3 py-1.5 text-sm bg-[var(--color-fg)] text-[var(--color-bg)] rounded-full"
                >
                  {point}
                </span>
              ))}
            </div>
          </div>

          {/* 조화 노트 */}
          <div className="pt-4 border-t border-[var(--color-border)]">
            <p className="text-sm italic text-[var(--color-muted)] leading-relaxed">
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
