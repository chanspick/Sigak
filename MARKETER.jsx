import React, { useState, useRef } from 'react';

/**
 * SIGAK /profile page
 *
 * 3-tab structure: 피드 / 시각 / 변화
 *
 * 피드 탭:
 *   1. 내 판정 그리드 (Instagram 3-col, 마지막 셀은 /verdict/new 링크)
 *   2. "다음 한 걸음" — horizontal scroll 배너, ◀▶ 버튼 포함
 *   3. 계정 섹션 — 충전/온보딩 재설정/로그아웃
 *
 * 시각 탭:
 *   - PI — PERSONAL IMAGE 안내 박스
 *   - 블러 잠금 미리보기 (실제 PI 데이터 주입 시 여기 들어감)
 *   - 하단 CTA: "충전하고 PI 확인 · 50 토큰"
 *
 * 변화 탭:
 *   - 3건 미만 빈 상태 안내
 *   - 지금까지 건수 카운트
 *
 * 백엔드 연동 포인트:
 *   - user: GET /api/v1/auth/me (닉네임, 카카오 이미지 URL, 카카오 ID)
 *   - wallet.balance: GET /api/v1/tokens/balance
 *   - verdicts: GET /api/v1/verdicts?limit=30
 *       각 item: { id, gold_photo_url (signed URL), blur_released }
 *   - features 토큰 cost: backend config 매핑 필요
 *   - PI 50 토큰: 실제 PI 해제 비용과 맞출 것
 *
 * 모바일:
 *   - max-w 430px, mx-auto
 *   - 탭/TopBar 모두 일반 flow (sticky 아님)
 *   - 배너 scroll-snap + ◀▶ 버튼 (스와이프 + 클릭 모두 대응)
 *   - safe-area-inset-bottom for iOS
 */

