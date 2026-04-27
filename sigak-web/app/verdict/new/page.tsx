// SIGAK MVP v1.2 — /verdict/new
//
// 사진 업로드 + Analyzing 흐름. 기존 HomeScreen 컴포넌트 그대로 재사용.
// 로그인 가드 + consent/onboarding 가드.
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { HomeScreen } from "@/components/sigak/home-screen";
import { SigakLoading } from "@/components/ui/sigak";
import { getToken } from "@/lib/auth";
import { ApiError } from "@/lib/api/fetch";
import { getMe } from "@/lib/api/onboarding";

export default function VerdictNewPage() {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/auth/login?next=/verdict/new");
      return;
    }
    (async () => {
      try {
        const me = await getMe();
        if (!me.consent_completed) {
          router.replace("/onboarding/welcome");
          return;
        }
        if (!me.onboarding_completed) {
          router.replace("/onboarding/step/1");
          return;
        }
        setReady(true);
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/auth/login");
          return;
        }
        // 네트워크 실패 시 진행시키되 HomeScreen 자체가 API 실패 처리
        setReady(true);
      }
    })();
  }, [router]);

  if (!ready) {
    return <SigakLoading message="잠시만요" hint="" />;
  }

  return <HomeScreen />;
}
