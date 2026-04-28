// SIGAK MVP v2 BM — FeedShell
//
// /, /vision, /change 3개 경로가 공유하는 상단 레이아웃.
// FeedTopBar + 프로필 섹션 + 탭 바(URL 기반 active) + children(탭 컨텐츠).
//
// 탭 active는 usePathname 기반. 탭 클릭 → router.push(경로).
"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import { getCurrentUser } from "@/lib/auth";
import { useAvatar } from "@/hooks/use-avatar";
import { FeedTopBar } from "@/components/ui/sigak";

interface FeedShellProps {
  /** 상위 탭 컨텐츠 (VerdictGrid / VisionView / ChangeView) */
  children: React.ReactNode;
  /** 프로필 섹션의 "피드 N" 숫자. 피드 탭에서만 의미 있고, 다른 탭은 null 가능. */
  verdictCount?: number | null;
}

type TabKey = "feed" | "vision" | "change";

const TABS: { key: TabKey; label: string; href: string }[] = [
  { key: "feed", label: "피드", href: "/" },
  { key: "vision", label: "시각", href: "/vision" },
  { key: "change", label: "변화", href: "/change" },
];

interface ProfileState {
  name: string;
  kakaoId: string;
}

function resolveActiveTab(pathname: string): TabKey {
  if (pathname.startsWith("/vision")) return "vision";
  if (pathname.startsWith("/change")) return "change";
  return "feed";
}

export function FeedShell({ children, verdictCount = null }: FeedShellProps) {
  const router = useRouter();
  const pathname = usePathname();
  const active = resolveActiveTab(pathname);
  const { feedAvatarUrl, kakaoAvatarUrl } = useAvatar();

  const [profile, setProfile] = useState<ProfileState>({
    name: "",
    kakaoId: "",
  });

  useEffect(() => {
    const u = getCurrentUser();
    if (u) {
      setProfile({
        name: u.name || "익명",
        kakaoId: u.kakaoId || "",
      });
    }
  }, []);

  return (
    <>
      <FeedTopBar />
      <ProfileSection
        name={profile.name}
        kakaoId={profile.kakaoId}
        feedAvatarUrl={feedAvatarUrl}
        kakaoAvatarUrl={kakaoAvatarUrl}
        verdictCount={verdictCount}
      />
      <TabBar
        active={active}
        onChange={(key) => {
          const next = TABS.find((t) => t.key === key);
          if (next) router.push(next.href);
        }}
      />
      {children}
    </>
  );
}

// ─────────────────────────────────────────────
//  ProfileSection (기존 feed-view에서 이식)
// ─────────────────────────────────────────────

interface ProfileSectionProps {
  name: string;
  kakaoId: string;
  feedAvatarUrl: string | null;
  kakaoAvatarUrl: string;
  verdictCount: number | null;
}

function ProfileSection({
  name,
  kakaoId,
  feedAvatarUrl,
  kakaoAvatarUrl,
  verdictCount,
}: ProfileSectionProps) {
  const avatarSrc = feedAvatarUrl || kakaoAvatarUrl;
  return (
    <section
      style={{
        padding: "24px 24px 20px",
        display: "flex",
        alignItems: "center",
        gap: 18,
      }}
    >
      <div
        style={{
          width: 72,
          height: 72,
          borderRadius: "50%",
          overflow: "hidden",
          background: "rgba(0, 0, 0, 0.06)",
          flexShrink: 0,
        }}
      >
        {avatarSrc && (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={avatarSrc}
            alt="profile"
            onError={(e) => {
              if (
                feedAvatarUrl &&
                kakaoAvatarUrl &&
                e.currentTarget.src !== kakaoAvatarUrl
              ) {
                e.currentTarget.src = kakaoAvatarUrl;
              }
            }}
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
            fontSize: 18,
            fontWeight: 400,
            letterSpacing: "-0.01em",
            color: "var(--color-ink)",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {name || "익명"}
        </div>
        {kakaoId && (
          <div
            className="font-sans"
            style={{
              marginTop: 2,
              fontSize: 12,
              opacity: 0.5,
              letterSpacing: "-0.005em",
              color: "var(--color-ink)",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            @{kakaoId}
          </div>
        )}
      </div>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          minWidth: 48,
        }}
      >
        <span
          className="font-serif tabular-nums"
          style={{
            fontSize: 20,
            fontWeight: 400,
            color: "var(--color-ink)",
            lineHeight: 1,
          }}
        >
          {verdictCount == null ? "—" : verdictCount.toLocaleString()}
        </span>
        <span
          className="font-sans uppercase"
          style={{
            marginTop: 4,
            fontSize: 10,
            fontWeight: 600,
            letterSpacing: "1.5px",
            opacity: 0.5,
            color: "var(--color-ink)",
          }}
        >
          피드
        </span>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────
//  TabBar
// ─────────────────────────────────────────────

interface TabBarProps {
  active: TabKey;
  onChange: (tab: TabKey) => void;
}

function TabBar({ active, onChange }: TabBarProps) {
  return (
    <nav
      style={{
        display: "grid",
        gridTemplateColumns: `repeat(${TABS.length}, 1fr)`,
        borderTop: "1px solid rgba(0, 0, 0, 0.1)",
        borderBottom: "1px solid rgba(0, 0, 0, 0.1)",
      }}
    >
      {TABS.map((t) => {
        const isActive = t.key === active;
        return (
          <button
            key={t.key}
            type="button"
            onClick={() => onChange(t.key)}
            className="font-sans"
            style={{
              padding: "14px 0 12px",
              background: "transparent",
              border: "none",
              borderBottom: isActive
                ? "2px solid var(--color-ink)"
                : "2px solid transparent",
              color: "var(--color-ink)",
              fontSize: 12,
              fontWeight: 600,
              letterSpacing: "1.5px",
              cursor: "pointer",
              opacity: isActive ? 1 : 0.4,
              transition: "opacity 120ms ease, border-color 120ms ease",
              marginBottom: -1,
            }}
          >
            {t.label}
          </button>
        );
      })}
    </nav>
  );
}
