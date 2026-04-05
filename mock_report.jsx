import { useState } from "react";

// ─── Design Tokens ───
const T = {
  bg: "#F3F0EB",
  fg: "#000000",
  muted: "#666666",
  border: "#E0DCD6",
  blurBg: "rgba(243,240,235,0.85)",
  serif: "'Noto Serif KR', 'Noto Serif', Georgia, serif",
  sans: "-apple-system, BlinkMacSystemFont, 'Pretendard Variable', sans-serif",
};

// ─── Blur Overlay ───
function BlurLock({ children, locked, teaser }) {
  if (!locked) return children;
  return (
    <div style={{ position: "relative" }}>
      {teaser}
      <div style={{ position: "relative" }}>
        {children}
        <div style={{
          position: "absolute", inset: 0,
          backdropFilter: "blur(8px)",
          background: T.blurBg,
          mask: "linear-gradient(to bottom, transparent 0%, black 15%)",
          WebkitMask: "linear-gradient(to bottom, transparent 0%, black 15%)",
        }} />
      </div>
    </div>
  );
}

// ─── Section Wrapper ───
function Section({ label, children }) {
  return (
    <section style={{
      padding: "40px 0",
      borderBottom: `1px solid ${T.border}`,
    }}>
      <div style={{
        fontSize: 10, fontWeight: 600, letterSpacing: 3,
        color: T.muted, textTransform: "uppercase", marginBottom: 20,
        fontFamily: T.sans,
      }}>{label}</div>
      {children}
    </section>
  );
}

// ─── Coordinate Bar ───
function CoordBar({ axis, current, target }) {
  return (
    <div style={{
      padding: 20, border: `1px solid ${T.border}`,
      background: "rgba(255,255,255,0.3)",
    }}>
      <div style={{
        fontSize: 11, color: T.muted, marginBottom: 14,
        letterSpacing: 1, fontFamily: T.sans,
      }}>{axis}</div>
      <div style={{
        height: 3, background: T.border, borderRadius: 2,
        position: "relative", marginBottom: 10,
      }}>
        <div style={{
          position: "absolute", left: `${current * 100}%`, top: -4,
          width: 11, height: 11, borderRadius: "50%",
          background: T.fg, transform: "translateX(-50%)",
        }} />
        <div style={{
          position: "absolute", left: `${target * 100}%`, top: -4,
          width: 11, height: 11, borderRadius: "50%",
          border: `2px solid ${T.fg}`, background: "transparent",
          transform: "translateX(-50%)",
        }} />
        {/* Direction arrow */}
        <div style={{
          position: "absolute",
          left: `${Math.min(current, target) * 100 + 3}%`,
          right: `${(1 - Math.max(current, target)) * 100 + 3}%`,
          top: 0, height: 3,
          background: current < target
            ? "linear-gradient(to right, transparent, rgba(0,0,0,0.15))"
            : "linear-gradient(to left, transparent, rgba(0,0,0,0.15))",
        }} />
      </div>
      <div style={{
        display: "flex", justifyContent: "space-between",
        fontSize: 10, color: T.muted, fontFamily: T.sans,
      }}>
        <span>현재 <b style={{ color: T.fg }}>{Math.round(current * 100)}</b></span>
        <span>추구미 <b style={{ color: T.fg }}>{Math.round(target * 100)}</b></span>
      </div>
    </div>
  );
}

// ─── Tag ───
function Tag({ children, filled }) {
  return (
    <span style={{
      display: "inline-block",
      padding: "5px 14px",
      fontSize: 11,
      fontWeight: 600,
      borderRadius: 20,
      fontFamily: T.sans,
      ...(filled
        ? { background: T.fg, color: T.bg }
        : { border: `1px solid ${T.border}`, color: T.muted }
      ),
    }}>{children}</span>
  );
}

// ─── Bullet ───
function Bullet({ children }) {
  return (
    <div style={{
      display: "flex", alignItems: "flex-start", gap: 10,
      fontSize: 13.5, lineHeight: 1.75, marginBottom: 4,
    }}>
      <span style={{
        width: 4, height: 4, borderRadius: "50%",
        background: T.fg, marginTop: 9, flexShrink: 0,
      }} />
      <span>{children}</span>
    </div>
  );
}

