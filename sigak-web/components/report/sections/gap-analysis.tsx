// 추구미 갭 분석 섹션 (standard 잠금)
// 현재→추구 방향을 시각적으로 강하게 표현

import Image from "next/image";

interface GapAnalysisContent {
  current_type: string;
  current_type_id?: number;
  aspiration_type: string;
  aspiration_type_id?: number;
  gap_summary: string;
  direction_items: {
    axis: string;
    label: string;
    from: string;
    to: string;
    recommendation: string;
  }[];
}

interface GapAnalysisProps {
  content: GapAnalysisContent;
  locked: boolean;
}

// 추구미 갭 분석 — 비주얼 방향 시각화
export function GapAnalysis({ content, locked }: GapAnalysisProps) {
  const currentImg = content.current_type_id
    ? `/images/types/type_${content.current_type_id}.jpg`
    : null;
  const aspirationImg = content.aspiration_type_id
    ? `/images/types/type_${content.aspiration_type_id}.jpg`
    : null;

  return (
    <section className="py-10 border-b border-[var(--color-border)]">
      {/* 섹션 헤더 */}
      <h2 className="text-xs font-semibold tracking-[3px] uppercase text-[var(--color-muted)] mb-6">
        GAP ANALYSIS
      </h2>

      {/* 현재 → 추구 비주얼 카드 — 항상 선명 */}
      <div className="flex items-center gap-4 mb-6">
        {/* 현재 유형 */}
        <div className="flex flex-col items-center gap-2 flex-1">
          {currentImg && (
            <div className="w-16 h-20 md:w-20 md:h-24 relative rounded-lg overflow-hidden bg-[var(--color-border)]">
              <Image
                src={currentImg}
                alt={content.current_type}
                fill
                className="object-cover opacity-70"
                sizes="80px"
              />
            </div>
          )}
          <span className="text-xs text-center text-[var(--color-muted)]">현재</span>
          <span className="text-sm font-medium text-center leading-tight">
            {content.current_type}
          </span>
        </div>

        {/* 화살표 */}
        <div className="flex flex-col items-center gap-1 shrink-0 px-2">
          <div className="w-8 md:w-12 h-px bg-[var(--color-fg)]" />
          <span className="text-lg">&rarr;</span>
          <div className="w-8 md:w-12 h-px bg-[var(--color-fg)]" />
        </div>

        {/* 추구 유형 */}
        <div className="flex flex-col items-center gap-2 flex-1">
          {aspirationImg && (
            <div className="w-16 h-20 md:w-20 md:h-24 relative rounded-lg overflow-hidden bg-[var(--color-border)] ring-2 ring-[var(--color-fg)]">
              <Image
                src={aspirationImg}
                alt={content.aspiration_type}
                fill
                className="object-cover"
                sizes="80px"
              />
            </div>
          )}
          <span className="text-xs text-center text-[var(--color-muted)]">추구</span>
          <span className="text-sm font-bold text-center leading-tight">
            {content.aspiration_type}
          </span>
        </div>
      </div>

      {/* 갭 요약 */}
      <p className="text-base leading-relaxed font-serif mb-8">
        {content.gap_summary}
      </p>

      {/* 상세 방향 — 잠금 시 블러 */}
      <div className={locked ? "select-none" : ""}>
        <div className="relative">
          <div className="flex flex-col gap-5">
            {content.direction_items.map((item) => (
              <div
                key={item.axis}
                className="p-4 border border-[var(--color-border)] rounded-lg"
              >
                {/* 축 + 방향 */}
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold tracking-[1px] uppercase text-[var(--color-muted)]">
                    {item.label}
                  </span>
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-[var(--color-muted)]">{item.from}</span>
                    <span className="text-xs">&rarr;</span>
                    <span className="font-semibold">{item.to}</span>
                  </div>
                </div>
                {/* 추천 */}
                <p className="text-sm leading-relaxed">
                  {item.recommendation}
                </p>
              </div>
            ))}
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
