"use client";

// 캐스팅 전용 랜딩 페이지
// 광고 2번("셀카 올리고 캐스팅") 유입 유저를 위한 독립 랜딩.
// CTA → /start (기존 카카오 로그인 → 티어 선택 → 설문 플로우)

import { useState, useEffect, useRef, type ReactNode } from "react";
import Link from "next/link";
import { NotificationBell } from "@/components/notification/notification-bell";

/* ── Reveal on scroll ── */
function Reveal({
  children,
  delay = 0,
  className = "",
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setVisible(true);
          obs.disconnect();
        }
      },
      { threshold: 0.05 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  return (
    <div
      ref={ref}
      className={className}
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? "none" : "translateY(16px)",
        transition: `opacity 0.7s ease ${delay}s, transform 0.7s ease ${delay}s`,
      }}
    >
      {children}
    </div>
  );
}

/* ── 프로세스 스텝 데이터 ── */
const STEPS = [
  {
    num: "01",
    title: "셀카 업로드",
    desc: "정면 사진 한 장과 5분 설문. 추구하는 이미지와 매력 포인트를 알려주세요.",
  },
  {
    num: "02",
    title: "AI 매력 분석",
    desc: "얼굴 구조, 피부톤, 이미지 유형을 다차원 좌표로 매핑합니다. 당신만의 매력이 데이터가 됩니다.",
  },
  {
    num: "03",
    title: "캐스팅 풀 등록",
    desc: "풀 리포트를 받은 후, 캐스팅 풀 참여를 선택할 수 있어요. 개인정보는 수락 전까지 보호됩니다.",
  },
  {
    num: "04",
    title: "제안이 도착",
    desc: "에이전시와 브랜드가 좌표 기반으로 탐색 후, 출연료를 포함한 구체적 제안을 보냅니다.",
  },
] as const;

/* ── 캐스팅 카드 목업 데이터 ── */
const INVITATIONS = [
  {
    from: "Alpha Agency",
    purpose: "화보 촬영",
    fee: "₩500,000",
    date: "2026. 4. 20",
  },
  {
    from: "Scene Studio",
    purpose: "브랜드 광고 모델",
    fee: "₩800,000",
    date: "2026. 5. 3",
  },
] as const;

/* ── 티어 데이터 (캐스팅 랜딩 전용) ── */
const CASTING_TIERS = [
  {
    label: "OVERVIEW",
    price: "₩2,900",
    original: "₩5,000",
    desc: "얼굴 구조 분석, 피부톤, 3축 좌표 요약. 나를 먼저 파악하고 싶다면.",
    cta: "오버뷰 시작",
    featured: false,
  },
  {
    label: "FULL REPORT",
    rec: "RECOMMENDED",
    price: "₩29,000",
    original: "₩49,000",
    desc: "오버뷰 + 헤어 TOP 3, 메이크업 가이드, 트렌드 포지셔닝, 캐스팅 풀 등록 가능.",
    cta: "풀 리포트 + 캐스팅 등록",
    featured: true,
  },
  {
    label: "CELEBRITY POOL",
    price: "₩100,000",
    desc: "풀 리포트 + 상세 프로필 + 우선 매칭. 에이전시 검색에서 상위 노출됩니다.",
    cta: "셀럽 풀 등록",
    featured: false,
  },
] as const;

/* ── FAQ 데이터 ── */
const FAQS = [
  {
    q: "캐스팅이 보장되나요?",
    a: "캐스팅은 보장이 아닌 기회입니다. 에이전시가 좌표 기반으로 탐색하며, 매칭 제안 여부는 프로젝트에 따라 달라집니다.",
  },
  {
    q: "내 사진이 공개되나요?",
    a: "캐스팅 풀에 등록해도 개인정보는 매칭 수락 전까지 절대 공유되지 않습니다. 언제든 해제 가능합니다.",
  },
  {
    q: "리포트만 받아도 되나요?",
    a: "물론이에요. 캐스팅 풀 등록은 선택입니다. 리포트 자체가 헤어, 메이크업, 스타일링 가이드를 포함한 완결된 상품입니다.",
  },
] as const;

/* ── 3열 Row 레이아웃 (1:1:2 그리드) ── */
function Row({
  c1,
  c2,
  c3,
}: {
  c1: ReactNode;
  c2: ReactNode;
  c3: ReactNode;
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_2fr] gap-3 md:gap-6 items-start">
      <div>{c1}</div>
      <div>{c2}</div>
      <div>{c3}</div>
    </div>
  );
}

