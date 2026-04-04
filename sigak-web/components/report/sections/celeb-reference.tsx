// 셀럽 레퍼런스 섹션 (full 잠금)
// 블러 시: "수지와 85% 유사" 선명, 이유/스타일링 블러
// 공개 시: celeb, similarity, reasons, styling_tips 전체 표시

interface CelebReferenceContent {
  celeb: string;
  similarity: number;
  reasons: string[];
  styling_tips: string[];
}

interface CelebReferenceProps {
  content: CelebReferenceContent;
  locked: boolean;
}

// 셀럽 레퍼런스 - 유사 셀럽 분석 결과와 스타일링 팁 표시
export function CelebReference({ content, locked }: CelebReferenceProps) {
  return (
    <section className="py-10 border-b border-[var(--color-border)]">
      {/* 섹션 헤더 */}
      <h2 className="text-xs font-semibold tracking-[3px] uppercase text-[var(--color-muted)] mb-6">
        CELEB REFERENCE
      </h2>

      {/* 티저 헤드라인 - 항상 선명 (블러 위) */}
      <p className="text-2xl font-bold font-serif mb-6">
        {content.celeb}와 {content.similarity}% 유사
      </p>

      {/* 상세 내용 - 잠금 시 블러 처리 */}
      <div className={locked ? "select-none" : ""}>
        <div className="relative">
          {/* 유사 이유 */}
          <div className="mb-6">
            <h3 className="text-sm font-semibold mb-2">유사 포인트</h3>
            <ul className="flex flex-col gap-1.5">
              {content.reasons.map((reason) => (
                <li
                  key={reason}
                  className="flex items-start gap-2 text-sm leading-relaxed"
                >
                  <span className="w-1 h-1 rounded-full bg-[var(--color-fg)] mt-2 shrink-0" />
                  {reason}
                </li>
              ))}
            </ul>
          </div>

          {/* 스타일링 팁 */}
          <div>
            <h3 className="text-sm font-semibold mb-2">스타일링 팁</h3>
            <ul className="flex flex-col gap-1.5">
              {content.styling_tips.map((tip) => (
                <li
                  key={tip}
                  className="flex items-start gap-2 text-sm leading-relaxed"
                >
                  <span className="w-1 h-1 rounded-full bg-[var(--color-fg)] mt-2 shrink-0" />
                  {tip}
                </li>
              ))}
            </ul>
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
