"use client";

// 마이페이지: 리포트 + 캐스팅 내역 2컬럼

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getMyReports, getCastingStatus, castingOptOut } from "@/lib/api/client";
import { logout } from "@/lib/auth";
import { NotificationBell } from "@/components/notification/notification-bell";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

interface MyReport {
  id: string;
  access_level: string;
  created_at: string;
  url: string;
}

interface CastingMatch {
  id: string;
  agency_name: string;
  purpose: string;
  fee: string;
  response: "pending" | "accept" | "decline";
  requested_at: string;
  responded_at: string | null;
}

const LEVEL_LABELS: Record<string, string> = {
  free: "무료",
  standard: "스탠다드",
  standard_pending: "스탠다드 (대기)",
  full_pending: "풀 (대기)",
  full: "풀 리포트",
};

const RESPONSE_LABELS: Record<string, { text: string; color: string }> = {
  pending: { text: "대기 중", color: "text-[var(--color-muted)]" },
  accept: { text: "수락", color: "text-green-700" },
  decline: { text: "반려", color: "text-[var(--color-danger)]" },
};

interface CastingStatus {
  opted_in: boolean;
  opted_at: string | null;
}

export default function MyPage() {
  const router = useRouter();
  const [reports, setReports] = useState<MyReport[]>([]);
  const [castingMatches, setCastingMatches] = useState<CastingMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [userName, setUserName] = useState("");
  const [castingStatus, setCastingStatus] = useState<CastingStatus | null>(null);
  const [optingOut, setOptingOut] = useState(false);

  useEffect(() => {
    const userId = localStorage.getItem("sigak_user_id");
    const name = localStorage.getItem("sigak_user_name");
    if (name) setUserName(name);

    if (!userId) {
      router.replace("/sia");
      return;
    }

    (async () => {
      try {
        const [reportsData, castingData, notifsRes] = await Promise.all([
          getMyReports(userId),
          getCastingStatus(userId).catch(() => null),
          fetch(`${API_URL}/api/v1/notifications?user_id=${userId}`).then(r => r.ok ? r.json() : { notifications: [] }),
        ]);
        setReports(reportsData.reports);
        if (castingData) setCastingStatus(castingData);

        // 알림에서 casting_match 타입만 추출
        const matches: CastingMatch[] = [];
        for (const n of notifsRes.notifications || []) {
          if (n.type !== "casting_match") continue;
          try {
            const data = typeof n.message === "string" ? JSON.parse(n.message) : n.message;
            matches.push({
              id: n.id,
              agency_name: data.agency_name || "",
              purpose: data.purpose || "",
              fee: data.fee || "",
              response: data.response || "pending",
              requested_at: data.requested_at || n.created_at,
              responded_at: data.responded_at || null,
            });
          } catch { /* JSON 파싱 실패 무시 */ }
        }
        setCastingMatches(matches);
      } catch (e) {
        console.error("[my]", e);
      } finally {
        setLoading(false);
      }
    })();
  }, [router]);

  const handleOptOut = async () => {
    const userId = localStorage.getItem("sigak_user_id");
    if (!userId || optingOut) return;
    setOptingOut(true);
    try {
      await castingOptOut(userId);
      setCastingStatus({ opted_in: false, opted_at: null });
    } catch (e) {
      console.error("[casting opt-out]", e);
    } finally {
      setOptingOut(false);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--color-bg)] text-[var(--color-fg)]">
      {/* ── 다크 헤더 ── */}
      <nav className="sticky top-0 z-[100] flex items-center justify-between px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] h-[60px] bg-[var(--color-fg)] text-[var(--color-bg)]">
        <Link href="/" className="text-xs font-bold tracking-[5px] no-underline text-[var(--color-bg)]">SIGAK</Link>
        <div className="flex items-center gap-4">
          <button
            onClick={logout}
            className="text-[10px] tracking-[1px] opacity-40 hover:opacity-80 transition-opacity cursor-pointer"
          >
            로그아웃
          </button>
          <span className="text-[10px] font-medium tracking-[2px]">내 리포트</span>
          <NotificationBell />
        </div>
      </nav>

      {/* ── 히어로 ── */}
      <section className="bg-[var(--color-fg)] text-[var(--color-bg)] px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] pt-10 pb-12">
        <div className="max-w-4xl">
          <p className="text-[10px] font-medium tracking-[4px] uppercase opacity-40 mb-4">MY PAGE</p>
          <h1 className="font-[family-name:var(--font-serif)] text-[clamp(24px,4vw,36px)] font-normal leading-[1.3]">
            {userName ? `${userName}님,` : "안녕하세요,"}
            <br />
            <span className="opacity-50">분석 완료된 리포트입니다.</span>
          </h1>
        </div>
      </section>

      {/* ── 콘텐츠: 2컬럼 ── */}
      <div className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-10">
        <div className="max-w-4xl">

          {loading && (
            <div className="flex items-center justify-center py-20">
              <div className="w-5 h-5 border-2 border-[var(--color-fg)] border-t-transparent animate-spin" />
            </div>
          )}

          {!loading && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
              {/* ── 좌: 리포트 ── */}
              <div>
                <p className="text-[10px] font-medium tracking-[3px] uppercase text-[var(--color-muted)] mb-5">REPORTS</p>

                {reports.length === 0 ? (
                  <div className="py-12 text-center border border-dashed border-[var(--color-border)]">
                    <p className="text-[13px] text-[var(--color-muted)] mb-4">아직 리포트가 없습니다.</p>
                    <Link
                      href="/sia"
                      className="inline-block px-6 py-2.5 bg-[var(--color-fg)] text-[var(--color-bg)] text-[11px] font-medium tracking-[1px] no-underline hover:opacity-80 transition-opacity"
                    >
                      진단 시작하기
                    </Link>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {reports.map((report) => (
                      <Link
                        key={report.id}
                        href={report.url}
                        className="flex items-center justify-between px-5 py-4 border border-[var(--color-border)] hover:border-[var(--color-fg)] transition-colors no-underline text-[var(--color-fg)] group"
                      >
                        <div>
                          <p className="text-[13px] font-semibold">
                            {LEVEL_LABELS[report.access_level] || report.access_level}
                          </p>
                          <p className="text-[11px] text-[var(--color-muted)] mt-1">
                            {report.created_at
                              ? new Date(report.created_at).toLocaleDateString("ko-KR", {
                                  year: "numeric",
                                  month: "long",
                                  day: "numeric",
                                })
                              : ""}
                          </p>
                        </div>
                        <span className="text-[11px] text-[var(--color-muted)] group-hover:text-[var(--color-fg)] transition-colors">
                          보기 →
                        </span>
                      </Link>
                    ))}

                    <Link
                      href="/sia"
                      className="block text-center py-3 text-[11px] text-[var(--color-muted)] hover:text-[var(--color-fg)] transition-colors"
                    >
                      + 새 진단 시작하기
                    </Link>
                  </div>
                )}

                {/* 캐스팅 풀 상태 */}
                {castingStatus?.opted_in && (
                  <div className="mt-8">
                    <p className="text-[10px] font-medium tracking-[3px] uppercase text-[var(--color-muted)] mb-4">CASTING POOL</p>
                    <div className="flex items-center justify-between px-5 py-4 border border-[var(--color-border)]">
                      <div>
                        <p className="text-[13px] font-semibold">등록됨</p>
                        <p className="text-[11px] text-[var(--color-muted)] mt-0.5">
                          {castingStatus.opted_at
                            ? new Date(castingStatus.opted_at).toLocaleDateString("ko-KR", {
                                year: "numeric",
                                month: "long",
                                day: "numeric",
                              })
                            : "매칭 파트너가 검색 가능"}
                        </p>
                      </div>
                      <button
                        onClick={handleOptOut}
                        disabled={optingOut}
                        className="text-[11px] text-[var(--color-danger)] hover:underline disabled:opacity-50 cursor-pointer"
                      >
                        {optingOut ? "해제 중..." : "해제"}
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* ── 우: 캐스팅 내역 ── */}
              <div>
                <p className="text-[10px] font-medium tracking-[3px] uppercase text-[var(--color-muted)] mb-5">CASTING INVITATIONS</p>

                {castingMatches.length === 0 ? (
                  <div className="py-12 text-center border border-dashed border-[var(--color-border)]">
                    <p className="text-[13px] text-[var(--color-muted)]">캐스팅 제안이 없습니다.</p>
                    <p className="text-[11px] text-[var(--color-muted)] mt-1 opacity-60">캐스팅 풀에 등록하면 제안을 받을 수 있어요.</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {castingMatches.map((match) => {
                      const status = RESPONSE_LABELS[match.response] || RESPONSE_LABELS.pending;
                      return (
                        <Link
                          key={match.id}
                          href={`/casting/invitation?id=${match.id}`}
                          className="block px-5 py-4 border border-[var(--color-border)] hover:border-[var(--color-fg)] transition-colors no-underline text-[var(--color-fg)]"
                        >
                          <div className="flex items-start justify-between mb-2">
                            <p className="text-[13px] font-semibold">{match.agency_name}</p>
                            <span className={`text-[10px] font-bold tracking-[1px] uppercase ${status.color}`}>
                              {status.text}
                            </span>
                          </div>
                          {match.purpose && (
                            <p className="text-[11px] text-[var(--color-muted)]">{match.purpose}</p>
                          )}
                          {match.fee && (
                            <p className="text-[11px] mt-1">
                              <span className="text-[var(--color-muted)]">출연료</span>{" "}
                              <span className="font-medium">{match.fee}</span>
                            </p>
                          )}
                          <p className="text-[10px] text-[var(--color-muted)] mt-2 opacity-60">
                            {match.requested_at
                              ? new Date(match.requested_at).toLocaleDateString("ko-KR", {
                                  year: "numeric",
                                  month: "long",
                                  day: "numeric",
                                })
                              : ""}
                          </p>

                          {/* 대기 중이면 안내 */}
                          {match.response === "pending" && (
                            <p className="text-[10px] text-[var(--color-muted)] mt-2">탭하여 상세 보기 →</p>
                          )}
                        </Link>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
