"use client";

import { useState, useEffect, useRef, type ReactNode } from "react";
import Image from "next/image";
import Link from "next/link";

function Reveal({ children, delay = 0, className = "" }: { children: ReactNode; delay?: number; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => { const el = ref.current; if (!el) return; const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setVisible(true); obs.disconnect(); } }, { threshold: 0.15 }); obs.observe(el); return () => obs.disconnect(); }, []);
  return (<div ref={ref} className={className} style={{ opacity: visible ? 1 : 0, transform: visible ? "translateY(0)" : "translateY(28px)", transition: `opacity 0.9s ease ${delay}s, transform 0.9s ease ${delay}s` }}>{children}</div>);
}

const GALLERY = [
  { id: "owl", src: "/images/sculptures/owl.png", alt: "부엉이 조각상", axis: "샤프 · 쿨글램", desc: "강렬한 인상과 선명한 윤곽. 도시적 세련미와 대담한 구조가 만들어내는 압도적 아우라." },
  { id: "cat", src: "/images/sculptures/cat.png", alt: "고양이 조각상", axis: "소프트 · 프레시", desc: "경쾌한 톤과 자연스러운 곡선. 가볍지만 또렷한 인상이 전하는 편안한 호감." },
  { id: "fox", src: "/images/sculptures/fox.png", alt: "여우 조각상", axis: "성숙 · 시크", desc: "깊은 인상과 볼드한 구조. 시간이 쌓아올린 무게감과 세련된 존재감." },
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
  return (
    <div className="min-h-screen bg-bg text-fg antialiased">
      <nav className="sticky top-0 z-[100] flex items-center justify-between px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] h-[60px] bg-fg text-bg">
        <div className="hidden md:flex items-center gap-7">
          {["About", "Method", "Team"].map((t) => (
            <a key={t} href={`#${t.toLowerCase()}`} className="text-[11px] font-medium tracking-[2.5px] uppercase opacity-70 transition-opacity duration-200 hover:opacity-100">{t}</a>
          ))}
        </div>
        <span className="text-[13px] font-semibold tracking-[6px] uppercase">SIGAK</span>
        <div className="flex items-center gap-5">
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
            </div><div className="relative aspect-[3/4] w-full overflow-hidden"><Image src="/images/sculptures/deer.png" alt="사슴 조각상" fill className="object-cover" sizes="(max-width: 768px) 100vw, 50vw" priority /></div></div></Reveal></section>
      <Reveal><section className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-8 md:py-12"><div className="grid grid-cols-2 md:grid-cols-4 border border-black/10">
            {(["12,400+", "3축", "24hr", "93%"] as const).map((num, i) => (
              <div key={num} className={`flex flex-col px-7 py-6 ${i < 3 ? "border-r border-black/10" : ""} ${i === 1 ? "max-md:border-r-0" : ""}`}>
                <span className="text-[11px] font-semibold tracking-[1px] opacity-40 mb-2.5">
                  {["미감 데이터", "좌표계 매핑", "리포트 딜리버리", "만족도"][i]}
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
              <p className="text-[15px] leading-[1.7] opacity-70">기존 이미지 컨설팅은 쿨톤, 봄웰, 내추럴 같은 고정된 라벨을 붙여줍니다. 하지만 미감은 고정되지 않습니다 — 트렌드에 따라 이동하고, 취향에 따라 방향이 달라집니다. SIGAK은 당신의 얼굴 구조, 피부톤, 스타일 취향을 다차원 좌표계 위에 배치합니다. 현재 위치와 추구하는 방향 사이의 차이가 곧 구체적인 실행 가이드가 됩니다.</p>
            </div>
            </div>
        </Reveal>
      </section>

      {/* COORDINATE PREVIEW */}
      <section className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-7 md:py-10">
        <Reveal>
          <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_2fr] gap-3 md:gap-6 items-start">
            <div>
              <h2 className="text-[clamp(18px,2.5vw,28px)] font-extrabold tracking-[1px] leading-[1.3]">Coordinate</h2>
            </div>
            <div>
              <p className="font-[family-name:var(--font-serif)] text-[clamp(16px,2vw,24px)] font-normal leading-[1.4]">3축 좌표계 미리보기</p>
            </div>
            <div>
              <div className="space-y-0">
                {AXES.map((axis) => (
                  <div key={axis.label} className="py-5 border-b border-black/10 last:border-b-0">
                    <div className="text-xs tracking-[0.15em] opacity-40 mb-3 font-medium">{axis.label}</div>
                    <div className="relative h-1 bg-black/[0.08] rounded-sm">
                      <div className="absolute top-1/2 w-2.5 h-2.5 rounded-full bg-fg" style={{ left: `${axis.current * 100}%`, transform: "translateX(-50%) translateY(-50%)" }} />
                      <div className="absolute top-1/2 w-2.5 h-2.5 rounded-full border-2 border-fg bg-transparent" style={{ left: `${axis.target * 100}%`, transform: "translateX(-50%) translateY(-50%)" }} />
                    </div>
                    <div className="flex justify-between mt-2 text-[10px] opacity-40"><span>{axis.left}</span><span>{axis.right}</span></div>
                  </div>
                ))}
              </div>
              <div className="mt-5 flex gap-4 text-[10px] opacity-40">
                <span className="flex items-center gap-1.5"><span className="inline-block w-2 h-2 rounded-full bg-fg" />현재 위치</span>
                <span className="flex items-center gap-1.5"><span className="inline-block w-2 h-2 rounded-full border-2 border-fg" />추구미</span>
              </div>
            </div>
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
                <div className="relative aspect-[3/4] w-full overflow-hidden">
                  <Image src={item.src} alt={item.alt} fill className="object-cover" sizes="(max-width: 640px) 100vw, 33vw" />
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
      <Reveal>
        <Link href="/start" className="block px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-10 md:py-14 text-center group border-t border-black/10">
          <p className="font-[family-name:var(--font-serif)] text-[clamp(16px,2vw,24px)] font-normal leading-[1.4] opacity-50 mb-3">셀카 한 장과 5분의 설문으로</p>
          <p className="text-[clamp(24px,4vw,40px)] font-bold tracking-[1px] transition-opacity duration-200 group-hover:opacity-50">
            → 진단 시작하기
          </p>
          <p className="mt-3 text-[11px] opacity-30">₩5,000부터</p>
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
