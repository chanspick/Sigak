"use client";

import { useState, useCallback } from "react";
import Image from "next/image";
import Link from "next/link";
import { Nav } from "@/components/landing/nav";
import { Footer } from "@/components/landing/footer";
import { BookingOverlay } from "@/components/landing/booking-overlay";
import { Divider } from "@/components/ui/divider";
import { RevealOnScroll } from "@/components/ui/reveal-on-scroll";
import type { Tier } from "@/lib/types/tier";

// 조각상 데이터
const SCULPTURES = [
  {
    id: "deer",
    number: "01",
    label: "ELEGANCE",
    title: "자연스러운 우아함",
    description:
      "부드러운 곡선과 고요한 시선. 절제된 구조 안에서 피어나는 기품 있는 인상. 사파이어빛 눈과 섬세한 뿔이 만들어내는 조화로운 균형.",
    src: "/images/sculptures/deer.webp",
    alt: "사슴 조각상 - 사파이어 눈, 자연스러운 우아함",
  },
  {
    id: "hawk",
    number: "02",
    label: "BOLD",
    title: "날카로운 존재감",
    description:
      "강렬한 시선과 선명한 윤곽. 도시적 세련미와 대담한 구조가 만들어내는 압도적 인상. 루비빛 눈과 크리스탈이 빚어낸 샤프한 아우라.",
    src: "/images/sculptures/hawk.webp",
    alt: "매 조각상 - 루비 눈, 날카로운 존재감",
  },
  {
    id: "cat",
    number: "03",
    label: "SOFT",
    title: "부드러운 매력",
    description:
      "경쾌한 톤과 자연스러운 곡선. 가볍지만 또렷한 인상이 만들어내는 편안한 호감. 에메랄드빛 눈이 전하는 프레시하고 위트 있는 감성.",
    src: "/images/sculptures/cat.webp",
    alt: "고양이 조각상 - 에메랄드 눈, 부드러운 매력",
  },
  {
    id: "wolf",
    number: "04",
    label: "CHIC",
    title: "성숙한 깊이",
    description:
      "깊은 인상과 볼드한 구조. 시간이 쌓아올린 무게감과 세련된 분위기가 만들어내는 시크한 존재감. 앰버빛 눈과 체인이 상징하는 성숙한 미감.",
    src: "/images/sculptures/wolf.webp",
    alt: "늑대 조각상 - 앰버 눈, 성숙한 깊이",
  },
] as const;

// 프로세스 단계 데이터
const STEPS = [
  {
    number: "01",
    title: "셀카 업로드",
    description:
      "정면 사진 1장과 간단한 설문. 추구하는 이미지, 레퍼런스, 현재 고민을 자유롭게 작성합니다.",
  },
  {
    number: "02",
    title: "AI 좌표 분석",
    description:
      "얼굴 구조, 피부톤, 스타일 취향을 3축 좌표계에 매핑. 트렌드 데이터와 교차 분석합니다.",
  },
  {
    number: "03",
    title: "맞춤 리포트",
    description:
      "현재 위치에서 추구미까지의 구체적 경로. 메이크업, 헤어, 스타일링 실행 가이드를 제공합니다.",
  },
] as const;

