"use client";

// 마이페이지: 로그인한 유저의 리포트 목록

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

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
        const [reportsRes, castingRes] = await Promise.all([
          fetch(`${API_URL}/api/v1/my/reports?user_id=${userId}`),
          fetch(`${API_URL}/api/v1/casting/status?user_id=${userId}`),
        ]);
        if (reportsRes.ok) {
          const data = await reportsRes.json();
          setReports(data.reports);
        }
        if (castingRes.ok) {
          const data = await castingRes.json();
          setCastingStatus(data);
        }
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
      const res = await fetch(`${API_URL}/api/v1/casting/opt-out?user_id=${userId}`, {
        method: "POST",
      });
      if (res.ok) {
        setCastingStatus({ opted_in: false, opted_at: null });
      }
    } catch (e) {
      console.error("[casting opt-out]", e);
    } finally {
      setOptingOut(false);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--color-bg)] text-[var(--color-fg)]">
      <div className="max-w-lg mx-auto px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-12">
        <h1 className="text-xl font-semibold tracking-tight mb-1">
          {userName ? `${userName}님의 리포트` : "내 리포트"}
        </h1>
        <p className="text-sm text-[var(--color-muted)] mb-8">
          분석 완료된 리포트를 확인하세요.
        </p>

        {/* 캐스팅 풀 상태 */}
        {castingStatus?.opted_in && (
          <div className="flex items-center justify-between py-4 mb-8 border-b border-[var(--color-border)]">
            <div>
              <p className="text-sm font-semibold">캐스팅 풀</p>
              <p className="text-xs text-[var(--color-muted)]">
                {castingStatus.opted_at
                  ? new Date(castingStatus.opted_at).toLocaleDateString("ko-KR", {
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                    }) + " 등록"
                  : "등록됨"}
              </p>
            </div>
            <button
              onClick={handleOptOut}
              disabled={optingOut}
              className="text-xs text-[var(--color-danger)] hover:underline disabled:opacity-50"
            >
              {optingOut ? "해제 중..." : "등록 해제"}
            </button>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="w-6 h-6 border-2 border-[var(--color-fg)] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : reports.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-sm text-[var(--color-muted)] mb-4">
              아직 리포트가 없습니다.
            </p>
            <Link
              href="/start"
              className="text-sm font-medium underline"
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
                className="block border border-[var(--color-border)] px-5 py-4 hover:bg-black/[0.02] transition-colors no-underline text-[var(--color-fg)]"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">
                      {LEVEL_LABELS[report.access_level] || report.access_level}
                    </p>
                    <p className="text-xs text-[var(--color-muted)] mt-1">
                      {report.created_at
                        ? new Date(report.created_at).toLocaleDateString("ko-KR", {
                            year: "numeric",
                            month: "long",
                            day: "numeric",
                          })
                        : ""}
                    </p>
                  </div>
                  <span className="text-xs text-[var(--color-muted)]">보기 →</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
