import { useState, useEffect, useRef, useCallback } from "react";

/* ─── DATA ─── */
const ALL_SLOTS = ["09:00","10:00","11:00","12:00","13:00","14:00","15:00","16:00","17:00","18:00"];
const T3 = ["basic","creator","wedding"];
const fullDay = () => ALL_SLOTS.flatMap(time => T3.map(tier => ({ time, tier }))); // 30 per day
const bk = (arr) => arr.map(([time,tier]) => ({ time, tier }));

const BOOKINGS = {
  // Week 1
  "2026-04-10": bk([["10:00","basic"],["10:00","creator"],["11:00","basic"],["14:00","wedding"],["15:00","basic"],["15:00","creator"],["16:00","wedding"],["17:00","basic"],["17:00","creator"],["18:00","wedding"]]),
  "2026-04-11": fullDay(),
  "2026-04-12": fullDay(),
  "2026-04-13": bk([["11:00","basic"],["14:00","creator"],["14:00","wedding"]]),
  "2026-04-14": bk([["10:00","wedding"],["15:00","basic"],["15:00","creator"],["16:00","wedding"]]),
  "2026-04-15": bk([["14:00","basic"],["14:00","creator"],["17:00","wedding"]]),
  "2026-04-16": bk([["15:00","creator"],["16:00","wedding"],["16:00","basic"],["18:00","creator"]]),
  // Week 2
  "2026-04-17": bk([["09:00","basic"],["09:00","creator"],["10:00","wedding"],["10:00","basic"],["11:00","creator"],["14:00","basic"],["14:00","wedding"],["15:00","creator"],["16:00","basic"],["16:00","wedding"],["17:00","creator"],["18:00","wedding"]]),
  "2026-04-18": fullDay(),
  "2026-04-19": fullDay(),
  "2026-04-20": bk([["10:00","basic"],["10:00","creator"],["14:00","wedding"],["15:00","basic"]]),
  "2026-04-21": bk([["11:00","wedding"],["11:00","creator"],["16:00","basic"]]),
  "2026-04-22": bk([["14:00","creator"],["14:00","wedding"]]),
  "2026-04-23": bk([["10:00","basic"],["15:00","wedding"],["15:00","creator"]]),
  // Week 3
  "2026-04-24": bk([["10:00","wedding"],["10:00","basic"],["11:00","creator"],["11:00","wedding"],["13:00","basic"],["14:00","creator"],["14:00","wedding"],["15:00","basic"],["16:00","creator"],["17:00","wedding"],["17:00","basic"],["18:00","creator"]]),
  "2026-04-25": fullDay(),
  "2026-04-26": fullDay(),
  "2026-04-27": bk([["11:00","creator"],["14:00","basic"],["14:00","wedding"],["15:00","creator"]]),
  "2026-04-28": bk([["10:00","basic"],["10:00","wedding"],["16:00","creator"]]),
  "2026-04-29": bk([["14:00","wedding"],["15:00","basic"],["15:00","creator"]]),
  "2026-04-30": bk([["10:00","creator"],["11:00","wedding"],["11:00","basic"],["15:00","creator"]]),
};

const TOTAL_SLOTS = 21 * 10 * 3; // 630
const allBookings = Object.values(BOOKINGS).flat();
const totalBooked = allBookings.length;
const totalRemain = TOTAL_SLOTS - totalBooked;
const bookedByTier = (tid) => allBookings.filter(b => b.tier === tid).length;
const isSlotBooked = (d, t, tid) => BOOKINGS[fmtD(d)]?.some(b => b.time === t && b.tier === tid);
const isDaySoldOut = (d) => BOOKINGS[fmtD(d)]?.length === 30;

