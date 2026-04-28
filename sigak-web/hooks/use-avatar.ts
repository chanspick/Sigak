// SIGAK — useAvatar (홈/설정/피드쉘 공용 아바타 hook, 2026-04-28)
//
// 우선순위: IG 첫 피드 사진(R2 영구 URL) → 카카오 프사 fallback.
// 호출처는 항상 `feedAvatarUrl || kakaoAvatarUrl` 로 src 결정.
// 마운트 즉시 = localStorage 캐시 반영. 백그라운드 = /auth/me 호출하여 갱신.
//
// 백엔드 보장 (sigak/routes/auth.py:170-175):
//   feed_avatar_url 은 r2_public_base_url prefix 검증 통과한 URL 만 반환.
//   raw IG CDN URL (24-48h 만료) / r2:// 스킴 / R2 public 미설정은 모두 null.
"use client";

import { useEffect, useState } from "react";

import { getToken } from "@/lib/auth";
import { getMe } from "@/lib/api/onboarding";

const STORAGE_KEY = "sigak_feed_avatar";

export interface AvatarSources {
  /** IG 첫 피드 사진 (R2 영구 URL). null = 없음 / 미인증 / 미수집. */
  feedAvatarUrl: string | null;
  /** 카카오 프사. fallback 용. 빈 문자열 = 없음 (호출처가 gradient 표시). */
  kakaoAvatarUrl: string;
}

// 동시 마운트 (홈 + 피드쉘 등) 에서 /auth/me 중복 호출 방지.
let sessionFetchInFlight: Promise<string | null> | null = null;

export function useAvatar(): AvatarSources {
  const [feedAvatarUrl, setFeedAvatarUrl] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(STORAGE_KEY) || null;
  });
  const [kakaoAvatarUrl] = useState<string>(() => {
    if (typeof window === "undefined") return "";
    return localStorage.getItem("sigak_profile_image") || "";
  });

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!getToken()) return;

    let cancelled = false;
    const promise =
      sessionFetchInFlight ??
      getMe().then((me) => me.feed_avatar_url ?? null);
    sessionFetchInFlight = promise;

    promise
      .then((url) => {
        if (cancelled) return;
        if (url) {
          localStorage.setItem(STORAGE_KEY, url);
          setFeedAvatarUrl(url);
        } else {
          localStorage.removeItem(STORAGE_KEY);
          setFeedAvatarUrl(null);
        }
      })
      .catch(() => {
        // 네트워크 오류는 캐시 유지 — 다음 마운트에 재시도.
      })
      .finally(() => {
        sessionFetchInFlight = null;
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return { feedAvatarUrl, kakaoAvatarUrl };
}
