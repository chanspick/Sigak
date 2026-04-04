// 한줄 요약 섹션 (항상 공개)

interface ExecutiveSummaryContent {
  summary: string;
}

interface ExecutiveSummaryProps {
  content: ExecutiveSummaryContent;
  locked: boolean;
}

// 리포트 핵심 한줄 요약 - 전반적인 분석 결과를 한 문장으로 제공
export function ExecutiveSummary({ content }: ExecutiveSummaryProps) {
  return (
    <section className="py-10 border-b border-[var(--color-border)]">
      {/* 섹션 헤더 */}
      <h2 className="text-xs font-semibold tracking-[3px] uppercase text-[var(--color-muted)] mb-4">
        SUMMARY
      </h2>
      {/* 요약 텍스트 */}
      <p className="text-lg leading-relaxed font-serif">
        {content.summary}
      </p>
    </section>
  );
}