const TIERS = [
  {
    id: "basic", name: "시선", nameUp: "시선", sub: "나를 읽다", price: 50000,
    desc: "이목구비 비율 · 얼굴형 정밀 분석, 피부톤 × 컬러 복합 매칭, 헤어 · 눈썹 · 안경 핏 설계, 트렌드 포지셔닝, 추구미 방향 로드맵, 메이크업 가이드.",
    target: "나를 객관적으로 알고 싶은 분",
  },
  {
    id: "creator", name: "시각 Creator", nameUp: "시각 CREATOR", sub: "화면 속 나를 설계하다", price: 200000,
    desc: "시선 전 항목 포함. 내 채널 톤에 맞는 얼굴 · 스타일링 최적화, 썸네일 · 프로필 최적 앵글 설계, 브랜드 미팅 · 면접 시 타겟 이미지로의 갭 분석과 교정.",
    target: "내 콘텐츠와 내 이미지 사이 간극을 줄이고 싶은 분",
  },
  {
    id: "wedding", name: "시각 Wedding", nameUp: "시각 WEDDING", sub: "스드메 전에, 나를 먼저", price: 200000,
    desc: "시선 전 항목 포함. 스드메 컨셉 최적화, 얼굴형 맞춤 드레스 라인 · 헤어 · 메이크업 방향, 스튜디오 조명 · 각도 가이드.",
    target: "스드메를 고르는 기준이 필요한 분",
  },
];

const SLOTS = ["09:00","10:00","11:00","12:00","13:00","14:00","15:00","16:00","17:00","18:00"];
const DN = ["일","월","화","수","목","금","토"];
const pad = n => String(n).padStart(2, "0");
const fmtD = d => `2026-04-${pad(d)}`;
const dayName = d => DN[new Date(2026, 3, d).getDay()];
const getApril = () => {
  const r = [], s = new Date(2026, 3, 1).getDay();
  for (let i = 0; i < s; i++) r.push(null);
  for (let i = 1; i <= 30; i++) r.push(i);
  return r;
};

/* ─── Reveal ─── */
function R({ children, className = "" }) {
  const ref = useRef(null);
  const [v, sV] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const o = new IntersectionObserver(([e]) => { if (e.isIntersecting) sV(true); }, { threshold: 0.05 });
    o.observe(el);
    return () => o.disconnect();
  }, []);
  return (
    <div ref={ref} className={className} style={{
      opacity: v ? 1 : 0, transform: v ? "none" : "translateY(20px)",
      transition: "opacity 0.8s ease, transform 0.8s ease",
    }}>{children}</div>
  );
}

