import { useState, useRef, useEffect } from "react";

/* ── Reveal on scroll ── */
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
      opacity: v ? 1 : 0, transform: v ? "none" : "translateY(16px)",
      transition: "opacity 0.7s ease, transform 0.7s ease",
    }}>{children}</div>
  );
}

const Rule = () => <div className="rule" />;

const Row = ({ c1, c2, c3 }) => (
  <section className="row">
    <div className="row-grid">
      <div className="col-1">{c1}</div>
      <div className="col-2">{c2}</div>
      <div className="col-3">{c3}</div>
    </div>
  </section>
);

export default function CastingLanding() {
  return (
    <div className="root">
      <style>{CSS}</style>

      {/* NAV */}
      <nav className="nav">
        <div className="nav-l"><a href="/" className="nav-link">SIGAK</a></div>
        <span className="logo">CASTING</span>
        <div className="nav-r"><a href="/start" className="nav-link">시작하기</a></div>
      </nav>

      {/* ═══ HERO ═══ */}
      <section className="hero">
        <R>
          <div className="hero-grid">
            <div className="hero-text">
              <p className="hero-label">SELFIE CASTING AGENCY</p>
              <h1 className="hero-h">셀카 한 장으로<br/>캐스팅 제안을 받다.</h1>
              <p className="hero-sub">
                AI가 당신의 매력 포인트를 분석하고,<br/>
                에이전시와 브랜드가 당신을 찾아옵니다.
              </p>
            </div>
            <div className="hero-side">
              <a href="/start" className="hero-cta">내 매력 분석 시작하기</a>
              <p className="hero-price">₩2,900부터 · 24시간 내 결과</p>
            </div>
          </div>
        </R>
      </section>
      <Rule />

      {/* ═══ 01. PROCESS ═══ */}
      <R><Row
        c1={<><h2 className="row-title">01</h2><span className="row-remain">PROCESS</span></>}
        c2={<p className="row-sub">셀카에서<br/>캐스팅 제안까지.</p>}
        c3={<div className="steps">
          <div className="step">
            <span className="step-num">01</span>
            <div>
              <p className="step-title">셀카 업로드</p>
              <p className="step-desc">정면 사진 한 장과 5분 설문. 추구하는 이미지와 매력 포인트를 알려주세요.</p>
            </div>
          </div>
          <div className="step">
            <span className="step-num">02</span>
            <div>
              <p className="step-title">AI 매력 분석</p>
              <p className="step-desc">얼굴 구조, 피부톤, 이미지 유형을 다차원 좌표로 매핑합니다. 당신만의 매력이 데이터가 됩니다.</p>
            </div>
          </div>
          <div className="step">
            <span className="step-num">03</span>
            <div>
              <p className="step-title">캐스팅 풀 등록</p>
              <p className="step-desc">풀 리포트를 받은 후, 캐스팅 풀 참여를 선택할 수 있어요. 개인정보는 수락 전까지 보호됩니다.</p>
            </div>
          </div>
          <div className="step" style={{borderBottom:"none"}}>
            <span className="step-num">04</span>
            <div>
              <p className="step-title">제안이 도착</p>
              <p className="step-desc">에이전시와 브랜드가 좌표 기반으로 탐색 후, 출연료를 포함한 구체적 제안을 보냅니다.</p>
            </div>
          </div>
        </div>}
      /></R>
      <Rule />

      {/* ═══ 02. INVITATION — 캐스팅 카드 ═══ */}
      <R><Row
        c1={<><h2 className="row-title">02</h2><span className="row-remain">INVITATION</span></>}
        c2={<p className="row-sub">이런 제안이<br/>도착합니다.</p>}
        c3={<div className="cards">
          <div className="card">
            <p className="card-label">CASTING INVITATION</p>
            <div className="card-rows">
              <div className="card-row"><span className="card-key">From</span><span className="card-val">Alpha Agency</span></div>
              <div className="card-row"><span className="card-key">Purpose</span><span className="card-val">화보 촬영</span></div>
              <div className="card-row"><span className="card-key">Fee</span><span className="card-val card-val-b">₩500,000</span></div>
              <div className="card-row"><span className="card-key">Date</span><span className="card-val">2026. 4. 20</span></div>
            </div>
            <div className="card-actions">
              <button className="card-btn card-btn-fill">수락하기</button>
              <button className="card-btn card-btn-outline">괜찮습니다</button>
            </div>
          </div>
          <div className="card">
            <p className="card-label">CASTING INVITATION</p>
            <div className="card-rows">
              <div className="card-row"><span className="card-key">From</span><span className="card-val">Scene Studio</span></div>
              <div className="card-row"><span className="card-key">Purpose</span><span className="card-val">브랜드 광고 모델</span></div>
              <div className="card-row"><span className="card-key">Fee</span><span className="card-val card-val-b">₩800,000</span></div>
              <div className="card-row"><span className="card-key">Date</span><span className="card-val">2026. 5. 3</span></div>
            </div>
            <div className="card-actions">
              <button className="card-btn card-btn-fill">수락하기</button>
              <button className="card-btn card-btn-outline">괜찮습니다</button>
            </div>
          </div>
          <p className="card-note">* 실제 제안 예시를 기반으로 구성된 목업입니다</p>
        </div>}
      /></R>
      <Rule />

      {/* ═══ 03. WHY — AI 분석 전제 조건 ═══ */}
      <R><Row
        c1={<><h2 className="row-title">03</h2><span className="row-remain">WHY</span></>}
        c2={<p className="row-sub">캐스팅의 시작은<br/>매력 분석입니다.</p>}
        c3={<div>
          <p className="row-desc">
            에이전시가 당신을 찾으려면, 먼저 당신의 매력이 데이터로 존재해야 합니다.
            AI가 얼굴 구조, 피부톤, 이미지 유형을 분석하고 — 그 결과가 캐스팅 풀의 기반이 됩니다.
          </p>
          <p className="row-desc" style={{marginTop:16, opacity:0.4}}>
            분석 리포트 자체도 헤어, 메이크업, 스타일링 가이드를 포함하고 있어
            캐스팅 여부와 관계없이 가치가 있어요.
          </p>
        </div>}
      /></R>
      <Rule />

      {/* ═══ 04. PRICING ═══ */}
      <R><Row
        c1={<><h2 className="row-title">04</h2><span className="row-remain">PRICING</span></>}
        c2={<p className="row-sub">선택하세요.</p>}
        c3={<div className="tiers">
          <div className="tier">
            <div className="tier-head">
              <span className="tier-label">OVERVIEW</span>
              <div className="tier-price-row">
                <span className="tier-price">₩2,900</span>
                <span className="tier-original">₩5,000</span>
              </div>
            </div>
            <p className="tier-desc">얼굴 구조 분석, 피부톤, 3축 좌표 요약. 나를 먼저 파악하고 싶다면.</p>
            <a href="/start" className="tier-cta tier-cta-outline">오버뷰 시작</a>
          </div>
          <div className="tier tier-featured">
            <div className="tier-head">
              <span className="tier-label">FULL REPORT<span className="tier-rec">RECOMMENDED</span></span>
              <div className="tier-price-row">
                <span className="tier-price">₩29,000</span>
                <span className="tier-original">₩49,000</span>
              </div>
            </div>
            <p className="tier-desc">오버뷰 + 헤어 TOP 3, 메이크업 가이드, 트렌드 포지셔닝, 캐스팅 풀 등록 가능.</p>
            <a href="/start" className="tier-cta tier-cta-fill">풀 리포트 + 캐스팅 등록</a>
          </div>
          <div className="tier">
            <div className="tier-head">
              <span className="tier-label">CELEBRITY POOL</span>
              <div className="tier-price-row">
                <span className="tier-price">₩100,000</span>
              </div>
            </div>
            <p className="tier-desc">풀 리포트 + 상세 프로필 + 우선 매칭. 에이전시 검색에서 상위 노출됩니다.</p>
            <a href="/start" className="tier-cta tier-cta-outline">셀럽 풀 등록</a>
          </div>
        </div>}
      /></R>
      <Rule />

      {/* ═══ 05. FAQ ═══ */}
      <R><Row
        c1={<><h2 className="row-title">05</h2><span className="row-remain">FAQ</span></>}
        c2={<p className="row-sub">자주 묻는 질문.</p>}
        c3={<div className="faqs">
          <div className="faq">
            <p className="faq-q">캐스팅이 보장되나요?</p>
            <p className="faq-a">캐스팅은 보장이 아닌 기회입니다. 에이전시가 좌표 기반으로 탐색하며, 매칭 제안 여부는 프로젝트에 따라 달라집니다.</p>
          </div>
          <div className="faq">
            <p className="faq-q">내 사진이 공개되나요?</p>
            <p className="faq-a">캐스팅 풀에 등록해도 개인정보는 매칭 수락 전까지 절대 공유되지 않습니다. 언제든 해제 가능합니다.</p>
          </div>
          <div className="faq" style={{borderBottom:"none"}}>
            <p className="faq-q">리포트만 받아도 되나요?</p>
            <p className="faq-a">물론이에요. 캐스팅 풀 등록은 선택입니다. 리포트 자체가 헤어, 메이크업, 스타일링 가이드를 포함한 완결된 상품입니다.</p>
          </div>
        </div>}
      /></R>
      <Rule />

      {/* ═══ FINAL CTA ═══ */}
      <section className="cta-section">
        <R>
          <div className="cta-inner">
            <h2 className="cta-h">당신의 매력을 데이터로.</h2>
            <p className="cta-sub">셀카 한 장 · 5분 설문 · 24시간 내 결과</p>
            <a href="/start" className="cta-btn">시작하기</a>
          </div>
        </R>
      </section>

      {/* FOOTER */}
      <footer className="ft">
        <div className="ft-links">
          <a href="/terms" className="ft-link">이용약관</a>
          <a href="/terms" className="ft-link">개인정보처리방침</a>
          <a href="/refund" className="ft-link">환불규정</a>
          <a href="mailto:partner@sigak.asia" className="ft-link">partner@sigak.asia</a>
        </div>
        <span className="ft-c">주식회사 시각 | 대표: 조찬형 | © 2026 SIGAK</span>
      </footer>
    </div>
  );
}

