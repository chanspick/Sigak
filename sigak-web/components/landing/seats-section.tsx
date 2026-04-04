// 참여자 카운터 섹션
// 단순 참여 현황 표시

import { RevealOnScroll } from "@/components/ui/reveal-on-scroll";

/** 하드코딩 참여자 수 (추후 API 연동) */
const PARTICIPANT_COUNT = 47;

export function SeatsSection() {
  return (
    <RevealOnScroll>
      <section className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-8 md:py-12">
        <div className="flex flex-col items-center text-center">
          <span className="text-[11px] font-semibold tracking-[1.5px] uppercase opacity-40 mb-3">
            현재 참여 현황
          </span>
          <span className="font-[family-name:var(--font-serif)] text-[clamp(48px,6vw,72px)] font-light leading-none">
            {PARTICIPANT_COUNT}
            <span className="font-[family-name:var(--font-sans)] text-base font-normal opacity-40 ml-2">
              명 참여
            </span>
          </span>
          <p className="mt-4 text-[13px] opacity-30">
            지금 바로 AI 자가진단을 시작해보세요
          </p>
        </div>
      </section>
    </RevealOnScroll>
  );
}
