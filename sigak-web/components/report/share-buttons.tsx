"use client";

// 공유 버튼 컴포넌트 — 공유하기(네이티브) + 링크 복사
import { useState } from "react";

interface ShareButtonsProps {
  title: string;
  description: string;
}

export function ShareButtons({ title, description }: ShareButtonsProps) {
  const [copied, setCopied] = useState(false);

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const input = document.createElement("input");
      input.value = window.location.href;
      document.body.appendChild(input);
      input.select();
      document.execCommand("copy");
      document.body.removeChild(input);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleShare = async () => {
    const url = window.location.href;

    // 모바일: 네이티브 공유 (카카오톡, 인스타 DM 등 자동 노출)
    if (navigator.share) {
      try {
        await navigator.share({ title, text: description, url });
        return;
      } catch {
        // 사용자가 취소한 경우 무시
      }
    }

    // 데스크톱 폴백: 링크 복사
    handleCopyLink();
  };

  return (
    <div className="flex gap-3 w-full max-w-sm mx-auto">
      {/* 공유하기 */}
      <button
        onClick={handleShare}
        className="flex-1 flex items-center justify-center gap-2 py-3 rounded-lg bg-[var(--color-fg)] text-[var(--color-bg)] text-sm font-semibold hover:opacity-90 transition-all"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M4 8V13a1 1 0 001 1h6a1 1 0 001-1V8M8 1v9M5 4l3-3 3 3" />
        </svg>
        공유하기
      </button>

      {/* 링크 복사 */}
      <button
        onClick={handleCopyLink}
        className="flex-1 flex items-center justify-center gap-2 py-3 rounded-lg border border-[var(--color-fg)] text-sm font-semibold hover:bg-[var(--color-fg)] hover:text-[var(--color-bg)] transition-all"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M6.5 9.5l3-3M7 11.5l-1.3 1.3a2.12 2.12 0 01-3-3L4 8.5M9 4.5l1.3-1.3a2.12 2.12 0 013 3L12 7.5" />
        </svg>
        {copied ? "복사 완료" : "링크 복사"}
      </button>
    </div>
  );
}