/* ─── Booking Overlay ─── */
function Overlay({ open, onClose, initTier }) {
  const [tier, setTier] = useState(initTier);
  const [day, setDay] = useState(null);
  const [time, setTime] = useState(null);
  const [form, setF] = useState({ name:"", phone:"", ig:"", pN:"", pP:"" });
  const [done, setDone] = useState(false);
  const [loading, setL] = useState(false);
  const april = getApril();
  const tObj = TIERS.find(t => t.id === tier);
  const isW = tier === "wedding";
  const ok = form.name && form.phone && day && time && tier && (!isW || (form.pN && form.pP));

  useEffect(() => { if (initTier) setTier(initTier); }, [initTier]);
  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [open]);

  const pay = () => { setL(true); setTimeout(() => { setL(false); setDone(true); }, 1800); };
  const reset = () => { setDone(false); setDay(null); setTime(null); setF({ name:"",phone:"",ig:"",pN:"",pP:"" }); onClose(); };

  if (!open) return null;

  return (
    <div className="ov-bg" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="ov-panel">
        <div className="ov-head">
          <span className="ov-ht">예약</span>
          <button className="ov-x" onClick={onClose}>✕</button>
        </div>
        <div className="ov-scroll">
          {done ? (
            <div className="ov-done">
              <p className="ov-done-t">예약 완료</p>
              <p className="ov-done-s">상세 안내는 카카오톡으로 연락드립니다.</p>
              <div className="ov-done-d">
                {[["진단",tObj?.name],["날짜",`4월 ${day}일 (${dayName(day)})`],["시간",time],["이름",form.name]].map(([k,v])=>(
                  <div key={k} className="ov-done-r"><span className="ov-done-l">{k}</span><span className="ov-done-v">{v}</span></div>
                ))}
              </div>
              <button className="ov-btn" onClick={reset}>닫기</button>
            </div>
          ) : (<>
            {/* Tier */}
            <div className="ov-sec">
              <p className="ov-lab">진단 선택</p>
              <div className="ov-tiers">
                {TIERS.map(t=>(
                  <button key={t.id} onClick={()=>{setTier(t.id);setF(f=>({...f,pN:"",pP:""}));}}
                    className={`ov-ti ${tier===t.id?"ov-ti-a":""}`}>
                    <span className="ov-ti-n">{t.name}</span>
                    <span className="ov-ti-p">₩{t.price.toLocaleString()}</span>
                    <span className="ov-ti-r">{bookedByTier(t.id)}건 예약됨</span>
                  </button>
                ))}
              </div>
            </div>
            {/* Calendar */}
            {tier&&<div className="ov-sec">
              <p className="ov-lab">날짜 — 2026년 4월</p>
              <div className="ov-cal-h">{DN.map(d=><div key={d} className="ov-cal-dn">{d}</div>)}</div>
              <div className="ov-cal-b">
                {april.map((dd,i)=>{
                  if(!dd) return <div key={`e${i}`}/>;
                  const av = dd>=10&&dd<=30, sel=day===dd;
                  return <button key={dd} disabled={!av} onClick={()=>{setDay(dd);setTime(null);}}
                    className={`ov-cal-d ${sel?"ov-cal-s":""} ${!av?"ov-cal-x":""}`}>{dd}</button>;
                })}
              </div>
            </div>}
            {/* Time */}
            {day&&<div className="ov-sec">
              <p className="ov-lab">시간{time&&<span className="ov-lab-s"> — 4/{day}({dayName(day)}) {time}</span>}</p>
              <div className="ov-tg">
                {SLOTS.map(t=>{
                  const bk=isSlotBooked(day,t,tier), sel=time===t;
                  return <button key={t} disabled={bk} onClick={()=>setTime(t)}
                    className={`ov-tb ${sel?"ov-tb-s":""} ${bk?"ov-tb-x":""}`}>{bk?"마감":t}</button>;
                })}
              </div>
            </div>}
            {/* Form */}
            {time&&<div className="ov-sec">
              <p className="ov-lab">정보</p>
              <div className="ov-fm">
                <Inp l="이름" r v={form.name} c={v=>setF(f=>({...f,name:v}))} p="홍길동"/>
                <Inp l="연락처" r v={form.phone} c={v=>setF(f=>({...f,phone:v}))} p="010-0000-0000"/>
                <Inp l="인스타그램" v={form.ig} c={v=>setF(f=>({...f,ig:v}))} p="@username"/>
                {isW&&<><Inp l="파트너 이름" r v={form.pN} c={v=>setF(f=>({...f,pN:v}))} p="파트너 이름"/>
                <Inp l="파트너 연락처" r v={form.pP} c={v=>setF(f=>({...f,pP:v}))} p="010-0000-0000"/></>}
              </div>
            </div>}
            {/* Pay */}
            {time&&<>
              <button disabled={!ok||loading} onClick={pay} className={`ov-pay ${ok?"ov-pay-ok":""}`}>
                {loading?<span className="sp"/>:ok?`₩${tObj.price.toLocaleString()} 결제하기`:"정보를 입력해주세요"}
              </button>
              <p className="ov-pm">토스페이먼츠 · 카카오페이 · 네이버페이</p>
            </>}
          </>)}
        </div>
      </div>
    </div>
  );
}

function Inp({l,r,v,c,p}){
  return <div className="ov-f"><label className="ov-fl">{l}{r&&<span className="ov-fr">*</span>}</label>
    <input className="ov-fi" value={v} onChange={e=>c(e.target.value)} placeholder={p}/></div>;
}