export default function CastingLandingPage() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  useEffect(() => {
    setIsLoggedIn(!!localStorage.getItem("sigak_user_id"));
  }, []);

  return (
    <div className="min-h-screen bg-bg text-fg antialiased">
      {/* ── NAV ── */}
      <nav className="sticky top-0 z-[100] flex items-center justify-between px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] h-[56px] md:h-[60px] bg-fg text-bg">
        <div className="flex items-center">
          <Link
            href="/"
            className="text-[10px] md:text-[11px] font-medium tracking-[2.5px] uppercase opacity-70 hover:opacity-100 transition-opacity no-underline text-[var(--color-bg)]"
          >
            SIGAK
          </Link>
        </div>
        <span className="text-[12px] md:text-[13px] font-semibold tracking-[5px] md:tracking-[6px] uppercase absolute left-1/2 -translate-x-1/2">
          CASTING
        </span>
        <div className="flex items-center gap-3 md:gap-5">
          {isLoggedIn && (
            <>
              <Link
                href="/my"
                className="hidden md:block text-[11px] font-medium tracking-[1.5px] uppercase opacity-70 hover:opacity-100 transition-opacity no-underline text-[var(--color-bg)]"
              >
                내 리포트
              </Link>
              <NotificationBell />
            </>
          )}
          <Link
            href="/start"
            className="text-[10px] md:text-[11px] font-medium tracking-[1.5px] md:tracking-[2.5px] px-3 py-1.5 border border-white/30 hover:border-white/60 transition-colors no-underline text-[var(--color-bg)]"
          >
            시작하기
          </Link>
        </div>
      </nav>

      {/* ── HERO ── */}
      <section className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] pt-10 pb-8 md:pt-[60px] md:pb-12">
        <Reveal>
          <div className="flex flex-col md:flex-row md:justify-between md:items-end gap-6 md:gap-10">
            <div className="md:max-w-[64%]">
              <p className="text-[11px] font-semibold tracking-[3px] opacity-30 mb-5">
                SELFIE CASTING AGENCY
              </p>
              <h1 className="font-[family-name:var(--font-serif)] text-[clamp(32px,5vw,52px)] font-normal leading-[1.35]">
                셀카 한 장으로
                <br />
                캐스팅 제안을 받다.
              </h1>
              <p className="mt-4 text-[15px] opacity-50 leading-[1.7]">
                AI가 당신의 매력 포인트를 분석하고,
                <br />
                에이전시와 브랜드가 당신을 찾아옵니다.
              </p>
            </div>
            <div className="md:text-right">
              <Link
                href="/start"
                className="inline-block px-8 py-3.5 bg-fg text-bg text-[13px] font-semibold tracking-[0.3px] no-underline hover:opacity-90 transition-opacity"
              >
                내 매력 분석 시작하기
              </Link>
              <p className="mt-3 text-[12px] opacity-35">
                ₩2,900부터 · 24시간 내 결과
              </p>
            </div>
          </div>
        </Reveal>
      </section>

      {/* 구분선 */}
      <div className="h-px bg-black/[0.15] mx-[var(--spacing-page-x-mobile)] md:mx-[var(--spacing-page-x)]" />

      {/* ── 01. PROCESS ── */}
      <section className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-7 md:py-10">
        <Reveal>
          <Row
            c1={
              <>
                <h2 className="text-[clamp(18px,2.5vw,28px)] font-extrabold tracking-[1px] leading-[1.3]">
                  01
                </h2>
                <span className="block mt-2 text-[11px] font-semibold tracking-[1.5px] opacity-35">
                  PROCESS
                </span>
              </>
            }
            c2={
              <p className="font-[family-name:var(--font-serif)] text-[clamp(16px,2vw,24px)] font-normal leading-[1.4]">
                셀카에서
                <br />
                캐스팅 제안까지.
              </p>
            }
            c3={
              <div>
                {STEPS.map((step, i) => (
                  <div
                    key={step.num}
                    className={`flex gap-5 py-4 ${i < STEPS.length - 1 ? "border-b border-black/[0.06]" : ""}`}
                  >
                    <span className="font-[family-name:var(--font-serif)] text-[18px] font-light opacity-25 shrink-0 w-7">
                      {step.num}
                    </span>
                    <div>
                      <p className="text-[15px] font-bold mb-1">
                        {step.title}
                      </p>
                      <p className="text-[14px] opacity-50 leading-[1.7]">
                        {step.desc}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            }
          />
        </Reveal>
      </section>

      <div className="h-px bg-black/[0.15] mx-[var(--spacing-page-x-mobile)] md:mx-[var(--spacing-page-x)]" />

      {/* ── 02. INVITATION ── */}
      <section className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-7 md:py-10">
        <Reveal>
          <Row
            c1={
              <>
                <h2 className="text-[clamp(18px,2.5vw,28px)] font-extrabold tracking-[1px] leading-[1.3]">
                  02
                </h2>
                <span className="block mt-2 text-[11px] font-semibold tracking-[1.5px] opacity-35">
                  INVITATION
                </span>
              </>
            }
            c2={
              <p className="font-[family-name:var(--font-serif)] text-[clamp(16px,2vw,24px)] font-normal leading-[1.4]">
                이런 제안이
                <br />
                도착합니다.
              </p>
            }
            c3={
              <div>
                <div className="flex flex-col md:flex-row gap-4">
                  {INVITATIONS.map((inv) => (
                    <div
                      key={inv.from}
                      className="flex-1 min-w-[260px] p-6 border border-black/[0.12]"
                    >
                      <p className="text-[10px] font-bold tracking-[2px] opacity-25 mb-5">
                        CASTING INVITATION
                      </p>
                      <div className="flex flex-col gap-2.5">
                        <div className="flex justify-between items-center">
                          <span className="text-[11px] opacity-35 tracking-[1px]">
                            From
                          </span>
                          <span className="text-[14px] font-medium">
                            {inv.from}
                          </span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-[11px] opacity-35 tracking-[1px]">
                            Purpose
                          </span>
                          <span className="text-[14px] font-medium">
                            {inv.purpose}
                          </span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-[11px] opacity-35 tracking-[1px]">
                            Fee
                          </span>
                          <span className="text-[14px] font-extrabold">
                            {inv.fee}
                          </span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-[11px] opacity-35 tracking-[1px]">
                            Date
                          </span>
                          <span className="text-[14px] font-medium">
                            {inv.date}
                          </span>
                        </div>
                      </div>
                      <div className="flex gap-2 mt-5">
                        <span className="flex-1 py-2.5 text-center text-[12px] font-semibold bg-fg text-bg select-none">
                          수락하기
                        </span>
                        <span className="flex-1 py-2.5 text-center text-[12px] font-semibold border border-black/[0.12] select-none">
                          괜찮습니다
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
                <p className="mt-4 text-[12px] opacity-25 italic">
                  * 실제 제안 예시를 기반으로 구성된 목업입니다
                </p>
              </div>
            }
          />
        </Reveal>
      </section>

      <div className="h-px bg-black/[0.15] mx-[var(--spacing-page-x-mobile)] md:mx-[var(--spacing-page-x)]" />

      {/* ── 03. WHY ── */}
      <section className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-7 md:py-10">
        <Reveal>
          <Row
            c1={
              <>
                <h2 className="text-[clamp(18px,2.5vw,28px)] font-extrabold tracking-[1px] leading-[1.3]">
                  03
                </h2>
                <span className="block mt-2 text-[11px] font-semibold tracking-[1.5px] opacity-35">
                  WHY
                </span>
              </>
            }
            c2={
              <p className="font-[family-name:var(--font-serif)] text-[clamp(16px,2vw,24px)] font-normal leading-[1.4]">
                캐스팅의 시작은
                <br />
                매력 분석입니다.
              </p>
            }
            c3={
              <div>
                <p className="text-[15px] leading-[1.7] opacity-70">
                  에이전시가 당신을 찾으려면, 먼저 당신의 매력이 데이터로
                  존재해야 합니다. AI가 얼굴 구조, 피부톤, 이미지 유형을
                  분석하고 — 그 결과가 캐스팅 풀의 기반이 됩니다.
                </p>
                <p className="mt-4 text-[15px] leading-[1.7] opacity-40">
                  분석 리포트 자체도 헤어, 메이크업, 스타일링 가이드를 포함하고
                  있어 캐스팅 여부와 관계없이 가치가 있어요.
                </p>
              </div>
            }
          />
        </Reveal>
      </section>

      <div className="h-px bg-black/[0.15] mx-[var(--spacing-page-x-mobile)] md:mx-[var(--spacing-page-x)]" />

      {/* ── 04. PRICING ── */}
      <section className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-7 md:py-10">
        <Reveal>
          <Row
            c1={
              <>
                <h2 className="text-[clamp(18px,2.5vw,28px)] font-extrabold tracking-[1px] leading-[1.3]">
                  04
                </h2>
                <span className="block mt-2 text-[11px] font-semibold tracking-[1.5px] opacity-35">
                  PRICING
                </span>
              </>
            }
            c2={
              <p className="font-[family-name:var(--font-serif)] text-[clamp(16px,2vw,24px)] font-normal leading-[1.4]">
                선택하세요.
              </p>
            }
            c3={
              <div>
                {CASTING_TIERS.map((t, i) => (
                  <div
                    key={t.label}
                    className={`grid grid-cols-1 md:grid-cols-[1fr_2fr_auto] gap-3 md:gap-5 items-center py-6 ${i < CASTING_TIERS.length - 1 ? "border-b border-black/[0.06]" : ""}`}
                  >
                    {/* 라벨 + 가격 */}
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-bold tracking-[2px]">
                          {t.label}
                        </span>
                        {"rec" in t && t.rec && (
                          <span className="text-[9px] font-bold tracking-[1.5px] px-2 py-0.5 bg-fg text-bg">
                            {t.rec}
                          </span>
                        )}
                      </div>
                      <div className="flex items-baseline gap-2 mt-2">
                        <span className="font-[family-name:var(--font-serif)] text-[24px] font-semibold">
                          {t.price}
                        </span>
                        {"original" in t && t.original && (
                          <span className="text-[13px] opacity-30 line-through">
                            {t.original}
                          </span>
                        )}
                      </div>
                    </div>
                    {/* 설명 */}
                    <p className="text-[14px] opacity-50 leading-[1.6]">
                      {t.desc}
                    </p>
                    {/* CTA */}
                    <Link
                      href="/start"
                      className={`inline-block px-6 py-3 text-[12px] font-semibold tracking-[0.3px] text-center whitespace-nowrap no-underline transition-opacity hover:opacity-80 ${
                        t.featured
                          ? "bg-fg text-bg"
                          : "bg-transparent text-fg border border-black/[0.12]"
                      }`}
                    >
                      {t.cta}
                    </Link>
                  </div>
                ))}
              </div>
            }
          />
        </Reveal>
      </section>

      <div className="h-px bg-black/[0.15] mx-[var(--spacing-page-x-mobile)] md:mx-[var(--spacing-page-x)]" />

      {/* ── 05. FAQ ── */}
      <section className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-7 md:py-10">
        <Reveal>
          <Row
            c1={
              <>
                <h2 className="text-[clamp(18px,2.5vw,28px)] font-extrabold tracking-[1px] leading-[1.3]">
                  05
                </h2>
                <span className="block mt-2 text-[11px] font-semibold tracking-[1.5px] opacity-35">
                  FAQ
                </span>
              </>
            }
            c2={
              <p className="font-[family-name:var(--font-serif)] text-[clamp(16px,2vw,24px)] font-normal leading-[1.4]">
                자주 묻는 질문.
              </p>
            }
            c3={
              <div>
                {FAQS.map((faq, i) => (
                  <div
                    key={faq.q}
                    className={`py-4 ${i < FAQS.length - 1 ? "border-b border-black/[0.06]" : ""}`}
                  >
                    <p className="text-[15px] font-bold mb-1.5">{faq.q}</p>
                    <p className="text-[14px] opacity-50 leading-[1.7]">
                      {faq.a}
                    </p>
                  </div>
                ))}
              </div>
            }
          />
        </Reveal>
      </section>

      <div className="h-px bg-black/[0.15] mx-[var(--spacing-page-x-mobile)] md:mx-[var(--spacing-page-x)]" />

      {/* ── FINAL CTA ── */}
      <Reveal>
        <Link
          href="/start"
          className="block px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-10 md:py-14 text-center group"
        >
          <h2 className="font-[family-name:var(--font-serif)] text-[clamp(24px,4vw,40px)] font-normal mb-3">
            당신의 매력을 데이터로.
          </h2>
          <p className="text-[14px] opacity-40 mb-8">
            셀카 한 장 · 5분 설문 · 24시간 내 결과
          </p>
          <span className="inline-block px-12 py-3.5 bg-fg text-bg text-[14px] font-semibold tracking-[0.5px] transition-opacity duration-200 group-hover:opacity-80">
            시작하기
          </span>
        </Link>
      </Reveal>

      {/* ── FOOTER ── */}
      <footer className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-8 md:py-10 border-t border-black/10">
        <div className="max-w-3xl mx-auto">
          <div className="flex flex-wrap gap-x-6 gap-y-1 text-[11px] opacity-40 mb-4">
            <Link
              href="/terms"
              className="hover:opacity-70 transition-opacity"
            >
              이용약관
            </Link>
            <Link
              href="/terms"
              className="hover:opacity-70 transition-opacity"
            >
              개인정보처리방침
            </Link>
            <Link
              href="/refund"
              className="hover:opacity-70 transition-opacity"
            >
              환불규정
            </Link>
            <a
              href="mailto:partner@sigak.asia"
              className="hover:opacity-70 transition-opacity"
            >
              partner@sigak.asia
            </a>
          </div>
          <p className="text-[10px] leading-[1.8] opacity-25">
            주식회사 시각 | 대표: 조찬형 | partner@sigak.asia
            <br />
            &copy; 2026 SIGAK. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
