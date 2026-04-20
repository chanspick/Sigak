// SIGAK MVP v1.2 — /onboarding/complete
//
// 4스텝 완료 직후 진입. 짧은 축하 카피 + "사진 올리기" CTA로 / (home) 유도.
// /home 자체는 D-4에서 MVP upload 스크린으로 교체 예정.
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { getToken } from "@/lib/auth";
import { ApiError } from "@/lib/api/fetch";
import { getMe } from "@/lib/api/onboarding";
import { PrimaryButton } from "@/components/ui/sigak";

export default function OnboardingCompletePage() {
  const router = useRouter();

  // 유효성: 로그인 + consent + onboarding 모두 완료된 상태에서만 이 페이지가 의미 있음.
  // 아니면 해당 단계로 되돌림.
  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.replace("/auth/login");
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
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/auth/login");
        }
        // 네트워크 실패는 화면 유지
      }
    })();
  }, [router]);

  return (
    <div className="flex min-h-screen flex-col bg-paper text-ink">
      <div className="flex-1 px-6 pt-[15vh]">
        {/* 큰 SIGAK 워드마크 */}
        <div
          className="font-display font-medium text-ink"
          style={{
            fontSize: 26,
            letterSpacing: "0.32em",
            paddingLeft: "0.32em",
            lineHeight: 1,
            textAlign: "center",
          }}
        >
          SIGAK
        </div>

        {/* 축하 카피 */}
        <h1
          className="mt-12 text-center font-sans font-medium text-ink"
          style={{ fontSize: 28, lineHeight: 1.3, letterSpacing: "-0.02em" }}
        >
          준비가 끝났어요.
        </h1>
        <p
          className="mt-4 text-center font-sans text-ink"
          style={{ fontSize: 14, lineHeight: 1.7, letterSpacing: "-0.005em" }}
        >
          이제 후보 사진 3~10장을 올리면
          <br />
          당신의 오늘 한 장을 골라드려요.
        </p>

        {/* 4스텝 체크 표시 */}
        <ul className="mx-auto mt-12 max-w-[220px] space-y-2">
          {["체형", "얼굴", "추구미", "자기 인식"].map((t, i) => (
            <li key={t} className="flex items-center gap-3">
              <span
                aria-hidden
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: "var(--color-sage)",
                }}
              />
              <span
                className="font-mono text-mute tabular-nums"
                style={{ fontSize: 10, letterSpacing: "0.14em" }}
              >
                /00{i + 1}
              </span>
              <span
                className="font-sans text-ink"
                style={{ fontSize: 13, letterSpacing: "-0.005em" }}
              >
                {t}
              </span>
            </li>
          ))}
        </ul>
      </div>

      {/* 하단 CTA */}
      <div className="px-5 pb-10 pt-4">
        <PrimaryButton onClick={() => router.push("/")}>사진 올리러 가기</PrimaryButton>
      </div>
    </div>
  );
}
