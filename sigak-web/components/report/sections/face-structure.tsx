// 얼굴 구조 분석 섹션 (항상 공개)
// 프리미엄 컨설팅 리포트 스타일: 정량 메트릭 + 분포 바 + 맥락 텍스트

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

interface FaceStructureContent {
  face_type: string;
  face_length_ratio: number;
  jaw_angle: number;
  symmetry_score?: number;
  golden_ratio_score?: number;
  symmetry_label?: string;
  golden_ratio_label?: string;
  metrics: FaceMetric[];
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
    "사각형":
      "M20 15 L80 15 C85 15 88 18 88 23 L88 80 C88 85 85 88 80 88 L20 88 C15 88 12 85 12 80 L12 23 C12 18 15 15 20 15Z",
    "하트형":
      "M50 90 C30 75 10 55 12 35 C14 20 28 12 42 12 C48 12 50 16 50 16 C50 16 52 12 58 12 C72 12 86 20 88 35 C90 55 70 75 50 90Z",
    "긴형":
      "M50 5 C65 5 78 18 80 35 C82 52 80 70 72 82 C65 92 55 98 50 98 C45 98 35 92 28 82 C20 70 18 52 20 35 C22 18 35 5 50 5Z",
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
        className="text-[var(--color-border)]"
      />
      <line
        x1="25"
        y1="50"
        x2="75"
        y2="50"
        stroke="currentColor"
        strokeWidth="0.5"
        strokeDasharray="2,3"
        className="text-[var(--color-border)]"
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

// 수치 포맷 — 정수/소수점 구분
function formatValue(value: number, unit: string): string {
  if (value == null) return "";
  const formatted = value >= 1 ? value.toFixed(1) : value.toFixed(3);
  return `${formatted}${unit}`;
}

// 얼굴 구조 분석 — 프리미엄 레이아웃
export function FaceStructure({ content }: FaceStructureProps) {
  return (
    <section className="py-10 border-b border-[var(--color-border)]">
      {/* 섹션 헤더 */}
      <h2 className="text-[11px] font-semibold tracking-[3px] uppercase text-[var(--color-muted)] mb-8">
        FACE STRUCTURE
      </h2>

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

      {/* ─── 정량 메트릭 리스트 ─── */}
      <div className="flex flex-col">
        {content.metrics.map((metric, idx) => (
          <div
            key={metric.key}
            className={`py-4 ${idx > 0 ? "mt-0" : ""}`}
            style={{
              // 메트릭 사이 미세한 간격 (보더 대신 여백으로 구분)
              paddingTop: idx > 0 ? "16px" : "0",
            }}
          >
            {/* 상단 행: 라벨(좌) + 값 또는 맥락 라벨(우) */}
            <div className="flex items-baseline justify-between mb-2">
              <span className="text-[13px] text-[var(--color-muted)] tracking-[0.3px]">
                {metric.label}
              </span>
              <span className="text-[15px] font-semibold tabular-nums text-[var(--color-fg)]">
                {metric.show_numeric_value !== false
                  ? formatValue(metric.value, metric.unit)
                  : metric.context_label ?? ""}
              </span>
            </div>

            {/* 분포 바 — 전체 폭 */}
            {metric.min_label && metric.max_label && (
              <div className="mb-2">
                <DistributionBar
                  percentile={metric.percentile}
                  minLabel={metric.min_label}
                  maxLabel={metric.max_label}
                />
              </div>
            )}

            {/* 맥락 설명 — 백분위 텍스트 제거 후 표시 (Fix #12) */}
            <p className="text-[11px] text-[var(--color-muted)] leading-relaxed opacity-80">
              {stripPercentileText(metric.context)}
            </p>

            {/* 미세 구분선 (마지막 항목 제외) */}
            {idx < content.metrics.length - 1 && (
              <div className="mt-4 h-px bg-[var(--color-border)] opacity-40" />
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
