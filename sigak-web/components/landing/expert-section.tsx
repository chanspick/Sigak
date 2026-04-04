// 전문가 소개 섹션
// 같은 3열 그리드 구조: 이름 | 역할 | 설명

import { RevealOnScroll } from "@/components/ui/reveal-on-scroll";

interface ExpertSectionProps {
  name: string;
  role: string;
  description: string;
}

export function ExpertSection({ name, role, description }: ExpertSectionProps) {
  return (
    <RevealOnScroll>
      <section className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-7 md:py-10">
        <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_2fr] gap-3 md:gap-6 items-start">
          {/* 1열: 이름 */}
          <div>
            <h2 className="text-[clamp(18px,2.5vw,28px)] font-extrabold tracking-[1px] leading-[1.3]">
              {name}
            </h2>
          </div>

          {/* 2열: 역할 */}
          <div>
            <p className="font-[family-name:var(--font-serif)] text-[clamp(16px,2vw,24px)] font-normal leading-[1.4]">
              {role}
            </p>
          </div>

          {/* 3열: 설명 */}
          <div>
            <p className="text-[15px] leading-[1.7] opacity-70">
              {description}
            </p>
          </div>
        </div>
      </section>
    </RevealOnScroll>
  );
}
