"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";

interface Notification {
  id: string;
  type: string;
  title: string;
  message: string;
  link: string | null;
  is_read: boolean;
  created_at: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

/** 알림 시간을 간결하게 포맷 (오늘이면 시간만, 아니면 월/일) */
function formatTime(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const isToday =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate();

  if (isToday) {
    return date.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" });
  }
  return date.toLocaleDateString("ko-KR", { month: "long", day: "numeric" });
}

/** 캐스팅 알림 메시지에서 JSON 파싱 */
function parseCastingData(message: string): { agency_name: string; purpose: string; requested_at: string } | null {
  try {
    return JSON.parse(message);
  } catch {
    return null;
  }
}

/** 알림 목록에서 캐스팅 초대 미리보기 */
function CastingInvitePreview({ notif }: { notif: Notification }) {
  return (
    <div className="py-1">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-[9px] font-bold tracking-[1.5px] uppercase px-1.5 py-0.5 bg-[var(--color-fg)] text-[var(--color-bg)]">
          CASTING
        </span>
        <span className="text-[10px] text-[var(--color-muted)]">{formatTime(notif.created_at)}</span>
      </div>
      <p className="text-sm font-medium text-[var(--color-fg)]">{notif.title}</p>
      <p className="text-[11px] text-[var(--color-muted)] mt-0.5">탭하여 상세 보기</p>
    </div>
  );
}

/** 캐스팅 초대장 모달 */
function CastingInviteModal({ notif, onClose }: { notif: Notification; onClose: () => void }) {
  const data = parseCastingData(notif.message);
  const requestedDate = data?.requested_at
    ? new Date(data.requested_at).toLocaleDateString("ko-KR", { year: "numeric", month: "long", day: "numeric" })
    : "";

  return (
    <div className="fixed inset-0 z-[300] flex items-center justify-center bg-black/50" onClick={onClose}>
      <div className="bg-[var(--color-bg)] w-full max-w-sm mx-4 overflow-hidden" onClick={(e) => e.stopPropagation()}>
        {/* 헤더 */}
        <div className="bg-[var(--color-fg)] text-[var(--color-bg)] px-8 py-8 text-center">
          <p className="text-[10px] font-bold tracking-[4px] uppercase opacity-60 mb-3">CASTING INVITATION</p>
          <p className="text-[11px] tracking-[2px] uppercase opacity-40">SIGAK</p>
        </div>

        {/* 본문 */}
        <div className="px-8 py-8">
          <p className="text-[11px] text-[var(--color-muted)] tracking-[1px] uppercase mb-2">From</p>
          <p className="text-xl font-bold mb-6">{data?.agency_name || "에이전시"}</p>

          {data?.purpose && (
            <>
              <p className="text-[11px] text-[var(--color-muted)] tracking-[1px] uppercase mb-2">Purpose</p>
              <p className="text-[15px] leading-relaxed mb-6">{data.purpose}</p>
            </>
          )}

          <div className="border-t border-[var(--color-border)] pt-5 mb-6">
            <p className="text-[11px] text-[var(--color-muted)] tracking-[1px] uppercase mb-2">Date</p>
            <p className="text-[13px]">{requestedDate}</p>
          </div>

          <p className="text-[12px] text-[var(--color-muted)] leading-relaxed text-center">
            SIGAK 팀이 확인 후<br />
            상세 내용을 연락드리겠습니다.
          </p>
        </div>

        {/* 닫기 */}
        <div className="px-8 pb-8">
          <button
            onClick={onClose}
            className="w-full py-3 text-[12px] font-medium tracking-[1px] border border-[var(--color-border)] hover:bg-black/[0.03] transition-colors cursor-pointer"
          >
            확인
          </button>
        </div>
      </div>
    </div>
  );
}

export function NotificationBell() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedCasting, setSelectedCasting] = useState<Notification | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  const getUserId = () => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("sigak_user_id");
  };

  const fetchNotifications = useCallback(async () => {
    const userId = getUserId();
    if (!userId) return;
    try {
      const res = await fetch(`${API_URL}/api/v1/notifications?user_id=${userId}`);
      if (!res.ok) return;
      const data = await res.json();
      setNotifications(data.notifications);
      setUnreadCount(data.unread_count);
    } catch (e) {
      console.error("[notifications]", e);
    }
  }, []);

  // 30초마다 폴링 (로그인 유저만)
  useEffect(() => {
    if (!getUserId()) return;
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  // 바깥 클릭 시 드롭다운 닫기
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // 알림 클릭 → 읽음 처리 + 이동
  const handleClick = async (notif: Notification) => {
    if (!notif.is_read) {
      await fetch(`${API_URL}/api/v1/notifications/${notif.id}/read`, { method: "POST" });
      setNotifications((prev) =>
        prev.map((n) => (n.id === notif.id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    }
    if (notif.link) {
      router.push(notif.link);
    }
    setIsOpen(false);
  };

  // 전체 읽음
  const handleReadAll = async () => {
    const userId = getUserId();
    if (!userId) return;
    await fetch(`${API_URL}/api/v1/notifications/read-all?user_id=${userId}`, { method: "POST" });
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    setUnreadCount(0);
  };

  return (
    <>
    <div className="relative" ref={dropdownRef}>
      {/* 벨 아이콘 */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2"
        aria-label="알림"
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 18 18"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          aria-hidden="true"
        >
          <path d="M9 16.2a1.8 1.8 0 01-1.8-1.8h3.6a1.8 1.8 0 01-1.8 1.8z" />
          <path d="M13.5 8.1a4.5 4.5 0 00-9 0c0 3.6-1.8 5.4-1.8 5.4h12.6s-1.8-1.8-1.8-5.4z" />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-[var(--color-danger)] text-white text-[10px] font-bold rounded-full flex items-center justify-center animate-[scale-in_0.2s_ease-out]">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {/* 드롭다운 */}
      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-[calc(100vw-32px)] max-w-80 bg-[var(--color-bg)] border border-[var(--color-border)] shadow-lg z-[150] max-h-96 overflow-y-auto">
          <div className="px-4 py-3 border-b border-[var(--color-border)] flex justify-between items-center">
            <span className="text-sm font-semibold text-[var(--color-fg)]">알림</span>
            {unreadCount > 0 && (
              <button
                onClick={handleReadAll}
                className="text-xs text-[var(--color-muted)] hover:underline"
              >
                모두 읽음
              </button>
            )}
          </div>

          {notifications.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm text-[var(--color-muted)]">
              알림이 없습니다
            </div>
          ) : (
            notifications.map((notif) => (
              <button
                key={notif.id}
                onClick={() => {
                  if (notif.type === "casting_match") {
                    handleClick(notif);
                    setSelectedCasting(notif);
                  } else {
                    handleClick(notif);
                  }
                }}
                className={`w-full px-4 py-3 text-left border-b border-[var(--color-border)] hover:bg-black/[0.03] transition-colors ${
                  notif.is_read ? "opacity-50" : ""
                }`}
              >
                {notif.type === "casting_match" ? (
                  <CastingInvitePreview notif={notif} />
                ) : (
                  <>
                    <p className="text-sm font-medium text-[var(--color-fg)]">{notif.title}</p>
                    <p className="text-xs text-[var(--color-muted)] mt-0.5">{notif.message}</p>
                    <p className="text-[10px] text-[var(--color-muted)] mt-1">
                      {formatTime(notif.created_at)}
                    </p>
                  </>
                )}
              </button>
            ))
          )}
        </div>
      )}

    </div>

    {/* 캐스팅 초대장 모달 */}
    {selectedCasting && (
      <CastingInviteModal
        notif={selectedCasting}
        onClose={() => setSelectedCasting(null)}
      />
    )}
    </>
  );
}
