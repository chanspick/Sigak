// 피부톤 분석 섹션 (standard 잠금)
// 블러 시: "웜톤 · 밝은 편" 선명, 분석 텍스트/컬러 블러
// 공개 시: tone, brightness, recommended/avoid colors 전체 표시

interface SkinAnalysisContent {
  tone: string;
  brightness: string;
  recommended_colors: string[];
  avoid_colors: string[];
}

interface SkinAnalysisProps {
  content: SkinAnalysisContent;
  locked: boolean;
}

// 피부톤 분석 - 톤, 밝기, 추천/비추천 컬러 표시
export function SkinAnalysis({ content, locked }: SkinAnalysisProps) {
  return (
    <section className="py-10 border-b border-[var(--color-border)]">
      {/* 섹션 헤더 */}
      <h2 className="text-xs font-semibold tracking-[3px] uppercase text-[var(--color-muted)] mb-6">
        SKIN ANALYSIS
      </h2>

      {/* 티저 헤드라인 - 항상 선명하게 표시 (블러 위) */}
      <p className="text-2xl font-bold font-serif mb-6">
        {content.tone} &middot; {content.brightness}
      </p>

      {/* 상세 분석 내용 - 잠금 시 블러 처리 */}
      <div className={locked ? "select-none" : ""}>
        <div className="relative">
          {/* 추천 컬러 */}
          <div className="mb-4">
            <h3 className="text-sm font-semibold mb-2">추천 컬러</h3>
            <div className="flex flex-wrap gap-2">
              {content.recommended_colors.map((color) => (
                <span
                  key={color}
                  className="px-3 py-1.5 text-sm bg-[var(--color-fg)] text-[var(--color-bg)] rounded-full"
                >
                  {color}
                </span>
              ))}
            </div>
          </div>

          {/* 피해야 할 컬러 */}
          <div>
            <h3 className="text-sm font-semibold mb-2">피해야 할 컬러</h3>
            <div className="flex flex-wrap gap-2">
              {content.avoid_colors.map((color) => (
                <span
                  key={color}
                  className="px-3 py-1.5 text-sm border border-[var(--color-border)] rounded-full text-[var(--color-muted)]"
                >
                  {color}
                </span>
              ))}
            </div>
          </div>

          {/* 블러 오버레이 - 상세 내용만 덮음 */}
          {locked && (
            <div className="absolute inset-0 blur-overlay blur-fade-out" />
          )}
        </div>
      </div>
    </section>
  );
}
