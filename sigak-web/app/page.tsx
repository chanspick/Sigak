"use client";

import { useState, useEffect, useRef, useCallback, type ReactNode } from "react";
import Image from "next/image";
import Link from "next/link";
import { BookingOverlay } from "@/components/landing/booking-overlay";
import type { Tier } from "@/lib/types/tier";

function Reveal({ children, delay = 0, className = "" }: { children: ReactNode; delay?: number; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => { const el = ref.current; if (!el) return; const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setVisible(true); obs.disconnect(); } }, { threshold: 0.15 }); obs.observe(el); return () => obs.disconnect(); }, []);
  return (<div ref={ref} className={className} style={{ opacity: visible ? 1 : 0, transform: visible ? "translateY(0)" : "translateY(28px)", transition: `opacity 0.9s ease ${delay}s, transform 0.9s ease ${delay}s` }}>{children}</div>);
}

const GALLERY = [
  { id: "hawk", src: "/images/sculptures/hawk.webp", alt: "매 조각상", axis: "샤프 · 쿨글램", desc: "강렴한 인상과 선명한 윤곽. 도시적 세련미와 대담한 구조가 만들어내는 압도적 아우라." },
  { id: "cat", src: "/images/sculptures/cat.webp", alt: "고양이 조각상", axis: "소프트 · 프레시", desc: "경쾌한 톤과 자연스러운 곡선. 가볍지만 또렷한 인상이 전하는 편안한 호감." },
  { id: "wolf", src: "/images/sculptures/wolf.webp", alt: "늑대 조각상", axis: "성숙 · 시크", desc: "깊은 인상과 볼드한 구조. 시간이 쌍아올린 무게감과 세련된 존재감." },
] as const;
const PROCESS = [
  { step: "01", title: "셀카 업로드", desc: "정면 사진 1장과 간단한 설문. 추구하는 이미지, 레퍼런스, 현재 고민을 자유롭게." },
  { step: "02", title: "AI 좌표 분석", desc: "얼굴 구조, 피부톤, 스타일 취향을 3축 좌표계에 매핑. 트렌드 데이터와 교차 분석." },
  { step: "03", title: "맞춤 리포트", desc: "현재 위치에서 추구미까지의 구체적 경로. 메이크업, 헤어, 스타일링 실행 가이드." },
] as const;
const TEAM = [
  { role: "CV / ML Engineer", focus: "얼굴 구조 분석, 미감 좌표계 설계, 영상처리 파이프라인" },
  { role: "Aesthetic Director", focus: "트렌드 분석, 미감 해석, 리포트 큐레이션" },
  { role: "Product Designer", focus: "사용자 경험 설계, 리포트 시각화" },
  { role: "Growth Lead", focus: "시장 검증, B2B 매칭, 데이터 전략" },
] as const;
const AXES = [
  { label: "인상", left: "소프트", right: "샤프", current: 0.35, target: 0.7 },
  { label: "톤", left: "웰내추럴", right: "쿨글램", current: 0.6, target: 0.8 },
  { label: "무드", left: "프레시큐트", right: "성숙시크", current: 0.45, target: 0.65 },
] as const;