/* ─── MAIN ─── */
export default function App() {
  const [ovOpen, setOv] = useState(false);
  const [ovTier, setOvT] = useState(null);
  const book = useCallback((tid) => { setOvT(tid||null); setOv(true); }, []);

  return (
    <div className="root">
      <style>{CSS}</style>

      {/* NAV */}
      <nav className="nav">
        <div className="nav-l">
          <span className="nav-link">WORK</span>
          <span className="nav-link">ABOUT</span>
        </div>
        <span className="logo">SIGAK</span>
        <div className="nav-r">
          <button className="nav-link nav-book" onClick={()=>book()}>예약</button>
        </div>
      </nav>

      {/* HERO */}
      <section className="hero">
        <R>
          <div className="hero-grid">
            <div className="hero-text">
              <h1 className="hero-h">당신을 아는 사람들.</h1>
              <p className="hero-sub">당신이 온전히 당신일 수 있게.</p>
            </div>
            <div className="hero-side">
              <p className="hero-link" onClick={()=>book()}>→ 예약하기</p>
              <p className="hero-link-s">↓ 서비스 소개</p>
            </div>
          </div>
        </R>
      </section>

      <div className="rule"/>

      {/* TIERS */}
      {TIERS.map((t, i) => (
        <div key={t.id}>
          <R>
            <section className="row">
              <div className="row-grid">
                <div className="col-1">
                  <h2 className="row-title">{t.nameUp}</h2>
                  <span className="row-remain">{bookedByTier(t.id)}건 예약</span>
                </div>
                <div className="col-2">
                  <p className="row-sub">{t.sub}</p>
                  <p className="row-price">₩{t.price.toLocaleString()}</p>
                </div>
                <div className="col-3">
                  <p className="row-target">{t.target}</p>
                  <p className="row-desc">{t.desc}</p>
                  <p className="row-cta" onClick={()=>book(t.id)}>→ 예약하기</p>
                </div>
              </div>
            </section>
          </R>
          <div className="rule"/>
        </div>
      ))}

      {/* EXPERTS */}
      <R>
        <section className="row">
          <div className="row-grid">
            <div className="col-1"><h2 className="row-title">HAN</h2></div>
            <div className="col-2"><p className="row-sub">미감 엔지니어</p></div>
            <div className="col-3">
              <p className="row-desc">4년간 수천 개의 얼굴을 읽으며 쌓아온 미감 판단 체계. 얼굴 구조, 피부톤, 트렌드 포지셔닝.</p>
            </div>
          </div>
        </section>
      </R>
      <div className="rule"/>
      <R>
        <section className="row">
          <div className="row-grid">
            <div className="col-1"><h2 className="row-title">JIN</h2></div>
            <div className="col-2"><p className="row-sub">비주얼 디렉터</p></div>
            <div className="col-3">
              <p className="row-desc">카메라 앞 이미지 최적화 4년. 각도, 조명, 포즈 분석을 통한 비주얼 포텐셜 극대화.</p>
            </div>
          </div>
        </section>
      </R>
      <div className="rule"/>

      {/* SEATS */}
      <R>
        <section className="seats">
          <div className="seats-grid">
            {TIERS.map(t=>(
              <div key={t.id} className="seats-item">
                <span className="seats-label">{t.name}</span>
                <span className="seats-num">{bookedByTier(t.id)}<span className="seats-unit">건 예약</span></span>
              </div>
            ))}
            <div className="seats-item seats-total">
              <span className="seats-label">잔여</span>
              <span className="seats-num">{totalRemain}<span className="seats-unit">석 / {TOTAL_SLOTS}</span></span>
            </div>
          </div>
        </section>
      </R>
      <div className="rule"/>

      {/* CTA */}
      <R>
        <section className="cta" onClick={()=>book()}>
          <p className="cta-t">→ 예약하기</p>
        </section>
      </R>

      {/* FOOTER */}
      <footer className="ft">
        <span className="ft-c">© 2026 시각(SIGAK). ALL RIGHTS RESERVED</span>
      </footer>

      <Overlay open={ovOpen} onClose={()=>setOv(false)} initTier={ovTier}/>
    </div>
  );
}

