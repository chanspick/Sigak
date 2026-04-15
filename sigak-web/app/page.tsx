"use client";

import { useState, useEffect, useRef, type ReactNode } from "react";
import Image from "next/image";
import Link from "next/link";
import { NotificationBell } from "@/components/notification/notification-bell";
import { MOCK_REPORT } from "@/lib/constants/mock-report";

function Reveal({ children, delay = 0, className = "" }: { children: ReactNode; delay?: number; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => { const el = ref.current; if (!el) return; const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setVisible(true); obs.disconnect(); } }, { threshold: 0.15 }); obs.observe(el); return () => obs.disconnect(); }, []);
  return (<div ref={ref} className={className} style={{ opacity: visible ? 1 : 0, transform: visible ? "translateY(0)" : "translateY(28px)", transition: `opacity 0.9s ease ${delay}s, transform 0.9s ease ${delay}s` }}>{children}</div>);
}

const GALLERY = [
  { id: "owl", src: "/images/sculptures/owl.png", alt: "부엉이 조각상", axis: "또렷한 · 강렬한", desc: "강렬한 인상과 선명한 윤곽. 도시적 세련미와 대담한 구조가 만들어내는 압도적 아우라." },
  { id: "cat", src: "/images/sculptures/cat.png", alt: "고양이 조각상", axis: "부드러운 · 발랄한", desc: "경쾌한 톤과 자연스러운 곡선. 가볍지만 또렷한 인상이 전하는 편안한 호감." },
  { id: "fox", src: "/images/sculptures/fox.png", alt: "여우 조각상", axis: "성숙한 · 강렬한", desc: "깊은 인상과 강렬한 구조. 시간이 쌓아올린 무게감과 세련된 존재감." },
] as const;

const TIERS = [
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
    cta: "풀 리포트 시작",
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

const TEAM = [
  { role: "CV / ML Engineer", focus: "얼굴 구조 분석, 미감 좌표계 설계, 영상처리 파이프라인" },
  { role: "Aesthetic Director", focus: "트렌드 분석, 미감 해석, 리포트 큐레이션" },
  { role: "Product Designer", focus: "사용자 경험 설계, 리포트 시각화" },
  { role: "Growth Lead", focus: "시장 검증, B2B 매칭, 데이터 전략" },
] as const;

function Row({ c1, c2, c3 }: { c1: ReactNode; c2: ReactNode; c3: ReactNode }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_2fr] gap-3 md:gap-6 items-start">
      <div>{c1}</div>
      <div>{c2}</div>
      <div>{c3}</div>
    </div>
  );
}

