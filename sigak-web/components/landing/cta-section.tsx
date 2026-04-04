// CTA 섹션
// 가운데 정렬 "→ 예약하기" 대형 텍스트, 클릭 시 예약 오버레이 열기

import { RevealOnScroll } from "@/components/ui/reveal-on-scroll";

interface CtaSectionProps {
  onBook: () => void;
}

export function CtaSection({ onBook }: CtaSectionProps) {
  return (
    <RevealOnScroll>
      <section
        className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-10 md:py-14 text-center cursor-pointer group"
        onClick={onBook}
      >
        <p className="text-[clamp(24px,4vw,40px)] font-bold tracking-[1px] transition-opacity duration-200 group-hover:opacity-50">
          → 예약하기
        </p>
      </section>
    </RevealOnScroll>
  );
}
