// SIGAK MVP v1.2 (D-6) — /profile
//
// 마케터 redesign (redesign/프로필_1815.html) 차용:
//   - 3탭 (피드 / 시각 / 변화) 구조
//   - menu (NumStep 스타일) — 01 피드 분석하기 FREE / 02 추구미 살펴보기 🪙20
//   - 시각 / 변화 탭은 placeholder (PI / Monthly 곧 출시)
//   - menu 03~05 (시각 분석하기 / 소통하기 / 이벤트) 는 본인 카피 전달 후 추가
//
// 토큰 잔액 + 충전 / logout / 계정 탈퇴 / 약관 링크는 모두 보존.
"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { getCurrentUser, getToken, logout } from "@/lib/auth";
import { useOnboardingGuard } from "@/hooks/use-onboarding-guard";
import { useTokenBalance } from "@/hooks/use-token-balance";
import { FeedTopBar } from "@/components/ui/sigak";
import { VerdictGrid } from "@/components/sigak/verdict-grid";
import { SiteFooter } from "@/components/sigak/site-footer";

type Tab = "feed" | "sigak" | "change";

export default function ProfilePage() {
  const router = useRouter();
  const { status } = useOnboardingGuard();
  const { balance } = useTokenBalance();

  const [tab, setTab] = useState<Tab>("feed");

  const [profile, setProfile] = useState<{
    name: string;
    email: string;
    profileImage: string;
    kakaoId: string;
  } | null>(null);

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

  function handleLogout() {
    if (typeof window !== "undefined") {
      const ok = window.confirm("로그아웃 하시겠어요?");
      if (!ok) return;
    }
    logout();
  }

  function handleDeleteAccount() {
    if (typeof window === "undefined") return;
    const ok = window.confirm(
      "계정 탈퇴를 요청하시겠어요?\n\n" +
        "운영팀 (partner@sigak.asia) 에 탈퇴 요청 이메일이 발송됩니다.\n" +
        "요청 확인 후 7일 내에 계정과 관련 데이터가 삭제됩니다.",
    );
    if (!ok) return;
    const kakaoId = profile?.kakaoId || "(unknown)";
    const subject = encodeURIComponent("[SIGAK] 계정 탈퇴 요청");
    const body = encodeURIComponent(
      "SIGAK 계정 탈퇴를 요청합니다.\n\n" +
        `카카오 ID: ${kakaoId}\n` +
        "요청 일시: " +
        new Date().toISOString() +
        "\n\n" +
        "다음 데이터의 삭제를 요청합니다:\n" +
        "- 계정 및 프로필\n" +
        "- 판정 / 피드 / 추구미 분석 / Best Shot 기록\n" +
        "- 업로드 사진 및 생성 결과물\n" +
        "- Sia 대화 기록\n",
    );
    window.location.href = `mailto:partner@sigak.asia?subject=${subject}&body=${body}`;
  }

  if (status !== "ready") {
    return <div style={{ minHeight: "100vh", background: "var(--color-paper)" }} aria-busy />;
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--color-paper)",
        color: "var(--color-ink)",
        fontFamily: "var(--font-sans)",
      }}
    >
      <FeedTopBar backTarget="/" />

      {/* PROFILE ME — 큰 아바타 + 이름 + 이메일 (중앙 정렬) */}
      <section style={{ padding: "32px 24px 28px", textAlign: "center" }}>
        <div
          style={{
            width: 72,
            height: 72,
            borderRadius: "50%",
            margin: "0 auto 16px",
            overflow: "hidden",
            background:
              profile?.profileImage
                ? "transparent"
                : "linear-gradient(135deg, #e8d9c8, #b8a58a)",
            boxShadow: "0 4px 12px rgba(0,0,0,0.06)",
          }}
        >
          {profile?.profileImage && (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={profile.profileImage}
              alt=""
              style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
            />
          )}
        </div>
        <div
          className="font-serif"
          style={{
            fontSize: 22,
            fontWeight: 500,
            letterSpacing: "-0.018em",
            color: "var(--color-ink)",
            marginBottom: 6,
          }}
        >
          {profile?.name || "익명"}
        </div>
        {profile?.email && (
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              color: "var(--color-mute)",
              letterSpacing: "0.02em",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              padding: "0 24px",
            }}
          >
            {profile.email}
          </div>
        )}
      </section>

      {/* TABS — 피드 / 시각 / 변화 */}
      <nav
        style={{
          display: "flex",
          justifyContent: "center",
          gap: 32,
          padding: "0 24px",
          borderBottom: "1px solid var(--color-line)",
        }}
      >
        {[
          { key: "feed", label: "피드" },
          { key: "sigak", label: "시각" },
          { key: "change", label: "변화" },
        ].map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key as Tab)}
            className="font-serif"
            style={{
              padding: "16px 0",
              fontSize: 14.5,
              fontWeight: 500,
              letterSpacing: "-0.01em",
              color: tab === t.key ? "var(--color-ink)" : "var(--color-mute)",
              background: "transparent",
              border: "none",
              borderBottom:
                tab === t.key ? "1.5px solid var(--color-danger)" : "1.5px solid transparent",
              marginBottom: -1,
              cursor: "pointer",
              userSelect: "none",
            }}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {/* TAB CONTENT */}
      {tab === "feed" && (
        <section style={{ padding: "20px 0 0" }}>
          <VerdictGrid />
        </section>
      )}

      {tab === "sigak" && <SoonCard emoji="🛠️" text="개발중! 조금만 기다려요 ㅎㅎ" sub="coming soon" />}

      {tab === "change" && <SoonCard emoji="🌱" text="coming soon.." />}

      {/* MENU — 01 피드 분석하기 / 02 추구미 살펴보기 (03~05 본인 카피 후 추가) */}
      <section style={{ padding: "44px 24px 0" }}>
        <div
          style={{
            paddingBottom: 16,
            borderBottom: "1px solid var(--color-line)",
            marginBottom: 4,
          }}
        >
          <div
            className="font-serif"
            style={{
              fontSize: 20,
              fontWeight: 500,
              letterSpacing: "-0.018em",
              color: "var(--color-ink)",
            }}
          >
            menu
          </div>
        </div>

        <MenuStep
          num="01"
          title="피드 분석하기"
          sub={"SIA와 대화하며 내 피드를 분석하고\n추구미를 알려드려요"}
          badge="FREE"
          badgeMuted
          href="/sia"
        />
        <MenuStep
          num="02"
          title="추구미 살펴보기"
          sub={"추구미에 부합하는 인스타 계정 및 핀터레스트를\n알려주시면 유사도와 개선점을 알려드려요"}
          badge="🪙 20"
          href="/aspiration"
        />
      </section>

      {/* 토큰 잔액 + 충전 */}
      <section
        style={{
          padding: "32px 24px 0",
          marginTop: 32,
          borderTop: "1px solid var(--color-line)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 10,
                letterSpacing: "0.14em",
                textTransform: "uppercase",
                color: "var(--color-mute)",
                marginBottom: 6,
              }}
            >
              TOKEN BALANCE
            </div>
            <div
              className="font-serif tabular-nums"
              style={{
                fontSize: 32,
                fontWeight: 500,
                color: "var(--color-ink)",
                lineHeight: 1,
                letterSpacing: "-0.02em",
              }}
            >
              {balance == null ? "—" : balance.toLocaleString()}
              <span
                style={{
                  fontFamily: "var(--font-sans)",
                  fontSize: 13,
                  color: "var(--color-mute)",
                  marginLeft: 6,
                }}
              >
                토큰
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={() => router.push("/tokens/purchase")}
            className="font-sans"
            style={{
              padding: "12px 22px",
              background: "var(--color-ink)",
              color: "var(--color-paper)",
              border: "none",
              borderRadius: 100,
              fontSize: 14,
              fontWeight: 600,
              letterSpacing: "-0.01em",
              cursor: "pointer",
            }}
          >
            충전하기
          </button>
        </div>
      </section>

      {/* 계정 — 약관 / 로그아웃 / 계정 탈퇴 (Task #5 설정 페이지 분리 전 임시 위치) */}
      <section
        style={{
          padding: "44px 24px 24px",
          marginTop: 32,
          borderTop: "1px solid var(--color-line)",
        }}
      >
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 10,
            letterSpacing: "0.14em",
            textTransform: "uppercase",
            color: "var(--color-mute)",
            marginBottom: 14,
          }}
        >
          ACCOUNT
        </div>
        <AccountLink href="/profile/edit" label="내 정보 수정" />
        <AccountLink href="/terms#tos" label="이용약관" />
        <AccountLink href="/terms#privacy" label="개인정보처리방침" />
        <AccountLink href="/terms#tos" label="환불 정책" />
        <AccountAction label="로그아웃" onClick={handleLogout} danger />
        <AccountAction
          label="계정 탈퇴"
          sublabel="운영팀에 이메일로 요청이 전송되며, 확인 후 7일 내 처리됩니다."
          onClick={handleDeleteAccount}
          danger
        />
      </section>

      <SiteFooter />
    </div>
  );
}