export default function HomePage() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  useEffect(() => { setIsLoggedIn(!!localStorage.getItem("sigak_user_id")); }, []);

  return (
    <div className="min-h-screen bg-bg text-fg antialiased">
      {/* ── NAV ── */}
      <nav className="sticky top-0 z-[100] flex items-center justify-between px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] h-[56px] md:h-[60px] bg-fg text-bg">
        <Link href="/" className="text-[12px] md:text-[13px] font-semibold tracking-[5px] md:tracking-[6px] uppercase no-underline text-[var(--color-bg)] shrink-0">SIGAK</Link>
        <div className="hidden md:flex items-center gap-7 absolute left-1/2 -translate-x-1/2">
          {["Method", "Casting", "Team"].map((t) => (
            <a key={t} href={`#${t.toLowerCase()}`} className="text-[11px] font-medium tracking-[2.5px] uppercase opacity-50 transition-opacity duration-200 hover:opacity-100">{t}</a>
          ))}
        </div>
        <div className="flex items-center gap-3 md:gap-5">
          {isLoggedIn ? (
            <>
              <Link href="/my" className="hidden md:block text-[11px] font-medium tracking-[1.5px] uppercase opacity-70 hover:opacity-100 transition-opacity no-underline text-[var(--color-bg)]">내 리포트</Link>
              <Link href="/my" className="md:hidden" aria-label="내 리포트">
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5"><circle cx="9" cy="6" r="3.5" /><path d="M2.5 16.5c0-3.5 2.9-5.5 6.5-5.5s6.5 2 6.5 5.5" /></svg>
              </Link>
              <NotificationBell />
            </>
          ) : (
            <Link href="/start" className="text-[10px] md:text-[11px] font-medium tracking-[1.5px] uppercase opacity-70 hover:opacity-100 transition-opacity no-underline text-[var(--color-bg)]">로그인</Link>
          )}
          <Link href="/start" className="text-[10px] md:text-[11px] font-medium tracking-[1.5px] md:tracking-[2.5px] px-3 py-1.5 border border-white/30 hover:border-white/60 transition-colors no-underline text-[var(--color-bg)]">진단 시작</Link>
        </div>
      </nav>

      {/* ════════════════════════════════════════════
          전환 구간 (스크롤 3번)
          ════════════════════════════════════════════ */}

      {/* ── HERO — 슬림 헤더 ── */}
      <section className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] pt-10 pb-8 md:pt-[60px] md:pb-8">
        <Reveal>
          <h1 className="font-[family-name:var(--font-serif)] text-[clamp(32px,5vw,52px)] font-normal leading-[1.35] tracking-[-0.01em]">
            AI가 읽는<br />당신의 얼굴.
          </h1>
          <p className="mt-4 text-[14px] opacity-40">
            셀카 한 장 · 5분 설문 · ₩2,900부터
          </p>
        </Reveal>
      </section>

      <div className="h-px bg-black/[0.15] mx-[var(--spacing-page-x-mobile)] md:mx-[var(--spacing-page-x)]" />

      {/* ── Report 미리보기 — 핵심 훅 ── */}
      <section className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-7 md:py-10">
        <Reveal>
          <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_2fr] gap-3 md:gap-6 items-start mb-10">
            <div><h2 className="text-[clamp(18px,2.5vw,28px)] font-extrabold tracking-[1px] leading-[1.3]">Report</h2></div>
            <div><p className="font-[family-name:var(--font-serif)] text-[clamp(16px,2vw,24px)] font-normal leading-[1.4]">리포트 미리보기</p></div>
            <div><p className="text-[15px] leading-[1.7] opacity-70">AI가 분석한 얼굴 구조 지표, 퍼스널 컬러, 추구미 갭 분석, 헤어 추천까지 — 실제 리포트의 일부입니다.</p></div>
          </div>
        </Reveal>

        {(() => {
          const faceSection = MOCK_REPORT.sections.find(s => s.id === "face_structure");
          const skinSection = MOCK_REPORT.sections.find(s => s.id === "skin_analysis");
          const gapSection = MOCK_REPORT.sections.find(s => s.id === "gap_analysis");
          const hairSection = MOCK_REPORT.sections.find(s => s.id === "hair_recommendation");
          const face = faceSection?.content as Record<string, unknown> | undefined;
          const skin = skinSection?.content as Record<string, unknown> | undefined;
          const gap = gapSection?.content as Record<string, unknown> | undefined;
          const hair = hairSection?.content as Record<string, unknown> | undefined;
          const metrics = (face?.metrics as Array<{ key: string; label: string; value: number; percentile: number; min_label: string; max_label: string; context_label: string }>) || [];
          const recommended = (skin?.recommended as Array<{ name: string; hex: string; usage: string }>) || [];
          const directionItems = (gap?.direction_items as Array<{ label: string; label_low: string; label_high: string; from_score: number; to_score: number; difficulty: string }>) || [];
          const topCombo = ((hair?.top_combos as Array<{ rank: number; front: { name_kr: string; image: string }; back: { name_kr: string; image_front: string }; why: string }>) || [])[0];
          const catalog = hair?.catalog as { front: Array<{ id: string; name_kr: string; image: string }>; back: Array<{ id: string; name_kr: string; image_front: string }> } | undefined;

          return (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Reveal delay={0.05}>
                <div className="border border-black/10 p-6">
                  <p className="text-[11px] font-semibold tracking-[1.5px] uppercase opacity-40 mb-5">얼굴 구조</p>
                  <div className="space-y-4">
                    {metrics.slice(0, 4).map(m => (
                      <div key={m.key}>
                        <div className="flex justify-between mb-1.5">
                          <span className="text-[12px] font-medium">{m.label}</span>
                          <span className="text-[11px] opacity-40">{m.context_label}</span>
                        </div>
                        <div className="relative h-1 bg-black/[0.06] rounded-sm">
                          <div className="absolute top-0 left-0 h-full bg-fg/30 rounded-sm" style={{ width: `${m.percentile}%` }} />
                        </div>
                        <div className="flex justify-between mt-1 text-[10px] opacity-30">
                          <span>{m.min_label}</span>
                          <span>{m.max_label}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </Reveal>
              <Reveal delay={0.1}>
                <div className="border border-black/10 p-6">
                  <p className="text-[11px] font-semibold tracking-[1.5px] uppercase opacity-40 mb-5">퍼스널 컬러</p>
                  <div className="flex items-center gap-4 mb-5">
                    <div className="w-12 h-12 rounded-full border border-black/10" style={{ background: skin?.hex_sample as string || "#6F4F3C" }} />
                    <div>
                      <p className="text-[15px] font-semibold">{skin?.tone as string}</p>
                      <p className="text-[11px] opacity-50 mt-0.5">{skin?.tone_description as string}</p>
                    </div>
                  </div>
                  <p className="text-[11px] font-semibold tracking-[1px] opacity-40 mb-3">추천 컬러</p>
                  <div className="flex gap-2">
                    {recommended.map(c => (
                      <div key={c.name} className="flex flex-col items-center gap-1">
                        <div className="w-8 h-8 rounded-full border border-black/10" style={{ background: c.hex }} />
                        <span className="text-[9px] opacity-50">{c.name}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </Reveal>
              <Reveal delay={0.15}>
                <div className="border border-black/10 p-6">
                  <p className="text-[11px] font-semibold tracking-[1.5px] uppercase opacity-40 mb-5">갭 분석</p>
                  <div className="flex items-center gap-3 mb-5">
                    <span className="text-[13px] font-medium">{gap?.current_type as string}</span>
                    <span className="text-[11px] opacity-30">→</span>
                    <span className="text-[13px] font-medium">{gap?.aspiration_type as string}</span>
                  </div>
                  <div className="space-y-3">
                    {directionItems.map(d => (
                      <div key={d.label}>
                        <div className="flex justify-between mb-1">
                          <span className="text-[12px] font-medium">{d.label}</span>
                          <span className="text-[10px] opacity-40">{d.difficulty}</span>
                        </div>
                        <div className="relative h-1 bg-black/[0.06] rounded-sm">
                          <div className="absolute top-1/2 w-2 h-2 rounded-full bg-fg" style={{ left: `${(d.from_score + 1) / 2 * 100}%`, transform: "translateX(-50%) translateY(-50%)" }} />
                          <div className="absolute top-1/2 w-2 h-2 rounded-full border-2 border-fg bg-transparent" style={{ left: `${(d.to_score + 1) / 2 * 100}%`, transform: "translateX(-50%) translateY(-50%)" }} />
                        </div>
                        <div className="flex justify-between mt-1 text-[10px] opacity-30">
                          <span>{d.label_low}</span>
                          <span>{d.label_high}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </Reveal>
              <Reveal delay={0.2}>
                <div className="border border-black/10 p-6">
                  <p className="text-[11px] font-semibold tracking-[1.5px] uppercase opacity-40 mb-5">헤어 추천</p>
                  {topCombo && (
                    <p className="text-[13px] font-semibold mb-4">{topCombo.front.name_kr} + {topCombo.back.name_kr}</p>
                  )}
                  {catalog && (
                    <div className="grid grid-cols-3 gap-3">
                      <div className="flex flex-col">
                        <div className="relative aspect-[3/4] w-full overflow-hidden bg-black/[0.03] mb-2">
                          <Image src={topCombo?.front.image || catalog.front[3].image} alt={topCombo?.front.name_kr || ""} fill className="object-cover" sizes="(max-width: 768px) 30vw, 15vw" />
                          <span className="absolute top-1.5 left-1.5 text-[8px] font-bold bg-fg text-bg px-1.5 py-0.5">앞머리</span>
                        </div>
                        <p className="text-[11px] font-semibold leading-tight">{topCombo?.front.name_kr || catalog.front[3].name_kr}</p>
                      </div>
                      {[catalog.back[1], catalog.back[10]].map((style) => (
                        <div key={style.id} className="flex flex-col">
                          <div className="relative aspect-[3/4] w-full overflow-hidden bg-black/[0.03] mb-2">
                            <Image src={style.image_front} alt={style.name_kr} fill className="object-cover" sizes="(max-width: 768px) 30vw, 15vw" />
                            <span className="absolute top-1.5 left-1.5 text-[8px] font-bold bg-fg text-bg px-1.5 py-0.5">뒷머리</span>
                          </div>
                          <p className="text-[11px] font-semibold leading-tight">{style.name_kr}</p>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="mt-4 pt-3 border-t border-black/[0.06]">
                    <p className="text-[11px] opacity-40">앞머리 8종 + 뒷머리 13종에서 얼굴형에 최적화된 조합 추천</p>
                  </div>
                </div>
              </Reveal>
            </div>
          );
        })()}
      </section>

      <div className="h-px bg-black/[0.15] mx-[var(--spacing-page-x-mobile)] md:mx-[var(--spacing-page-x)]" />

      {/* ── PRICING ── */}
      <section className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-7 md:py-10">
        <Reveal>
          <Row
            c1={
              <span className="block text-[11px] font-semibold tracking-[1.5px] opacity-35">
                PRICING
              </span>
            }
            c2={
              <p className="font-[family-name:var(--font-serif)] text-[clamp(16px,2vw,24px)] font-normal leading-[1.4]">
                선택하세요.
              </p>
            }
            c3={
              <div>
                {TIERS.map((t, i) => (
                  <div
                    key={t.label}
                    className={`grid grid-cols-1 md:grid-cols-[1fr_2fr_auto] gap-3 md:gap-5 items-center py-6 ${i < TIERS.length - 1 ? "border-b border-black/[0.06]" : ""}`}
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-bold tracking-[2px]">{t.label}</span>
                        {"rec" in t && t.rec && (
                          <span className="text-[9px] font-bold tracking-[1.5px] px-2 py-0.5 bg-fg text-bg">{t.rec}</span>
                        )}
                      </div>
                      <div className="flex items-baseline gap-2 mt-2">
                        <span className="font-[family-name:var(--font-serif)] text-[24px] font-semibold">{t.price}</span>
                        {"original" in t && t.original && (
                          <span className="text-[13px] opacity-30 line-through">{t.original}</span>
                        )}
                      </div>
                    </div>
                    <p className="text-[14px] opacity-50 leading-[1.6]">{t.desc}</p>
                    <Link
                      href="/start"
                      className={`inline-block px-6 py-3 text-[12px] font-semibold tracking-[0.3px] text-center whitespace-nowrap no-underline transition-opacity hover:opacity-80 ${
                        t.featured ? "bg-fg text-bg" : "bg-transparent text-fg border border-black/[0.12]"
                      }`}
                    >
                      {t.cta}
                    </Link>
                  </div>
                ))}

                {/* 인라인 안내 */}
                <div className="mt-6 pt-5 border-t border-black/[0.06]">
                  <p className="text-[12px] opacity-30 leading-[1.8]">
                    셀카 한 장 · 5분 설문 · 24시간 내 결과
                  </p>
                </div>
              </div>
            }
          />
        </Reveal>
      </section>

      {/* ════════════════════════════════════════════
          보조 구간 (더 스크롤하면)
          ════════════════════════════════════════════ */}

      <div className="h-px bg-black/[0.15] mx-[var(--spacing-page-x-mobile)] md:mx-[var(--spacing-page-x)]" />

      {/* ── Method — 3축 갤러리 ── */}
      <section id="method" className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-7 md:py-10">
        <Reveal>
          <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_2fr] gap-3 md:gap-6 items-start mb-10">
            <div><h2 className="text-[clamp(18px,2.5vw,28px)] font-extrabold tracking-[1px] leading-[1.3]">Method</h2></div>
            <div><p className="font-[family-name:var(--font-serif)] text-[clamp(16px,2vw,24px)] font-normal leading-[1.4]">미감의 세 방향</p></div>
            <div><p className="text-[15px] leading-[1.7] opacity-70">세 가지 축이 만들어내는 미감의 좌표. 각 방향은 고정된 유형이 아니라, 당신이 이동할 수 있는 공간입니다.</p></div>
          </div>
        </Reveal>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-0.5">
          {GALLERY.map((item, i) => (
            <Reveal key={item.id} delay={i * 0.12}>
              <div>
                <div className="relative aspect-[2/3] w-[70%] mx-auto overflow-hidden">
                  <Image src={item.src} alt={item.alt} fill className="object-contain" sizes="(max-width: 640px) 70vw, 23vw" />
                </div>
                <div className="pt-5 pb-2">
                  <h3 className="font-[family-name:var(--font-serif)] text-sm font-normal mb-1.5">{item.axis}</h3>
                  <p className="text-[11px] opacity-50 leading-[1.6]">{item.desc}</p>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      <div className="h-px bg-black/[0.15] mx-[var(--spacing-page-x-mobile)] md:mx-[var(--spacing-page-x)]" />

      {/* ── Casting — /casting 링크 ── */}
      <section id="casting" className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-7 md:py-10">
        <Reveal>
          <Row
            c1={<h2 className="text-[clamp(18px,2.5vw,28px)] font-extrabold tracking-[1px] leading-[1.3]">Casting</h2>}
            c2={
              <p className="font-[family-name:var(--font-serif)] text-[clamp(16px,2vw,24px)] font-normal leading-[1.4]">
                분석을 넘어,<br />기회로 연결
              </p>
            }
            c3={
              <div>
                <p className="text-[15px] leading-[1.7] opacity-70 mb-6">
                  동의한 유저에 한해, 에이전시와 브랜드가 좌표 기반으로 적합한 인재를 탐색합니다. 개인정보는 수락 전까지 공유되지 않습니다.
                </p>
                <Link
                  href="/casting"
                  className="inline-block px-6 py-3 text-[12px] font-semibold tracking-[0.3px] border border-black/[0.12] no-underline transition-opacity hover:opacity-60"
                >
                  캐스팅 자세히 보기 →
                </Link>
              </div>
            }
          />
        </Reveal>
      </section>

      <div className="h-px bg-black/[0.15] mx-[var(--spacing-page-x-mobile)] md:mx-[var(--spacing-page-x)]" />

      {/* ── Team ── */}
      <section id="team" className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-7 md:py-10">
        <Reveal>
          <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_2fr] gap-3 md:gap-6 items-start mb-10">
            <div><h2 className="text-[clamp(18px,2.5vw,28px)] font-extrabold tracking-[1px] leading-[1.3]">Team</h2></div>
            <div><p className="font-[family-name:var(--font-serif)] text-[clamp(16px,2vw,24px)] font-normal leading-[1.4]">기술과 미감,<br />양쪽을 읽는 팀</p></div>
            <div><p className="text-[15px] leading-[1.7] opacity-70">컴퓨터 비전 엔지니어와 미감 전문가가 함께 만듭니다. 얼굴 구조를 정밀하게 분석하는 영상처리 기술 위에, 미감의 맥락을 읽는 전문가의 해석이 더해집니다.</p></div>
          </div>
        </Reveal>
        <div className="grid grid-cols-2 md:grid-cols-4 border border-black/10">
          {TEAM.map((m, i) => (
            <Reveal key={m.role} delay={i * 0.08}>
              <div className={`flex flex-col px-7 py-6 ${i < 3 ? "border-r border-black/10" : ""} ${i === 1 ? "max-md:border-r-0" : ""}`}>
                <span className="text-[11px] font-semibold tracking-[1px] opacity-40 mb-2.5">{m.role}</span>
                <span className="text-[12px] leading-[1.6] opacity-70">{m.focus}</span>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-8 md:py-10 border-t border-black/10">
        <div className="max-w-3xl mx-auto">
          <div className="flex flex-wrap gap-x-6 gap-y-1 text-[11px] opacity-40 mb-4">
            <Link href="/terms" className="hover:opacity-70 transition-opacity">이용약관</Link>
            <Link href="/terms" className="hover:opacity-70 transition-opacity">개인정보처리방침</Link>
            <Link href="/refund" className="hover:opacity-70 transition-opacity">환불규정</Link>
            <a href="mailto:partner@sigak.asia" className="hover:opacity-70 transition-opacity">partner@sigak.asia</a>
          </div>
          <p className="text-[10px] leading-[1.8] opacity-25">
            주식회사 시각 | 대표: 조찬형 | partner@sigak.asia<br />
            &copy; 2026 SIGAK. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
