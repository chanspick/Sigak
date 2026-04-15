import { useState, useRef, useEffect } from "react";

/*
  SIGAK Casting Invitation — "복권 긁기 전" 오브제

  디자인 의도:
  - 페이지의 컴포넌트가 아니라 페이지 위에 놓인 "물건"
  - 종이 질감, 미세한 텍스처, 다른 물성
  - 핵심 정보가 가려져 있어서 궁금증 유발
  - "내 것인데 아직 안 열었다" 느낌
*/

function R({ children }) {
  const ref = useRef(null);
  const [v, sV] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const o = new IntersectionObserver(([e]) => { if (e.isIntersecting) sV(true); }, { threshold: 0.1 });
    o.observe(el);
    return () => o.disconnect();
  }, []);
  return (
    <div ref={ref} style={{
      opacity: v ? 1 : 0, transform: v ? "translateY(0)" : "translateY(24px)",
      transition: "opacity 0.9s ease, transform 0.9s ease",
    }}>{children}</div>
  );
}

export default function CastingInvitation() {
  const [hover, setHover] = useState(false);

  return (
    <div className="casting-wrap">
      <style>{CSS}</style>

      {/* 배경 컨텍스트 — 이 위에 초대장이 "놓여있는" 느낌 */}
      <div className="casting-bg">

        {/* 섹션 헤더 — 1:1:2 그리드 */}
        <div className="section-header">
          <div className="sh-num">
            <span className="sh-n">02</span>
            <span className="sh-label">INVITATION</span>
          </div>
          <div className="sh-sub">
            이런 초대장이<br/>도착합니다.
          </div>
          <div className="sh-spacer" />
        </div>

        {/* 초대장 오브제 — 중앙 배치 */}
        <R>
          <div className="invite-stage">
            <div
              className={`invite-card ${hover ? "invite-hover" : ""}`}
              onMouseEnter={() => setHover(true)}
              onMouseLeave={() => setHover(false)}
            >
              {/* 종이 텍스처 오버레이 */}
              <div className="paper-texture" />

              {/* 상단: SIGAK 엠보싱 */}
              <div className="invite-top">
                <span className="invite-brand">SIGAK</span>
                <span className="invite-type">CASTING INVITATION</span>
              </div>

              {/* 구분선 */}
              <div className="invite-rule" />

              {/* 수신자 */}
              <div className="invite-to">
                <span className="invite-to-label">To.</span>
                <span className="invite-to-name">
                  <span className="redacted-block" style={{width: 64}} />
                  <span style={{marginLeft: 2}}> 님</span>
                </span>
              </div>

              {/* 본문 — 핵심 정보 가림 */}
              <div className="invite-body">
                <div className="invite-row">
                  <span className="invite-key">브랜드</span>
                  <span className="invite-val">
                    <span className="redacted-block" style={{width: 48}} />
                    <span style={{marginLeft: 3}}>코스메틱</span>
                  </span>
                </div>
                <div className="invite-row">
                  <span className="invite-key">캠페인</span>
                  <span className="invite-val">
                    2026 S/S
                    <span className="redacted-inline" style={{width: 44}} />
                    <span style={{marginLeft: 3}}>화보</span>
                  </span>
                </div>
                <div className="invite-row">
                  <span className="invite-key">보수</span>
                  <span className="invite-val invite-fee">
                    ₩ <span className="redacted-block" style={{width: 52, height: 18}} />,000
                  </span>
                </div>
                <div className="invite-row">
                  <span className="invite-key">일정</span>
                  <span className="invite-val">
                    6월
                    <span className="redacted-block" style={{width: 18}} />일, 서울
                    <span className="redacted-inline" style={{width: 52}} />
                    <span style={{marginLeft: 3}}>스튜디오</span>
                  </span>
                </div>
              </div>

              {/* 하단 안내 */}
              <div className="invite-rule" style={{marginTop: 28}} />

              <div className="invite-footer">
                <p className="invite-note">
                  AI 매력 분석을 완료하면<br/>
                  캐스팅 풀에 등록되고, 이 초대장이 열립니다.
                </p>
              </div>

              {/* CTA */}
              <a href="/start" className="invite-cta">
                내 초대장 열기
              </a>

            </div>

            {/* 두 번째 초대장 — 뒤에 살짝 비치는 것 (깊이감) */}
            <div className="invite-shadow-card">
              <div className="paper-texture" />
            </div>
          </div>
        </R>

        {/* 하단 안내 텍스트 */}
        <R>
          <div className="casting-bottom">
            <p className="casting-bottom-text">
              제안은 목적, 일정, 출연료를 포함하여 도착합니다.
            </p>
            <p className="casting-bottom-sub">
              수락 전까지 개인정보는 공유되지 않습니다.
            </p>
          </div>
        </R>

      </div>
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
  --sans: 'Pretendard Variable', Pretendard, -apple-system, BlinkMacSystemFont, sans-serif;
  --paper: #FDFBF7;
  --paper-border: rgba(0,0,0,0.08);
}

* { box-sizing: border-box; margin: 0; padding: 0; }

.casting-wrap {
  font-family: var(--sans);
  color: var(--black);
  background: var(--bg);
}

.casting-bg {
  padding: 40px 60px 56px;
}

/* ── 섹션 헤더 1:1:2 ── */
.section-header {
  display: grid;
  grid-template-columns: 1fr 1fr 2fr;
  gap: 24px;
  margin-bottom: 48px;
}
.sh-num {}
.sh-n {
  display: block;
  font-size: clamp(18px,2.5vw,28px);
  font-weight: 800;
  letter-spacing: 1px;
}
.sh-label {
  display: block;
  margin-top: 8px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1.5px;
  opacity: 0.35;
}
.sh-sub {
  font-family: var(--serif);
  font-size: clamp(16px,2vw,24px);
  font-weight: 400;
  line-height: 1.4;
}

/* ── 초대장 스테이지 ── */
.invite-stage {
  position: relative;
  display: flex;
  justify-content: center;
  padding: 20px 0 32px;
}

/* ── 두 번째 카드 (뒤에 깔리는 것) ── */
.invite-shadow-card {
  position: absolute;
  top: 28px;
  width: min(420px, 90%);
  height: 100%;
  background: var(--paper);
  border: 1px solid var(--paper-border);
  transform: rotate(1.2deg);
  z-index: 0;
  overflow: hidden;
}

/* ── 메인 초대장 카드 ── */
.invite-card {
  position: relative;
  z-index: 1;
  width: min(420px, 90%);
  background: var(--paper);
  border: 1px solid var(--paper-border);
  padding: 40px 36px 32px;
  transition: transform 0.4s ease;
  overflow: hidden;
}
.invite-hover {
  transform: translateY(-3px);
}

/* ── 종이 텍스처 ── */
.paper-texture {
  position: absolute;
  inset: 0;
  opacity: 0.3;
  pointer-events: none;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.4'/%3E%3C/svg%3E");
  background-size: 128px 128px;
}

/* ── 상단 브랜드 ── */
.invite-top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 8px;
}
.invite-brand {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 6px;
  opacity: 0.2;
}
.invite-type {
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 2.5px;
  opacity: 0.2;
}

