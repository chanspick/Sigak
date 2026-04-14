"use client";

// 마이페이지: 다크 헤더 + 리포트 목록 + 캐스팅 상태 + 로그아웃

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getMyReports, getCastingStatus, castingOptOut } from "@/lib/api/client";
import { logout } from "@/lib/auth";
import { NotificationBell } from "@/components/notification/notification-bell";

interface MyReport {
  id: string;
  access_level: string;
  created_at: string;
  url: string;
}

const LEVEL_LABELS: Record<string, string> = {
  free: "무료",
  standard: "스탠다드",
  standard_pending: "스탠다드 (대기)",
  full_pending: "풀 (대기)",
  full: "풀 리포트",
};

interface CastingStatus {
  opted_in: boolean;
  opted_at: string | null;
}

export default function MyPage() {
  const router = useRouter();
  const [reports, setReports] = useState<MyReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [userName, setUserName] = useState("");
  const [castingStatus, setCastingStatus] = useState<CastingStatus | null>(null);
  const [optingOut, setOptingOut] = useState(false);

  useEffect(() => {
    const userId = localStorage.getItem("sigak_user_id");
    const name = localStorage.getItem("sigak_user_name");
    if (name) setUserName(name);

    if (!userId) {
      router.replace("/start");
      return;
    }

    (async () => {
      try {
        const [reportsData, castingData] = await Promise.all([
          getMyReports(userId),
          getCastingStatus(userId).catch(() => null),
        ]);
        setReports(reportsData.reports);
        if (castingData) setCastingStatus(castingData);
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
          <span className="text-[10px] font-medium tracking-[2px] opacity-100">내 리포트</span>
          <NotificationBell />
        </div>
      </nav>

      {/* ── 히어로 영역 ── */}
      <section className="bg-[var(--color-fg)] text-[var(--color-bg)] px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] pt-10 pb-12">
        <div className="max-w-2xl">
          <p className="text-[10px] font-medium tracking-[4px] uppercase opacity-40 mb-4">MY REPORT</p>
          <h1 className="font-[family-name:var(--font-serif)] text-[clamp(24px,4vw,36px)] font-normal leading-[1.3]">
            {userName ? `${userName}님,` : "안녕하세요,"}
            <br />
            <span className="opacity-50">분석 완료된 리포트입니다.</span>
          </h1>
        </div>
      </section>

      {/* ── 콘텐츠 ── */}
      <div className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-10">
        <div className="max-w-2xl">

          {/* 로딩 */}
          {loading && (
            <div className="flex items-center justify-center py-20">
              <div className="w-5 h-5 border-2 border-[var(--color-fg)] border-t-transparent animate-spin" />
            </div>
          )}

          {/* 리포트 없음 */}
          {!loading && reports.length === 0 && (
            <div className="py-16 text-center">
              <p className="text-[13px] text-[var(--color-muted)] mb-6">아직 분석된 리포트가 없습니다.</p>
              <Link
                href="/start"
                className="inline-block px-8 py-3 bg-[var(--color-fg)] text-[var(--color-bg)] text-[12px] font-medium tracking-[1px] no-underline hover:opacity-80 transition-opacity"
              >
                진단 시작하기
              </Link>
            </div>
          )}

          {/* 리포트 목록 */}
          {!loading && reports.length > 0 && (
            <>
              <p className="text-[10px] font-medium tracking-[3px] uppercase text-[var(--color-muted)] mb-5">REPORTS</p>
              <div className="space-y-3 mb-12">
                {reports.map((report) => (
                  <Link
                    key={report.id}
                    href={report.url}
                    className="flex items-center justify-between px-6 py-5 border border-[var(--color-border)] hover:border-[var(--color-fg)] transition-colors no-underline text-[var(--color-fg)] group"
                  >
                    <div>
                      <p className="text-[14px] font-semibold">
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
              </div>
            </>
          )}

          {/* 캐스팅 풀 */}
          {!loading && castingStatus?.opted_in && (
            <>
              <p className="text-[10px] font-medium tracking-[3px] uppercase text-[var(--color-muted)] mb-5">CASTING POOL</p>
              <div className="flex items-center justify-between px-6 py-5 border border-[var(--color-border)] mb-12">
                <div>
                  <p className="text-[14px] font-semibold">캐스팅 풀 등록됨</p>
                  <p className="text-[11px] text-[var(--color-muted)] mt-1">
                    {castingStatus.opted_at
                      ? new Date(castingStatus.opted_at).toLocaleDateString("ko-KR", {
                          year: "numeric",
                          month: "long",
                          day: "numeric",
                        }) + " 등록"
                      : "매칭 파트너가 프로필을 검색할 수 있습니다"}
                  </p>
                </div>
                <button
                  onClick={handleOptOut}
                  disabled={optingOut}
                  className="text-[11px] text-[var(--color-danger)] hover:underline disabled:opacity-50 cursor-pointer"
                >
                  {optingOut ? "해제 중..." : "등록 해제"}
                </button>
              </div>
            </>
          )}

          {/* 새 진단 + 하단 메뉴 */}
          {!loading && (
            <div className="border-t border-[var(--color-border)] pt-8 flex items-center justify-between">
              <Link
                href="/start"
                className="text-[12px] font-medium hover:opacity-60 transition-opacity"
              >
                → 새 진단 시작하기
              </Link>
              <button
                onClick={logout}
                className="text-[11px] text-[var(--color-muted)] hover:text-[var(--color-fg)] transition-colors cursor-pointer"
              >
                로그아웃
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
