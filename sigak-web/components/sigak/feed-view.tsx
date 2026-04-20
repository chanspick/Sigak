// SIGAK MVP v1.2 (D-6 revised) — FeedView
//
// 피드 상단 프로필 섹션 + 탭(피드/진단/추구미/변화) + 탭별 content.
// 피드 탭만 활성, 나머지는 "준비중" placeholder.
"use client";

import { useEffect, useState } from "react";

import { getCurrentUser } from "@/lib/auth";
import { VerdictGrid } from "./verdict-grid";

type TabKey = "feed" | "dx" | "aim" | "change";

const TABS: { key: TabKey; label: string }[] = [
  { key: "feed", label: "피드" },
  { key: "dx", label: "진단" },
  { key: "aim", label: "추구미" },
  { key: "change", label: "변화" },
];

interface ProfileState {
  name: string;
  email: string;
  profileImage: string;
}

export function FeedView() {
  const [total, setTotal] = useState<number | null>(null);
  const [tab, setTab] = useState<TabKey>("feed");
  const [profile, setProfile] = useState<ProfileState>({
    name: "",
    email: "",
    profileImage: "",
  });

  useEffect(() => {
    const u = getCurrentUser();
    if (u) {
      setProfile({
        name: u.name || "익명",
        email: u.email || "",
        profileImage: u.profileImage || "",
      });
    }
  }, []);

  return (
    <>
      <ProfileSection
        name={profile.name}
        email={profile.email}
        profileImage={profile.profileImage}
        verdictCount={total}
      />
      <TabBar active={tab} onChange={setTab} />

      {tab === "feed" && <VerdictGrid onTotalChange={setTotal} />}
      {tab !== "feed" && <TabPlaceholder label={labelFor(tab)} />}
    </>
  );
}

function labelFor(tab: TabKey): string {
  return TABS.find((t) => t.key === tab)?.label ?? "";
}

// ─────────────────────────────────────────────
//  ProfileSection
// ─────────────────────────────────────────────

interface ProfileSectionProps {
  name: string;
  email: string;
  profileImage: string;
  verdictCount: number | null;
}

function ProfileSection({
  name,
  email,
  profileImage,
  verdictCount,
}: ProfileSectionProps) {
  return (
    <section
      style={{
        padding: "24px 24px 20px",
        display: "flex",
        alignItems: "center",
        gap: 18,
      }}
    >
      {/* Avatar */}
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
        {profileImage && (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={profileImage}
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

      {/* Info */}
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
        {email && (
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
            {email}
          </div>
        )}
      </div>

      {/* Verdict count — Instagram stat style */}
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
              marginBottom: -1, // 하단 border와 겹치게
            }}
          >
            {t.label}
          </button>
        );
      })}
    </nav>
  );
}

// ─────────────────────────────────────────────
//  TabPlaceholder — 비활성 탭
// ─────────────────────────────────────────────

function TabPlaceholder({ label }: { label: string }) {
  return (
    <div
      style={{
        minHeight: "40vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "0 28px",
        gap: 6,
      }}
    >
      <span
        className="font-serif"
        style={{
          fontSize: 20,
          fontWeight: 400,
          letterSpacing: "-0.01em",
          color: "var(--color-ink)",
          opacity: 0.55,
        }}
      >
        {label}
      </span>
      <span
        className="font-sans"
        style={{
          fontSize: 12,
          opacity: 0.35,
          letterSpacing: "-0.005em",
          color: "var(--color-ink)",
        }}
      >
        준비 중입니다.
      </span>
    </div>
  );
}
