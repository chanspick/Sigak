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
  { id: "cat", src: "/images/sculptures/cat.png", alt: "고양이 조각상", axis: "부드러운 · 생기있는", desc: "경쾌한 톤과 자연스러운 곡선. 가볍지만 또렷한 인상이 전하는 편안한 호감." },
  { id: "fox", src: "/images/sculptures/fox.png", alt: "여우 조각상", axis: "성숙한 · 강렬한", desc: "깊은 인상과 강렬한 구조. 시간이 쌓아올린 무게감과 세련된 존재감." },
] as const;
const PROCESS = [
  { step: "01", title: "셀카 업로드", desc: "정면 사진 1장과 간단한 설문. 추구하는 이미지, 레퍼런스, 현재 고민을 자유롭게." },
  { step: "02", title: "AI 좌표 분석", desc: "얼굴 구조, 피부톤, 스타일 취향을 3축 좌표계에 매핑해요." },
  { step: "03", title: "맞춤 리포트", desc: "현재 위치에서 추구미까지의 구체적 경로. 메이크업, 헤어, 스타일링 실행 가이드." },
] as const;
const TEAM = [
  { role: "CV / ML Engineer", focus: "얼굴 구조 분석, 미감 좌표계 설계, 영상처리 파이프라인" },
  { role: "Aesthetic Director", focus: "트렌드 분석, 미감 해석, 리포트 큐레이션" },
  { role: "Product Designer", focus: "사용자 경험 설계, 리포트 시각화" },
  { role: "Growth Lead", focus: "시장 검증, B2B 매칭, 데이터 전략" },
] as const;

