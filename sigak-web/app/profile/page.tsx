// SIGAK MVP v1.2 (D-6) — /profile
//
// 카카오 프로필 + 토큰 잔액 + 충전 링크 + 설정 리스트 + 로그아웃.
// FeedTopBar 사용(홈/프로필 공용).
"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { getCurrentUser, getToken, logout } from "@/lib/auth";
import { useOnboardingGuard } from "@/hooks/use-onboarding-guard";
import { useTokenBalance } from "@/hooks/use-token-balance";
import { FeedTopBar } from "@/components/ui/sigak";
import { SiteFooter } from "@/components/sigak/site-footer";

export default function ProfilePage() {
  const router = useRouter();
  const { status } = useOnboardingGuard();
  const { balance } = useTokenBalance();

  const [profile, setProfile] = useState<{
    name: string;
    email: string;
    profileImage: string;
    kakaoId: string;
  } | null>(null);

  const [error] = useState<string | null>(null);

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
    logout(); // lib/auth.ts — 토큰 clear 후 "/" 로 이동
  }

  function handleDeleteAccount() {
    // 백엔드 self-serve 탈퇴 endpoint 구축 전까지는 운영팀 이메일로 요청 처리.
    // 개인정보보호법상 삭제 경로 제공 의무 충족 용도.
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
      "요청 일시: " + new Date().toISOString() + "\n\n" +
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

      {/* 프로필 정보 */}
      <section style={{ padding: "36px 28px 28px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: "50%",
              overflow: "hidden",
              background: "rgba(0, 0, 0, 0.06)",
              flexShrink: 0,
            }}
          >
            {profile?.profileImage && (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img
                src={profile.profileImage}
                alt="profile"
                style={{
                  width: "100%",
                  height: "100%",
                  objectFit: "cover",
                  display: "block",
                }}
              />
            )}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              className="font-serif"
              style={{
                fontSize: 20,
                fontWeight: 400,
                letterSpacing: "-0.01em",
                color: "var(--color-ink)",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {profile?.name || "익명"}
            </div>
            {profile?.email && (
              <div
                className="font-sans"
                style={{
                  marginTop: 4,
                  fontSize: 12,
                  opacity: 0.5,
                  letterSpacing: "-0.005em",
                  color: "var(--color-ink)",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {profile.email}
              </div>
            )}
          </div>
        </div>
      </section>

      <Rule />

      {/* 토큰 잔액 */}
      <section style={{ padding: "20px 28px" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <Label>토큰 잔액</Label>
            <div
              className="font-serif tabular-nums"
              style={{
                marginTop: 6,
                fontSize: 28,
                fontWeight: 400,
                color: "var(--color-ink)",
                lineHeight: 1,
              }}
            >
              {balance == null ? "—" : balance.toLocaleString()}
              <span
                className="font-sans"
                style={{ fontSize: 13, opacity: 0.5, marginLeft: 6 }}
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
              padding: "10px 18px",
              background: "var(--color-ink)",
              color: "var(--color-paper)",
              border: "none",
              fontSize: 13,
              fontWeight: 600,
              letterSpacing: "0.5px",
              cursor: "pointer",
              borderRadius: 0,
            }}
          >
            충전하기
          </button>
        </div>
      </section>

      <Rule />

      {/* 설정 리스트 */}
      <section style={{ padding: "8px 0 0" }}>
        <SettingLink
          label="내 정보 수정"
          sublabel="등록한 인스타그램이 바뀌었거나, 분석 결과가 본인 결과 어긋날 때 여기서 다시 맞춰주세요."
          href="/profile/edit"
        />
        <SettingLink label="이용약관" href="/terms#tos" />
        <SettingLink label="개인정보처리방침" href="/terms#privacy" />
        <SettingLink label="환불 정책" href="/terms#tos" />
        <SettingRow label="로그아웃" onClick={handleLogout} danger />
        <SettingRow
          label="계정 탈퇴"
          sublabel="운영팀에 이메일로 요청이 전송되며, 확인 후 7일 내 처리됩니다."
          onClick={handleDeleteAccount}
          danger
        />
      </section>

      {error && (
        <p
          className="font-sans"
          role="alert"
          style={{
            padding: "0 28px 20px",
            fontSize: 12,
            color: "var(--color-danger)",
            letterSpacing: "-0.005em",
          }}
        >
          {error}
        </p>
      )}

      <div style={{ height: 20 }} />

      {/* 사업자 정보 (PG 심사 필수) */}
      <SiteFooter />
    </div>
  );
}

// ─────────────────────────────────────────────
//  Primitives
// ─────────────────────────────────────────────

function Rule() {
  return (
    <div
      style={{
        height: 1,
        background: "var(--color-ink)",
        margin: "0 28px",
        opacity: 0.1,
      }}
    />
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <span
      className="font-sans uppercase"
      style={{
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: "1.5px",
        opacity: 0.4,
        color: "var(--color-ink)",
      }}
    >
      {children}
    </span>
  );
}

function SettingRow({
  label,
  sublabel,
  onClick,
  busy = false,
  danger = false,
}: {
  label: string;
  sublabel?: string;
  onClick: () => void;
  busy?: boolean;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={busy}
      className="font-sans"
      style={{
        display: "flex",
        width: "100%",
        padding: "16px 28px",
        background: "transparent",
        border: "none",
        borderTop: "1px solid rgba(0, 0, 0, 0.1)",
        letterSpacing: "-0.005em",
        textAlign: "left",
        cursor: busy ? "default" : "pointer",
        opacity: busy ? 0.5 : 1,
        alignItems: sublabel ? "flex-start" : "center",
      }}
    >
      <span
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          gap: sublabel ? 4 : 0,
        }}
      >
        <span
          style={{
            fontSize: 14,
            color: danger ? "var(--color-danger)" : "var(--color-ink)",
          }}
        >
          {busy ? "처리 중..." : label}
        </span>
        {sublabel && !busy && (
          <span
            className="font-sans"
            style={{
              fontSize: 11,
              lineHeight: 1.55,
              opacity: 0.5,
              color: "var(--color-ink)",
              letterSpacing: "-0.005em",
            }}
          >
            {sublabel}
          </span>
        )}
      </span>
      <span style={{ opacity: 0.3, fontSize: 14, marginLeft: 10 }}>›</span>
    </button>
  );
}

function SettingLink({
  label,
  href,
  sublabel,
}: {
  label: string;
  href: string;
  sublabel?: string;
}) {
  return (
    <Link
      href={href}
      className="font-sans"
      style={{
        display: "flex",
        padding: "16px 28px",
        borderTop: "1px solid rgba(0, 0, 0, 0.1)",
        fontSize: 14,
        letterSpacing: "-0.005em",
        color: "var(--color-ink)",
        textDecoration: "none",
        alignItems: sublabel ? "flex-start" : "center",
      }}
    >
      <span
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          gap: sublabel ? 4 : 0,
        }}
      >
        <span style={{ fontSize: 14, color: "var(--color-ink)" }}>{label}</span>
        {sublabel && (
          <span
            className="font-sans"
            style={{
              fontSize: 11,
              lineHeight: 1.55,
              opacity: 0.5,
              color: "var(--color-ink)",
              letterSpacing: "-0.005em",
            }}
          >
            {sublabel}
          </span>
        )}
      </span>
      <span style={{ opacity: 0.3, fontSize: 14, marginLeft: 10 }}>›</span>
    </Link>
  );
}