const CSS = `
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css');
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@200;300;400;600;700;900&display=swap');

:root {
  --bg: #F3F0EB;
  --black: #000000;
  --serif: 'Noto Serif KR', 'Georgia', serif;
  --sans: 'Pretendard Variable', Pretendard, -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); }
::selection { background: var(--black); color: var(--bg); }
.root { font-family: var(--sans); color: var(--black); background: var(--bg); min-height: 100vh; }

/* ── NAV ── */
.nav {
  position: sticky; top: 0; z-index: 100;
  display: flex; justify-content: space-between; align-items: center;
  padding: 0 60px; height: 60px;
  background: var(--black); color: var(--bg);
}
.nav-l, .nav-r { display: flex; align-items: center; }
.nav-link {
  font-size: 11px; font-weight: 500; letter-spacing: 2.5px;
  text-transform: uppercase; opacity: 0.7; text-decoration: none; color: var(--bg);
}
.logo { font-size: 13px; font-weight: 600; letter-spacing: 6px; text-transform: uppercase; }

/* ── RULE ── */
.rule { height: 1px; background: var(--black); margin: 0 60px; opacity: 0.15; }

/* ── ROW (1:1:2 grid) ── */
.row { padding: 40px 60px; }
.row-grid { display: grid; grid-template-columns: 1fr 1fr 2fr; gap: 24px; align-items: start; }
.row-title { font-size: clamp(18px,2.5vw,28px); font-weight: 800; letter-spacing: 1px; line-height: 1.3; }
.row-remain { display: block; margin-top: 8px; font-size: 11px; font-weight: 600; letter-spacing: 1.5px; opacity: 0.35; }
.row-sub { font-family: var(--serif); font-size: clamp(16px,2vw,24px); font-weight: 400; line-height: 1.4; }
.row-desc { font-size: 15px; line-height: 1.7; opacity: 0.7; }

/* ── HERO ── */
.hero { padding: 60px 60px 48px; }
.hero-grid { display: flex; justify-content: space-between; align-items: flex-end; }
.hero-text { max-width: 64%; }
.hero-label {
  font-size: 11px; font-weight: 600; letter-spacing: 3px;
  opacity: 0.3; margin-bottom: 20px;
}
.hero-h {
  font-family: var(--serif); font-size: clamp(32px,5vw,52px);
  font-weight: 400; line-height: 1.35;
}
.hero-sub { margin-top: 16px; font-size: 15px; opacity: 0.5; line-height: 1.7; }
.hero-side { text-align: right; }
.hero-cta {
  display: inline-block; padding: 14px 32px;
  background: var(--black); color: var(--bg);
  font-family: var(--sans); font-size: 13px; font-weight: 600;
  letter-spacing: 0.3px; text-decoration: none;
  border: none;
}
.hero-price { margin-top: 12px; font-size: 12px; opacity: 0.35; }

/* ── STEPS ── */
.steps {}
.step {
  display: flex; gap: 20px; padding: 16px 0;
  border-bottom: 1px solid rgba(0,0,0,0.06);
}
.step-num {
  font-family: var(--serif); font-size: 18px; font-weight: 300;
  opacity: 0.25; flex-shrink: 0; width: 28px;
}
.step-title { font-size: 15px; font-weight: 700; margin-bottom: 4px; }
.step-desc { font-size: 14px; opacity: 0.5; line-height: 1.7; }

/* ── CASTING CARDS ── */
.cards { display: flex; gap: 16px; flex-wrap: wrap; }
.card {
  flex: 1; min-width: 260px; padding: 24px;
  border: 1px solid rgba(0,0,0,0.12);
}
.card-label {
  font-size: 10px; font-weight: 700; letter-spacing: 2px;
  opacity: 0.25; margin-bottom: 20px;
}
.card-rows { display: flex; flex-direction: column; gap: 10px; }
.card-row { display: flex; justify-content: space-between; align-items: center; }
.card-key { font-size: 11px; opacity: 0.35; letter-spacing: 1px; }
.card-val { font-size: 14px; font-weight: 500; }
.card-val-b { font-weight: 800; }
.card-actions { display: flex; gap: 8px; margin-top: 20px; }
.card-btn {
  flex: 1; padding: 10px; font-family: var(--sans);
  font-size: 12px; font-weight: 600; cursor: pointer;
  letter-spacing: 0.3px;
}
.card-btn-fill {
  background: var(--black); color: var(--bg); border: none;
}
.card-btn-outline {
  background: transparent; color: var(--black);
  border: 1px solid rgba(0,0,0,0.12);
}
.card-note {
  width: 100%; margin-top: 16px;
  font-size: 12px; opacity: 0.25; font-style: italic;
}

/* ── TIERS ── */
.tiers { display: flex; flex-direction: column; gap: 0; }
.tier {
  padding: 24px 0;
  border-bottom: 1px solid rgba(0,0,0,0.06);
  display: grid; grid-template-columns: 1fr 2fr auto; gap: 20px; align-items: center;
}
.tier:last-child { border-bottom: none; }
.tier-featured { }
.tier-head { }
.tier-label {
  font-size: 11px; font-weight: 700; letter-spacing: 2px;
  display: flex; align-items: center; gap: 8px;
}
.tier-rec {
  font-size: 9px; font-weight: 700; letter-spacing: 1.5px;
  padding: 2px 8px; background: var(--black); color: var(--bg);
}
.tier-price-row { display: flex; align-items: baseline; gap: 8px; margin-top: 8px; }
.tier-price { font-family: var(--serif); font-size: 24px; font-weight: 600; }
.tier-original { font-size: 13px; opacity: 0.3; text-decoration: line-through; }
.tier-desc { font-size: 14px; opacity: 0.5; line-height: 1.6; }
.tier-cta {
  display: inline-block; padding: 12px 24px;
  font-family: var(--sans); font-size: 12px; font-weight: 600;
  letter-spacing: 0.3px; text-decoration: none; text-align: center;
  white-space: nowrap;
}
.tier-cta-fill { background: var(--black); color: var(--bg); border: none; }
.tier-cta-outline { background: transparent; color: var(--black); border: 1px solid rgba(0,0,0,0.12); }

/* ── FAQ ── */
.faqs {}
.faq { padding: 16px 0; border-bottom: 1px solid rgba(0,0,0,0.06); }
.faq-q { font-size: 15px; font-weight: 700; margin-bottom: 6px; }
.faq-a { font-size: 14px; opacity: 0.5; line-height: 1.7; }

/* ── FINAL CTA ── */
.cta-section { padding: 56px 60px; text-align: center; }
.cta-inner {}
.cta-h {
  font-family: var(--serif); font-size: clamp(24px,4vw,40px);
  font-weight: 400; margin-bottom: 12px;
}
.cta-sub { font-size: 14px; opacity: 0.4; margin-bottom: 32px; }
.cta-btn {
  display: inline-block; padding: 14px 48px;
  background: var(--black); color: var(--bg);
  font-family: var(--sans); font-size: 14px; font-weight: 600;
  text-decoration: none; letter-spacing: 0.5px;
}

/* ── FOOTER ── */
.ft {
  padding: 32px 60px; text-align: center;
  border-top: 1px solid rgba(0,0,0,0.1);
}
.ft-links { display: flex; justify-content: center; gap: 20px; margin-bottom: 12px; flex-wrap: wrap; }
.ft-link { font-size: 11px; opacity: 0.3; text-decoration: none; color: var(--black); }
.ft-c { font-size: 11px; letter-spacing: 1px; opacity: 0.2; }

/* ── MOBILE ── */
@media (max-width: 768px) {
  .nav { padding: 0 24px; }
  .hero { padding: 40px 24px 32px; }
  .hero-grid { flex-direction: column; gap: 24px; align-items: flex-start; }
  .hero-text { max-width: 100%; }
  .hero-side { text-align: left; }
  .rule { margin: 0 24px; }
  .row { padding: 28px 24px; }
  .row-grid { grid-template-columns: 1fr; gap: 12px; }
  .cards { flex-direction: column; }
  .tier { grid-template-columns: 1fr; gap: 12px; }
  .cta-section { padding: 40px 24px; }
  .ft { padding: 24px; }
  .ft-links { gap: 12px; }
}
`;