export default function HomePage() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  useEffect(() => { setIsLoggedIn(!!localStorage.getItem("sigak_user_id")); }, []);

  return (
    <div className="min-h-screen bg-bg text-fg antialiased">
      <nav className="sticky top-0 z-[100] relative flex items-center justify-between px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] h-[60px] bg-fg text-bg">
        <div className="hidden md:flex items-center gap-7">
          {["About", "Method", "Team", "Casting"].map((t) => (
            <a key={t} href={`#${t.toLowerCase()}`} className="text-[11px] font-medium tracking-[2.5px] uppercase opacity-70 transition-opacity duration-200 hover:opacity-100">{t}</a>
          ))}
        </div>
        <span className="absolute left-1/2 -translate-x-1/2 text-[13px] font-semibold tracking-[6px] uppercase pointer-events-none">SIGAK</span>
        <div className="flex items-center gap-5">
          {isLoggedIn && (
            <Link href="/my" className="text-[11px] font-medium tracking-[1.5px] uppercase opacity-70 transition-opacity duration-200 hover:opacity-100 no-underline text-[var(--color-bg)]">내 리포트</Link>
          )}
          {isLoggedIn && <NotificationBell />}
          <Link href="/start" className="text-[11px] font-medium tracking-[2.5px] uppercase opacity-70 transition-opacity duration-200 hover:opacity-100">진단 시작</Link>
        </div>
      </nav>
      <section className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] pt-10 pb-8 md:pt-[60px] md:pb-12"><Reveal><div className="grid grid-cols-1 md:grid-cols-2 gap-10 md:gap-16 items-end"><div>
              <h1 className="font-[family-name:var(--font-serif)] text-[clamp(32px,5vw,52px)] font-normal leading-[1.35] tracking-[-0.01em]">
                미감을<br />좌표로 읽다
              </h1>
              <p className="mt-5 text-[15px] leading-[1.7] opacity-50">
                당신의 얼굴, 취향, 트렌드를 하나의 공간에 배치합니다.<br />
                현재 위치에서 추구하는 방향까지 — 구체적 경로를 설계합니다.
              </p>
              <div className="mt-8 flex items-center gap-6">
                <Link href="/start" className="text-sm font-medium transition-opacity duration-200 hover:opacity-50">→ 내 좌표 확인하기</Link>
                <a href="#about" className="text-sm opacity-40">↓ 더 알아보기</a>
              </div>
            </div><div className="relative aspect-[2/3] w-[60%] ml-auto overflow-hidden"><Image src="/images/sculptures/deer.png" alt="사슴 조각상" fill className="object-contain" sizes="(max-width: 768px) 60vw, 30vw" priority /></div></div></Reveal></section>
      <Reveal><section className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-8 md:py-12"><div className="grid grid-cols-2 md:grid-cols-4 border border-black/10">
            {(["3축", "AI 분석", "24hr", "맞춤형"] as const).map((num, i) => (
              <div key={num} className={`flex flex-col px-7 py-6 ${i < 3 ? "border-r border-black/10" : ""} ${i === 1 ? "max-md:border-r-0" : ""}`}>
                <span className="text-[11px] font-semibold tracking-[1px] opacity-40 mb-2.5">
                  {["좌표계", "얼굴 구조", "리포트 딜리버리", "스타일링 가이드"][i]}
                </span>
                <span className="font-[family-name:var(--font-serif)] text-[clamp(28px,4vw,48px)] font-light leading-none">
                  {num}
                </span>
              </div>
            ))}
          </div></section></Reveal>
      <section id="about" className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-7 md:py-10">
        <Reveal><div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_2fr] gap-3 md:gap-6 items-start"><div>
              <h2 className="text-[clamp(18px,2.5vw,28px)] font-extrabold tracking-[1px] leading-[1.3]">About</h2>
            </div>
            <div>
              <p className="font-[family-name:var(--font-serif)] text-[clamp(16px,2vw,24px)] font-normal leading-[1.4]">라벨이 아닌,<br />좌표를 드립니다</p>
            </div>
            <div>
              <p className="text-[15px] leading-[1.7] opacity-70">기존 진단은 &ldquo;쿨톤이에요&rdquo;, &ldquo;가을 웜이에요&rdquo; 같은 고정 라벨을 붙여줍니다. 하지만 미감은 고정되지 않아요 — 트렌드에 따라 이동하고, 취향에 따라 방향이 달라집니다. SIGAK은 당신의 얼굴 구조, 피부톤, 스타일 취향을 다차원 좌표계 위에 배치합니다. 현재 위치와 추구하는 방향 사이의 차이가 곧 구체적인 실행 가이드가 됩니다.</p>
            </div>
            </div>
        </Reveal>
      </section>

      {/* REPORT PREVIEW — Mock Report 기반 샘플 */}
      <section className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-7 md:py-10 border-t border-black/10">
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
              {/* 얼굴 구조 지표 */}
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

              {/* 퍼스널 컬러 */}
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

              {/* 갭 분석 */}
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

              {/* 헤어 추천 */}
              <Reveal delay={0.2}>
                <div className="border border-black/10 p-6">
                  <p className="text-[11px] font-semibold tracking-[1.5px] uppercase opacity-40 mb-5">헤어 추천</p>
                  {topCombo && (
                    <p className="text-[13px] font-semibold mb-4">{topCombo.front.name_kr} + {topCombo.back.name_kr}</p>
                  )}
                  {catalog && (
                    <div className="grid grid-cols-3 gap-3">
                      {/* 추천 앞머리 */}
                      <div className="flex flex-col">
                        <div className="relative aspect-[3/4] w-full overflow-hidden bg-black/[0.03] mb-2">
                          <Image src={topCombo?.front.image || catalog.front[3].image} alt={topCombo?.front.name_kr || ""} fill className="object-cover" sizes="(max-width: 768px) 30vw, 15vw" />
                          <span className="absolute top-1.5 left-1.5 text-[8px] font-bold bg-fg text-bg px-1.5 py-0.5">앞머리</span>
                        </div>
                        <p className="text-[11px] font-semibold leading-tight">{topCombo?.front.name_kr || catalog.front[3].name_kr}</p>
                      </div>
                      {/* 카탈로그 뒷머리 2종 (서로 다른 길이) */}
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

        <Reveal delay={0.25}>
          <div className="mt-8 text-center">
            <Link href="/start" className="text-sm font-medium transition-opacity duration-200 hover:opacity-50">
              → 내 리포트 받아보기
            </Link>
          </div>
        </Reveal>
      </section>

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
      <section className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-7 md:py-10 border-t border-black/10">
        <Reveal>
          <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_2fr] gap-3 md:gap-6 items-start mb-10">
            <div><h2 className="text-[clamp(18px,2.5vw,28px)] font-extrabold tracking-[1px] leading-[1.3]">Process</h2></div>
            <div><p className="font-[family-name:var(--font-serif)] text-[clamp(16px,2vw,24px)] font-normal leading-[1.4]">셀카 한 장에서<br />리포트까지</p></div>
            <div />
          </div>
        </Reveal>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-10">
              {PROCESS.map((item, i) => (
                <Reveal key={item.step} delay={i * 0.15}>
                  <div>
                    <div className="font-[family-name:var(--font-serif)] text-[clamp(32px,4vw,48px)] font-light leading-none opacity-20 mb-4">{item.step}</div>
                    <h3 className="text-[15px] font-semibold mb-2.5">{item.title}</h3>
                    <p className="text-[12px] leading-[1.8] opacity-50">{item.desc}</p>
                  </div>
                </Reveal>
              ))}
        </div>
      </section>
      <section id="team" className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-7 md:py-10 border-t border-black/10">
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
      <section id="casting" className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-7 md:py-10 border-t border-black/10">
        <Reveal>
          <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_2fr] gap-3 md:gap-6 items-start mb-10">
            <div><h2 className="text-[clamp(18px,2.5vw,28px)] font-extrabold tracking-[1px] leading-[1.3]">Casting</h2></div>
            <div><p className="font-[family-name:var(--font-serif)] text-[clamp(16px,2vw,24px)] font-normal leading-[1.4]">분석을 넘어,<br />기회로 연결</p></div>
            <div><p className="text-[15px] leading-[1.7] opacity-70">SIGAK의 분석 데이터는 개인 스타일링에서 끝나지 않습니다. 동의한 유저에 한해, 에이전시와 브랜드가 좌표 기반으로 적합한 인재를 탐색할 수 있는 캐스팅 풀을 운영합니다.</p></div>
          </div>
        </Reveal>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          {[
            { num: "01", title: "옵트인 동의", desc: "풀 리포트 하단에서 캐스팅 풀 참여를 선택할 수 있어요. 언제든 해제 가능합니다." },
            { num: "02", title: "매칭 제안", desc: "에이전시가 좌표·얼굴형·이미지 유형으로 검색 후, 목적과 출연료를 포함한 제안을 보냅니다." },
            { num: "03", title: "수락 또는 거절", desc: "초대장을 확인하고 수락하면 연락처와 리포트 요약이 전달됩니다. 거절 시 정보는 공유되지 않아요." },
          ].map((item, i) => (
            <Reveal key={item.num} delay={i * 0.12}>
              <div>
                <div className="font-[family-name:var(--font-serif)] text-[clamp(32px,4vw,48px)] font-light leading-none opacity-20 mb-4">{item.num}</div>
                <h3 className="text-[15px] font-semibold mb-2.5">{item.title}</h3>
                <p className="text-[12px] leading-[1.8] opacity-50">{item.desc}</p>
              </div>
            </Reveal>
          ))}
        </div>

        {/* 초대장 미리보기 */}
        <Reveal delay={0.3}>
          <div className="mt-10 flex justify-center">
            <div className="w-full max-w-[300px] border border-black/10 select-none">
              <div className="bg-fg text-bg px-6 py-6 text-center">
                <p className="text-[7px] tracking-[5px] uppercase opacity-40 mb-2">You are invited</p>
                <p className="font-[family-name:var(--font-serif)] text-[14px] font-normal leading-snug">캐스팅 제안이<br />도착했습니다</p>
              </div>
              <div className="px-6 py-5">
                <p className="text-[8px] text-black/30 tracking-[2px] uppercase mb-1">From</p>
                <p className="text-[14px] font-bold mb-4">YG Entertainment</p>
                <div className="flex gap-4 mb-4">
                  <div className="flex-1">
                    <p className="text-[8px] text-black/30 tracking-[2px] uppercase mb-1">Purpose</p>
                    <p className="text-[11px]">뮤직비디오 출연</p>
                  </div>
                  <div>
                    <p className="text-[8px] text-black/30 tracking-[2px] uppercase mb-1">Fee</p>
                    <p className="text-[11px] font-semibold">₩500,000</p>
                  </div>
                </div>
                <div className="w-full h-px bg-black/10 mb-4" />
                <div className="flex gap-2">
                  <div className="flex-1 py-2 text-center text-[10px] font-semibold bg-fg text-bg">수락하기</div>
                  <div className="flex-1 py-2 text-center text-[10px] border border-black/10 text-black/30">괜찮습니다</div>
                </div>
              </div>
            </div>
          </div>
        </Reveal>
      </section>

      <Reveal>
        <Link href="/start" className="block px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-10 md:py-14 text-center group border-t border-black/10">
          <p className="font-[family-name:var(--font-serif)] text-[clamp(16px,2vw,24px)] font-normal leading-[1.4] opacity-50 mb-3">셀카 한 장과 5분의 설문으로</p>
          <p className="text-[clamp(24px,4vw,40px)] font-bold tracking-[1px] transition-opacity duration-200 group-hover:opacity-50">
            → 진단 시작하기
          </p>
          <p className="mt-3 text-[11px] opacity-30"><span className="line-through mr-1">₩5,000</span>₩2,900부터</p>
        </Link>
      </Reveal>
      <footer className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-6 md:py-8 text-center border-t border-black/10">
        <span className="text-[11px] tracking-[1.5px] opacity-30">
          &copy; 2026 시각(SIGAK). ALL RIGHTS RESERVED
        </span>
      </footer>
    </div>
  );
}
