// 얼굴 구조 분석 섹션 (항상 공개)
// 얼굴형 시각 아이콘 + 비율 표시 + 특징 태그

interface FaceStructureContent {
  face_type: string;
  ratio: string;
  features: string[];
}

interface FaceStructureProps {
  content: FaceStructureContent;
  locked: boolean;
}

// 얼굴형 → SVG 아이콘 (간단한 실루엣)
function FaceShapeIcon({ shape }: { shape: string }) {
  // 얼굴형별 SVG path — 미니멀 라인 드로잉
  const paths: Record<string, string> = {
    "타원형": "M50 10 C70 10 85 25 88 45 C90 65 80 85 65 92 C55 96 45 96 35 92 C20 85 10 65 12 45 C15 25 30 10 50 10Z",
    "둥근형": "M50 12 C72 12 88 28 88 50 C88 72 72 88 50 88 C28 88 12 72 12 50 C12 28 28 12 50 12Z",
    "사각형": "M20 15 L80 15 C85 15 88 18 88 23 L88 80 C88 85 85 88 80 88 L20 88 C15 88 12 85 12 80 L12 23 C12 18 15 15 20 15Z",
    "하트형": "M50 90 C30 75 10 55 12 35 C14 20 28 12 42 12 C48 12 50 16 50 16 C50 16 52 12 58 12 C72 12 86 20 88 35 C90 55 70 75 50 90Z",
    "긴형": "M50 5 C65 5 78 18 80 35 C82 52 80 70 72 82 C65 92 55 98 50 98 C45 98 35 92 28 82 C20 70 18 52 20 35 C22 18 35 5 50 5Z",
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
      <line x1="50" y1="20" x2="50" y2="80" stroke="currentColor" strokeWidth="0.5" strokeDasharray="2,3" className="text-[var(--color-border)]" />
      <line x1="25" y1="50" x2="75" y2="50" stroke="currentColor" strokeWidth="0.5" strokeDasharray="2,3" className="text-[var(--color-border)]" />
    </svg>
  );
}

// 얼굴 구조 분석
export function FaceStructure({ content }: FaceStructureProps) {
  return (
    <section className="py-10 border-b border-[var(--color-border)]">
      {/* 섹션 헤더 */}
      <h2 className="text-xs font-semibold tracking-[3px] uppercase text-[var(--color-muted)] mb-6">
        FACE STRUCTURE
      </h2>

      {/* 얼굴형 아이콘 + 정보 */}
      <div className="flex items-center gap-6 mb-6">
        <FaceShapeIcon shape={content.face_type} />
        <div>
          <p className="text-2xl font-bold font-serif">{content.face_type}</p>
          <p className="text-sm text-[var(--color-muted)] mt-1">
            비율 {content.ratio}
          </p>
        </div>
      </div>

      {/* 특징 태그 */}
      <div className="flex flex-wrap gap-2">
        {content.features.map((feature) => (
          <span
            key={feature}
            className="px-3 py-1.5 text-sm border border-[var(--color-border)] rounded-full"
          >
            {feature}
          </span>
        ))}
      </div>
    </section>
  );
}