// ─────────────────────────────────────────────
//  MenuStep — 마케터 nextstep 스타일 (01 / 02 / ...)
// ─────────────────────────────────────────────

function MenuStep({
  num,
  title,
  sub,
  badge,
  badgeMuted,
  href,
}: {
  num: string;
  title: string;
  sub: string;
  badge: string;
  badgeMuted?: boolean;
  href: string;
}) {
  return (
    <Link
      href={href}
      style={{
        display: "grid",
        gridTemplateColumns: "44px 1fr auto",
        gap: 14,
        padding: "22px 0",
        borderBottom: "1px solid var(--color-line)",
        alignItems: "flex-start",
        textDecoration: "none",
        color: "var(--color-ink)",
      }}
    >
      <div
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 13,
          fontWeight: 500,
          color: "var(--color-danger)",
          letterSpacing: "0.06em",
          paddingTop: 2,
        }}
      >
        {num}
      </div>
      <div style={{ minWidth: 0 }}>
        <div
          className="font-serif"
          style={{
            fontSize: 15,
            fontWeight: 500,
            color: "var(--color-ink)",
            letterSpacing: "-0.013em",
            marginBottom: 5,
          }}
        >
          {title}
        </div>
        <div
          className="font-sans"
          style={{
            fontSize: 12.5,
            color: "var(--color-mute)",
            lineHeight: 1.55,
            letterSpacing: "-0.005em",
            wordBreak: "keep-all",
            whiteSpace: "pre-line",
          }}
        >
          {sub}
        </div>
      </div>
      <span
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 10.5,
          letterSpacing: "0.1em",
          color: badgeMuted ? "var(--color-mute)" : "var(--color-danger)",
          background: badgeMuted ? "rgba(0, 0, 0, 0.05)" : "rgba(181, 75, 43, 0.08)",
          padding: "5px 10px",
          borderRadius: 100,
          fontWeight: 500,
          textTransform: "uppercase",
          whiteSpace: "nowrap",
          flexShrink: 0,
          marginTop: 2,
          alignSelf: "flex-start",
        }}
      >
        {badge}
      </span>
    </Link>
  );
}

