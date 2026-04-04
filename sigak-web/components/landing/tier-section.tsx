// 티어 소개 섹션 (3번 반복 사용)
// 3열 그리드: 이름 | 서브+가격 | 타겟+설명+CTA

import Link from "next/link";
import { RevealOnScroll } from "@/components/ui/reveal-on-scroll";
import type { Tier } from "@/lib/types/tier";

interface TierSectionProps {
  tier: Tier;
  onStart: (tierId: Tier["id"]) => void;
}

export function TierSection({ tier, onStart }: TierSectionProps) {
  return (
    <RevealOnScroll>
      <section className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-7 md:py-10">
        <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_2fr] gap-3 md:gap-6 items-start">
          {/* 1열: 이름 */}
          <div>
            <h2 className="text-[clamp(18px,2.5vw,28px)] font-extrabold tracking-[1px] leading-[1.3]">
              {tier.nameUp}
            </h2>
          </div>

          {/* 2열: 서브타이틀 + 가격 */}
          <div>
            <p className="font-[family-name:var(--font-serif)] text-[clamp(16px,2vw,24px)] font-normal leading-[1.4]">
              {tier.sub}
            </p>
            <p className="mt-2 font-[family-name:var(--font-serif)] text-[clamp(14px,1.5vw,18px)] font-semibold opacity-50">
              ₩{tier.price.toLocaleString()}
            </p>
          </div>

          {/* 3열: 타겟 + 설명 + CTA */}
          <div>
            <p className="text-[13px] font-semibold opacity-40 mb-2">
              {tier.target}
            </p>
            <p className="text-[15px] leading-[1.7] opacity-70">
              {tier.desc}
            </p>
            <Link
              href={`/start?tier=${tier.id}`}
              className="inline-block mt-4 text-sm font-medium transition-opacity duration-200 hover:opacity-50 no-underline text-[var(--color-fg)]"
              onClick={(e) => {
                e.preventDefault();
                onStart(tier.id);
              }}
            >
              시작하기
            </Link>
          </div>
        </div>
      </section>
    </RevealOnScroll>
  );
}
