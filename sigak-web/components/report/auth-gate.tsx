"use client";

// 인증 + 소유권 게이트
// - 비로그인 → 카카오 로그인으로 리다이렉트
// - 타인의 리포트 → 오버뷰(공유용)로 리다이렉트

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getKakaoLoginUrl } from "@/lib/api/client";

interface AuthGateProps {
  /** 리포트 소유자 user_id */
  reportUserId: string;
  /** 로그인 후 / 타인 접근 시 돌아갈 URL (오버뷰) */
  fallbackUrl: string;
}

export function AuthGate({ reportUserId, fallbackUrl }: AuthGateProps) {
  const router = useRouter();

  useEffect(() => {
    const currentUserId = localStorage.getItem("sigak_user_id");

    if (!currentUserId) {
      // 비로그인 → 카카오 로그인으로 리다이렉트
      sessionStorage.setItem("sigak_redirect", fallbackUrl);
      getKakaoLoginUrl().then(({ auth_url }) => {
        window.location.href = auth_url;
      });
      return;
    }

    if (currentUserId !== reportUserId) {
      // 타인의 리포트 → 오버뷰로 리다이렉트
      router.replace(fallbackUrl);
    }
  }, [reportUserId, fallbackUrl, router]);

  return null;
}
