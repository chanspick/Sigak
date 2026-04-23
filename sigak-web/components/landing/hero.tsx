// 히어로 섹션
// 제목 "당신을 아는 사람들." (serif font), 부제, 시작 링크

import Link from "next/link";
import { RevealOnScroll } from "@/components/ui/reveal-on-scroll";

interface HeroProps {
  onStart: () => void;
}

export function Hero({ onStart }: HeroProps) {
  return (
    <section className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] pt-10 pb-8 md:pt-[60px] md:pb-12">
      <RevealOnScroll>
        <div className="flex flex-col items-start gap-6 md:flex-row md:justify-between md:items-end">
          {/* 왼쪽 텍스트 */}
          <div className="w-full md:max-w-[68%]">
            <h1 className="font-[family-name:var(--font-serif)] text-[clamp(32px,5vw,52px)] font-normal leading-[1.35] tracking-[-0.01em]">
              당신을 아는 사람들.
            </h1>
            <p className="mt-5 text-sm leading-[1.7] opacity-50">
              당신이 온전히 당신일 수 있게.
            </p>
          </div>

          {/* 오른쪽 링크 */}
          <div className="text-left md:text-right md:pb-1">
            <Link
              href="/sia"
              className="text-sm font-medium mb-1.5 transition-opacity duration-200 hover:opacity-60 no-underline text-[var(--color-fg)]"
              onClick={(e) => {
                e.preventDefault();
                onStart();
              }}
            >
              지금 시작하기
            </Link>
            <p className="text-sm opacity-40 mt-1.5">서비스 소개</p>
          </div>
        </div>
      </RevealOnScroll>
    </section>
  );
}