/* ─── CSS ─── */
const CSS = `
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css');
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@200;300;400;600;700;900&display=swap');

:root {
  --bg: #F3F0EB;
  --black: #000000;
  --white: #FFFFFF;
  --serif: 'Noto Serif KR', 'Georgia', serif;
  --sans: 'Pretendard Variable', Pretendard, -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif;
}

* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); }
::selection { background: var(--black); color: var(--bg); }

.root {
  font-family: var(--sans);
  color: var(--black);
  background: var(--bg);
  min-height: 100vh;
}

/* ── NAV ── */
.nav {
  position: sticky; top: 0; z-index: 100;
  display: flex; justify-content: space-between; align-items: center;
  padding: 0 60px; height: 60px;
  background: var(--black); color: var(--bg);
}
.nav-l, .nav-r { display: flex; align-items: center; gap: 28px; }
.nav-link {
  font-size: 11px; font-weight: 500;
  letter-spacing: 2.5px;
  text-transform: uppercase;
  cursor: pointer; opacity: 0.7;
  transition: opacity 0.2s;
  background: none; border: none; color: var(--bg);
  font-family: var(--sans);
}
.nav-link:hover { opacity: 1; }
.nav-book { opacity: 1; }
.logo {
  font-family: var(--sans);
  font-size: 13px; font-weight: 600;
  letter-spacing: 6px;
  text-transform: uppercase;
}

/* ── HERO ── */
.hero { padding: 60px 60px 48px; }
.hero-grid {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}
.hero-text { max-width: 68%; }
.hero-h {
  font-family: var(--serif);
  font-size: clamp(32px, 5vw, 52px);
  font-weight: 400;
  line-height: 1.35;
  letter-spacing: -0.01em;
}
.hero-sub {
  margin-top: 20px;
  font-size: 14px;
  line-height: 1.7;
  color: var(--black);
  opacity: 0.5;
}
.hero-side { text-align: right; padding-bottom: 4px; }
.hero-link {
  font-size: 14px; font-weight: 500;
  cursor: pointer;
  margin-bottom: 6px;
  transition: opacity 0.2s;
}
.hero-link:hover { opacity: 0.6; }
.hero-link-s {
  font-size: 14px;
  opacity: 0.4;
}

/* ── RULE ── */
.rule {
  height: 1px;
  background: var(--black);
  margin: 0 60px;
  opacity: 0.15;
}

/* ── ROW (3-col) ── */
.row { padding: 40px 60px; }
.row-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 2fr;
  gap: 24px;
  align-items: start;
}
.col-1 {}
.col-2 {}
.col-3 {}

.row-title {
  font-family: var(--sans);
  font-size: clamp(18px, 2.5vw, 28px);
  font-weight: 800;
  letter-spacing: 1px;
  line-height: 1.3;
}
.row-remain {
  display: inline-block;
  margin-top: 8px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1px;
  opacity: 0.35;
}
.row-sub {
  font-family: var(--serif);
  font-size: clamp(16px, 2vw, 24px);
  font-weight: 400;
  line-height: 1.4;
}
.row-price {
  margin-top: 8px;
  font-family: var(--serif);
  font-size: clamp(14px, 1.5vw, 18px);
  font-weight: 600;
  opacity: 0.5;
}
.row-target {
  font-size: 13px;
  font-weight: 600;
  opacity: 0.4;
  margin-bottom: 8px;
}
.row-desc {
  font-size: 15px;
  line-height: 1.7;
  opacity: 0.7;
}
.row-cta {
  margin-top: 16px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s;
}
.row-cta:hover { opacity: 0.5; }

/* ── SEATS ── */
.seats { padding: 48px 60px; }
.seats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0;
  border: 1px solid rgba(0,0,0,0.1);
}
.seats-item {
  display: flex; flex-direction: column;
  padding: 24px 28px;
  border-right: 1px solid rgba(0,0,0,0.1);
}
.seats-item:last-child { border-right: none; }
.seats-total { background: rgba(0,0,0,0.03); }
.seats-label {
  font-size: 11px; font-weight: 600;
  letter-spacing: 1px;
  opacity: 0.4;
  margin-bottom: 10px;
}
.seats-num {
  font-family: var(--serif);
  font-size: clamp(32px, 4vw, 48px);
  font-weight: 300;
  line-height: 1;
}
.seats-unit {
  font-family: var(--sans);
  font-size: 14px;
  font-weight: 400;
  opacity: 0.4;
  margin-left: 4px;
}

/* ── CTA ── */
.cta {
  padding: 56px 60px;
  text-align: center;
  cursor: pointer;
}
.cta-t {
  font-family: var(--sans);
  font-size: clamp(24px, 4vw, 40px);
  font-weight: 700;
  letter-spacing: 1px;
  transition: opacity 0.2s;
}
.cta:hover .cta-t { opacity: 0.5; }

/* ── FOOTER ── */
.ft {
  padding: 32px 60px;
  text-align: center;
  border-top: 1px solid rgba(0,0,0,0.1);
}
.ft-c {
  font-size: 11px;
  letter-spacing: 1.5px;
  opacity: 0.3;
}

/* ── OVERLAY ── */
.ov-bg {
  position: fixed; inset: 0; z-index: 200;
  background: rgba(0,0,0,0.5);
  display: flex; justify-content: flex-end;
  animation: ovIn .25s ease;
}
@keyframes ovIn { from { opacity: 0; } }
.ov-panel {
  width: min(480px, 100%); height: 100%;
  background: var(--bg);
  display: flex; flex-direction: column;
  animation: ovSlide .3s cubic-bezier(.22,1,.36,1);
}
@keyframes ovSlide { from { transform: translateX(100%); } }
.ov-head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 18px 28px;
  border-bottom: 1px solid rgba(0,0,0,0.1);
}
.ov-ht { font-size: 12px; font-weight: 600; letter-spacing: 2px; text-transform: uppercase; }
.ov-x { background: none; border: none; font-size: 16px; cursor: pointer; opacity: 0.4; transition: opacity .2s; }
.ov-x:hover { opacity: 1; }
.ov-scroll { flex: 1; overflow-y: auto; padding: 24px 28px 40px; }
.ov-sec { margin-bottom: 28px; }
.ov-lab { font-size: 11px; font-weight: 600; letter-spacing: 1.5px; text-transform: uppercase; opacity: 0.4; margin-bottom: 12px; }
.ov-lab-s { font-weight: 500; opacity: 0.8; letter-spacing: 0; text-transform: none; }

.ov-tiers { display: flex; gap: 8px; }
.ov-ti {
  flex: 1; padding: 14px 8px; text-align: center;
  border: 1px solid rgba(0,0,0,0.12); background: transparent;
  cursor: pointer; font-family: var(--sans); transition: all .15s;
}
.ov-ti:hover { border-color: rgba(0,0,0,0.4); }
.ov-ti-a { border-color: var(--black); background: var(--black); color: var(--bg); }
.ov-ti-n { display: block; font-size: 12px; font-weight: 700; letter-spacing: 0.5px; margin-bottom: 4px; }
.ov-ti-p { display: block; font-family: var(--serif); font-size: 16px; font-weight: 400; }
.ov-ti-r { display: block; font-size: 10px; margin-top: 4px; opacity: 0.4; }
.ov-ti-a .ov-ti-r { opacity: 0.6; }

.ov-cal-h { display: grid; grid-template-columns: repeat(7,1fr); text-align: center; margin-bottom: 4px; }
.ov-cal-dn { font-size: 10px; font-weight: 600; opacity: 0.3; padding: 6px; }
.ov-cal-b { display: grid; grid-template-columns: repeat(7,1fr); gap: 2px; }
.ov-cal-d {
  font-family: var(--sans); font-size: 13px; font-weight: 500;
  padding: 10px 0; background: transparent; border: none;
  cursor: pointer; transition: all .15s; text-align: center;
}
.ov-cal-d:hover:not(:disabled) { background: rgba(0,0,0,0.05); }
.ov-cal-s { background: var(--black) !important; color: var(--bg) !important; font-weight: 700; }
.ov-cal-x { opacity: 0.15 !important; cursor: default !important; }

.ov-tg { display: grid; grid-template-columns: repeat(5,1fr); gap: 6px; }
.ov-tb {
  font-family: var(--sans); padding: 11px 0; font-size: 13px; font-weight: 500;
  background: transparent; border: 1px solid rgba(0,0,0,0.1);
  cursor: pointer; transition: all .15s;
}
.ov-tb:hover:not(:disabled) { border-color: var(--black); }
.ov-tb-s { background: var(--black) !important; color: var(--bg) !important; border-color: var(--black) !important; }
.ov-tb-x { opacity: 0.2 !important; cursor: default !important; }

.ov-fm { display: flex; flex-direction: column; gap: 12px; }
.ov-fl { display: block; font-size: 11px; font-weight: 600; letter-spacing: 0.5px; opacity: 0.5; margin-bottom: 6px; }
.ov-fr { margin-left: 2px; }
.ov-fi {
  width: 100%; padding: 12px 14px; font-family: var(--sans);
  font-size: 14px; background: transparent;
  border: 1px solid rgba(0,0,0,0.12); outline: none;
  transition: border-color .2s;
}
.ov-fi::placeholder { opacity: 0.25; }
.ov-fi:focus { border-color: var(--black); }

.ov-pay {
  width: 100%; padding: 16px; margin-top: 24px;
  font-family: var(--sans); font-size: 14px; font-weight: 700;
  border: none; background: rgba(0,0,0,0.08); color: rgba(0,0,0,0.3);
  cursor: not-allowed; transition: all .2s;
  display: flex; align-items: center; justify-content: center; gap: 8px;
}
.ov-pay-ok { background: var(--black); color: var(--bg); cursor: pointer; }
.ov-pay-ok:hover { opacity: 0.85; }
.ov-pm { text-align: center; font-size: 10px; opacity: 0.3; margin-top: 10px; }

.ov-done { padding: 48px 0; text-align: center; }
.ov-done-t { font-family: var(--serif); font-size: 22px; font-weight: 400; margin-bottom: 8px; }
.ov-done-s { font-size: 13px; opacity: 0.4; margin-bottom: 28px; }
.ov-done-d { border: 1px solid rgba(0,0,0,0.1); padding: 20px; text-align: left; margin-bottom: 24px; }
.ov-done-r { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.06); font-size: 14px; }
.ov-done-r:last-child { border: none; }
.ov-done-l { opacity: 0.4; }
.ov-done-v { font-weight: 700; }
.ov-btn {
  font-family: var(--sans); font-size: 13px; font-weight: 600;
  padding: 12px 36px; background: var(--black); color: var(--bg);
  border: none; cursor: pointer; letter-spacing: 1px;
}

.sp {
  display: inline-block; width: 16px; height: 16px;
  border: 2px solid rgba(243,240,235,0.3); border-top-color: var(--bg);
  border-radius: 50%; animation: spin .5s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* RESPONSIVE */
@media (max-width: 768px) {
  .nav { padding: 0 24px; }
  .nav-l { display: none; }
  .hero { padding: 40px 24px 32px; }
  .hero-grid { flex-direction: column; align-items: flex-start; gap: 24px; }
  .hero-text { max-width: 100%; }
  .hero-side { text-align: left; }
  .rule { margin: 0 24px; }
  .row { padding: 28px 24px; }
  .row-grid { grid-template-columns: 1fr; gap: 12px; }
  .seats { padding: 32px 24px; }
  .seats-grid { grid-template-columns: repeat(2, 1fr); }
  .seats-item:nth-child(2) { border-right: none; }
  .cta { padding: 40px 24px; }
  .ft { padding: 24px; }
  .ov-tiers { flex-direction: column; }
  .ov-tg { grid-template-columns: repeat(3,1fr); }
}
`;