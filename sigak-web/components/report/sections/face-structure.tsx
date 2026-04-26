// 얼굴 구조 분석 섹션: FREE 영역 + STANDARD 잠금 영역
// 프리미엄 컨설팅 리포트 스타일: 정량 메트릭 + 분포 바 + 맥락 텍스트 + 심층 해석

import { DistributionBar } from "@/components/report/charts/distribution-bar";

interface FaceMetric {
  key: string;
  label: string;
  value: number;
  unit: string;
  percentile: number;
  context: string;
  min_label?: string;
  max_label?: string;
  show_numeric_value?: boolean;
  context_label?: string;
}

interface FeatureInterpretation {
  feature: string;
  label: string;
  value: number;
  unit: string;
  percentile: number;
  range_label: string;
  interpretation: string;
  min_label?: string;
  max_label?: string;
  show_numeric_value?: boolean;
  context_label?: string;
}

interface FaceStructureContent {
  // FREE 영역
  face_type: string;
  face_length_ratio: number;
  jaw_angle: number;
  symmetry_label?: string;
  golden_ratio_label?: string;
  metrics: FaceMetric[];

  // STANDARD 영역 (기존 face_interpretation 데이터)
  overall_impression?: string;
  feature_interpretations?: FeatureInterpretation[];
  harmony_note?: string;
  distinctive_points?: string[];
  interpretation_unlock_level?: string;
}

interface FaceStructureProps {
  content: FaceStructureContent;
  locked: boolean;
}

// 얼굴형 → SVG 아이콘 (미니멀 라인 드로잉)
function FaceShapeIcon({ shape }: { shape: string }) {
  const paths: Record<string, string> = {
    "타원형":
      "M50 10 C70 10 85 25 88 45 C90 65 80 85 65 92 C55 96 45 96 35 92 C20 85 10 65 12 45 C15 25 30 10 50 10Z",
    "둥근형":
      "M50 12 C72 12 88 28 88 50 C88 72 72 88 50 88 C28 88 12 72 12 50 C12 28 28 12 50 12Z",
    "각진형":
      "M20 15 L80 15 C85 15 88 18 88 23 L88 80 C88 85 85 88 80 88 L20 88 C15 88 12 85 12 80 L12 23 C12 18 15 15 20 15Z",
    "하트형":
      "M50 90 C30 75 10 55 12 35 C14 20 28 12 42 12 C48 12 50 16 50 16 C50 16 52 12 58 12 C72 12 86 20 88 35 C90 55 70 75 50 90Z",
    "긴형":
      "M50 5 C65 5 78 18 80 35 C82 52 80 70 72 82 C65 92 55 98 50 98 C45 98 35 92 28 82 C20 70 18 52 20 35 C22 18 35 5 50 5Z",
    "역삼각형":
      "M50 10 C65 10 78 15 85 28 C88 35 86 42 80 48 C72 55 60 62 50 90 C40 62 28 55 20 48 C14 42 12 35 15 28 C22 15 35 10 50 10Z",
    "다이아몬드형":
      "M50 8 C58 8 72 25 82 45 C88 55 85 60 78 65 C68 72 58 88 50 92 C42 88 32 72 22 65 C15 60 12 55 18 45 C28 25 42 8 50 8Z",
  };
  const d = paths[shape] ?? paths["타원형"];

  return (
    <svg viewBox="0 0 100 100" className="w-16 h-16 md:w-20 md:h-20">
      <path
        d={d}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        className="text-[var(--color-fg)]"
      />
      {/* 중심선 */}
      <line
        x1="50"
        y1="20"
        x2="50"
        y2="80"
        stroke="currentColor"
        strokeWidth="0.5"
        strokeDasharray="2,3"
        className="text-[var(--color-line)]"
      />
      <line
        x1="25"
        y1="50"
        x2="75"
        y2="50"
        stroke="currentColor"
        strokeWidth="0.5"
        strokeDasharray="2,3"
        className="text-[var(--color-line)]"
      />
    </svg>
  );
}

// "상위 X%", "하위 X%", "P45" 등 백분위 텍스트 제거 (Fix #12)
function stripPercentileText(text: string): string {
  return text
    .replace(/[상하]위\s*\d+(\.\d+)?%/g, "")
    .replace(/P\d+/g, "")
    .replace(/\s{2,}/g, " ")
    .trim();
}

