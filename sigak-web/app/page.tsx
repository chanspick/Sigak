"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Image from "next/image";
import Link from "next/link";

// IntersectionObserver 기반 스크롤 reveal
function useReveal<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          obs.disconnect();
        }
      },
      { threshold: 0.15 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return { ref, visible };
}

// Reveal 래퍼 컴포넌트
function Reveal({
  children,
  delay = 0,
  className = "",
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  const { ref, visible } = useReveal<HTMLDivElement>();
  return (
    <div
      ref={ref}
      className={`transition-all duration-[900ms] ease-out ${
        visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-7"
      } ${className}`}
      style={{ transitionDelay: `${delay}s` }}
    >
      {children}
    </div>
  );
}

// 3축 좌표계 시각화 컴포넌트
function AxisIndicator({
  label,
  leftLabel,
  rightLabel,
  position,
}: {
  label: string;
  leftLabel: string;
  rightLabel: string;
  position: number;
}) {
  return (
    <div className="py-5 border-b border-[var(--color-border)] last:border-b-0">
      <div className="text-xs tracking-[0.15em] text-[var(--color-muted)] mb-3 font-medium">
        {label}
      </div>
      <div className="relative h-1 bg-black/[0.08] rounded-full">
        <div
          className="absolute top-1/2 w-2.5 h-2.5 rounded-full bg-[var(--color-fg)]"
          style={{
            left: `${position * 100}%`,
            transform: "translateX(-50%) translateY(-50%)",
          }}
        />
      </div>
      <div className="flex justify-between mt-2 text-[10px] text-[var(--color-muted)]">
        <span>{leftLabel}</span>
        <span>{rightLabel}</span>
      </div>
    </div>
  );
}
// 메인 페이지
export default function HomePage() {
  const [scrolled, setScrolled] = useState(false);
  const [scrollY, setScrollY] = useState(0);

  const handleScroll = useCallback(() => {
    const y = window.scrollY;
    setScrollY(y);
    setScrolled(y > 60);
  }, []);

  useEffect(() => {
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, [handleScroll]);

  return (
    <div className="min-h-screen bg-[var(--color-bg)] text-[var(--color-fg)]">
      {/* NAV */}
      <nav
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          scrolled
            ? "bg-[var(--color-blur-bg)] backdrop-blur-xl border-b border-[var(--color-border)]"
            : "bg-transparent border-b border-transparent"
        }`}
      >
        <div className="max-w-[1200px] mx-auto flex items-center justify-between h-14 px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)]">
          <Link
            href="/"
            className="text-[13px] font-bold tracking-[0.4em] uppercase"
          >
            SIGAK
          </Link>

          {/* 데스크톱 네비게이션 */}
          <div className="hidden md:flex items-center gap-8">
            {[
              { label: "About", href: "#about" },
              { label: "Method", href: "#method" },
              { label: "Process", href: "#process" },
            ].map((item) => (
              <a
                key={item.label}
                href={item.href}
                className="text-[11px] tracking-[0.15em] text-[var(--color-muted)] uppercase hover:text-[var(--color-fg)] transition-colors"
              >
                {item.label}
              </a>
            ))}
            <Link
              href="/start"
              className="text-[11px] tracking-[0.15em] px-5 py-2 bg-[var(--color-fg)] text-[var(--color-bg)] uppercase font-semibold hover:opacity-80 transition-opacity"
            >
              진단 시작
            </Link>
          </div>

          {/* 모바일 CTA */}
          <Link
            href="/start"
            className="md:hidden text-[11px] tracking-[0.15em] px-4 py-1.5 bg-[var(--color-fg)] text-[var(--color-bg)] uppercase font-semibold"
          >
            진단 시작
          </Link>
        </div>
      </nav>

      {/* HERO */}
      <section className="min-h-screen flex flex-col justify-center pt-20 pb-20 px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] relative">
        <div className="max-w-[1200px] w-full mx-auto grid grid-cols-1 md:grid-cols-2 gap-10 md:gap-16 items-center">
          {/* 카피 */}
          <div className="order-2 md:order-1">
            <div className="text-[10px] tracking-[0.35em] text-[var(--color-muted)] uppercase mb-6 font-semibold">
              Aesthetic Coordinate System
            </div>
            <h1 className="font-[var(--font-serif)] text-[clamp(36px,5vw,56px)] font-normal leading-[1.3] mb-6">
              미감을
              <br />
              좌표로 읽다
            </h1>
            <p className="text-[15px] leading-[1.8] text-[var(--color-muted)] max-w-[400px] mb-10">
              당신의 얼굴, 취향, 트렌드를 하나의 공간에 배치합니다. 현재
              위치에서 추구하는 방향까지 &mdash; 구체적 경로를 설계합니다.
            </p>
            <div className="flex items-center gap-4 flex-wrap">
              <Link
                href="/start"
                className="px-9 py-3.5 bg-[var(--color-fg)] text-[var(--color-bg)] text-[13px] font-semibold tracking-[0.08em] hover:opacity-80 transition-opacity"
              >
                내 좌표 확인하기
              </Link>
              <a
                href="#about"
                className="text-[12px] text-[var(--color-muted)] tracking-[0.08em] border-b border-[var(--color-border)] pb-0.5 hover:text-[var(--color-fg)] hover:border-[var(--color-fg)] transition-colors"
              >
                더 알아보기 &rarr;
              </a>
            </div>
          </div>

          {/* 히어로 조각상 이미지 */}
          <div className="order-1 md:order-2 relative aspect-[3/4] w-full max-w-[500px] mx-auto md:mx-0">
            <Image
              src="/images/sculptures/deer.webp"
              alt="SIGAK 시그니처 조각상 - 사슴"
              fill
              priority
              className="object-cover"
              sizes="(max-width: 768px) 100vw, 50vw"
            />
          </div>
        </div>

        {/* 스크롤 인디케이터 */}
        <div
          className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 transition-opacity duration-500"
          style={{ opacity: scrollY > 100 ? 0 : 0.4 }}
        >
          <div className="w-px h-8 bg-[var(--color-fg)]" />
          <span className="text-[9px] tracking-[0.25em] uppercase">
            Scroll
          </span>
        </div>
      </section>
      {/* STATS STRIP */}
      <Reveal>
        <section className="border-t border-b border-[var(--color-border)] max-w-[1200px] mx-auto grid grid-cols-2 md:grid-cols-4">
          {[
            ["12,400+", "미감 데이터 분석"],
            ["3축", "좌표계 매핑"],
            ["24hr", "리포트 딜리버리"],
            ["93%", "만족도"],
          ].map(([num, desc], i) => (
            <div
              key={i}
              className={`py-9 px-6 text-center ${i < 3 ? "border-r border-[var(--color-border)]" : ""}`}
            >
              <div className="text-[28px] font-[var(--font-serif)] font-normal mb-1.5">
                {num}
              </div>
              <div className="text-[10px] tracking-[0.15em] text-[var(--color-muted)] uppercase">
                {desc}
              </div>
            </div>
          ))}
        </section>
      </Reveal>

      {/* ABOUT */}
      <section
        id="about"
        className="py-28 md:py-32 px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] max-w-[1200px] mx-auto"
      >
        <Reveal>
          <div className="grid grid-cols-1 md:grid-cols-[1fr_1.2fr] gap-16 md:gap-20 items-start">
            <div>
              <div className="text-[10px] tracking-[0.35em] text-[var(--color-muted)] uppercase mb-4 font-semibold">
                About SIGAK
              </div>
              <h2 className="font-[var(--font-serif)] text-[clamp(28px,3.5vw,40px)] font-normal leading-[1.4] mb-8">
                라벨이 아닌,
                <br />
                좌표를 드립니다
              </h2>
              <p className="text-[14px] leading-[2] text-[var(--color-muted)]">
                기존 이미지 컨설팅은 &ldquo;쿨톤&rdquo;,
                &ldquo;봄웜&rdquo;, &ldquo;내추럴&rdquo;같은 고정된 라벨을
                붙여줍니다. 하지만 미감은 고정되지 않습니다 &mdash; 트렌드에 따라
                이동하고, 취향에 따라 방향이 달라집니다.
              </p>
              <div className="my-8 border-t border-[var(--color-border)]" />
              <p className="text-[14px] leading-[2] text-[var(--color-muted)]">
                SIGAK은 당신의 얼굴 구조, 피부톤, 스타일 취향을 다차원
                좌표계 위에 배치합니다. 현재 위치와 추구하는 방향 사이의
                차이가 곧 구체적인 실행 가이드가 됩니다.
              </p>
            </div>

            {/* 3축 좌표 프리뷰 */}
            <div className="bg-[#E8E5DF] p-8 md:p-12">
              <div className="text-[10px] tracking-[0.3em] text-[var(--color-muted)] uppercase mb-8">
                3-Axis Coordinate Preview
              </div>
              <AxisIndicator
                label="인상"
                leftLabel="소프트"
                rightLabel="샤프"
                position={0.35}
              />
              <AxisIndicator
                label="톤"
                leftLabel="웜내추럴"
                rightLabel="쿨글램"
                position={0.6}
              />
              <AxisIndicator
                label="무드"
                leftLabel="프레시큐트"
                rightLabel="성숙시크"
                position={0.45}
              />
              <div className="flex gap-4 mt-6 text-[10px] text-[var(--color-muted)]">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-[var(--color-fg)] inline-block" />
                  현재 위치
                </span>
              </div>
            </div>
          </div>
        </Reveal>
      </section>
      {/* GALLERY */}
      <section
        id="method"
        className="pb-28 md:pb-32 px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] max-w-[1200px] mx-auto"
      >
        <Reveal>
          <div className="text-[10px] tracking-[0.35em] text-[var(--color-muted)] uppercase mb-4 font-semibold">
            The Three Dimensions
          </div>
          <h2 className="font-[var(--font-serif)] text-[clamp(28px,3.5vw,40px)] font-normal leading-[1.4] mb-12">
            미감의 세 방향
          </h2>
        </Reveal>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-0.5">
          {[
            {
              src: "/images/sculptures/hawk.webp",
              alt: "매 조각상 - 샤프하고 쿨글램한 미감",
              axis: "샤프 · 쿨글램",
              desc: "강렬한 인상, 날카로운 구조, 도시적 세련미",
            },
            {
              src: "/images/sculptures/cat.webp",
              alt: "고양이 조각상 - 소프트하고 프레시한 미감",
              axis: "소프트 · 프레시",
              desc: "부드러운 곡선, 경쾌한 톤, 자연스러운 귀여움",
            },
            {
              src: "/images/sculptures/wolf.webp",
              alt: "늑대 조각상 - 성숙하고 시크한 미감",
              axis: "성숙 · 시크",
              desc: "깊은 인상, 볼드한 구조, 성숙한 분위기",
            },
          ].map((item, i) => (
            <Reveal key={item.src} delay={i * 0.12}>
              <div>
                <div className="relative aspect-[3/4] w-full bg-[#E8E5DF] overflow-hidden">
                  <Image
                    src={item.src}
                    alt={item.alt}
                    fill
                    className="object-cover"
                    sizes="(max-width: 640px) 100vw, 33vw"
                  />
                </div>
                <div className="pt-5 pb-2">
                  <h3 className="font-[var(--font-serif)] text-[14px] font-normal mb-1.5">
                    {item.axis}
                  </h3>
                  <p className="text-[11px] text-[var(--color-muted)] leading-[1.6]">
                    {item.desc}
                  </p>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* PROCESS */}
      <section
        id="process"
        className="border-t border-[var(--color-border)] py-24 md:py-28 px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] max-w-[1200px] mx-auto"
      >
        <Reveal>
          <div className="grid grid-cols-1 md:grid-cols-[0.4fr_1fr] gap-16 md:gap-20">
            <div>
              <div className="text-[10px] tracking-[0.35em] text-[var(--color-muted)] uppercase mb-4 font-semibold">
                Process
              </div>
              <h2 className="font-[var(--font-serif)] text-[28px] font-normal leading-[1.4]">
                셀카 한 장에서
                <br />
                리포트까지
              </h2>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-10">
              {[
                {
                  step: "01",
                  title: "셀카 업로드",
                  desc: "정면 사진 1장과 간단한 설문. 추구하는 이미지, 레퍼런스, 현재 고민을 자유롭게.",
                },
                {
                  step: "02",
                  title: "AI 좌표 분석",
                  desc: "얼굴 구조, 피부톤, 스타일 취향을 3축 좌표계에 매핑. 트렌드 데이터와 교차 분석.",
                },
                {
                  step: "03",
                  title: "맞춤 리포트",
                  desc: "현재 위치에서 추구미까지의 구체적 경로. 메이크업, 헤어, 스타일링 실행 가이드.",
                },
              ].map((item, i) => (
                <Reveal key={item.step} delay={i * 0.15}>
                  <div>
                    <div className="text-[32px] font-[var(--font-serif)] font-light text-[var(--color-border)] mb-4">
                      {item.step}
                    </div>
                    <h3 className="text-[15px] font-semibold mb-2.5">
                      {item.title}
                    </h3>
                    <p className="text-[12px] leading-[1.8] text-[var(--color-muted)]">
                      {item.desc}
                    </p>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </Reveal>
      </section>
      {/* CTA */}
      <section className="border-t border-[var(--color-border)] py-28 md:py-32 text-center px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)]">
        <Reveal>
          <div className="max-w-[520px] mx-auto">
            <div className="text-[10px] tracking-[0.35em] text-[var(--color-muted)] uppercase mb-5 font-semibold">
              Start Now
            </div>
            <h2 className="font-[var(--font-serif)] text-[clamp(28px,4vw,44px)] font-normal leading-[1.3] mb-5">
              내 미감 좌표를
              <br />
              확인해보세요
            </h2>
            <p className="text-[14px] text-[var(--color-muted)] leading-[1.8] mb-9">
              셀카 한 장과 5분의 설문으로
              <br />
              당신만의 미감 리포트를 받아보세요.
            </p>
            <Link
              href="/start"
              className="inline-block px-12 py-4 bg-[var(--color-fg)] text-[var(--color-bg)] text-[14px] font-semibold tracking-[0.15em] hover:opacity-80 transition-opacity"
            >
              진단 시작하기
            </Link>
            <div className="mt-4 text-[11px] text-[var(--color-border)]">
              ₩5,000부터
            </div>
          </div>
        </Reveal>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-[var(--color-border)] max-w-[1200px] mx-auto px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-10 flex justify-between items-center">
        <span className="text-[11px] tracking-[0.3em] font-bold uppercase">
          SIGAK
        </span>
        <span className="text-[10px] text-[var(--color-border)] tracking-[0.08em]">
          &copy; 2026 SIGAK. All rights reserved.
        </span>
      </footer>
    </div>
  );
}
