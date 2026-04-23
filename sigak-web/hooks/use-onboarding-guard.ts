// SIGAK — useOnboardingGuard (3-stage gate: consent → essentials → Sia)
//
// 모든 authed 페이지에서 호출. 규칙:
//   1. JWT 없음 → /auth/login
//   2. 예외 경로(EXEMPT_PATH_PREFIXES) 는 가드 우회
//   3. GET /api/v1/auth/me 로 consent_completed / essentials_completed / onboarding_completed 확인
//   4. consent_completed=false → /onboarding/welcome
//   5. essentials_completed=false → /onboarding/essentials
//                                   (Step 0: gender + birth_date + ig_handle)
//   6. onboarding_completed=false → /sia/new (Sia 대화 진입)
//                                   * Phase N3 Sia UI 완성 전 임시로 legacy step/{n} 경로도 지원
//   7. 모두 true 면 통과 (status="ready")
//   8. 401 오면 토큰 정리 + /auth/login
//
// 사용:
//   "use client";
//   import { useOnboardingGuard } from "@/hooks/use-onboarding-guard";
//   export default function HomePage() {
//     const { status } = useOnboardingGuard();
//     if (status !== "ready") return null;
//     return <HomeScreen />;
//   }
"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import { getToken } from "@/lib/auth";
import { ApiError } from "@/lib/api/fetch";
import { getMe } from "@/lib/api/onboarding";
import type { AuthMeV2Response } from "@/lib/types/mvp";

type GuardStatus = "checking" | "redirecting" | "ready";

/** prefix 매칭 기반 예외 경로 — 이 경로들은 가드 우회.
 *  /onboarding/* 가 포함되어야 온보딩 welcome/step/complete 페이지가 무한 루프 없이 작동.
 *  /auth/* 는 로그인/콜백, /terms·/refund 는 약관 딥링크, /profile 은 설정 화면.
 *  /tokens/* 는 결제 플로우(인증 되어 있으면 consent/onboarding 미완 상태여도 접근 허용). */
const EXEMPT_PATH_PREFIXES = [
  "/onboarding",
  "/tokens",
  "/profile",
  "/auth",
  "/terms",
  "/refund",
] as const;

function isExempt(pathname: string): boolean {
  return EXEMPT_PATH_PREFIXES.some(
    (p) => pathname === p || pathname.startsWith(`${p}/`),
  );
}

export interface UseOnboardingGuardResult {
  status: GuardStatus;
  /** /auth/me 응답. consent+onboarding 모두 완료된 상태에서 채워짐. */
  me: AuthMeV2Response | null;
  error: string | null;
}

export function useOnboardingGuard(): UseOnboardingGuardResult {
  const router = useRouter();
  const pathname = usePathname();
  const [status, setStatus] = useState<GuardStatus>("checking");
  const [me, setMe] = useState<AuthMeV2Response | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    // 1. 예외 경로는 곧바로 ready (로그인 여부와 무관하게 통과 — 각 페이지가 자체 처리)
    if (isExempt(pathname)) {
      setStatus("ready");
      return;
    }

    // 2. JWT 없으면 로그인으로
    const token = getToken();
    if (!token) {
      setStatus("redirecting");
      router.replace("/auth/login");
      return;
    }

    // 3. me 조회 후 3단계 게이트 분기
    (async () => {
      try {
        const meData = await getMe();
        if (cancelled) return;

        // 3-a. 약관 동의 미완료 → welcome
        if (!meData.consent_completed) {
          setStatus("redirecting");
          router.replace("/onboarding/welcome");
          return;
        }

        // 3-b. Step 0 구조화 입력 미완료 → essentials
        if (!meData.essentials_completed) {
          setStatus("redirecting");
          router.replace("/onboarding/essentials");
          return;
        }

        // 3-c. Sia 대화 미완료 → /sia/new
        if (!meData.onboarding_completed) {
          setStatus("redirecting");
          router.replace("/sia");
          return;
        }

        // 3-d. 모두 완료
        setMe(meData);
        setStatus("ready");
      } catch (e) {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 401) {
          // authFetch가 이미 토큰 clear함
          setStatus("redirecting");
          router.replace("/auth/login");
          return;
        }
        const msg = e instanceof Error ? e.message : "unknown error";
        setError(msg);
        // 네트워크 실패 시 사용자를 막지 않음 — ready로 통과시키되 상위에서 처리 가능
        setStatus("ready");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [pathname, router]);

  return { status, me, error };
}
