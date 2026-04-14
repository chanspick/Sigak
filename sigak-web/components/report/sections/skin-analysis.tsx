// 퍼스널컬러 분석 섹션 (standard 잠금)
// v3: BEST/OK/AVOID 3단계 팔레트 + 활용 가이드 + 헤어컬러 추천

interface ColorItem {
  name: string;
  hex: string;
  usage?: string;
  why?: string;
}

interface HairColor {
  name: string;
  hex: string;
  why: string;
}

interface SkinAnalysisContent {
  tone: string;
  tone_description: string;
  hex_sample: string;
  // 3단계 팔레트
  best_colors?: ColorItem[];
  okay_colors?: ColorItem[];
  avoid_colors?: ColorItem[];
  // 하위호환
  recommended?: ColorItem[];
  avoid?: ColorItem[];
  avoid_reason?: string;
  // 헤어컬러
  hair_colors?: HairColor[];
  // 활용 가이드
  lip_direction?: string;
  cheek_direction?: string;
  eye_direction?: string;
  foundation_guide?: string;
}

interface SkinAnalysisProps {
  content: SkinAnalysisContent;
  locked: boolean;
}

export function SkinAnalysis({ content, locked }: SkinAnalysisProps) {
  const best = content.best_colors ?? content.recommended ?? [];
  const okay = content.okay_colors ?? [];
  const avoid = content.avoid_colors ?? content.avoid ?? [];
  const hairColors = content.hair_colors ?? [];
  const hasGuide = content.lip_direction || content.cheek_direction || content.eye_direction || content.foundation_guide;

  return (
    <section className="py-10 border-b border-[var(--color-border)]">
      {/* 섹션 헤더 */}
      <h2 className="text-xs font-semibold tracking-[3px] uppercase text-[var(--color-muted)] mb-6">
        PERSONAL COLOR
      </h2>

      {/* 피부색 샘플 + 타입 */}
      <div className="flex items-center gap-4 mb-8">
        <div
          className="w-14 h-14 rounded-full border-2 border-[var(--color-border)] shadow-sm shrink-0"
          style={{ backgroundColor: content.hex_sample || "#D4A574" }}
        />
        <div>
          <p className="font-[family-name:var(--font-serif)] text-xl font-bold">{content.tone}</p>
          {content.tone_description && (
            <p className="text-[13px] text-[var(--color-muted)] mt-1 leading-relaxed">
              {content.tone_description}
            </p>
          )}
        </div>
      </div>

      {/* 컬러 팔레트 + 가이드 — 잠금 시 블러 */}
      <div className={locked ? "select-none" : ""}>
        <div className="relative">

          {/* ── BEST 컬러 ── */}
          {best.length > 0 && (
            <div className="mb-8">
              <div className="flex items-center gap-2 mb-4">
                <span className="text-[10px] font-bold tracking-[2px] uppercase px-2 py-0.5 bg-[var(--color-fg)] text-[var(--color-bg)]">
                  BEST
                </span>
                <span className="text-[11px] text-[var(--color-muted)]">가장 어울리는 색</span>
              </div>
              <div className="space-y-3">
                {best.map((c) => (
                  <div key={c.name} className="flex items-start gap-3">
                    <div
                      className="w-10 h-10 rounded-full border border-white/20 shadow-sm shrink-0 mt-0.5"
                      style={{ backgroundColor: c.hex }}
                    />
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[13px] font-medium">{c.name}</span>
                        {c.usage && (
                          <span className="text-[9px] px-1.5 py-0.5 border border-[var(--color-border)] text-[var(--color-muted)]">
                            {c.usage}
                          </span>
                        )}
                      </div>
                      {c.why && (
                        <p className="text-[11px] text-[var(--color-muted)] mt-0.5 leading-relaxed">{c.why}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── OK 컬러 ── */}
          {okay.length > 0 && (
            <div className="mb-8">
              <div className="flex items-center gap-2 mb-4">
                <span className="text-[10px] font-bold tracking-[2px] uppercase px-2 py-0.5 border border-[var(--color-border)]">
                  OK
                </span>
                <span className="text-[11px] text-[var(--color-muted)]">활용할 수 있는 색</span>
              </div>
              <div className="space-y-3">
                {okay.map((c) => (
                  <div key={c.name} className="flex items-start gap-3">
                    <div
                      className="w-10 h-10 rounded-full border border-[var(--color-border)] shadow-sm shrink-0 mt-0.5"
                      style={{ backgroundColor: c.hex }}
                    />
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[13px] font-medium">{c.name}</span>
                        {c.usage && (
                          <span className="text-[9px] px-1.5 py-0.5 border border-[var(--color-border)] text-[var(--color-muted)]">
                            {c.usage}
                          </span>
                        )}
                      </div>
                      {c.why && (
                        <p className="text-[11px] text-[var(--color-muted)] mt-0.5 leading-relaxed">{c.why}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── AVOID 컬러 ── */}
          {avoid.length > 0 && (
            <div className="mb-8">
              <div className="flex items-center gap-2 mb-4">
                <span className="text-[10px] font-bold tracking-[2px] uppercase px-2 py-0.5 bg-[var(--color-danger)]/10 text-[var(--color-danger)]">
                  AVOID
                </span>
                <span className="text-[11px] text-[var(--color-muted)]">피하면 좋은 색</span>
              </div>
              <div className="space-y-3">
                {avoid.map((c) => (
                  <div key={c.name} className="flex items-start gap-3 opacity-60">
                    <div
                      className="w-10 h-10 rounded-full border border-[var(--color-border)] shadow-sm shrink-0 mt-0.5"
                      style={{ backgroundColor: c.hex }}
                    />
                    <div className="min-w-0">
                      <span className="text-[13px] font-medium">{c.name}</span>
                      {c.why && (
                        <p className="text-[11px] text-[var(--color-muted)] mt-0.5 leading-relaxed">{c.why}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── 컬러 활용 가이드 ── */}
          {hasGuide && (
            <div className="mb-8 border-t border-[var(--color-border)] pt-6">
              <h3 className="text-[10px] font-bold tracking-[2px] uppercase text-[var(--color-muted)] mb-4">
                컬러 활용 가이드
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {content.lip_direction && (
                  <GuideItem label="LIP" text={content.lip_direction} />
                )}
                {content.cheek_direction && (
                  <GuideItem label="CHEEK" text={content.cheek_direction} />
                )}
                {content.eye_direction && (
                  <GuideItem label="EYE" text={content.eye_direction} />
                )}
                {content.foundation_guide && (
                  <GuideItem label="BASE" text={content.foundation_guide} />
                )}
              </div>
            </div>
          )}

          {/* ── 추천 헤어컬러 ── */}
          {hairColors.length > 0 && (
            <div className="border-t border-[var(--color-border)] pt-6">
              <h3 className="text-[10px] font-bold tracking-[2px] uppercase text-[var(--color-muted)] mb-4">
                추천 헤어컬러
              </h3>
              <div className="space-y-3">
                {hairColors.map((c, i) => (
                  <div key={c.name} className="flex items-start gap-3">
                    <div className="relative shrink-0 mt-0.5">
                      <div
                        className="w-10 h-10 rounded-full border border-white/20 shadow-sm"
                        style={{ backgroundColor: c.hex }}
                      />
                      {i === 0 && (
                        <span className="absolute -top-1 -right-1 text-[8px] font-bold bg-[var(--color-fg)] text-[var(--color-bg)] w-4 h-4 flex items-center justify-center">
                          1
                        </span>
                      )}
                    </div>
                    <div className="min-w-0">
                      <span className="text-[13px] font-medium">{c.name}</span>
                      <p className="text-[11px] text-[var(--color-muted)] mt-0.5 leading-relaxed">{c.why}</p>
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

// 활용 가이드 아이템
function GuideItem({ label, text }: { label: string; text: string }) {
  return (
    <div className="flex gap-3 items-start">
      <span className="text-[9px] font-bold tracking-[1.5px] text-[var(--color-muted)] w-10 shrink-0 pt-0.5">
        {label}
      </span>
      <p className="text-[12px] leading-relaxed">{text}</p>
    </div>
  );
}
