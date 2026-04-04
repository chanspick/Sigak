// 히어로 섹션
// 제목 "당신을 아는 사람들." (serif font), 부제, 예약 링크

import { RevealOnScroll } from "@/components/ui/reveal-on-scroll";

interface HeroProps {
  onBook: () => void;
}

export function Hero({ onBook }: HeroProps) {
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
            <p
              className="text-sm font-medium cursor-pointer mb-1.5 transition-opacity duration-200 hover:opacity-60"
              onClick={onBook}
            >
              → 예약하기
            </p>
            <p className="text-sm opacity-40">↓ 서비스 소개</p>
          </div>
        </div>
      </RevealOnScroll>
    </section>
  );
}
