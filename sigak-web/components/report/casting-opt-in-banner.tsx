"use client";

// 캐스팅 풀 opt-in 배너
// 풀 리포트(access_level="full") 하단에 표시
// 체크박스 동의 후 등록 가능, 약관 토글 제공

import { useState, useEffect } from "react";

interface CastingOptInBannerProps {
  userId: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

export function CastingOptInBanner({ userId }: CastingOptInBannerProps) {
  const [status, setStatus] = useState<"loading" | "not_opted" | "opted_in" | "error">("loading");
  const [agreed, setAgreed] = useState(false);
  const [showTerms, setShowTerms] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetch(`${API_URL}/api/v1/casting/status?user_id=${userId}`)
      .then((r) => r.json())
      .then((data) => setStatus(data.opted_in ? "opted_in" : "not_opted"))
      .catch(() => setStatus("error"));
  }, [userId]);

  const handleOptIn = async () => {
    if (!agreed || submitting) return;
    setSubmitting(true);
    try {
      const res = await fetch(
        `${API_URL}/api/v1/casting/opt-in?user_id=${userId}`,
        { method: "POST" },
      );
      if (res.ok) {
        setStatus("opted_in");
        import("@/lib/analytics").then(({ trackCastingOptIn }) => trackCastingOptIn());
      }
    } catch {
      console.error("[casting opt-in] failed");
    } finally {
      setSubmitting(false);
    }
  };

  // 로딩 중 — 높이 유지용 placeholder
  if (status === "loading") {
    return (
      <div className="py-10 px-6 border border-[var(--color-border)]">
        <div className="animate-pulse">
          <div className="h-3 w-24 bg-black/[0.06] mb-4" />
          <div className="h-6 w-64 bg-black/[0.06] mb-2" />
          <div className="h-4 w-full bg-black/[0.06] mb-1" />
          <div className="h-4 w-3/4 bg-black/[0.06]" />
        </div>
      </div>
    );
  }

  if (status === "error") return null;

  if (status === "opted_in") {
    return (
      <div className="py-8 px-6 border border-[var(--color-border)] text-center">
        <p className="text-sm font-semibold">캐스팅 풀에 등록되어 있습니다</p>
        <p className="text-xs text-[var(--color-muted)] mt-1">
          매칭 파트너가 회원님의 프로필을 검색할 수 있습니다
        </p>
      </div>
    );
  }

  return (
    <div className="py-10 px-6 border border-[var(--color-border)]">
      {/* 헤더 */}
      <p className="text-xs font-semibold tracking-[4px] uppercase text-[var(--color-muted)] mb-4">
        CASTING POOL
      </p>
      <h3 className="font-[family-name:var(--font-serif)] text-xl font-bold mb-2">
        '좋아요' 대신 '캐스팅 제안' 받을 시간.
      </h3>
      <p className="text-sm text-[var(--color-muted)] mb-6 leading-relaxed">
        SIGAK이 제작사 · 에이전시에 당신의 프로필을 연결해 드립니다.
        캐스팅 디렉터가 내 유형을 검색할 수 있으며,
        매칭 시 사전 동의 후 연결됩니다. 언제든 등록 해제 가능합니다.
      </p>

      {/* 체크리스트 */}
      <div className="flex flex-col gap-2 mb-6 text-sm">
        {[
          "캐스팅 디렉터가 내 유형을 검색 가능",
          "매칭 시 사전 동의 후 연결",
          "언제든 등록 해제 가능",
        ].map((text) => (
          <div key={text} className="flex items-center gap-2">
            <span className="text-[var(--color-muted)]">-</span>
            <span>{text}</span>
          </div>
        ))}
      </div>

      {/* 동의 체크박스 */}
      <label className="flex items-start gap-2.5 mb-4 cursor-pointer">
        <input
          type="checkbox"
          checked={agreed}
          onChange={(e) => setAgreed(e.target.checked)}
          className="mt-0.5 w-4 h-4 accent-[var(--color-fg)] cursor-pointer"
        />
        <span className="text-xs text-[var(--color-muted)] leading-relaxed">
          캐스팅 매칭 서비스{" "}
          <button
            type="button"
            onClick={() => setShowTerms(!showTerms)}
            className="underline"
          >
            개인정보 제3자 제공
          </button>
          에 동의합니다
        </span>
      </label>

      {/* 약관 상세 (토글) */}
      {showTerms && (
        <div className="mb-4 p-4 bg-black/[0.03] text-xs text-[var(--color-muted)] leading-relaxed">
          <p className="font-semibold mb-2">개인정보 제3자 제공 동의</p>
          <p>제공받는 자: 캐스팅 디렉터, 제작사, 광고 에이전시, 매니지먼트사 등 SIGAK과 제휴한 업체</p>
          <p className="mt-1">제공 항목: 얼굴형 분석 결과, 이미지 유형, 3축 좌표, 사진(동의한 사진에 한함)</p>
          <p className="mt-1">제공 목적: 캐스팅 · 오디션 · 모델 매칭 · 광고 출연 등 업무 연결</p>
          <p className="mt-1">보유 기간: 제공 목적 달성 시까지 (최대 1년). 철회 요청 시 즉시 파기.</p>
          <p className="mt-1">※ SIGAK은 매칭 파트너에게 실명 및 연락처를 직접 제공하지 않으며, 매칭 성사 시 추가 동의를 받은 후 전달합니다.</p>
        </div>
      )}

      {/* 등록 버튼 */}
      <button
        onClick={handleOptIn}
        disabled={!agreed || submitting}
        className={[
          "w-full py-3.5 text-sm font-bold tracking-[0.5px] transition-all",
          agreed && !submitting
            ? "bg-[var(--color-fg)] text-[var(--color-bg)] hover:opacity-90 cursor-pointer"
            : "bg-black/[0.08] text-[var(--color-muted)] cursor-not-allowed",
        ].join(" ")}
      >
        {submitting ? "등록 중..." : "캐스팅 풀 등록하기"}
      </button>
    </div>
  );
}
