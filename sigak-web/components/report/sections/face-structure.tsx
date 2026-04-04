// 얼굴 구조 분석 섹션 (항상 공개)

interface FaceStructureContent {
  face_type: string;
  ratio: string;
  features: string[];
}

interface FaceStructureProps {
  content: FaceStructureContent;
  locked: boolean;
}

// 얼굴 구조 분석 - 얼굴형, 비율, 특징 리스트 표시
export function FaceStructure({ content }: FaceStructureProps) {
  return (
    <section className="py-10 border-b border-[var(--color-border)]">
      {/* 섹션 헤더 */}
      <h2 className="text-xs font-semibold tracking-[3px] uppercase text-[var(--color-muted)] mb-6">
        FACE STRUCTURE
      </h2>

      {/* 얼굴형 + 비율 */}
      <div className="flex items-baseline gap-4 mb-6">
        <span className="text-2xl font-bold font-serif">
          {content.face_type}
        </span>
        <span className="text-sm text-[var(--color-muted)]">
          비율 {content.ratio}
        </span>
      </div>

      {/* 특징 리스트 */}
      <ul className="flex flex-col gap-2">
        {content.features.map((feature) => (
          <li
            key={feature}
            className="flex items-center gap-2 text-sm"
          >
            {/* 불릿 포인트 */}
            <span className="w-1 h-1 rounded-full bg-[var(--color-fg)] shrink-0" />
            {feature}
          </li>
        ))}
      </ul>
    </section>
  );
}