export default function HomePage() {
  const [overlayOpen, setOverlayOpen] = useState(false);
  const [overlayTier, setOverlayTier] = useState<Tier["id"] | null>(null);

  const book = useCallback((tierId?: Tier["id"]) => {
    setOverlayTier(tierId ?? null);
    setOverlayOpen(true);
  }, []);

  return (
    <div className="min-h-screen bg-[var(--color-bg)] text-[var(--color-fg)]">
      {/* NAV */}
      <Nav onBook={() => book()} />

      {/* HERO */}
      <section className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] pt-10 pb-8 md:pt-[60px] md:pb-12">
        <RevealOnScroll>
          <div className="flex flex-col items-start gap-6 md:flex-row md:justify-between md:items-end">
            {/* 왼쪽 텍스트 */}
            <div className="w-full md:max-w-[68%]">
              <h1 className="font-[family-name:var(--font-serif)] text-[clamp(32px,5vw,52px)] font-normal leading-[1.35] tracking-[-0.01em]">
                미감을 좌표로 읽다.
              </h1>
              <p className="mt-5 text-sm leading-[1.7] opacity-50">
                당신의 얼굴, 취향, 트렌드를 하나의 좌표 위에 배치합니다.
              </p>
            </div>

            {/* 오른쪽 링크 */}
            <div className="text-left md:text-right md:pb-1">
              <Link
                href="/start"
                className="text-sm font-medium cursor-pointer mb-1.5 transition-opacity duration-200 hover:opacity-60 block"
              >
                &rarr; 지금 시작하기
              </Link>
              <p className="text-sm opacity-40">&darr; 서비스 소개</p>
            </div>
          </div>
        </RevealOnScroll>
      </section>

      <Divider className="mx-[var(--spacing-page-x-mobile)] md:mx-[var(--spacing-page-x)]" />

      {/* STATS STRIP */}
      <RevealOnScroll>
        <section className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-8 md:py-12">
          <div className="grid grid-cols-2 md:grid-cols-4 border border-black/10">
            {[
              { number: "3축", label: "좌표계 분석" },
              { number: "AI", label: "미감 엔진" },
              { number: "24hr", label: "리포트 딜리버리" },
              { number: "₩5,000~", label: "시작 가격" },
            ].map((stat, i) => (
              <div
                key={stat.label}
                className={`flex flex-col px-7 py-6 ${
                  i < 3 ? "border-r border-black/10" : ""
                } ${i === 1 ? "max-md:border-r-0" : ""}`}
              >
                <span className="text-[11px] font-semibold tracking-[1px] opacity-40 mb-2.5">
                  {stat.label}
                </span>
                <span className="font-[family-name:var(--font-serif)] text-[clamp(32px,4vw,48px)] font-light leading-none">
                  {stat.number}
                </span>
              </div>
            ))}
          </div>
        </section>
      </RevealOnScroll>

      <Divider className="mx-[var(--spacing-page-x-mobile)] md:mx-[var(--spacing-page-x)]" />

      {/* SCULPTURE GALLERY */}
      {SCULPTURES.map((sculpture, index) => (
        <div key={sculpture.id}>
          <RevealOnScroll>
            <section className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-7 md:py-10">
              <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_2fr] gap-3 md:gap-6 items-start">
                {/* 1열: 번호 + 라벨 */}
                <div>
                  <h2 className="text-[clamp(18px,2.5vw,28px)] font-extrabold tracking-[1px] leading-[1.3]">
                    {sculpture.label}
                  </h2>
                  <span className="inline-block mt-2 text-[11px] font-semibold tracking-[1px] opacity-35">
                    {sculpture.number}
                  </span>
                </div>

                {/* 2열: 한글 제목 */}
                <div>
                  <p className="font-[family-name:var(--font-serif)] text-[clamp(16px,2vw,24px)] font-normal leading-[1.4]">
                    {sculpture.title}
                  </p>
                </div>

                {/* 3열: 설명 + 이미지 */}
                <div>
                  <p className="text-[15px] leading-[1.7] opacity-70 mb-6">
                    {sculpture.description}
                  </p>
                  <div className="relative aspect-[3/4] w-full max-w-[480px] bg-[#E8E5DF] overflow-hidden">
                    <Image
                      src={sculpture.src}
                      alt={sculpture.alt}
                      fill
                      className="object-cover"
                      sizes="(max-width: 768px) 100vw, 40vw"
                      priority={index === 0}
                    />
                  </div>
                </div>
              </div>
            </section>
          </RevealOnScroll>

          <Divider className="mx-[var(--spacing-page-x-mobile)] md:mx-[var(--spacing-page-x)]" />
        </div>
      ))}

      {/* PROCESS */}
      <RevealOnScroll>
        <section className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-7 md:py-10">
          <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_2fr] gap-3 md:gap-6 items-start">
            {/* 1열: 라벨 */}
            <div>
              <h2 className="text-[clamp(18px,2.5vw,28px)] font-extrabold tracking-[1px] leading-[1.3]">
                PROCESS
              </h2>
              <span className="inline-block mt-2 text-[11px] font-semibold tracking-[1px] opacity-35">
                진행 과정
              </span>
            </div>

            {/* 2열: serif 제목 */}
            <div>
              <p className="font-[family-name:var(--font-serif)] text-[clamp(16px,2vw,24px)] font-normal leading-[1.4]">
                셀카 한 장에서
                <br />
                리포트까지
              </p>
            </div>

            {/* 3열: 3단계 */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-8">
              {STEPS.map((step) => (
                <div key={step.number}>
                  <span className="font-[family-name:var(--font-serif)] text-[clamp(32px,4vw,48px)] font-light leading-none text-[var(--color-border)]">
                    {step.number}
                  </span>
                  <h3 className="text-[13px] font-semibold mt-3 mb-2">
                    {step.title}
                  </h3>
                  <p className="text-[15px] leading-[1.7] opacity-70">
                    {step.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </RevealOnScroll>

      <Divider className="mx-[var(--spacing-page-x-mobile)] md:mx-[var(--spacing-page-x)]" />

      {/* ABOUT / METHOD */}
      <RevealOnScroll>
        <section className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-7 md:py-10">
          <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_2fr] gap-3 md:gap-6 items-start">
            {/* 1열: 라벨 */}
            <div>
              <h2 className="text-[clamp(18px,2.5vw,28px)] font-extrabold tracking-[1px] leading-[1.3]">
                METHOD
              </h2>
              <span className="inline-block mt-2 text-[11px] font-semibold tracking-[1px] opacity-35">
                3축 좌표계
              </span>
            </div>

            {/* 2열: serif 제목 */}
            <div>
              <p className="font-[family-name:var(--font-serif)] text-[clamp(16px,2vw,24px)] font-normal leading-[1.4]">
                라벨이 아닌,
                <br />
                좌표를 드립니다
              </p>
            </div>

            {/* 3열: 설명 + 좌표 프리뷰 */}
            <div>
              <p className="text-[15px] leading-[1.7] opacity-70 mb-6">
                기존 이미지 컨설팅은 고정된 라벨을 붙여줍니다. 하지만 미감은
                고정되지 않습니다. SIGAK은 당신의 얼굴 구조, 피부톤, 스타일
                취향을 다차원 좌표계 위에 배치합니다. 현재 위치와 추구하는 방향
                사이의 차이가 곧 구체적인 실행 가이드가 됩니다.
              </p>

              {/* 3축 좌표 프리뷰 */}
              <div className="bg-[#E8E5DF] p-7 md:p-10">
                <span className="text-[10px] tracking-[0.3em] text-[var(--color-muted)] uppercase block mb-6">
                  3-Axis Coordinate Preview
                </span>
                {[
                  { label: "인상", left: "소프트", right: "샤프", pos: 0.35 },
                  { label: "톤", left: "웜내추럴", right: "쿨글램", pos: 0.6 },
                  {
                    label: "무드",
                    left: "프레시큐트",
                    right: "성숙시크",
                    pos: 0.45,
                  },
                ].map((axis) => (
                  <div
                    key={axis.label}
                    className="py-5 border-b border-[var(--color-border)] last:border-b-0"
                  >
                    <div className="text-xs tracking-[0.15em] text-[var(--color-muted)] mb-3 font-medium">
                      {axis.label}
                    </div>
                    <div className="relative h-1 bg-black/[0.08] rounded-full">
                      <div
                        className="absolute top-1/2 w-2.5 h-2.5 rounded-full bg-[var(--color-fg)]"
                        style={{
                          left: `${axis.pos * 100}%`,
                          transform: "translateX(-50%) translateY(-50%)",
                        }}
                      />
                    </div>
                    <div className="flex justify-between mt-2 text-[10px] text-[var(--color-muted)]">
                      <span>{axis.left}</span>
                      <span>{axis.right}</span>
                    </div>
                  </div>
                ))}
                <div className="flex gap-4 mt-5 text-[10px] text-[var(--color-muted)]">
                  <span className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-[var(--color-fg)] inline-block" />
                    현재 위치
                  </span>
                </div>
              </div>
            </div>
          </div>
        </section>
      </RevealOnScroll>

      <Divider className="mx-[var(--spacing-page-x-mobile)] md:mx-[var(--spacing-page-x)]" />

      {/* CTA */}
      <RevealOnScroll>
        <section className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-10 md:py-14 text-center">
          <Link
            href="/start"
            className="text-[clamp(24px,4vw,40px)] font-bold tracking-[1px] transition-opacity duration-200 hover:opacity-50"
          >
            &rarr; 지금 시작하기
          </Link>
          <p className="mt-3 text-[11px] tracking-[1px] opacity-30">
            셀카 한 장, 5분 설문, ₩5,000부터
          </p>
        </section>
      </RevealOnScroll>

      {/* FOOTER */}
      <Footer />

      {/* BOOKING OVERLAY */}
      <BookingOverlay
        key={overlayTier}
        open={overlayOpen}
        onClose={() => setOverlayOpen(false)}
        initTier={overlayTier}
      />
    </div>
  );
}
