// SIGAK MVP v1.2 (Rebrand) — /onboarding/complete
//
// 4스텝 완료 후 축하 + 사진 올리기 CTA. 기능은 그대로 (me 체크 + redirect).
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { getToken } from "@/lib/auth";
import { ApiError } from "@/lib/api/fetch";
import { getMe } from "@/lib/api/onboarding";
import { PrimaryButton, TopBar } from "@/components/ui/sigak";

export default function OnboardingCompletePage() {
  const router = useRouter();

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
      }
    })();
  }, [router]);

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--color-paper)",
        color: "var(--color-ink)",
        fontFamily: "var(--font-sans)",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <TopBar backTarget="/" />

      {/* 본문 */}
      <section
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "0 28px",
        }}
      >
        <h1
          className="font-serif"
          style={{
            fontSize: 36,
            fontWeight: 400,
            lineHeight: 1.25,
            letterSpacing: "-0.02em",
            margin: 0,
            color: "var(--color-ink)",
          }}
        >
          준비가<br />끝났습니다.
        </h1>
        <p
          className="font-sans"
          style={{
            marginTop: 20,
            fontSize: 14,
            lineHeight: 1.7,
            opacity: 0.6,
            color: "var(--color-ink)",
            letterSpacing: "-0.005em",
          }}
        >
          사진 세 장이면 오늘의 한 장을<br />
          골라드립니다.
        </p>

        {/* 4스텝 체크 */}
        <ul style={{ marginTop: 40, padding: 0, listStyle: "none" }}>
          {["체형", "얼굴", "추구미", "자기 인식"].map((t, i) => (
            <li
              key={t}
              style={{
                display: "flex",
                alignItems: "baseline",
                gap: 14,
                padding: "11px 0",
                borderBottom: i === 3 ? "none" : "1px solid rgba(0, 0, 0, 0.1)",
              }}
            >
              <span
                className="font-serif tabular-nums"
                style={{
                  fontSize: 14,
                  fontWeight: 400,
                  opacity: 0.4,
                  color: "var(--color-ink)",
                }}
              >
                {String(i + 1).padStart(2, "0")}
              </span>
              <span
                className="font-sans"
                style={{
                  fontSize: 14,
                  letterSpacing: "-0.005em",
                  color: "var(--color-ink)",
                }}
              >
                {t}
              </span>
              <span style={{ flex: 1 }} />
              <span
                className="font-sans uppercase"
                style={{
                  fontSize: 10,
                  fontWeight: 600,
                  letterSpacing: "1.5px",
                  opacity: 0.4,
                  color: "var(--color-ink)",
                }}
              >
                DONE
              </span>
            </li>
          ))}
        </ul>
      </section>

      {/* CTA */}
      <div style={{ padding: "20px 28px 32px" }}>
        <PrimaryButton onClick={() => router.push("/verdict/new")}>
          사진 올리러 가기
        </PrimaryButton>
      </div>
    </div>
  );
}
