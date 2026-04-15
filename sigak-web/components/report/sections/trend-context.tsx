// 트렌드 컨텍스트 섹션 (full 잠금)
// 무드 매칭 + 트렌드 정합도 + 존별 메이크업 트렌드

interface MatchedMood {
  id: string;
  label_kr: string;
  description: string;
  keywords: string[];
  trend_score: number;
}

interface ActionTrendTag {
  zone: string;
  zone_kr: string;
  rising_top: string[];
  declining_top: string[];
}

interface MakeupTrend {
  zone: string;
  zone_kr: string;
  rising: string[];
  declining: string[];
  summary: string;
}

interface TrendContextContent {
  // v1 호환
  trends?: { title: string; description: string }[];
  // v2 풍부한 데이터
  season?: string;
  season_summary?: string;
  trend_direction?: { shape: number; volume: number; age: number };
  alignment?: string;
  alignment_kr?: string;
  alignment_description?: string;
  matched_mood?: MatchedMood | null;
  action_trend_tags?: ActionTrendTag[];
  makeup_trends?: MakeupTrend[];
}

interface TrendContextProps {
  content: TrendContextContent;
  locked: boolean;
}

// 정합도 배지 스타일
function getAlignmentStyle(alignment: string): string {
  if (alignment === "aligned") return "bg-[var(--color-fg)] text-[var(--color-bg)]";
  if (alignment === "divergent") return "border border-[var(--color-border)] text-[var(--color-muted)]";
  return "border border-[var(--color-border)] text-[var(--color-fg)]";
}

export function TrendContext({ content, locked }: TrendContextProps) {
  const isV2 = !!content.season;

  // v1 폴백: 기존 trends 배열 렌더링
  if (!isV2 && content.trends) {
    return (
      <section className="py-10 border-b border-[var(--color-border)]">
        <h2 className="text-xs font-semibold tracking-[3px] uppercase text-[var(--color-muted)] mb-6">
          TREND CONTEXT
        </h2>
        <div className="flex flex-col gap-6">
          {content.trends.map((trend) => (
            <div key={trend.title}>
              <h3 className="text-lg font-bold font-serif mb-3">{trend.title}</h3>
              <div className={locked ? "select-none" : ""}>
                <div className="relative">
                  <p className="text-sm leading-relaxed text-[var(--color-muted)]">{trend.description}</p>
                  {locked && <div className="absolute inset-0 blur-overlay blur-fade-out" />}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>
    );
  }

  const mood = content.matched_mood;
  const makeupTrends = content.makeup_trends ?? [];

  return (
    <section className="py-10 border-b border-[var(--color-border)]">
      {/* 섹션 헤더 */}
      <div className="flex items-center justify-between mb-8">
        <h2 className="text-[11px] font-semibold tracking-[3px] uppercase text-[var(--color-muted)]">
          TREND CONTEXT
        </h2>
        <span className="text-[10px] tracking-[1.5px] text-[var(--color-muted)] opacity-50">
          {content.season?.replace("_", " ")}
        </span>
      </div>

      {/* ─── 상세 내용 — 잠금 시 블러 ─── */}
      <div className={locked ? "select-none" : ""}>
        <div className="relative">

          {/* 시즌 요약 */}
          <p className="text-[15px] leading-relaxed font-serif mb-8">
            {content.season_summary}
          </p>

          {/* 무드 매칭 + 정합도 */}
          {mood && (
            <div className="p-5 border border-[var(--color-border)] rounded-lg mb-6">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-semibold tracking-[1.5px] uppercase text-[var(--color-muted)]">
                    YOUR MOOD
                  </span>
                  <span className="text-[14px] font-bold">
                    {mood.label_kr}
                  </span>
                </div>
                {content.alignment && (
                  <span className={`px-2 py-0.5 text-[10px] font-medium rounded-full ${getAlignmentStyle(content.alignment)}`}>
                    {content.alignment_kr}
                  </span>
                )}
              </div>
              <p className="text-[13px] leading-relaxed text-[var(--color-muted)] mb-3">
                {mood.description}
              </p>
              {/* 키워드 태그 */}
              <div className="flex flex-wrap gap-1.5">
                {mood.keywords.map((kw) => (
                  <span
                    key={kw}
                    className="px-2 py-0.5 text-[10px] border border-[var(--color-border)] text-[var(--color-muted)] rounded-full"
                  >
                    {kw}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* 정합도 설명 */}
          {content.alignment_description && (
            <p className="text-[13px] leading-relaxed text-[var(--color-muted)] mb-8">
              {content.alignment_description}
            </p>
          )}

          {/* 추천 × 트렌드 사후 태깅 */}
          {content.action_trend_tags && content.action_trend_tags.length > 0 && (
            <div className="mb-8">
              <p className="text-[11px] font-semibold tracking-[1.5px] uppercase text-[var(--color-muted)] mb-3">
                RECOMMENDATION × TREND
              </p>
              <div className="flex flex-col gap-2">
                {content.action_trend_tags.map((tag) => (
                  <div key={tag.zone} className="flex items-start gap-3 text-[13px]">
                    <span className="text-[var(--color-muted)] w-12 shrink-0 text-right">
                      {tag.zone_kr}
                    </span>
                    <div className="flex flex-wrap gap-1">
                      {tag.rising_top.map((r, i) => (
                        <span key={i} className="text-[11px] px-1.5 py-0.5 bg-[var(--color-fg)]/[0.05] rounded">
                          {r}
                        </span>
                      ))}
                      {tag.declining_top.map((d, i) => (
                        <span key={i} className="text-[11px] px-1.5 py-0.5 text-[var(--color-muted)] opacity-50 line-through">
                          {d}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 존별 메이크업 트렌드 요약 */}
          {makeupTrends.length > 0 && (
            <div>
              <p className="text-[11px] font-semibold tracking-[1.5px] uppercase text-[var(--color-muted)] mb-3">
                MAKEUP TRENDS
              </p>
              <div className="flex flex-col gap-3">
                {makeupTrends.map((mt) => (
                  <div key={mt.zone} className="pb-3 border-b border-[var(--color-border)] last:border-0">
                    <span className="text-[12px] font-semibold">{mt.zone_kr}</span>
                    <div className="flex flex-wrap gap-1 mt-1.5">
                      {mt.rising.map((r, i) => (
                        <span key={i} className="text-[10px] px-1.5 py-0.5 border border-[var(--color-border)] rounded-full">
                          {r}
                        </span>
                      ))}
                      {mt.declining.map((d, i) => (
                        <span key={i} className="text-[10px] px-1.5 py-0.5 text-[var(--color-muted)] opacity-40 line-through">
                          {d}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 블러 오버레이 */}
          {locked && <div className="absolute inset-0 blur-overlay blur-fade-out" />}
        </div>
      </div>
    </section>
  );
}
