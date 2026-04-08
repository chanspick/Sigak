// 피부톤 분석 섹션 (standard 잠금)
// v2: undertone × chroma 6타입 — 실제 피부색 샘플 + 구조화된 추천/회피 팔레트

interface ColorItem {
  name: string;
  hex: string;
  usage?: string;
}

interface SkinAnalysisContent {
  tone: string;
  tone_description: string;
  hex_sample: string;
  recommended: ColorItem[];
  avoid: ColorItem[];
  avoid_reason: string;
}

interface SkinAnalysisProps {
  content: SkinAnalysisContent;
  locked: boolean;
}

export function SkinAnalysis({ content, locked }: SkinAnalysisProps) {
  return (
    <section className="py-10 border-b border-[var(--color-border)]">
      {/* 섹션 헤더 */}
      <h2 className="text-xs font-semibold tracking-[3px] uppercase text-[var(--color-muted)] mb-6">
        SKIN TONE
      </h2>

      {/* 유저 피부색 샘플 + 타입 라벨 */}
      <div className="flex items-center gap-4 mb-4">
        <div
          className="w-12 h-12 rounded-full border-2 border-[var(--color-border)] shadow-sm"
          style={{ backgroundColor: content.hex_sample || "#D4A574" }}
        />
        <div>
          <p className="text-2xl font-bold font-serif">{content.tone}</p>
          {content.tone_description && (
            <p className="text-[13px] text-[var(--color-muted)] mt-1 leading-relaxed">
              {content.tone_description}
            </p>
          )}
        </div>
      </div>

      {/* 컬러 팔레트 — 잠금 시 블러 */}
      <div className={locked ? "select-none" : ""}>
        <div className="relative">
          {/* 추천 컬러 */}
          <div className="mb-6">
            <h3 className="text-xs font-semibold tracking-[2px] uppercase text-[var(--color-muted)] mb-3">
              어울리는 색
            </h3>
            <div className="flex flex-wrap gap-3">
              {(content.recommended ?? []).map((c) => (
                <div key={c.name} className="flex flex-col items-center gap-1.5">
                  <div
                    className="w-12 h-12 rounded-full shadow-sm border border-white/20"
                    style={{ backgroundColor: c.hex }}
                  />
                  <span className="text-[11px] font-medium text-[var(--color-fg)]">
                    {c.name}
                  </span>
                  {c.usage && (
                    <span className="text-[9px] px-1.5 py-0.5 rounded-full border border-[var(--color-border)] text-[var(--color-muted)]">
                      {c.usage}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* 피해야 할 컬러 */}
          <div>
            <h3 className="text-xs font-semibold tracking-[2px] uppercase text-[var(--color-muted)] mb-3">
              주의하면 좋은 색
            </h3>
            <div className="flex flex-wrap gap-3">
              {(content.avoid ?? []).map((c) => (
                <div key={c.name} className="flex flex-col items-center gap-1.5">
                  <div className="relative">
                    <div
                      className="w-12 h-12 rounded-full opacity-50 border border-[var(--color-border)]"
                      style={{ backgroundColor: c.hex }}
                    />
                    <div className="absolute inset-0 flex items-center justify-center text-[var(--color-danger)] text-lg font-bold">
                      ✕
                    </div>
                  </div>
                  <span className="text-[11px] text-[var(--color-muted)]">{c.name}</span>
                </div>
              ))}
            </div>
            {/* 회피 이유 */}
            {content.avoid_reason && (
              <p className="text-[12px] text-[var(--color-muted)] mt-3 leading-relaxed italic">
                {content.avoid_reason}
              </p>
            )}
          </div>

          {/* 블러 오버레이 */}
          {locked && (
            <div className="absolute inset-0 blur-overlay blur-fade-out" />
          )}
        </div>
      </div>
    </section>
  );
}
