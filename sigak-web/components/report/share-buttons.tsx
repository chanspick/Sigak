"use client";

// 공유 버튼 컴포넌트 — 카카오톡 공유 + 링크 복사
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
      // fallback
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

  const handleKakaoShare = () => {
    // 카카오톡 공유 — Kakao SDK 없이 모바일 딥링크 활용
    const url = window.location.href;
    const text = `${title}\n${description}`;
    // 카카오톡 URL scheme
    const kakaoUrl = `https://sharer.kakao.com/talk/friends/picker/link?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`;
    window.open(kakaoUrl, "_blank", "width=600,height=400");
  };

  return (
    <div className="flex gap-3 w-full max-w-sm mx-auto">
      {/* 카카오톡 공유 */}
      <button
        onClick={handleKakaoShare}
        className="flex-1 flex items-center justify-center gap-2 py-3 rounded-lg bg-[#FEE500] text-[#191919] text-sm font-semibold hover:brightness-95 transition-all"
      >
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <path
            d="M9 1C4.582 1 1 3.79 1 7.207c0 2.21 1.47 4.152 3.684 5.248l-.937 3.467a.225.225 0 00.339.243l4.07-2.684c.276.025.557.04.844.04 4.418 0 8-2.79 8-6.314C17 3.79 13.418 1 9 1z"
            fill="#191919"
          />
        </svg>
        카카오톡 공유
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
