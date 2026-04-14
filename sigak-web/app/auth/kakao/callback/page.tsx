"use client";

// 카카오 OAuth 콜백 페이지
// 인증 코드를 받아 토큰 교환 후 적절한 페이지로 리다이렉트
// 핵심: code 1회성 소비 보장 (StrictMode 2번 실행 + 모바일 중복 호출 방어)

import { useEffect, useState, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { exchangeKakaoToken } from "@/lib/api/client";

function CallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const processedRef = useRef(false); // code 중복 소비 방지

  useEffect(() => {
    // StrictMode 2번 실행 + 모바일 중복 호출 방어
    if (processedRef.current) return;

    const code = searchParams.get("code");
    const kakaoError = searchParams.get("error");

    // 카카오에서 에러로 돌아온 경우 (유저가 동의 취소 등)
    if (kakaoError) {
      const desc = searchParams.get("error_description") || "카카오 인증이 취소되었습니다.";
      setError(desc);
      return;
    }

    if (!code) {
      setError("인증 코드가 없습니다");
      return;
    }

    processedRef.current = true; // 이후 재실행 차단

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
        processedRef.current = false; // 실패 시 재시도 허용
        const message = err instanceof Error ? err.message : "";
        // 백엔드에서 온 에러 메시지가 있으면 표시
        if (message.includes("카카오")) {
          setError(message);
        } else {
          setError("카카오 로그인에 실패했습니다. 다시 시도해주세요.");
        }
        console.error("[kakao callback]", err);
      }
    })();
  }, [searchParams, router]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg)]">
        <div className="text-center px-6">
          <p className="text-sm text-[var(--color-danger)] mb-4">{error}</p>
          <a
            href="/start"
            className="text-sm font-medium underline text-[var(--color-fg)]"
          >
            다시 시도하기
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
