// SIGAK — /profile (마케터 redesign, 2026-04-24)
//
// 3-tab 구조: 피드 / 시각 / 변화. 모바일 max-w 430px.
// 기존 기능 전부 보존 (useOnboardingGuard / useTokenBalance / resetOnboarding /
// logout / SiteFooter) — UI 만 MARKETER.jsx 에 맞춰 교체.
//
// 피드 탭:
//   - TopBar (검정) + identity 헤더 + 탭
//   - "내 판정" 3열 그리드 (listVerdicts) + 마지막 셀 /verdict/new
//   - "다음 한 걸음" 수평 스크롤 배너 (Sia / 판정 / Best Shot / 추구미)
//   - 계정 섹션 (충전 / 시각 재설정 / 로그아웃)
// 시각 탭:
//   - PI 안내 + 블러 잠금 미리보기 + "충전하고 PI 확인" CTA
//   * PI 실 엔진 미구현 — placeholder. tokens/purchase?intent=pi 로만 이동.
// 변화 탭:
//   - 3건 미만 empty state.

"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError } from "@/lib/api/fetch";
import { resetOnboarding } from "@/lib/api/onboarding";
import { listVerdicts, resolvePhotoUrl } from "@/lib/api/verdicts";
import { getCurrentUser, getToken, logout } from "@/lib/auth";
import { useOnboardingGuard } from "@/hooks/use-onboarding-guard";
import { useTokenBalance } from "@/hooks/use-token-balance";
import { SiteFooter } from "@/components/sigak/site-footer";
import type { VerdictListItem } from "@/lib/types/mvp";

type TabKey = "feed" | "sigak" | "change";

interface Feature {
  key: string;
  ko: string;
  sub: string;
  cost: number;          // 토큰 (0 이면 "무료")
  href: string;
}

// tokens.py 에 맞춘 실제 소모량.
//   Sia:       무료
//   Verdict:   진단 해제 10 토큰 (COST_DIAGNOSIS_UNLOCK)
//   Best Shot: 30 토큰 (COST_BEST_SHOT)
//   Aspiration: 20 토큰 (COST_ASPIRATION_IG / _PINTEREST)
const FEATURES: readonly Feature[] = [
  { key: "sia",        ko: "Sia 대화",     sub: "대화로 당신을 같이 정리해요",          cost: 0,  href: "/sia" },
  { key: "verdict",    ko: "시각의 판정",  sub: "지금 장면 한 장을 골라드려요",          cost: 10, href: "/verdict/new" },
  { key: "bestshot",   ko: "Best Shot",    sub: "사진 여러 장에서 한 장",                cost: 30, href: "/best-shot" },
  { key: "aspiration", ko: "추구미 분석",  sub: "따라가는 이미지, 실제로 뭐가 다른지",   cost: 20, href: "/aspiration" },
];

// fallback gradient — gold_photo_url 이 null 일 때 셀 배경.
const VERDICT_GRADIENTS = [
  "linear-gradient(135deg, #d4c7b0 0%, #8a6f4f 100%)",
  "linear-gradient(135deg, #c9bdaa 0%, #9d8e78 100%)",
  "linear-gradient(200deg, #dcd2bf 0%, #ba9f7e 100%)",
  "linear-gradient(135deg, #b8a78a 0%, #80695a 100%)",
  "linear-gradient(165deg, #d6c5a7 0%, #9e8b6a 100%)",
];

