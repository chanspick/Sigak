// CTA 섹션
// 가운데 정렬 "지금 시작하기" 대형 텍스트, 클릭 시 /start 이동

import Link from "next/link";
import { RevealOnScroll } from "@/components/ui/reveal-on-scroll";

interface CtaSectionProps {
  onStart: () => void;
}

export function CtaSection({ onStart }: CtaSectionProps) {
  return (
    <RevealOnScroll>
      <section className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-10 md:py-14 text-center">
        <Link
          href="/sia"
          className="text-[clamp(24px,4vw,40px)] font-bold tracking-[1px] transition-opacity duration-200 hover:opacity-50 no-underline text-[var(--color-fg)]"
          onClick={(e) => {
            e.preventDefault();
            onStart();
          }}
        >
          지금 시작하기
        </Link>
      </section>
    </RevealOnScroll>
  );
}