export default function HomePage() {
  const [scrollY, setScrollY] = useState(0);
  const [overlayOpen, setOverlayOpen] = useState(false);
  const [overlayTier, setOverlayTier] = useState<Tier["id"] | null>(null);
  useEffect(() => { const onScroll = () => setScrollY(window.scrollY); window.addEventListener("scroll", onScroll, { passive: true }); return () => window.removeEventListener("scroll", onScroll); }, []);
  const book = useCallback((tierId?: Tier["id"]) => { setOverlayTier(tierId ?? null); setOverlayOpen(true); }, []);
  const navScrolled = scrollY > 60;
  return (
    <div className="min-h-screen bg-bg text-fg antialiased">
      <nav className="fixed top-0 left-0 right-0 z-[100] transition-all duration-300" style={{ background: navScrolled ? "rgba(243,240,235,0.92)" : "transparent", borderBottom: navScrolled ? "1px solid var(--color-border)" : "1px solid transparent", backdropFilter: navScrolled ? "blur(12px)" : "none" }}><div className="mx-auto flex max-w-[1200px] items-center justify-between px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] h-14"><span className="text-[13px] font-bold tracking-[6px] uppercase">SIGAK</span><div className="hidden md:flex items-center gap-8">{["About", "Method", "Team"].map((t) => (<a key={t} href={`#${t.toLowerCase()}`} className="text-[11px] tracking-[2px] uppercase text-muted hover:text-fg transition-colors duration-200">{t}</a>))}</div><div className="flex items-center gap-5"><button onClick={() => book()} className="hidden md:inline text-[11px] tracking-[2px] uppercase text-muted hover:text-fg transition-colors duration-200 bg-transparent border-none cursor-pointer">예약</button><Link href="/start" className="text-[11px] tracking-[2px] uppercase font-semibold px-5 py-2 bg-fg text-bg rounded-full hover:opacity-80 transition-opacity duration-200">진단 시작</Link></div></div></nav>
      <section className="relative flex min-h-screen flex-col items-center justify-center px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] pt-[120px] pb-20"><div className="mx-auto grid w-full max-w-[1200px] grid-cols-1 md:grid-cols-2 items-center gap-10 md:gap-[60px]"><div><div className="text-[10px] font-semibold tracking-[5px] uppercase text-muted mb-6">Aesthetic Coordinate System</div><h1 className="font-[family-name:var(--font-serif)] text-[clamp(36px,5vw,56px)] font-normal leading-[1.3] mb-6">미감을<br />좌표로 읽다</h1><p className="text-[15px] leading-[1.8] text-muted max-w-[400px] mb-10">당신의 얼굴, 취향, 트렌드를 하나의 공간에 배치합니다. 현재 위치에서 추구하는 방향까지 — 구체적 경로를 설계합니다.</p><div className="flex items-center gap-4 flex-wrap"><Link href="/start" className="px-9 py-3.5 bg-fg text-bg text-[13px] font-semibold tracking-[1px] hover:opacity-80 transition-opacity duration-200">내 좌표 확인하기</Link><a href="#about" className="text-[12px] text-muted tracking-[1px] border-b border-border pb-0.5 hover:text-fg transition-colors duration-200">더 알아보기 →</a></div></div><div className="relative aspect-[3/4] w-full bg-[#E8E5DF] overflow-hidden"><Image src="/images/sculptures/deer.webp" alt="사슴 조각상" fill className="object-cover" sizes="(max-width: 768px) 100vw, 50vw" priority /></div></div><div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 transition-opacity duration-500" style={{ opacity: scrollY > 100 ? 0 : 0.4 }}><div className="w-px h-8 bg-fg" /><span className="text-[9px] tracking-[3px] uppercase">Scroll</span></div></section>
      <Reveal><section className="mx-auto max-w-[1200px] grid grid-cols-2 md:grid-cols-4 border-y border-border">{([["12,400+", "미감 데이터 분석"], ["3축", "좌표계 매핑"], ["24hr", "리포트 딜리버리"], ["93%", "만족도"]] as const).map(([num, desc], i) => (<div key={desc} className={`py-9 px-6 text-center ${i < 3 ? "border-r border-border" : ""} ${i === 1 ? "max-md:border-r-0" : ""}`}><div className="font-[family-name:var(--font-serif)] text-[28px] font-normal mb-1.5">{num}</div><div className="text-[10px] tracking-[2px] text-muted uppercase">{desc}</div></div>))}</section></Reveal>
      <section id="about" className="mx-auto max-w-[1200px] px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-[120px]"><Reveal><div className="grid grid-cols-1 md:grid-cols-[1fr_1.2fr] gap-10 md:gap-20 items-start"><div>
              <div className="text-[10px] font-semibold tracking-[5px] uppercase text-muted mb-4">About SIGAK</div>
              <h2 className="font-[family-name:var(--font-serif)] text-[clamp(28px,3.5vw,40px)] font-normal leading-[1.4] mb-8">라벨이 아닌,<br />좌표를 드립니다</h2>
              <p className="text-sm leading-[2] text-muted mb-0">기존 이미지 컨설팅은 쿨톤, 봄웰, 내추럴 같은 고정된 라벨을 붙여줍니다. 하지만 미감은 고정되지 않습니다 — 트렌드에 따라 이동하고, 취향에 따라 방향이 달라집니다.</p>
              <div className="my-8 border-t border-border" />
              <p className="text-sm leading-[2] text-muted">SIGAK은 당신의 얼굴 구조, 피부톤, 스타일 취향을 다차원 좌표계 위에 배치합니다. 현재 위치와 추구하는 방향 사이의 차이가 곧 구체적인 실행 가이드가 됩니다.</p>
            </div>
            <div className="bg-[#E8E5DF] p-8 md:p-12 relative">
              <div className="text-[10px] tracking-[4px] text-muted uppercase mb-8">3-Axis Coordinate Preview</div>
              <div className="space-y-0">
                {AXES.map((axis) => (
                  <div key={axis.label} className="py-5 border-b border-border last:border-b-0">
                    <div className="text-xs tracking-[0.15em] text-muted mb-3 font-medium">{axis.label}</div>
                    <div className="relative h-1 bg-black/[0.08] rounded-sm">
                      <div className="absolute top-1/2 w-2.5 h-2.5 rounded-full bg-fg" style={{ left: `${axis.current * 100}%`, transform: "translateX(-50%) translateY(-50%)" }} />
                      <div className="absolute top-1/2 w-2.5 h-2.5 rounded-full border-2 border-fg bg-transparent" style={{ left: `${axis.target * 100}%`, transform: "translateX(-50%) translateY(-50%)" }} />
                    </div>
                    <div className="flex justify-between mt-2 text-[10px] text-muted"><span>{axis.left}</span><span>{axis.right}</span></div>
                  </div>
                ))}
              </div>
              <div className="mt-5 flex gap-4 text-[10px] text-muted">
                <span className="flex items-center gap-1.5"><span className="inline-block w-2 h-2 rounded-full bg-fg" />현재 위치</span>
                <span className="flex items-center gap-1.5"><span className="inline-block w-2 h-2 rounded-full border-2 border-fg" />추구미</span>
              </div>
            </div>
          </div>
        </Reveal>
      </section>
      <section id="method" className="mx-auto max-w-[1200px] px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] pb-[120px]">
        <Reveal>
          <div className="text-[10px] font-semibold tracking-[5px] uppercase text-muted mb-4">The Three Dimensions</div>
          <h2 className="font-[family-name:var(--font-serif)] text-[clamp(28px,3.5vw,40px)] font-normal leading-[1.4] mb-12">미감의 세 방향</h2>
        </Reveal>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-0.5">
          {GALLERY.map((item, i) => (
            <Reveal key={item.id} delay={i * 0.12}>
              <div>
                <div className="relative aspect-[3/4] w-full bg-[#E8E5DF] overflow-hidden">
                  <Image src={item.src} alt={item.alt} fill className="object-cover" sizes="(max-width: 640px) 100vw, 33vw" />
                </div>
                <div className="pt-5 pb-2">
                  <h3 className="font-[family-name:var(--font-serif)] text-sm font-normal mb-1.5">{item.axis}</h3>
                  <p className="text-[11px] text-muted leading-[1.6]">{item.desc}</p>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </section>
      <section className="border-t border-border mx-auto max-w-[1200px] px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-[100px]">
        <Reveal>
          <div className="grid grid-cols-1 md:grid-cols-[0.4fr_1fr] gap-10 md:gap-20">
            <div>
              <div className="text-[10px] font-semibold tracking-[5px] uppercase text-muted mb-4">Process</div>
              <h2 className="font-[family-name:var(--font-serif)] text-[28px] font-normal leading-[1.4]">셀카 한 장에서<br />리포트까지</h2>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-10">
              {PROCESS.map((item, i) => (
                <Reveal key={item.step} delay={i * 0.15}>
                  <div>
                    <div className="font-[family-name:var(--font-serif)] text-[32px] font-light text-border mb-4">{item.step}</div>
                    <h3 className="text-[15px] font-semibold mb-2.5">{item.title}</h3>
                    <p className="text-[12px] leading-[1.8] text-muted">{item.desc}</p>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </Reveal>
      </section>
      <section id="team" className="border-t border-border mx-auto max-w-[1200px] px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-[100px]">
        <Reveal>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-10 md:gap-20">
            <div>
              <div className="text-[10px] font-semibold tracking-[5px] uppercase text-muted mb-4">Team</div>
              <h2 className="font-[family-name:var(--font-serif)] text-[28px] font-normal leading-[1.4] mb-8">기술과 미감,<br />양쪽을 읽는 팀</h2>
              <p className="text-sm leading-[2] text-muted">컴퓨터 비전 엔지니어와 미감 전문가가 함께 만듭니다. 얼굴 구조를 정밀하게 분석하는 영상처리 기술 위에, 미감의 맥락을 읽는 전문가의 해석이 더해집니다.</p>
            </div>
            <div className="grid grid-cols-2 gap-0.5">
              {TEAM.map((m) => (
                <div key={m.role} className="bg-[#E8E5DF] p-7 flex flex-col justify-end min-h-[160px]">
                  <div className="text-[10px] tracking-[2px] text-muted uppercase mb-2">{m.role}</div>
                  <div className="text-[12px] text-muted leading-[1.6]">{m.focus}</div>
                </div>
              ))}
            </div>
          </div>
        </Reveal>
      </section>
      <section id="cta" className="border-t border-border px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-[120px] text-center">
        <Reveal>
          <div className="mx-auto max-w-[520px]">
            <div className="text-[10px] font-semibold tracking-[5px] uppercase text-muted mb-5">Start Now</div>
            <h2 className="font-[family-name:var(--font-serif)] text-[clamp(28px,4vw,44px)] font-normal leading-[1.3] mb-5">내 미감 좌표를<br />확인해보세요</h2>
            <p className="text-sm text-muted leading-[1.8] mb-9">셀카 한 장과 5분의 설문으로<br />당신만의 미감 리포트를 받아보세요.</p>
            <Link href="/start" className="inline-block px-12 py-4 bg-fg text-bg text-sm font-semibold tracking-[2px] hover:opacity-80 transition-opacity duration-200">진단 시작하기</Link>
            <div className="mt-4 text-[11px] text-border">₩5,000부터</div>
          </div>
        </Reveal>
      </section>
      <footer className="border-t border-border mx-auto max-w-[1200px] px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-10 flex flex-col sm:flex-row justify-between items-center gap-4">
        <span className="text-[11px] tracking-[4px] font-bold uppercase">SIGAK</span>
        <span className="text-[10px] text-border tracking-[1px]">&copy; 2026 SIGAK. All rights reserved.</span>
      </footer>
      <BookingOverlay key={overlayTier} open={overlayOpen} onClose={() => setOverlayOpen(false)} initTier={overlayTier} />
    </div>
  );
}