// ═══════════════════════════════════════════
// MAIN REPORT
// ═══════════════════════════════════════════
export default function SigakReport() {
  const [accessLevel, setAccessLevel] = useState("free");

  const isStandard = accessLevel === "standard" || accessLevel === "full";
  const isFull = accessLevel === "full";

  return (
    <div style={{
      background: T.bg, color: T.fg, fontFamily: T.sans,
      minHeight: "100vh", WebkitFontSmoothing: "antialiased",
    }}>
      <div style={{
        maxWidth: 640, margin: "0 auto",
        padding: "0 24px",
      }}>

        {/* ── DEMO TOGGLE ── */}
        <div style={{
          position: "sticky", top: 0, zIndex: 50,
          background: T.bg, padding: "12px 0",
          borderBottom: `1px solid ${T.border}`,
          display: "flex", gap: 8, alignItems: "center",
        }}>
          <span style={{ fontSize: 10, color: T.muted, letterSpacing: 2, marginRight: 8 }}>
            VIEW AS:
          </span>
          {["free", "standard", "full"].map(level => (
            <button key={level} onClick={() => setAccessLevel(level)} style={{
              padding: "5px 14px", fontSize: 10, fontWeight: 600,
              letterSpacing: 1, textTransform: "uppercase",
              border: accessLevel === level ? "none" : `1px solid ${T.border}`,
              background: accessLevel === level ? T.fg : "transparent",
              color: accessLevel === level ? T.bg : T.muted,
              cursor: "pointer", borderRadius: 0,
              fontFamily: T.sans,
            }}>{level}</button>
          ))}
        </div>

        {/* ── COVER ── */}
        <section style={{ padding: "60px 0 40px", borderBottom: `1px solid ${T.border}` }}>
          <div style={{
            fontSize: 10, fontWeight: 600, letterSpacing: 5,
            color: T.muted, textTransform: "uppercase", marginBottom: 16,
          }}>SIGAK REPORT</div>
          <h1 style={{
            fontSize: 28, fontFamily: T.serif, fontWeight: 400,
            margin: 0, marginBottom: 8,
          }}>미감 좌표 리포트</h1>
          <div style={{
            display: "flex", alignItems: "center", gap: 12,
            fontSize: 13, color: T.muted, marginTop: 16,
          }}>
            <span style={{ fontWeight: 500, color: T.fg }}>김서연</span>
            <span style={{ width: 1, height: 12, background: T.border }} />
            <span>2026.04.15</span>
            <span style={{ width: 1, height: 12, background: T.border }} />
            <span style={{ fontSize: 10, letterSpacing: 1 }}>BASIC</span>
          </div>
        </section>

        {/* ── EXECUTIVE SUMMARY ── always visible */}
        <Section label="Summary">
          <p style={{
            fontSize: 17, lineHeight: 1.85, fontFamily: T.serif,
            fontWeight: 400, margin: 0,
          }}>
            또렷한 이목구비와 시크한 구조를 가졌지만,
            내면에는 부드럽고 내추럴한 감성을 품고 있는 얼굴입니다.
            제니를 추구하지만 실제 구조는 한소희에 더 가까워 —
            강렬함을 '빌려오는' 것보다 '자신의 차가움을 살리는' 방향이
            훨씬 효과적입니다.
          </p>
        </Section>

        {/* ── FACE STRUCTURE ── always visible */}
        <Section label="Face Structure">
          <div style={{
            display: "flex", alignItems: "baseline", gap: 16, marginBottom: 24,
          }}>
            <span style={{ fontSize: 26, fontFamily: T.serif, fontWeight: 400 }}>
              긴 타원형
            </span>
            <span style={{ fontSize: 13, color: T.muted }}>비율 1:1.45</span>
          </div>
          <Bullet>이마-중안-하안 비율이 균일하며, 이마가 약간 넓은 편</Bullet>
          <Bullet>광대가 높고 볼이 슬림 — 각도에 따라 날카로워 보이는 구조</Bullet>
          <Bullet>턱선이 V라인에 가깝지만 끝이 뾰족하지 않고 자연스럽게 마무리</Bullet>
          <Bullet>눈이 길고 눈꼬리가 살짝 올라감 — 시크한 인상의 핵심</Bullet>
        </Section>

        {/* ── SKIN ANALYSIS ── standard lock */}
        <Section label="Skin Analysis">
          {/* Teaser always visible */}
          <p style={{
            fontSize: 24, fontFamily: T.serif, fontWeight: 400,
            margin: "0 0 20px",
          }}>
            웜뮤트 · 밝은 편
          </p>

          <BlurLock locked={!isStandard} teaser={null}>
            <div style={{ marginBottom: 20 }}>
              <div style={{
                fontSize: 13, fontWeight: 600, marginBottom: 10,
              }}>추천 컬러</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {["로즈베이지", "더스티핑크", "테라코타", "머스타드", "카키"].map(c => (
                  <Tag key={c} filled>{c}</Tag>
                ))}
              </div>
            </div>
            <div>
              <div style={{
                fontSize: 13, fontWeight: 600, marginBottom: 10,
              }}>피해야 할 컬러</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {["블루핑크", "네온", "퓨어화이트"].map(c => (
                  <Tag key={c}>{c}</Tag>
                ))}
              </div>
            </div>
          </BlurLock>
        </Section>

        {/* ── COORDINATE MAP ── standard lock */}
        <Section label="Coordinate Map">
          <div style={{
            display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 20,
          }}>
            {["클래식-모던", "내추럴-글램", "큐트-시크", "캐주얼-포멀"].map(a => (
              <Tag key={a}>{a}</Tag>
            ))}
          </div>

          <BlurLock locked={!isStandard} teaser={null}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <CoordBar axis="클래식 — 모던" current={0.35} target={0.55} />
              <CoordBar axis="내추럴 — 글램" current={0.4} target={0.75} />
              <CoordBar axis="큐트 — 시크" current={0.7} target={0.8} />
              <CoordBar axis="캐주얼 — 포멀" current={0.45} target={0.65} />
            </div>
            <div style={{
              marginTop: 16, display: "flex", gap: 20,
              fontSize: 10, color: T.muted,
            }}>
              <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: T.fg }} />
                현재 위치
              </span>
              <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", border: `2px solid ${T.fg}` }} />
                추구미
              </span>
            </div>

            {/* Interpretation */}
            <div style={{
              marginTop: 24, padding: 20,
              border: `1px solid ${T.border}`,
              background: "rgba(255,255,255,0.3)",
            }}>
              <div style={{
                fontSize: 10, letterSpacing: 2, color: T.muted,
                marginBottom: 10, textTransform: "uppercase",
              }}>GAP ANALYSIS</div>
              <p style={{ fontSize: 13, lineHeight: 1.8, margin: 0 }}>
                가장 큰 갭은 <b>내추럴→글램 축(+35p)</b>입니다. 현재 내추럴 영역에 있지만
                글램을 강하게 추구하고 있어요. 그러나 시크 축은 이미 0.7로 높은 편 —
                글램을 추구할 때 '화려함'보다 '시크한 글램(cold glam)'으로 가는 것이
                구조적으로 자연스럽습니다.
              </p>
            </div>
          </BlurLock>
        </Section>

        {/* ── CELEB REFERENCE ── full lock */}
        <Section label="Celeb Reference">
          <p style={{
            fontSize: 24, fontFamily: T.serif, fontWeight: 400,
            margin: "0 0 6px",
          }}>
            한소희와 82% 유사
          </p>
          <p style={{
            fontSize: 13, color: T.muted, margin: "0 0 20px",
          }}>
            추구미: 제니 (현재 위치와의 거리: 38p)
          </p>

          <BlurLock locked={!isFull} teaser={null}>
            <div style={{ marginBottom: 24 }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>
                한소희와 닮은 포인트
              </div>
              <Bullet>긴 눈 + 올라간 눈꼬리 → 무표정 시 시크한 인상</Bullet>
              <Bullet>높은 광대 + 슬림한 볼 → 각도에 따라 날카로워지는 구조</Bullet>
              <Bullet>웜뮤트 톤 피부 + 도톰한 입술 → 차가운 구조에 부드러움을 더하는 요소</Bullet>
            </div>
            <div style={{
              padding: 20, border: `1px solid ${T.border}`,
              background: "rgba(255,255,255,0.3)",
            }}>
              <div style={{
                fontSize: 10, letterSpacing: 2, color: T.muted,
                marginBottom: 10, textTransform: "uppercase",
              }}>WHY NOT 제니?</div>
              <p style={{ fontSize: 13, lineHeight: 1.8, margin: 0 }}>
                제니의 핵심은 <b>동그란 얼굴형 + 도톰한 입술 + 강한 눈매</b>의 대비에서
                오는 '귀여운데 강한' 텐션입니다. 서연님은 얼굴형 자체가 긴 타원형이라
                이 대비가 구조적으로 만들어지지 않아요.
                제니 스타일을 그대로 따라하면 '어울리지 않는 강렬함'이 되고,
                한소희처럼 '구조에서 나오는 자연스러운 시크함'을 살리는 게 정답입니다.
              </p>
            </div>
            <div style={{ marginTop: 20 }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>
                방향 제안: Cold Glam
              </div>
              <Bullet>제니의 '글램'이 아니라 한소희·장원영의 '시크 글램'을 레퍼런스로</Bullet>
              <Bullet>컬러 포인트는 눈매에 집중 — 립은 뮤트 톤 유지</Bullet>
              <Bullet>헤어는 볼륨보다 텍스처 — 웨이브보다 스트레이트 or 젖은 질감</Bullet>
            </div>
          </BlurLock>
        </Section>

        {/* ── TREND CONTEXT ── full lock */}
        <Section label="Trend Context">
          <h3 style={{
            fontSize: 18, fontFamily: T.serif, fontWeight: 400,
            margin: "0 0 12px",
          }}>2026 S/S — "Quiet Face"의 시대</h3>

          <BlurLock locked={!isFull} teaser={null}>
            <p style={{ fontSize: 13, lineHeight: 1.8, color: T.muted, margin: "0 0 20px" }}>
              과시적 글램에서 벗어나 '구조가 좋은 얼굴'이 다시 주목받고 있습니다.
              최소한의 메이크업으로 얼굴 구조 자체를 드러내는 트렌드 —
              서연님의 또렷한 이목구비와 높은 광대는 이 트렌드에 정확히 부합합니다.
            </p>
            <div style={{
              padding: 20, border: `1px solid ${T.border}`,
              background: "rgba(255,255,255,0.3)",
            }}>
              <div style={{ fontSize: 10, letterSpacing: 2, color: T.muted, marginBottom: 10 }}>
                POSITION IN TREND
              </div>
              <p style={{ fontSize: 13, lineHeight: 1.8, margin: 0 }}>
                현재 "Quiet Face" 트렌드의 <b>중심 영역에 위치</b>하고 있어요.
                별도의 방향 수정 없이 현재 구조를 잘 살리는 것만으로
                트렌드와 정렬됩니다. 오히려 과한 글램 시도가 트렌드 역행이 될 수 있어요.
              </p>
            </div>
          </BlurLock>
        </Section>

        {/* ── ACTION PLAN ── full lock */}
        <Section label="Action Plan">
          <div style={{
            display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 20,
          }}>
            <Tag filled>메이크업 HIGH</Tag>
            <Tag filled>헤어 MEDIUM</Tag>
            <Tag>스타일링 LOW</Tag>
          </div>

          <BlurLock locked={!isFull} teaser={null}>
            {/* Makeup */}
            <div style={{ marginBottom: 24 }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 10px" }}>
                메이크업
              </h3>
              <Bullet>베이스: 글로우보다 세미매트. 피부 결을 살리되 광택은 하이라이터로 포인트만</Bullet>
              <Bullet>아이: 브라운-버건디 계열 음영. 아이라인은 눈꼬리 연장 — 올라간 눈 구조를 강조</Bullet>
              <Bullet>립: 더스티로즈, MLBB 컬러. 선명한 레드보다 뮤트 톤이 얼굴 구조와 균형</Bullet>
              <Bullet>눈썹: 자연스러운 아치형 유지. 일자눈썹은 긴 얼굴형을 더 길어 보이게 함</Bullet>
            </div>

            {/* Hair */}
            <div style={{ marginBottom: 24 }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 10px" }}>
                헤어
              </h3>
              <Bullet>기장: 쇄골~가슴 중간. 너무 짧으면 긴 얼굴이 강조, 너무 길면 시크함이 희석</Bullet>
              <Bullet>스타일: S컬 레이어드 — 볼 옆에서 움직이면 광대와 턱선 밸런스</Bullet>
              <Bullet>컬러: 다크브라운~초콜릿. 밝은 컬러보다 어두운 톤이 시크한 구조를 받쳐줌</Bullet>
            </div>

            {/* Styling */}
            <div>
              <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 10px" }}>
                스타일링
              </h3>
              <Bullet>넥라인: V넥, 셔츠칼라 위주 — 긴 목과 쇄골 라인을 활용</Bullet>
              <Bullet>톤: 블랙, 네이비, 차콜 베이스에 더스티핑크나 머스타드 포인트</Bullet>
              <Bullet>실루엣: 구조감 있는 아우터(블레이저, 트렌치)가 체형과 얼굴 구조 모두에 맞음</Bullet>
            </div>
          </BlurLock>
        </Section>

        {/* ── EXPERT NOTE ── full only */}
        {isFull && (
          <Section label="Expert Note">
            <div style={{
              padding: 24, border: `1px solid ${T.border}`,
              background: "rgba(255,255,255,0.3)",
            }}>
              <p style={{
                fontSize: 14, lineHeight: 1.9, margin: 0,
                fontFamily: T.serif, fontStyle: "italic",
              }}>
                "서연님의 가장 큰 강점은 '가만히 있어도 인상이 남는 구조'입니다.
                이런 얼굴은 꾸밀수록 좋아지는 게 아니라, 적절히 비울수록 살아나요.
                제니에 대한 선망은 이해하지만 — 서연님의 구조는 제니와 정반대 방향에서
                아름답습니다. 한소희가 왜 강한 메이크업을 안 하는지 생각해보시면
                방향이 보일 거예요."
              </p>
              <div style={{
                marginTop: 16, fontSize: 11, color: T.muted,
                letterSpacing: 1,
              }}>— SIGAK Aesthetic Director</div>
            </div>
          </Section>
        )}

        {/* ── PAYWALL CTA ── */}
        {accessLevel !== "full" && (
          <section style={{
            padding: "48px 0",
            textAlign: "center",
          }}>
            <div style={{
              padding: 32, border: `1px solid ${T.border}`,
            }}>
              {accessLevel === "free" && (
                <>
                  <div style={{
                    fontSize: 10, letterSpacing: 3, color: T.muted,
                    marginBottom: 12, textTransform: "uppercase",
                  }}>UNLOCK STANDARD</div>
                  <p style={{
                    fontSize: 15, fontFamily: T.serif, margin: "0 0 6px",
                  }}>피부톤 분석 + 좌표계 전체 결과</p>
                  <p style={{
                    fontSize: 12, color: T.muted, margin: "0 0 24px",
                  }}>내 위치와 추구미 사이의 정확한 거리를 확인하세요</p>
                  <button style={{
                    padding: "14px 40px", background: T.fg, color: T.bg,
                    border: "none", fontSize: 13, fontWeight: 600,
                    letterSpacing: 1, cursor: "pointer",
                  }}>₩5,000 잠금 해제</button>
                </>
              )}
              {accessLevel === "standard" && (
                <>
                  <div style={{
                    fontSize: 10, letterSpacing: 3, color: T.muted,
                    marginBottom: 12, textTransform: "uppercase",
                  }}>UNLOCK FULL</div>
                  <p style={{
                    fontSize: 15, fontFamily: T.serif, margin: "0 0 6px",
                  }}>셀럽 매칭 + 트렌드 분석 + 실행 가이드</p>
                  <p style={{
                    fontSize: 12, color: T.muted, margin: "0 0 24px",
                  }}>"왜 제니가 아닌지" — 구체적 방향을 확인하세요</p>
                  <button style={{
                    padding: "14px 40px", background: T.fg, color: T.bg,
                    border: "none", fontSize: 13, fontWeight: 600,
                    letterSpacing: 1, cursor: "pointer",
                  }}>₩15,000 추가 잠금 해제</button>
                  <div style={{
                    marginTop: 8, fontSize: 10, color: T.muted,
                  }}>이전 결제 포함 총 ₩20,000</div>
                </>
              )}
            </div>
          </section>
        )}

        {/* ── FOOTER ── */}
        <footer style={{
          padding: "32px 0",
          textAlign: "center",
          fontSize: 10, color: T.muted, letterSpacing: 2,
        }}>
          SIGAK © 2026
        </footer>

      </div>
    </div>
  );
}