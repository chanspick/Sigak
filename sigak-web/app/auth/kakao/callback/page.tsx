// SIGAK MVP v1.2 — /auth/kakao/callback
//
// Kakao가 redirect_uri로 보낸 ``code``를 받아:
//   1. POST /api/v1/auth/kakao/token 으로 JWT + 유저 정보 교환
//   2. setAuthData()로 JWT + 레거시 필드 저장
//   3. sigak_redirect (로그인 전 보던 페이지)가 있으면 복귀, 없으면 / 로
//      (이후 app/page.tsx 또는 useOnboardingGuard가 온보딩 완료 여부에 따라 추가 redirect)
//
// 핵심 방어: code 1회성 소비 보장
//   - StrictMode 2번 실행 + 모바일 WebView 재호출 시 동일 code로 두 번 요청되면 KOE320.
//   - processedRef + sessionStorage 동시 사용.

"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { exchangeKakaoToken } from "@/lib/api/client";
import { getKakaoRedirectUri } from "@/lib/kakao";

function CallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const processedRef = useRef(false);

  useEffect(() => {
    if (processedRef.current) return;

    const code = searchParams.get("code");
    const kakaoError = searchParams.get("error");

    if (kakaoError) {
      const desc =
        searchParams.get("error_description") ||
        "카카오 인증이 취소되었습니다.";
      setError(desc);
      return;
    }

    if (!code) {
      setError("인증 코드가 없습니다");
      return;
    }

    // sessionStorage flag — 동일 code로 재진입 시 중복 교환 방지
    const seenKey = `sigak_kakao_code_seen:${code}`;
    if (typeof window !== "undefined" && sessionStorage.getItem(seenKey)) {
      return;
    }
    if (typeof window !== "undefined") sessionStorage.setItem(seenKey, "1");
    processedRef.current = true;

    (async () => {
      try {
        // ⚠️ login 페이지와 동일한 redirect_uri를 보내야 Kakao가 수락함.
        //    lib/kakao.ts의 getKakaoRedirectUri()가 양쪽에서 같은 값을 반환.
        const redirectUri = getKakaoRedirectUri();
        const result = await exchangeKakaoToken(code, redirectUri);

        // JWT + 레거시 필드 일괄 저장. 레거시 필드는 전환 기간 호환용.
        const { setAuthData } = await import("@/lib/auth");
        setAuthData({
          jwt: result.jwt,
          userId: result.user_id,
          kakaoId: result.kakao_id,
          name: result.name,
          email: result.email,
          profileImage: result.profile_image,
        });

        // 애널리틱스 (첫 로그인 여부는 reports 유무로 근사 — v1.2에서는 reports 사용 안 하지만 호환 유지)
        import("@/lib/analytics").then(({ identifyUser, trackKakaoLogin }) => {
          identifyUser(result.user_id, {
            name: result.name,
            email: result.email,
            kakao_id: result.kakao_id,
          });
          trackKakaoLogin(result.reports.length === 0);
        });

        // Redirect 결정
        //   1. 명시적 deep-link(sessionStorage sigak_redirect) 있으면 거기로
        //   2. 없으면 / 로 → 랜딩/홈이 useOnboardingGuard로 추가 라우팅
        const redirect = sessionStorage.getItem("sigak_redirect");
        if (redirect) {
          sessionStorage.removeItem("sigak_redirect");
          router.replace(redirect);
          return;
        }
        router.replace("/");
      } catch (err) {
        processedRef.current = false; // 재시도 허용
        if (typeof window !== "undefined") sessionStorage.removeItem(seenKey);
        const message = err instanceof Error ? err.message : "";
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
      <div className="flex min-h-screen items-center justify-center bg-paper">
        <div className="px-6 text-center">
          <p
            className="mb-4 font-sans"
            style={{
              fontSize: 13,
              color: "var(--color-danger)",
              letterSpacing: "-0.005em",
              lineHeight: 1.6,
            }}
            role="alert"
          >
            {error}
          </p>
          <a
            href="/auth/login"
            className="font-sans font-medium text-ink underline underline-offset-2"
            style={{ fontSize: 13 }}
          >
            다시 시도하기
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-paper">
      <div className="text-center">
        <div
          className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-t-transparent"
          style={{ borderColor: "var(--color-ink)", borderTopColor: "transparent" }}
        />
        <p
          className="font-sans text-mute"
          style={{ fontSize: 13, letterSpacing: "-0.005em" }}
        >
          카카오 로그인 중...
        </p>
      </div>
    </div>
  );
}

export default function KakaoCallbackPage() {
  return (
    <Suspense
      fallback={<div className="min-h-screen bg-paper" />}
    >
      <CallbackContent />
    </Suspense>
  );
}