// 얼굴 구조 분석 — 프리미엄 레이아웃 (FREE + STANDARD 통합)
export function FaceStructure({ content, locked }: FaceStructureProps) {
  return (
    <section className="py-10 border-b border-[var(--color-line)]">
      {/* 섹션 헤더 */}
      <h2 className="text-[11px] font-semibold tracking-[3px] uppercase text-[var(--color-muted)] mb-8">
        FACE STRUCTURE
      </h2>

      {/* ═══════════════════════════════════════════════ */}
      {/*  FREE 영역 — 항상 표시                          */}
      {/* ═══════════════════════════════════════════════ */}

      {/* 얼굴형 아이콘 + 요약 정보 */}
      <div className="flex items-center gap-6 mb-10">
        <FaceShapeIcon shape={content.face_type} />
        <div>
          <p className="text-2xl font-bold font-serif">
            {content.face_type}
          </p>
          <div className="flex gap-5 mt-2 text-[13px] text-[var(--color-muted)]">
            {content.symmetry_label && (
              <span className="font-semibold text-[var(--color-fg)] text-[14px]">
                {content.symmetry_label}
              </span>
            )}
            {content.golden_ratio_label && (
              <span className="font-semibold text-[var(--color-fg)] text-[14px]">
                {content.golden_ratio_label}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* ─── 전체 인상 요약 — 항상 표시 ─── */}
      {content.overall_impression && (
        <p className="text-lg leading-relaxed font-serif mb-10">
          {content.overall_impression}
        </p>
      )}

      {/* ─── 피처별 통합 카드: 분포바(FREE) + 해석(STANDARD) ─── */}
      {content.feature_interpretations && content.feature_interpretations.length > 0 && (
        <div className="flex flex-col gap-0">
          {content.feature_interpretations.map((fi, idx) => (
            <div
              key={fi.feature}
              className={`py-5 ${idx < (content.feature_interpretations?.length ?? 0) - 1 ? "border-b border-[var(--color-line)] border-opacity-40" : ""}`}
            >
              {/* 라벨 */}
              <div className="mb-2">
                <span className="text-[13px] font-medium text-[var(--color-fg)] tracking-[0.3px]">
                  {fi.label}
                </span>
              </div>

              {/* 분포 바 — 항상 표시 (FREE) */}
              {fi.min_label && fi.max_label && (
                <div className="mb-3">
                  <DistributionBar
                    percentile={fi.percentile}
                    minLabel={fi.min_label}
                    maxLabel={fi.max_label}
                  />
                </div>
              )}

              {/* 해석 텍스트 — 잠금 시 블러 (STANDARD) */}
              <div className={locked ? "select-none relative" : ""}>
                <p className="text-[13px] leading-relaxed text-[var(--color-muted)]">
                  {fi.interpretation}
                </p>
                {locked && idx === 0 && (
                  <div className="absolute inset-0 blur-overlay blur-fade-out rounded" />
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ─── 특징적 포인트 ─── */}
      {content.distinctive_points && content.distinctive_points.length > 0 && (
        <div className={`mt-8 mb-8 ${locked ? "select-none relative" : ""}`}>
          <h3 className="text-[11px] font-semibold tracking-[2px] uppercase text-[var(--color-muted)] mb-3">
            DISTINCTIVE POINTS
          </h3>
          <div className="flex flex-wrap gap-2">
            {content.distinctive_points.map((point) => (
              <span
                key={point}
                className="px-3 py-1.5 text-[13px] bg-[var(--color-fg)] text-[var(--color-bg)] rounded-full"
              >
                {point}
              </span>
            ))}
          </div>
          {locked && (
            <div className="absolute inset-0 blur-overlay blur-fade-out rounded-lg" />
          )}
        </div>
      )}

      {/* ─── 조화 노트 ─── */}
      {content.harmony_note && (
        <div className={`pt-5 border-t border-[var(--color-line)] ${locked ? "select-none relative" : ""}`}>
          <p className="text-[13px] italic text-[var(--color-muted)] leading-relaxed">
            {content.harmony_note}
          </p>
          {locked && (
            <div className="absolute inset-0 blur-overlay blur-fade-out rounded-lg" />
          )}
        </div>
      )}
    </section>
  );
}
