// 트렌드 컨텍스트 섹션 (full 잠금)
// 블러 시: 제목만 선명, 나머지 전부 블러
// 공개 시: trends with title and description 전체 표시

interface TrendItem {
  title: string;
  description: string;
}

interface TrendContextContent {
  trends: TrendItem[];
}

interface TrendContextProps {
  content: TrendContextContent;
  locked: boolean;
}

// 트렌드 컨텍스트 - 최신 트렌드 분석 결과 표시
export function TrendContext({ content, locked }: TrendContextProps) {
  return (
    <section className="py-10 border-b border-[var(--color-border)]">
      {/* 섹션 헤더 */}
      <h2 className="text-xs font-semibold tracking-[3px] uppercase text-[var(--color-muted)] mb-6">
        TREND CONTEXT
      </h2>

      {/* 트렌드 목록 */}
      <div className="flex flex-col gap-6">
        {content.trends.map((trend) => (
          <div key={trend.title}>
            {/* 트렌드 제목 - 항상 선명 (블러 위) */}
            <h3 className="text-lg font-bold font-serif mb-3">
              {trend.title}
            </h3>

            {/* 트렌드 설명 - 잠금 시 블러 처리 */}
            <div className={locked ? "select-none" : ""}>
              <div className="relative">
                <p className="text-sm leading-relaxed text-[var(--color-muted)]">
                  {trend.description}
                </p>

                {/* 블러 오버레이 - 설명만 덮음 */}
                {locked && (
                  <div className="absolute inset-0 blur-overlay blur-fade-out" />
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
