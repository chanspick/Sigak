// 피부톤 분석 섹션 (standard 잠금)
// 컬러 스와치 시각화 — 텍스트만 있던 컬러를 실제 색상 원으로 표시

// 추천/비추 컬러 → hex 매핑
const COLOR_MAP: Record<string, string> = {
  // 웜톤 추천
  "코랄": "#FF7F7F",
  "피치": "#FFCBA4",
  "웜베이지": "#D4A76A",
  "살구": "#FBCEB1",
  "테라코타": "#CC5533",
  "골드": "#CFB53B",
  "카멜": "#C19A6B",
  "버건디": "#800020",
  "올리브": "#708238",
  // 쿨톤 추천
  "로즈": "#C08081",
  "라벤더": "#B57EDC",
  "베이비핑크": "#F4C2C2",
  "쿨핑크": "#DB7093",
  "네이비": "#000080",
  "아이시블루": "#A5C8E1",
  "소프트핑크": "#F5B7B1",
  // 비추
  "블루베이스 핑크": "#C8A2C8",
  "쿨그레이": "#9DA3A5",
  "머스타드": "#CE9A00",
  "오렌지": "#FF6600",
  "네온": "#39FF14",
};

function getColorHex(name: string): string {
  return COLOR_MAP[name] ?? "#999999";
}

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

// 피부톤 분석 — 컬러 스와치 시각화
export function SkinAnalysis({ content, locked }: SkinAnalysisProps) {
  return (
    <section className="py-10 border-b border-[var(--color-border)]">
      {/* 섹션 헤더 */}
      <h2 className="text-xs font-semibold tracking-[3px] uppercase text-[var(--color-muted)] mb-6">
        SKIN TONE
      </h2>

      {/* 톤 + 밝기 대형 라벨 — 항상 선명 */}
      <div className="flex items-center gap-3 mb-8">
        <div
          className="w-10 h-10 rounded-full border-2 border-[var(--color-border)]"
          style={{
            background: content.tone === "웜톤"
              ? "linear-gradient(135deg, #FFCBA4, #D4A76A)"
              : content.tone === "쿨톤"
                ? "linear-gradient(135deg, #C8A2C8, #A5C8E1)"
                : "linear-gradient(135deg, #D4C5A9, #B8AFA0)",
          }}
        />
        <div>
          <p className="text-2xl font-bold font-serif">
            {content.tone} &middot; {content.brightness}
          </p>
        </div>
      </div>

      {/* 컬러 팔레트 — 잠금 시 블러 */}
      <div className={locked ? "select-none" : ""}>
        <div className="relative">
          {/* 추천 컬러 스와치 */}
          <div className="mb-6">
            <h3 className="text-xs font-semibold tracking-[2px] uppercase text-[var(--color-muted)] mb-3">
              RECOMMENDED
            </h3>
            <div className="flex flex-wrap gap-3">
              {content.recommended_colors.map((color) => (
                <div key={color} className="flex flex-col items-center gap-1.5">
                  <div
                    className="w-12 h-12 rounded-full shadow-sm border border-white/20"
                    style={{ backgroundColor: getColorHex(color) }}
                  />
                  <span className="text-xs text-[var(--color-muted)]">
                    {color}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* 피해야 할 컬러 */}
          <div>
            <h3 className="text-xs font-semibold tracking-[2px] uppercase text-[var(--color-muted)] mb-3">
              AVOID
            </h3>
            <div className="flex flex-wrap gap-3">
              {content.avoid_colors.map((color) => (
                <div key={color} className="flex flex-col items-center gap-1.5">
                  <div className="relative">
                    <div
                      className="w-12 h-12 rounded-full opacity-40 border border-[var(--color-border)]"
                      style={{ backgroundColor: getColorHex(color) }}
                    />
                    {/* X 표시 */}
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="w-8 h-px bg-[var(--color-danger)] rotate-45 absolute" />
                      <div className="w-8 h-px bg-[var(--color-danger)] -rotate-45 absolute" />
                    </div>
                  </div>
                  <span className="text-xs text-[var(--color-muted)]">
                    {color}
                  </span>
                </div>
              ))}
            </div>
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
