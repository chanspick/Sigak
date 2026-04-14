"use client";

// 카카오 OAuth 콜백 페이지
// 인증 코드를 받아 토큰 교환 후 적절한 페이지로 리다이렉트

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { exchangeKakaoToken } from "@/lib/api/client";

function CallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("code");
    if (!code) {
      setError("인증 코드가 없습니다");
      return;
    }

    (async () => {
      try {
        const result = await exchangeKakaoToken(code);

        // localStorage에 유저 정보 저장
        localStorage.setItem("sigak_user_id", result.user_id);
        localStorage.setItem("sigak_user_name", result.name);
        if (result.email) localStorage.setItem("sigak_user_email", result.email);
        if (result.profile_image) localStorage.setItem("sigak_profile_image", result.profile_image);
        localStorage.setItem("sigak_kakao_id", result.kakao_id);

        // 애널리틱스
        import("@/lib/analytics").then(({ identifyUser, trackKakaoLogin }) => {
          identifyUser(result.user_id, {
            name: result.name,
            email: result.email,
            kakao_id: result.kakao_id,
          });
          trackKakaoLogin(result.reports.length === 0);
        });

        // 리포트가 있으면 최신 리포트로 이동, 없으면 시작 페이지로
        if (result.reports.length > 0) {
          const latest = result.reports[result.reports.length - 1];
          router.replace(`/report/${latest.id}`);
        } else {
          router.replace("/start");
        }
      } catch (err) {
        setError("카카오 로그인에 실패했습니다. 다시 시도해주세요.");
        console.error(err);
      }
    })();
  }, [searchParams, router]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg)]">
        <div className="text-center">
          <p className="text-sm text-[var(--color-danger)] mb-4">{error}</p>
          <a
            href="/start"
            className="text-sm underline text-[var(--color-fg)]"
          >
            처음으로 돌아가기
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg)]">
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-[var(--color-fg)] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-sm text-[var(--color-muted)]">
          카카오 로그인 중...
        </p>
      </div>
    </div>
  );
}

export default function KakaoCallbackPage() {
  return (
    <Suspense
      fallback={<div className="min-h-screen bg-[var(--color-bg)]" />}
    >
      <CallbackContent />
    </Suspense>
  );
}