export default function ProfilePage() {
  const router = useRouter();
  const { status } = useOnboardingGuard();
  const { balance } = useTokenBalance();

  const [tab, setTab] = useState<TabKey>("feed");
  const bannerRef = useRef<HTMLDivElement | null>(null);

  const [profile, setProfile] = useState<{
    name: string;
    email: string;
    profileImage: string;
    kakaoId: string;
  } | null>(null);

  const [verdicts, setVerdicts] = useState<VerdictListItem[]>([]);
  const [resetting, setResetting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/auth/login?next=/profile");
      return;
    }
    const u = getCurrentUser();
    if (u) {
      setProfile({
        name: u.name || "",
        email: u.email || "",
        profileImage: u.profileImage || "",
        kakaoId: u.kakaoId || "",
      });
    }
  }, [router]);

  // Verdict 리스트 — 피드 탭 그리드 용.
  useEffect(() => {
    if (status !== "ready") return;
    let cancelled = false;
    (async () => {
      try {
        const res = await listVerdicts(30, 0);
        if (!cancelled) setVerdicts(res.verdicts);
      } catch (e) {
        // 리스트 조회 실패는 치명적이지 않음 — 그리드 비움. 인증 오류만 리디렉트.
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/auth/login?next=/profile");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [status, router]);

  async function handleResetOnboarding() {
    if (resetting) return;
    if (typeof window !== "undefined") {
      const ok = window.confirm(
        "온보딩을 처음부터 다시 진행하시겠어요?\n기존 답변은 자동 불러와집니다.",
      );
      if (!ok) return;
    }
    setResetting(true);
    setError(null);
    try {
      await resetOnboarding();
      router.push("/onboarding/welcome");
    } catch (e) {
      setResetting(false);
      if (e instanceof ApiError && e.status === 401) {
        router.replace("/auth/login");
        return;
      }
      setError(e instanceof Error ? e.message : "초기화 실패");
    }
  }

  function handleLogout() {
    if (typeof window !== "undefined") {
      const ok = window.confirm("로그아웃 하시겠어요?");
      if (!ok) return;
    }
    logout();
  }

  function scrollBanner(dir: "left" | "right") {
    const el = bannerRef.current;
    if (!el) return;
    const cardWidth = el.offsetWidth * 0.78 + 12;
    el.scrollBy({ left: dir === "right" ? cardWidth : -cardWidth, behavior: "smooth" });
  }

  if (status !== "ready") {
    return (
      <div
        style={{ minHeight: "100vh", background: "var(--color-paper)" }}
        aria-busy
      />
    );
  }

  const tabLabel: Record<TabKey, string> = {
    feed: "피드",
    sigak: "시각",
    change: "변화",
  };

  return (
    <div
      className="font-sans"
      style={{
        minHeight: "100vh",
        background: "var(--color-paper)",
        color: "var(--color-ink)",
      }}
    >
      {/* 지역 유틸리티 — MARKETER.jsx 에서 사용한 스크롤바/safe-area 제어. */}
      <style>{`
        .profile-no-scrollbar::-webkit-scrollbar { display: none; }
        .profile-no-scrollbar {
          -ms-overflow-style: none;
          scrollbar-width: none;
          -webkit-overflow-scrolling: touch;
        }
        .profile-safe-bottom { padding-bottom: max(24px, env(safe-area-inset-bottom)); }
        .profile-blur-soft { filter: blur(4px); }
      `}</style>

      <div style={{ maxWidth: 430, margin: "0 auto" }}>
        {/* TopBar */}
        <header
          style={{
            height: 48,
            background: "#0d0d0d",
            color: "#ffffff",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0 16px",
          }}
        >
          <div
            style={{
              fontSize: 13,
              fontWeight: 600,
              letterSpacing: "0.4em",
            }}
          >
            SIGAK
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span
              className="tabular-nums"
              style={{ fontSize: 14, fontWeight: 500 }}
            >
              {balance ?? 0}
            </span>
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: "50%",
                background: "#b0cfe8",
                overflow: "hidden",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              {profile?.profileImage ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img
                  src={profile.profileImage}
                  alt=""
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "cover",
                    display: "block",
                  }}
                />
              ) : (
                <AvatarFallback size={18} />
              )}
            </div>
            <Link
              href="/verdict/new"
              aria-label="새 판정"
              style={{
                width: 32,
                height: 32,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#ffffff",
              }}
            >
              <PlusIcon size={18} strokeWidth={1.4} />
            </Link>
          </div>
        </header>

        {/* Identity */}
        <section
          style={{
            padding: "24px 20px 20px",
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <div
              style={{
                width: 68,
                height: 68,
                borderRadius: "50%",
                background: "#b0cfe8",
                overflow: "hidden",
                flexShrink: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              {profile?.profileImage ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img
                  src={profile.profileImage}
                  alt=""
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "cover",
                    display: "block",
                  }}
                />
              ) : (
                <AvatarFallback size={44} />
              )}
            </div>
            <div style={{ minWidth: 0 }}>
              <div
                style={{
                  fontSize: 22,
                  fontWeight: 700,
                  color: "#000",
                  lineHeight: 1.15,
                }}
              >
                {profile?.name || "익명"}
              </div>
              {profile?.kakaoId && (
                <div
                  className="tabular-nums"
                  style={{
                    fontSize: 12,
                    color: "rgba(0,0,0,0.45)",
                    marginTop: 2,
                  }}
                >
                  @{profile.kakaoId}
                </div>
              )}
            </div>
          </div>
          <div style={{ textAlign: "right", paddingTop: 8 }}>
            <div
              style={{
                width: 28,
                height: 1,
                background: "rgba(0,0,0,0.3)",
                marginLeft: "auto",
                marginBottom: 6,
              }}
            />
            <div style={{ fontSize: 11, color: "rgba(0,0,0,0.55)" }}>
              {tabLabel[tab]}
            </div>
          </div>
        </section>

        {/* Tabs */}
        <nav
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            borderBottom: "1px solid rgba(0,0,0,0.15)",
          }}
        >
          {(["feed", "sigak", "change"] as const).map((key) => (
            <button
              key={key}
              type="button"
              onClick={() => setTab(key)}
              style={{
                height: 44,
                background: "transparent",
                border: "none",
                position: "relative",
                fontSize: 14,
                fontWeight: tab === key ? 600 : 400,
                color:
                  tab === key ? "#000" : "rgba(0,0,0,0.45)",
                cursor: "pointer",
                letterSpacing: "-0.005em",
              }}
            >
              {tabLabel[key]}
              {tab === key && (
                <span
                  style={{
                    position: "absolute",
                    left: "50%",
                    transform: "translateX(-50%)",
                    bottom: 0,
                    width: 64,
                    height: 1.5,
                    background: "#000",
                  }}
                />
              )}
            </button>
          ))}
        </nav>

        {/* 피드 탭 */}
        {tab === "feed" && (
          <>
            {/* 내 판정 그리드 */}
            <section style={{ paddingTop: 20, paddingBottom: 8 }}>
              <div
                style={{
                  padding: "0 20px",
                  display: "flex",
                  alignItems: "baseline",
                  justifyContent: "space-between",
                  marginBottom: 10,
                }}
              >
                <div style={{ fontSize: 13, fontWeight: 600, color: "#000" }}>
                  내 판정
                </div>
                <div
                  className="tabular-nums"
                  style={{ fontSize: 11, color: "rgba(0,0,0,0.45)" }}
                >
                  {verdicts.length}개
                </div>
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(3, 1fr)",
                  gap: 2,
                }}
              >
                {verdicts.map((v, i) => (
                  <VerdictCell
                    key={v.verdict_id}
                    item={v}
                    fallbackGradient={
                      VERDICT_GRADIENTS[i % VERDICT_GRADIENTS.length]
                    }
                    onClick={() =>
                      router.push(
                        `/verdict/${encodeURIComponent(v.verdict_id)}`,
                      )
                    }
                  />
                ))}
                <Link
                  href="/verdict/new"
                  aria-label="새 판정"
                  style={{
                    aspectRatio: "1 / 1",
                    background: "#e8e5df",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#1a1a1a",
                    textDecoration: "none",
                  }}
                >
                  <PlusIcon size={24} strokeWidth={1.2} />
                </Link>
              </div>
            </section>

            {/* 다음 한 걸음 배너 */}
            <section style={{ paddingTop: 32 }}>
              <div
                style={{
                  padding: "0 20px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginBottom: 12,
                }}
              >
                <div style={{ fontSize: 13, fontWeight: 600, color: "#000" }}>
                  다음 한 걸음
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <BannerNavButton
                    direction="left"
                    onClick={() => scrollBanner("left")}
                  />
                  <BannerNavButton
                    direction="right"
                    onClick={() => scrollBanner("right")}
                  />
                </div>
              </div>

              <div
                ref={bannerRef}
                className="profile-no-scrollbar"
                style={{
                  display: "flex",
                  gap: 12,
                  overflowX: "auto",
                  scrollSnapType: "x mandatory",
                  paddingLeft: 20,
                  scrollPaddingLeft: 20,
                }}
              >
                {FEATURES.map((f) => (
                  <FeatureCard key={f.key} feature={f} />
                ))}
                <div style={{ flexShrink: 0, width: 20 }} />
              </div>
            </section>

            {/* 계정 섹션 */}
            <section style={{ padding: "40px 20px 8px" }}>
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color: "#000",
                  marginBottom: 12,
                }}
              >
                계정
              </div>
              <div style={{ borderTop: "1px solid rgba(0,0,0,0.15)" }}>
                <Link
                  href="/tokens/purchase"
                  style={{
                    height: 48,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    borderBottom: "1px solid rgba(0,0,0,0.15)",
                    color: "#000",
                    textDecoration: "none",
                  }}
                >
                  <span style={{ fontSize: 14 }}>토큰 충전하기</span>
                  <span style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <span
                      className="tabular-nums"
                      style={{ fontSize: 12, color: "rgba(0,0,0,0.5)" }}
                    >
                      {balance ?? 0} 보유
                    </span>
                    <ChevronRight size={12} color="rgba(0,0,0,0.4)" />
                  </span>
                </Link>

                <button
                  type="button"
                  onClick={handleResetOnboarding}
                  disabled={resetting}
                  style={{
                    width: "100%",
                    height: 48,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    borderBottom: "1px solid rgba(0,0,0,0.15)",
                    background: "transparent",
                    border: "none",
                    borderTop: "none",
                    cursor: resetting ? "default" : "pointer",
                    padding: 0,
                    opacity: resetting ? 0.5 : 1,
                  }}
                >
                  <span style={{ fontSize: 14, color: "#000" }}>
                    {resetting ? "처리 중..." : "시각 재설정"}
                  </span>
                  <ChevronRight size={12} color="rgba(0,0,0,0.4)" />
                </button>

                <button
                  type="button"
                  onClick={handleLogout}
                  style={{
                    width: "100%",
                    height: 48,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    borderBottom: "1px solid rgba(0,0,0,0.15)",
                    background: "transparent",
                    border: "none",
                    borderTop: "none",
                    cursor: "pointer",
                    padding: 0,
                  }}
                >
                  <span
                    style={{
                      fontSize: 14,
                      color: "rgba(139,42,31,0.85)",   // #8B2A1F @ 85%
                    }}
                  >
                    로그아웃
                  </span>
                  <LogoutIcon size={12} color="rgba(139,42,31,0.5)" />
                </button>
              </div>
              {error && (
                <p
                  role="alert"
                  style={{
                    marginTop: 12,
                    fontSize: 12,
                    color: "var(--color-danger)",
                    letterSpacing: "-0.005em",
                  }}
                >
                  {error}
                </p>
              )}
            </section>
          </>
        )}

        {/* 시각 탭 */}
        {tab === "sigak" && (
          <>
            <section style={{ padding: "20px 20px 0" }}>
              <div
                style={{
                  background: "#ECE8E0",
                  borderRadius: 8,
                  padding: 20,
                }}
              >
                <div
                  style={{
                    fontSize: 11,
                    color: "rgba(0,0,0,0.55)",
                    letterSpacing: "0.15em",
                    marginBottom: 10,
                    fontWeight: 500,
                  }}
                >
                  PI — PERSONAL IMAGE
                </div>
                <div
                  style={{
                    fontSize: 13.5,
                    color: "rgba(0,0,0,0.75)",
                    lineHeight: 1.65,
                  }}
                >
                  피드 추천과 서비스는 모두 시각이 본 당신을
                  <br />
                  기반으로 만들어집니다.
                </div>
              </div>
            </section>

            <section style={{ padding: "16px 20px 0" }}>
              <div
                style={{
                  background: "#EDE8DE",
                  borderRadius: 8,
                  padding: 24,
                  position: "relative",
                  minHeight: 340,
                }}
              >
                {/* PI 블러 미리보기 — 실 데이터 주입 시 여기 렌더 + blur_released=false 유지 */}
                <div
                  className="profile-blur-soft"
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 20,
                    pointerEvents: "none",
                  }}
                >
                  {[
                    { labelW: "20%", textW: "75%" },
                    { labelW: "17%", textW: "66%" },
                    { labelW: "25%", textW: "80%" },
                    { labelW: "20%", textW: "60%" },
                    { labelW: "20%", textW: "66%" },
                  ].map((row, i) => (
                    <div
                      key={i}
                      style={{ display: "flex", flexDirection: "column", gap: 8 }}
                    >
                      <div
                        style={{
                          height: 7,
                          background: "rgba(0,0,0,0.12)",
                          borderRadius: 3,
                          width: row.labelW,
                        }}
                      />
                      <div
                        style={{
                          height: 10,
                          background: "rgba(0,0,0,0.08)",
                          borderRadius: 3,
                          width: row.textW,
                        }}
                      />
                    </div>
                  ))}
                </div>
                <div
                  style={{
                    position: "absolute",
                    inset: 0,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <div
                    style={{
                      width: 48,
                      height: 48,
                      borderRadius: "50%",
                      background: "#3a3a3a",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
                    }}
                  >
                    <LockIcon size={18} color="#ffffff" strokeWidth={1.8} />
                  </div>
                </div>
              </div>
            </section>

            <section style={{ padding: "16px 20px 0" }}>
              <Link
                href="/tokens/purchase?intent=pi"
                style={{
                  display: "flex",
                  width: "100%",
                  height: 56,
                  background: "#0d0d0d",
                  color: "#ffffff",
                  alignItems: "center",
                  justifyContent: "center",
                  textDecoration: "none",
                }}
              >
                <span style={{ fontSize: 14, fontWeight: 600 }}>
                  충전하고 PI 확인
                  <span style={{ opacity: 0.7, margin: "0 6px" }}>·</span>
                  <span className="tabular-nums">50 토큰</span>
                </span>
              </Link>
            </section>
          </>
        )}

        {/* 변화 탭 */}
        {tab === "change" && (
          <section
            style={{
              padding: "96px 20px",
              textAlign: "center",
            }}
          >
            <div
              style={{
                fontSize: 15,
                color: "rgba(0,0,0,0.65)",
                lineHeight: 1.75,
              }}
            >
              3건 이상의 판정이 쌓이면
              <br />
              변화의 궤적이 보입니다.
            </div>
            <div
              className="tabular-nums"
              style={{
                fontSize: 12,
                color: "rgba(0,0,0,0.4)",
                marginTop: 24,
              }}
            >
              지금까지: {verdicts.length}건
            </div>
          </section>
        )}

        <div className="profile-safe-bottom">
          <SiteFooter />
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
//  Subcomponents
// ─────────────────────────────────────────────