// ─────────────────────────────────────────────
//  Soon placeholder — 시각 / 변화 탭
// ─────────────────────────────────────────────

function SoonCard({ emoji, text, sub }: { emoji: string; text: string; sub?: string }) {
  return (
    <section style={{ padding: "32px 24px 0" }}>
      <div
        style={{
          background: "rgba(0, 0, 0, 0.04)",
          borderRadius: 14,
          padding: "48px 28px",
          textAlign: "center",
        }}
      >
        <div style={{ fontSize: 36, marginBottom: 14 }}>{emoji}</div>
        <div
          className="font-sans"
          style={{
            fontSize: 16,
            color: "var(--color-ink)",
            opacity: 0.75,
            lineHeight: 1.65,
            letterSpacing: "-0.005em",
            marginBottom: sub ? 8 : 0,
          }}
        >
          {text}
        </div>
        {sub && (
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              letterSpacing: "0.18em",
              color: "var(--color-mute)",
              textTransform: "uppercase",
            }}
          >
            {sub}
          </div>
        )}
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────
//  Account list (계정 영역 — Task #5 설정 페이지 분리 전 임시)
// ─────────────────────────────────────────────

function AccountLink({ href, label }: { href: string; label: string }) {
  return (
    <Link
      href={href}
      className="font-sans"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "14px 0",
        borderTop: "1px solid var(--color-line)",
        fontSize: 14,
        color: "var(--color-ink)",
        letterSpacing: "-0.005em",
        textDecoration: "none",
      }}
    >
      <span>{label}</span>
      <span style={{ color: "var(--color-mute-2)", fontSize: 14 }}>›</span>
    </Link>
  );
}

function AccountAction({
  label,
  sublabel,
  onClick,
  danger,
}: {
  label: string;
  sublabel?: string;
  onClick: () => void;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="font-sans"
      style={{
        display: "flex",
        width: "100%",
        padding: "14px 0",
        background: "transparent",
        border: "none",
        borderTop: "1px solid var(--color-line)",
        textAlign: "left",
        cursor: "pointer",
        alignItems: sublabel ? "flex-start" : "center",
        gap: 8,
      }}
    >
      <span style={{ flex: 1, display: "flex", flexDirection: "column", gap: sublabel ? 4 : 0 }}>
        <span
          style={{
            fontSize: 14,
            color: danger ? "var(--color-danger)" : "var(--color-ink)",
            letterSpacing: "-0.005em",
          }}
        >
          {label}
        </span>
        {sublabel && (
          <span
            style={{
              fontSize: 11,
              lineHeight: 1.55,
              color: "var(--color-mute)",
              letterSpacing: "-0.005em",
            }}
          >
            {sublabel}
          </span>
        )}
      </span>
      <span style={{ color: "var(--color-mute-2)", fontSize: 14, marginLeft: 10 }}>›</span>
    </button>
  );
}
