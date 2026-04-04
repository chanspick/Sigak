// 예약 현황 카운터 섹션
// 4열 그리드: 시선/Creator/Wedding/잔여

import { RevealOnScroll } from "@/components/ui/reveal-on-scroll";
import { TIERS } from "@/lib/constants/tiers";
import { bookedByTier, totalRemain, TOTAL_SLOTS } from "@/lib/constants/bookings";

export function SeatsSection() {
  return (
    <RevealOnScroll>
      <section className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-8 md:py-12">
        <div className="grid grid-cols-2 md:grid-cols-4 border border-black/10">
          {/* 티어별 예약 수 */}
          {TIERS.map((tier, index) => (
            <div
              key={tier.id}
              className={`flex flex-col px-7 py-6 border-r border-black/10 ${
                index === TIERS.length - 1 ? "max-md:border-r-0" : ""
              } ${index === 1 ? "max-md:border-r-0" : ""}`}
            >
              <span className="text-[11px] font-semibold tracking-[1px] opacity-40 mb-2.5">
                {tier.name}
              </span>
              <span className="font-[family-name:var(--font-serif)] text-[clamp(32px,4vw,48px)] font-light leading-none">
                {bookedByTier(tier.id)}
                <span className="font-[family-name:var(--font-sans)] text-sm font-normal opacity-40 ml-1">
                  건 예약
                </span>
              </span>
            </div>
          ))}

          {/* 잔여 석 */}
          <div className="flex flex-col px-7 py-6 bg-black/[0.03] border-r-0">
            <span className="text-[11px] font-semibold tracking-[1px] opacity-40 mb-2.5">
              잔여
            </span>
            <span className="font-[family-name:var(--font-serif)] text-[clamp(32px,4vw,48px)] font-light leading-none">
              {totalRemain}
              <span className="font-[family-name:var(--font-sans)] text-sm font-normal opacity-40 ml-1">
                석 / {TOTAL_SLOTS}
              </span>
            </span>
          </div>
        </div>
      </section>
    </RevealOnScroll>
  );
}