function VerdictCell({
  item,
  fallbackGradient,
  onClick,
}: {
  item: VerdictListItem;
  fallbackGradient: string;
  onClick: () => void;
}) {
  const locked = !item.blur_released;
  const url = resolvePhotoUrl(item.gold_photo_url);
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={`판정 ${item.verdict_id}`}
      style={{
        aspectRatio: "1 / 1",
        position: "relative",
        overflow: "hidden",
        background: url ? "rgba(0,0,0,0.04)" : fallbackGradient,
        border: "none",
        padding: 0,
        cursor: "pointer",
      }}
    >
      {url && (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img
          src={url}
          alt=""
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            display: "block",
          }}
        />
      )}
      {locked && (
        <>
          <div
            style={{
              position: "absolute",
              inset: 0,
              backdropFilter: "blur(14px)",
              WebkitBackdropFilter: "blur(14px)",
              background: "rgba(0,0,0,0.1)",
            }}
          />
          <div style={{ position: "absolute", top: 6, right: 6 }}>
            <LockIcon
              size={12}
              color="#ffffff"
              strokeWidth={1.8}
              shadow
            />
          </div>
        </>
      )}
    </button>
  );
}

function FeatureCard({ feature }: { feature: Feature }) {
  return (
    <Link
      href={feature.href}
      style={{
        scrollSnapAlign: "start",
        flexShrink: 0,
        width: "78%",
        background: "#ffffff",
        borderRadius: 12,
        overflow: "hidden",
        border: "1px solid rgba(0,0,0,0.1)",
        color: "#000",
        textDecoration: "none",
      }}
    >
      <div
        style={{
          padding: 20,
          height: 140,
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
        }}
      >
        <div>
          <div style={{ fontSize: 16, fontWeight: 700, lineHeight: 1.2, color: "#000" }}>
            {feature.ko}
          </div>
          <div
            style={{
              fontSize: 12.5,
              color: "rgba(0,0,0,0.55)",
              marginTop: 6,
              lineHeight: 1.5,
            }}
          >
            {feature.sub}
          </div>
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <span
            className="tabular-nums"
            style={{
              fontSize: 12,
              color: "rgba(0,0,0,0.7)",
              fontWeight: 500,
            }}
          >
            {feature.cost === 0 ? "무료" : `${feature.cost} 토큰`}
          </span>
          <div
            style={{
              width: 28,
              height: 28,
              borderRadius: "50%",
              background: "rgba(0,0,0,0.06)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <ChevronRight size={12} color="rgba(0,0,0,0.7)" />
          </div>
        </div>
      </div>
    </Link>
  );
}

function BannerNavButton({
  direction,
  onClick,
}: {
  direction: "left" | "right";
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={direction === "left" ? "이전" : "다음"}
      style={{
        width: 28,
        height: 28,
        borderRadius: "50%",
        border: "1px solid rgba(0,0,0,0.2)",
        background: "transparent",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        cursor: "pointer",
      }}
    >
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path
          d={direction === "left" ? "M15 6l-6 6 6 6" : "M9 6l6 6-6 6"}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </button>
  );
}

// ─────────────────────────────────────────────
//  Icons
// ─────────────────────────────────────────────

function AvatarFallback({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="#7aa0c1" aria-hidden>
      <path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm0 2c-3 0-8 1.5-8 4.5V21h16v-2.5c0-3-5-4.5-8-4.5z" />
    </svg>
  );
}

function PlusIcon({
  size,
  strokeWidth = 1.4,
}: {
  size: number;
  strokeWidth?: number;
}) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={strokeWidth} aria-hidden>
      <path d="M12 5v14M5 12h14" strokeLinecap="round" />
    </svg>
  );
}

function ChevronRight({
  size,
  color,
}: {
  size: number;
  color: string;
}) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.5" aria-hidden>
      <path d="M9 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function LockIcon({
  size,
  color,
  strokeWidth = 1.8,
  shadow = false,
}: {
  size: number;
  color: string;
  strokeWidth?: number;
  shadow?: boolean;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={strokeWidth}
      style={shadow ? { filter: "drop-shadow(0 1px 2px rgba(0,0,0,0.4))" } : undefined}
      aria-hidden
    >
      <rect x="5" y="11" width="14" height="10" rx="1" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </svg>
  );
}

function LogoutIcon({
  size,
  color,
}: {
  size: number;
  color: string;
}) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.5" aria-hidden>
      <path
        d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4M10 17l5-5-5-5M15 12H3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
