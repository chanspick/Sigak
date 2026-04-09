// 유형 매칭 섹션 (full 잠금)
// AI 유형 이미지 + 유사도 바 + 상세 분석
// 가장 시각적 임팩트가 큰 섹션

import Image from "next/image";

interface RunnerUp {
  type_name: string;
  type_id: number;
  similarity: number;
}

interface TypeReferenceContent {
  type_name: string;
  type_id: number;
  similarity: number;
  reasons: string[];
  styling_tips: string[];
  runner_ups: RunnerUp[];
}

interface TypeReferenceProps {
  content: TypeReferenceContent;
  locked: boolean;
}

// 유형 매칭 — AI 이미지 + 유사도 시각화
export function TypeReference({ content, locked }: TypeReferenceProps) {
  const typeIdToImg = (id: number) => {
    if (id >= 11 && id <= 18) return `/images/types/type_${id - 10}m.jpg`;
    return `/images/types/type_${id}.jpg`;
  };
  const mainImageSrc = typeIdToImg(content.type_id);

  return (
    <section className="py-10 border-b border-[var(--color-border)]">
      {/* 섹션 헤더 */}
      <h2 className="text-xs font-semibold tracking-[3px] uppercase text-[var(--color-muted)] mb-6">
        TYPE MATCH
      </h2>

      {/* 메인 매칭: 이미지 + 라벨 — 항상 선명 */}
      <div className="flex gap-6 mb-6">
        {/* AI 유형 이미지 */}
        <div className="shrink-0 w-28 h-36 md:w-36 md:h-44 relative rounded-lg overflow-hidden bg-[var(--color-border)]">
          <Image
            src={mainImageSrc}
            alt={`${content.type_name} 유형 레퍼런스`}
            fill
            className="object-cover"
            sizes="(max-width: 768px) 112px, 144px"
          />
        </div>

        {/* 유형 정보 */}
        <div className="flex flex-col justify-center flex-1 min-w-0">
          <p className="text-xs text-[var(--color-muted)] mb-1">
            Type {content.type_id}
          </p>
          <p className="text-2xl font-bold font-serif mb-3 leading-tight">
            &lsquo;{content.type_name}&rsquo;
          </p>
          {/* 유사도 */}
          <div className="flex items-center gap-3">
            <div className="flex-1 h-2 bg-[var(--color-border)] rounded-full overflow-hidden">
              <div
                className="h-full bg-[var(--color-fg)] rounded-full transition-all duration-700"
                style={{ width: `${content.similarity}%` }}
              />
            </div>
            <span className="text-lg font-bold tabular-nums">
              {content.similarity}%
            </span>
          </div>
        </div>
      </div>

      {/* 상세 내용 — 잠금 시 블러 */}
      <div className={locked ? "select-none" : ""}>
        <div className="relative">
          {/* 유사 이유 */}
          <div className="mb-6">
            <h3 className="text-xs font-semibold tracking-[2px] uppercase text-[var(--color-muted)] mb-3">
              WHY THIS TYPE
            </h3>
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

          {/* 스타일링 방향 */}
          <div className="mb-8">
            <h3 className="text-xs font-semibold tracking-[2px] uppercase text-[var(--color-muted)] mb-3">
              STYLING DIRECTION
            </h3>
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

          {/* Runner-ups — 미니 이미지 + 바 */}
          {content.runner_ups && content.runner_ups.length > 0 && (
            <div className="pt-6 border-t border-[var(--color-border)]">
              <h3 className="text-xs font-semibold tracking-[2px] uppercase text-[var(--color-muted)] mb-4">
                ALSO SIMILAR
              </h3>
              <div className="flex flex-col gap-4">
                {content.runner_ups.map((ru) => (
                  <div
                    key={ru.type_id}
                    className="flex items-center gap-3"
                  >
                    {/* 미니 이미지 */}
                    <div className="shrink-0 w-10 h-10 relative rounded-full overflow-hidden bg-[var(--color-border)]">
                      <Image
                        src={typeIdToImg(ru.type_id)}
                        alt={ru.type_name}
                        fill
                        className="object-cover"
                        sizes="40px"
                      />
                    </div>
                    <span className="text-sm font-medium flex-1 min-w-0 truncate">
                      {ru.type_name}
                    </span>
                    <div className="flex items-center gap-2 shrink-0">
                      <div className="w-16 h-1.5 bg-[var(--color-border)] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-[var(--color-muted)] rounded-full"
                          style={{ width: `${ru.similarity}%` }}
                        />
                      </div>
                      <span className="text-xs text-[var(--color-muted)] tabular-nums w-8 text-right">
                        {ru.similarity}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 블러 오버레이 */}
          {locked && (
            <div className="absolute inset-0 blur-overlay blur-fade-out" />
          )}
        </div>
      </div>
    </section>
  );
}
