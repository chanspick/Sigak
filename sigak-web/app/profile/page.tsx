// SIGAK MVP v1.2 — /profile (= 마케터 설정 디자인)
//
// IA (2026-04-26 정합):
//   - / (홈) = 마케터 프로필 디자인 (3탭 + menu)
//   - /profile = 이 페이지 = 마케터 설정 디자인 (계정 / 약관 / 로그아웃)
//
// 차용: redesign/설정_1815.html
//   topnav (← 뒤로 + sigak + 토큰 pill) → me (아바타+이름+이메일)
//   → token-section (토큰 잔액 32px + 충전하기 pill)
//   → settings-group: 인스타그램 핸들
//   → settings-group: 이용약관 / 개인정보처리방침 / 환불 정책
//   → settings-group: 로그아웃 / 계정 탈퇴 (danger)
"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { getCurrentUser, getToken, logout } from "@/lib/auth";
import { useTokenBalance } from "@/hooks/use-token-balance";
import { TopBar } from "@/components/ui/sigak";
import { SiteFooter } from "@/components/sigak/site-footer";

export default function SettingsPage() {
  const router = useRouter();
  const { balance } = useTokenBalance();

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

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--color-paper)",
        color: "var(--color-ink)",
        fontFamily: "var(--font-sans)",
      }}
    >
      {/* TOP NAV — TopBar 컴포넌트 사용 (홈 정합) */}
      <TopBar backTarget="/" />

      {/* PROFILE 영역 — 56x56 아바타 (gradient fallback) + 이름 + 이메일 */}
      <section
        style={{
          maxWidth: 480,
          margin: "0 auto",
          padding: "32px 24px 28px",
          display: "flex",
          alignItems: "center",
          gap: 18,
          borderBottom: "1px solid var(--color-line)",
        }}
      >
        <div
          style={{
            width: 56,
            height: 56,
            borderRadius: "50%",
            flexShrink: 0,
            background: profile?.profileImage
              ? "transparent"
              : "linear-gradient(135deg, #e8d9c8, #b8a58a)",
            overflow: "hidden",
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
        <div style={{ minWidth: 0, flex: 1 }}>
          <div
            className="font-serif"
            style={{
              fontSize: 18,
              fontWeight: 500,
              color: "var(--color-ink)",
              letterSpacing: "-0.015em",
              marginBottom: 4,
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
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {profile.email}
            </div>
          )}
        </div>
      </section>

      {/* TOKEN BALANCE — Noto Serif 32px + 충전하기 pill */}
      <section
        style={{
          maxWidth: 480,
          margin: "0 auto",
          padding: "24px 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: "1px solid var(--color-line)",
        }}
      >
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
              display: "flex",
              alignItems: "baseline",
              gap: 6,
            }}
          >
            <span>{balance == null ? "—" : balance.toLocaleString()}</span>
            <span
              style={{
                fontFamily: "var(--font-sans)",
                fontSize: 13,
                color: "var(--color-mute)",
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
            flexShrink: 0,
          }}
        >
          충전하기
        </button>
      </section>

      {/* SETTINGS — 그룹 1: 계정 정보 변경 */}
      <SettingsGroup>
        <SettingsLink
          title="인스타그램 핸들"
          sub="등록된 인스타그램을 변경할 수 있어요."
          href="/profile/edit"
        />
      </SettingsGroup>

      {/* SETTINGS — 그룹 2: 약관/정책 */}
      <SettingsGroup>
        <SettingsLink title="이용약관" href="/terms#tos" />
        <SettingsLink title="개인정보처리방침" href="/terms#privacy" />
        <SettingsLink title="환불 정책" href="/terms#tos" />
      </SettingsGroup>

      {/* SETTINGS — 그룹 3: 위험 액션 */}
      <SettingsGroup>
        <SettingsAction title="로그아웃" onClick={handleLogout} danger />
        <SettingsAction
          title="계정 탈퇴"
          sub="운영팀에 이메일로 요청이 전송되며, 확인 후 7일 내 처리됩니다."
          onClick={handleDeleteAccount}
          danger
        />
      </SettingsGroup>

      <div style={{ height: 40 }} />
      <SiteFooter />
    </div>
  );
}

// ─────────────────────────────────────────────
//  SettingsGroup — 마케터 settings-group (border-bottom 1px)
// ─────────────────────────────────────────────

function SettingsGroup({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        maxWidth: 480,
        margin: "0 auto",
        borderBottom: "1px solid var(--color-line)",
        padding: "8px 0",
      }}
    >
      {children}
    </div>
  );
}

// ─────────────────────────────────────────────
//  SettingsLink — 마케터 settings-item (Link 진입)
// ─────────────────────────────────────────────

function SettingsLink({
  title,
  sub,
  href,
}: {
  title: string;
  sub?: string;
  href: string;
}) {
  return (
    <Link
      href={href}
      style={{
        display: "flex",
        alignItems: sub ? "flex-start" : "center",
        padding: "18px 24px",
        gap: 14,
        textDecoration: "none",
        color: "var(--color-ink)",
        cursor: "pointer",
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          className="font-sans"
          style={{
            fontSize: 15,
            fontWeight: 500,
            color: "var(--color-ink)",
            letterSpacing: "-0.01em",
            marginBottom: sub ? 4 : 0,
          }}
        >
          {title}
        </div>
        {sub && (
          <div
            style={{
              fontSize: 12.5,
              color: "var(--color-mute)",
              lineHeight: 1.55,
              letterSpacing: "-0.003em",
              wordBreak: "keep-all",
            }}
          >
            {sub}
          </div>
        )}
      </div>
      <span style={{ color: "var(--color-mute-2)", fontSize: 13, flexShrink: 0 }}>›</span>
    </Link>
  );
}

// ─────────────────────────────────────────────
//  SettingsAction — danger 색 (로그아웃/계정 탈퇴)
// ─────────────────────────────────────────────

function SettingsAction({
  title,
  sub,
  onClick,
  danger,
}: {
  title: string;
  sub?: string;
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
        padding: "18px 24px",
        gap: 14,
        background: "transparent",
        border: "none",
        textAlign: "left",
        cursor: "pointer",
        alignItems: sub ? "flex-start" : "center",
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontSize: 15,
            fontWeight: 500,
            color: danger ? "var(--color-danger)" : "var(--color-ink)",
            letterSpacing: "-0.01em",
            marginBottom: sub ? 4 : 0,
          }}
        >
          {title}
        </div>
        {sub && (
          <div
            style={{
              fontSize: 12.5,
              color: "var(--color-mute)",
              lineHeight: 1.55,
              letterSpacing: "-0.003em",
              wordBreak: "keep-all",
            }}
          >
            {sub}
          </div>
        )}
      </div>
      <span
        style={{
          color: danger ? "rgba(163, 45, 45, 0.4)" : "var(--color-mute-2)",
          fontSize: 13,
          flexShrink: 0,
        }}
      >
        ›
      </span>
    </button>
  );
}