export default function SigakProfile() {
  const [tab, setTab] = useState('feed');
  const bannerRef = useRef(null);

  // TODO: 실 API 주입
  const user = { nickname: '최진규', kakaoId: '4844927004', kakaoImageUrl: null };
  const wallet = { balance: 0 };

  const features = [
    { key: 'sia',        ko: 'Sia 대화',      sub: '대화로 당신을 같이 정리해요',        cost: 0,  href: '/sia' },
    { key: 'verdict',    ko: '시각의 판정',   sub: '지금 장면 한 장을 골라드려요',        cost: 20, href: '/verdict/new' },
    { key: 'bestshot',   ko: 'Best Shot',    sub: '사진 여러 장에서 한 장',              cost: 15, href: '/best-shot' },
    { key: 'aspiration', ko: '추구미 분석',  sub: '따라가는 이미지, 실제로 뭐가 다른지',  cost: 10, href: '/aspiration' },
  ];

  // TODO: 실 API (verdicts) 주입. gradient → gold_photo_url 로 교체.
  const verdicts = [
    { id: '001', locked: false, gradient: 'linear-gradient(135deg, #d4c7b0 0%, #8a6f4f 100%)' },
    { id: '002', locked: true,  gradient: 'linear-gradient(135deg, #c9bdaa 0%, #9d8e78 100%)' },
    { id: '003', locked: false, gradient: 'linear-gradient(200deg, #dcd2bf 0%, #ba9f7e 100%)' },
    { id: '004', locked: true,  gradient: 'linear-gradient(135deg, #b8a78a 0%, #80695a 100%)' },
    { id: '005', locked: false, gradient: 'linear-gradient(165deg, #d6c5a7 0%, #9e8b6a 100%)' },
  ];

  const scrollBanner = (dir) => {
    if (!bannerRef.current) return;
    const cardWidth = bannerRef.current.offsetWidth * 0.78 + 12;
    bannerRef.current.scrollBy({ left: dir === 'right' ? cardWidth : -cardWidth, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-[#F3F0EB] text-[#1a1a1a]">
      <style>{`
        .font-ui {
          font-family: 'Pretendard Variable', Pretendard, -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', sans-serif;
        }
        .tnum { font-variant-numeric: tabular-nums; }
        .ls-wordmark { letter-spacing: 0.4em; }
        .ls-pi { letter-spacing: 0.15em; }
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; -webkit-overflow-scrolling: touch; }
        .safe-bottom { padding-bottom: max(24px, env(safe-area-inset-bottom)); }
        .no-tap { -webkit-tap-highlight-color: transparent; }
        .blur-soft { filter: blur(4px); }
      `}</style>

      <div className="max-w-[430px] mx-auto font-ui no-tap">

        {/* TopBar */}
        <header className="h-12 bg-[#0d0d0d] text-white flex items-center justify-between px-4">
          <div className="ls-wordmark text-[13px] font-semibold">SIGAK</div>
          <div className="flex items-center gap-3">
            <span className="text-[14px] font-medium tnum">{wallet.balance}</span>
            <div className="w-7 h-7 rounded-full bg-[#b0cfe8] flex items-center justify-center overflow-hidden">
              {user.kakaoImageUrl ? (
                <img src={user.kakaoImageUrl} alt="" className="w-full h-full object-cover" />
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="#7aa0c1">
                  <path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm0 2c-3 0-8 1.5-8 4.5V21h16v-2.5c0-3-5-4.5-8-4.5z"/>
                </svg>
              )}
            </div>
            <button aria-label="new" className="w-8 h-8 flex items-center justify-center">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4">
                <path d="M12 5v14M5 12h14" strokeLinecap="round"/>
              </svg>
            </button>
          </div>
        </header>

        {/* Identity */}
        <section className="px-5 pt-6 pb-5 flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className="w-[68px] h-[68px] rounded-full bg-[#b0cfe8] flex items-center justify-center overflow-hidden flex-shrink-0">
              {user.kakaoImageUrl ? (
                <img src={user.kakaoImageUrl} alt="" className="w-full h-full object-cover" />
              ) : (
                <svg width="44" height="44" viewBox="0 0 24 24" fill="#7aa0c1">
                  <path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm0 2c-3 0-8 1.5-8 4.5V21h16v-2.5c0-3-5-4.5-8-4.5z"/>
                </svg>
              )}
            </div>
            <div className="min-w-0">
              <div className="text-[22px] font-bold text-black leading-tight">{user.nickname}</div>
              <div className="text-[12px] text-black/45 mt-0.5 tnum">@{user.kakaoId}</div>
            </div>
          </div>
          <div className="text-right pt-2">
            <div className="w-7 h-px bg-black/30 ml-auto mb-1.5" />
            <div className="text-[11px] text-black/55">피드</div>
          </div>
        </section>

        {/* Tabs */}
        <nav className="grid grid-cols-3 border-b border-black/15">
          {[
            { key: 'feed',   label: '피드' },
            { key: 'sigak',  label: '시각' },
            { key: 'change', label: '변화' },
          ].map(t => (
            <button
              key={t.key}
              type="button"
              onClick={() => setTab(t.key)}
              className={`h-11 text-[14px] relative ${
                tab === t.key ? 'text-black font-semibold' : 'text-black/45'
              }`}
            >
              {t.label}
              {tab === t.key && (
                <span
                  style={{
                    position: 'absolute',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    bottom: 0,
                    width: 64,
                    height: 1.5,
                    background: '#000',
                  }}
                />
              )}
            </button>
          ))}
        </nav>

        {/* === 피드 탭 === */}
        {tab === 'feed' && (
          <>
            <section className="pt-5 pb-2">
              <div className="px-5 flex items-baseline justify-between mb-2.5">
                <div className="text-[13px] font-semibold text-black">내 판정</div>
                <div className="text-[11px] text-black/45 tnum">{verdicts.length}개</div>
              </div>
              <div className="grid grid-cols-3 gap-[2px]">
                {verdicts.map(v => (
                  <button
                    key={v.id}
                    className="aspect-square relative overflow-hidden"
                    style={{ background: v.gradient }}
                    aria-label={`verdict ${v.id}`}
                  >
                    {v.locked && (
                      <>
                        <div style={{
                          position: 'absolute', inset: 0,
                          backdropFilter: 'blur(14px)',
                          WebkitBackdropFilter: 'blur(14px)',
                          background: 'rgba(0,0,0,0.1)',
                        }} />
                        <div style={{ position: 'absolute', top: 6, right: 6 }}>
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.8" style={{ filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.4))' }}>
                            <rect x="5" y="11" width="14" height="10" rx="1"/>
                            <path d="M8 11V7a4 4 0 0 1 8 0v4"/>
                          </svg>
                        </div>
                      </>
                    )}
                  </button>
                ))}
                <a
                  href="/verdict/new"
                  className="aspect-square bg-[#e8e5df] flex items-center justify-center"
                  aria-label="new verdict"
                >
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#1a1a1a" strokeWidth="1.2">
                    <path d="M12 5v14M5 12h14" strokeLinecap="round"/>
                  </svg>
                </a>
              </div>
            </section>

            <section className="pt-8">
              <div className="px-5 flex items-center justify-between mb-3">
                <div className="text-[13px] font-semibold text-black">다음 한 걸음</div>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => scrollBanner('left')}
                    aria-label="prev"
                    className="w-7 h-7 rounded-full border border-black/20 flex items-center justify-center active:bg-black/5"
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M15 6l-6 6 6 6" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </button>
                  <button
                    type="button"
                    onClick={() => scrollBanner('right')}
                    aria-label="next"
                    className="w-7 h-7 rounded-full border border-black/20 flex items-center justify-center active:bg-black/5"
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M9 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </button>
                </div>
              </div>

              <div
                ref={bannerRef}
                className="no-scrollbar flex gap-3 overflow-x-auto snap-x snap-mandatory pl-5"
                style={{ scrollPaddingLeft: '20px' }}
              >
                {features.map((f) => (
                  <a
                    key={f.key}
                    href={f.href}
                    className="snap-start flex-shrink-0 w-[78%] bg-white rounded-[12px] overflow-hidden border border-black/10"
                  >
                    <div className="p-5 h-[140px] flex flex-col justify-between">
                      <div>
                        <div className="text-[16px] font-bold text-black leading-tight">{f.ko}</div>
                        <div className="text-[12.5px] text-black/55 mt-1.5 leading-[1.5]">{f.sub}</div>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="tnum text-[12px] text-black/70 font-medium">
                          {f.cost === 0 ? '무료' : `${f.cost} 토큰`}
                        </span>
                        <div className="w-7 h-7 rounded-full bg-black/[0.06] flex items-center justify-center">
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="text-black/70">
                            <path d="M9 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                        </div>
                      </div>
                    </div>
                  </a>
                ))}
                <div className="flex-shrink-0 w-5" />
              </div>
            </section>

            <section className="px-5 pt-10 pb-2">
              <div className="text-[13px] font-semibold text-black mb-3">계정</div>
              <div className="border-t border-black/15">
                <a href="/tokens/purchase" className="h-12 flex items-center justify-between border-b border-black/15">
                  <span className="text-[14px] text-black">토큰 충전하기</span>
                  <div className="flex items-center gap-3">
                    <span className="text-[12px] text-black/50 tnum">{wallet.balance} 보유</span>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-black/40">
                      <path d="M9 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </div>
                </a>
                <a href="/onboarding/welcome" className="h-12 flex items-center justify-between border-b border-black/15">
                  <span className="text-[14px] text-black">온보딩 재설정</span>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-black/40">
                    <path d="M9 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </a>
                <button type="button" className="w-full h-12 flex items-center justify-between border-b border-black/15">
                  <span className="text-[14px] text-[#8B2A1F]/85">로그아웃</span>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-[#8B2A1F]/50">
                    <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4M10 17l5-5-5-5M15 12H3" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </button>
              </div>
            </section>
          </>
        )}

        {/* === 시각 탭 === */}
        {tab === 'sigak' && (
          <>
            <section className="px-5 pt-5">
              <div className="bg-[#ECE8E0] rounded-[8px] p-5">
                <div className="text-[11px] text-black/55 ls-pi mb-2.5 font-medium">PI — PERSONAL IMAGE</div>
                <div className="text-[13.5px] text-black/75 leading-[1.65]">
                  피드 추천과 서비스는 모두 시각이 본 당신을<br/>
                  기반으로 만들어집니다.
                </div>
              </div>
            </section>

            <section className="px-5 pt-4">
              <div className="bg-[#EDE8DE] rounded-[8px] p-6 relative" style={{ minHeight: 340 }}>
                {/* 실제 구현 시: 이 블러 영역에 실 PI 데이터 렌더 + blur released false 시 filter: blur 유지 */}
                <div className="blur-soft space-y-5" style={{ pointerEvents: 'none' }}>
                  {[
                    { labelW: '20%', textW: '75%' },
                    { labelW: '17%', textW: '66%' },
                    { labelW: '25%', textW: '80%' },
                    { labelW: '20%', textW: '60%' },
                    { labelW: '20%', textW: '66%' },
                  ].map((row, i) => (
                    <div key={i} className="space-y-2">
                      <div style={{ height: 7, background: 'rgba(0,0,0,0.12)', borderRadius: 3, width: row.labelW }}></div>
                      <div style={{ height: 10, background: 'rgba(0,0,0,0.08)', borderRadius: 3, width: row.textW }}></div>
                    </div>
                  ))}
                </div>
                <div style={{
                  position: 'absolute', inset: 0,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <div style={{
                    width: 48, height: 48, borderRadius: '50%',
                    background: '#3a3a3a',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                  }}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.8">
                      <rect x="5" y="11" width="14" height="10" rx="1"/>
                      <path d="M8 11V7a4 4 0 0 1 8 0v4"/>
                    </svg>
                  </div>
                </div>
              </div>
            </section>

            <section className="px-5 pt-4">
              <a
                href="/tokens/purchase?intent=pi"
                className="block w-full h-14 bg-[#0d0d0d] text-white flex items-center justify-center"
              >
                <span className="text-[14px] font-semibold">
                  충전하고 PI 확인 <span className="opacity-70 mx-1.5">·</span> <span className="tnum">50 토큰</span>
                </span>
              </a>
            </section>
          </>
        )}

        {/* === 변화 탭 === */}
        {tab === 'change' && (
          <section className="px-5 py-24 text-center">
            <div className="text-[15px] text-black/65" style={{ lineHeight: 1.75 }}>
              3건 이상의 판정이 쌓이면<br/>
              변화의 궤적이 보입니다.
            </div>
            <div className="text-[12px] text-black/40 mt-6 tnum">
              지금까지: 0건
            </div>
          </section>
        )}

        {/* Footer */}
        <footer className="px-5 pt-10 pb-6 safe-bottom">
          <div className="flex items-center justify-center gap-5 text-[12px] text-black/55 mb-5">
            <a href="/terms">이용약관</a>
            <a href="/terms#privacy">개인정보처리방침</a>
            <a href="/terms#refund">환불정책</a>
          </div>
          <div className="text-center text-[11px] text-black/45" style={{ lineHeight: 1.7 }}>
            <div>주식회사 시각 | 대표: 조찬형 | 사업자등록번호: 207-87-03690</div>
            <div>통신판매업신고번호: 제 2025-서울서대문-1006호</div>
            <div>주소: 서울특별시 서대문구 연세로 2나길 61, 1층 코워킹 스페이스</div>
            <div className="tnum">02-6402-0025 · partner@sigak.asia</div>
            <div className="mt-2 text-black/35">© 2026 SIGAK. All rights reserved.</div>
          </div>
        </footer>

      </div>
    </div>
  );
}