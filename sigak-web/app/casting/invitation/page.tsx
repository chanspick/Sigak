"use client";

// 캐스팅 초대장 페이지 — 알림 클릭 시 이동
// /casting/invitation?id={notification_id}

import { useState, useEffect, useCallback, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

interface CastingData {
  agency_name: string;
  purpose: string;
  fee: string;
  response: string;
  requested_at: string;
  responded_at?: string;
}

function InvitationContent() {
  const params = useSearchParams();
  const router = useRouter();
  const notifId = params.get("id");
  const [data, setData] = useState<CastingData | null>(null);
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(true);
  const [responding, setResponding] = useState(false);

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

  const handleRespond = useCallback(async (response: "accept" | "decline") => {
    if (!notifId) return;
    setResponding(true);
    try {
      await fetch(`${API_URL}/api/v1/casting/respond/${notifId}?response=${response}`, {
        method: "POST",
        headers: { "ngrok-skip-browser-warning": "true" },
      });
      setData((prev) => prev ? { ...prev, response, responded_at: new Date().toISOString() } : prev);
    } catch (e) {
      console.error("[respond]", e);
    } finally {
      setResponding(false);
    }
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
    <div className="min-h-screen bg-[var(--color-bg)] flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-[360px]">
        {/* 초대장 카드 */}
        <div className="border border-[var(--color-border)]">
          {/* 헤더 — 프리미엄 블랙 */}
          <div className="bg-[var(--color-fg)] text-[var(--color-bg)] px-8 py-8 text-center">
            <p className="text-[8px] tracking-[6px] uppercase opacity-40 mb-3">
              You are invited
            </p>
            <p className="font-[family-name:var(--font-serif)] text-[18px] font-normal leading-snug">
              캐스팅 제안이<br />도착했습니다
            </p>
          </div>

          {/* 본문 — 컴팩트 */}
          <div className="px-8 py-7">
            {/* From */}
            <div className="mb-5">
              <p className="text-[9px] text-[var(--color-muted)] tracking-[2px] uppercase mb-1.5">From</p>
              <p className="text-lg font-bold tracking-tight">{data.agency_name}</p>
            </div>

            {/* Purpose + Fee + Date */}
            <div className="flex gap-4 mb-5">
              {data.purpose && (
                <div className="flex-1 min-w-0">
                  <p className="text-[9px] text-[var(--color-muted)] tracking-[2px] uppercase mb-1.5">Purpose</p>
                  <p className="text-[13px] leading-snug">{data.purpose}</p>
                </div>
              )}
              {data.fee && (
                <div className="shrink-0">
                  <p className="text-[9px] text-[var(--color-muted)] tracking-[2px] uppercase mb-1.5">Fee</p>
                  <p className="text-[13px] font-semibold">{data.fee}</p>
                </div>
              )}
              <div className="shrink-0">
                <p className="text-[9px] text-[var(--color-muted)] tracking-[2px] uppercase mb-1.5">Date</p>
                <p className="text-[13px]">{requestedDate}</p>
              </div>
            </div>

            {/* Divider */}
            <div className="w-full h-px bg-[var(--color-border)] mb-5" />

            {/* 이미 응답한 경우 */}
            {data.response === "accept" ? (
              <div className="text-center py-4">
                <p className="text-[13px] font-semibold mb-1">수락하셨습니다</p>
                <p className="text-[11px] text-[var(--color-muted)]">에이전시에 정보가 전달됩니다.</p>
              </div>
            ) : data.response === "decline" ? (
              <div className="text-center py-4">
                <p className="text-[13px] text-[var(--color-muted)]">정중히 거절하셨습니다</p>
              </div>
            ) : (
              <>
                <p className="text-[12px] text-center leading-relaxed mb-1">
                  관심이 있으시다면 수락해주세요.
                </p>
                <p className="text-[11px] text-[var(--color-muted)] text-center leading-relaxed mb-6">
                  수락 시 에이전시에 연락처와 리포트 요약을 전달합니다.
                </p>
                <div className="flex gap-3">
                  <button
                    onClick={() => handleRespond("accept")}
                    disabled={responding}
                    className="flex-1 py-3 text-[11px] font-semibold tracking-[1px] bg-[var(--color-fg)] text-[var(--color-bg)] hover:opacity-90 transition-opacity disabled:opacity-50 cursor-pointer"
                  >
                    {responding ? "처리 중..." : "수락하기"}
                  </button>
                  <button
                    onClick={() => handleRespond("decline")}
                    disabled={responding}
                    className="flex-1 py-3 text-[11px] font-medium tracking-[1px] border border-[var(--color-border)] text-[var(--color-muted)] hover:border-[var(--color-fg)] hover:text-[var(--color-fg)] transition-colors disabled:opacity-50 cursor-pointer"
                  >
                    괜찮습니다
                  </button>
                </div>
              </>
            )}
          </div>
        </div>

        {/* 하단 브랜딩 */}
        <p className="text-center text-[9px] text-[var(--color-muted)] tracking-[3px] mt-5 opacity-30">
          SIGAK
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