/* ── 구분선 ── */
.invite-rule {
  height: 1px;
  background: var(--black);
  opacity: 0.1;
  margin: 20px 0;
}

/* ── 수신자 ── */
.invite-to {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 28px;
}
.invite-to-label {
  font-family: var(--serif);
  font-size: 14px;
  font-weight: 300;
  opacity: 0.3;
}
.invite-to-name {
  font-family: var(--serif);
  font-size: 22px;
  font-weight: 400;
  display: flex;
  align-items: center;
}

/* ── 가림 처리 ── */
.redacted-block {
  display: inline-block;
  height: 14px;
  background: var(--black);
  opacity: 0.08;
  vertical-align: middle;
}
.redacted-inline {
  display: inline-block;
  width: 60px;
  height: 12px;
  background: var(--black);
  opacity: 0.06;
  vertical-align: middle;
  margin-left: 6px;
}

/* ── 본문 정보 행 ── */
.invite-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.invite-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.invite-key {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1.5px;
  opacity: 0.25;
  text-transform: uppercase;
  flex-shrink: 0;
}
.invite-val {
  font-size: 15px;
  font-weight: 500;
  text-align: right;
  display: flex;
  align-items: center;
  gap: 2px;
}
.invite-fee {
  font-family: var(--serif);
  font-size: 20px;
  font-weight: 600;
}

/* ── 하단 안내 ── */
.invite-footer {
  margin-top: 16px;
}
.invite-note {
  font-size: 12px;
  line-height: 1.8;
  opacity: 0.3;
  text-align: center;
}

/* ── CTA ── */
.invite-cta {
  display: block;
  margin-top: 20px;
  padding: 14px 0;
  text-align: center;
  background: var(--black);
  color: var(--paper);
  font-family: var(--sans);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.5px;
  text-decoration: none;
  transition: opacity 0.2s;
}
.invite-cta:hover {
  opacity: 0.85;
}

/* ── 하단 페이지 텍스트 ── */
.casting-bottom {
  text-align: center;
  margin-top: 40px;
}
.casting-bottom-text {
  font-size: 13px;
  opacity: 0.4;
  line-height: 1.7;
}
.casting-bottom-sub {
  font-size: 12px;
  opacity: 0.25;
  margin-top: 4px;
}

/* ── 모바일 ── */
@media (max-width: 768px) {
  .casting-bg { padding: 28px 24px 40px; }
  .section-header {
    grid-template-columns: 1fr;
    gap: 12px;
    margin-bottom: 36px;
  }
  .invite-card { padding: 32px 24px 28px; }
  .invite-fee { font-size: 18px; }
}
`;