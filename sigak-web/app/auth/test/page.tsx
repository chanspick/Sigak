"use client";

// 심사용 테스트 로그인 페이지
// URL: /auth/test?key=시크릿키
// 백엔드 test-login API 호출 → localStorage 세팅 → /start로 이동

import { useEffect, useState, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function TestLoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const processedRef = useRef(false);

  useEffect(() => {
    if (processedRef.current) return;

    const key = searchParams.get("key");
    if (!key) {
      setError("인증 키가 없습니다");
      return;
    }

    processedRef.current = true;

    (async () => {
      try {
        const resp = await fetch(`${API_URL}/api/v1/auth/test-login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ key }),
        });

        if (!resp.ok) {
          const body = await resp.json().catch(() => ({}));
          throw new Error(body.detail || "인증 실패");
        }

        const result = await resp.json();

        // localStorage에 유저 정보 저장 (카카오 로그인과 동일 구조)
        localStorage.setItem("sigak_user_id", result.user_id);
        localStorage.setItem("sigak_user_name", result.name);
        if (result.email) localStorage.setItem("sigak_user_email", result.email);
        if (result.profile_image) localStorage.setItem("sigak_profile_image", result.profile_image);
        localStorage.setItem("sigak_kakao_id", result.kakao_id);

        // 리포트가 있으면 최신 리포트로, 없으면 시작 페이지로
        if (result.reports && result.reports.length > 0) {
          const latest = result.reports[result.reports.length - 1];
          router.replace(`/report/${latest.id}`);
        } else {
          router.replace("/start");
        }
      } catch (err) {
        processedRef.current = false;
        setError(err instanceof Error ? err.message : "로그인 실패");
      }
    })();
  }, [searchParams, router]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg)]">
        <div className="text-center px-6">
          <p className="text-sm text-red-500 mb-4">{error}</p>
          <a href="/" className="text-sm font-medium underline text-[var(--color-fg)]">
            홈으로 돌아가기
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg)]">
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-[var(--color-fg)] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-sm text-[var(--color-muted)]">테스트 로그인 중...</p>
      </div>
    </div>
  );
}

export default function TestLoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[var(--color-bg)]" />}>
      <TestLoginContent />
    </Suspense>
  );
}
