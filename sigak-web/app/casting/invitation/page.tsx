"use client";

// 캐스팅 초대장 페이지 — 알림 클릭 시 이동
// /casting/invitation?id={notification_id}

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

interface CastingData {
  agency_name: string;
  purpose: string;
  requested_at: string;
}

function InvitationContent() {
  const params = useSearchParams();
  const notifId = params.get("id");
  const [data, setData] = useState<CastingData | null>(null);
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!notifId) {
      setLoading(false);
      return;
    }
    const userId = localStorage.getItem("sigak_user_id");
    if (!userId) {
      setLoading(false);
      return;
    }

    (async () => {
      try {
        // 알림 목록에서 해당 알림 찾기
        const res = await fetch(`${API_URL}/api/v1/notifications?user_id=${userId}`, {
          headers: { "ngrok-skip-browser-warning": "true" },
        });
        if (!res.ok) return;
        const result = await res.json();
        const notif = result.notifications?.find((n: { id: string }) => n.id === notifId);
        if (notif) {
          setTitle(notif.title);
          try {
            setData(JSON.parse(notif.message));
          } catch {
            // message가 JSON이 아닌 경우
          }
          // 읽음 처리
          await fetch(`${API_URL}/api/v1/notifications/${notifId}/read`, { method: "POST" });
        }
      } catch (e) {
        console.error("[invitation]", e);
      } finally {
        setLoading(false);
      }
    })();
  }, [notifId]);

  const requestedDate = data?.requested_at
    ? new Date(data.requested_at).toLocaleDateString("ko-KR", {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : "";

  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--color-bg)] flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-[var(--color-fg)] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-[var(--color-bg)] flex items-center justify-center text-center px-6">
        <div>
          <p className="text-sm text-[var(--color-muted)] mb-4">초대장을 불러올 수 없습니다</p>
          <Link href="/" className="text-sm underline">홈으로</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg)] flex items-center justify-center px-5 py-16">
      <div className="w-full max-w-md">
        {/* 초대장 카드 */}
        <div className="border border-[var(--color-border)]">
          {/* 헤더 */}
          <div className="bg-[var(--color-fg)] text-[var(--color-bg)] px-10 py-12 text-center">
            <p className="text-[9px] font-bold tracking-[5px] uppercase opacity-50 mb-4">
              CASTING INVITATION
            </p>
            <div className="w-12 h-px bg-[var(--color-bg)] opacity-20 mx-auto mb-4" />
            <p className="text-[12px] tracking-[4px] uppercase opacity-30">
              SIGAK
            </p>
          </div>

          {/* 본문 */}
          <div className="px-10 py-10">
            {/* From */}
            <div className="mb-8">
              <p className="text-[10px] text-[var(--color-muted)] tracking-[2px] uppercase mb-2">
                From
              </p>
              <p className="text-2xl font-bold tracking-tight">
                {data.agency_name}
              </p>
            </div>

            {/* Purpose */}
            {data.purpose && (
              <div className="mb-8">
                <p className="text-[10px] text-[var(--color-muted)] tracking-[2px] uppercase mb-2">
                  Purpose
                </p>
                <p className="text-[15px] leading-relaxed">
                  {data.purpose}
                </p>
              </div>
            )}

            {/* Divider */}
            <div className="w-full h-px bg-[var(--color-border)] mb-8" />

            {/* Date */}
            <div className="mb-10">
              <p className="text-[10px] text-[var(--color-muted)] tracking-[2px] uppercase mb-2">
                Date
              </p>
              <p className="text-[14px]">
                {requestedDate}
              </p>
            </div>

            {/* 안내 */}
            <div className="bg-black/[0.02] border border-[var(--color-border)] p-5 text-center mb-8">
              <p className="text-[13px] font-medium mb-1">
                SIGAK 팀이 확인 후 연락드리겠습니다
              </p>
              <p className="text-[11px] text-[var(--color-muted)] leading-relaxed">
                캐스팅 관련 상세 내용은<br />
                카카오톡으로 안내드립니다
              </p>
            </div>

            {/* 홈으로 */}
            <Link
              href="/my"
              className="block w-full py-3.5 text-center text-[12px] font-medium tracking-[1px] border border-[var(--color-fg)] text-[var(--color-fg)] hover:bg-[var(--color-fg)] hover:text-[var(--color-bg)] transition-colors no-underline"
            >
              내 리포트로 돌아가기
            </Link>
          </div>
        </div>

        {/* 하단 브랜딩 */}
        <p className="text-center text-[10px] text-[var(--color-muted)] tracking-[2px] mt-6 opacity-40">
          SIGAK CASTING POOL
        </p>
      </div>
    </div>
  );
}

export default function CastingInvitationPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[var(--color-bg)]" />}>
      <InvitationContent />
    </Suspense>
  );
}
