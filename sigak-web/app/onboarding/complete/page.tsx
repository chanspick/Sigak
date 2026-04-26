// SIGAK MVP v1.2 (Rebrand) — /onboarding/complete
//
// 4스텝 완료 후 축하 + 사진 올리기 CTA. 기능은 그대로 (me 체크 + redirect).
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { getToken } from "@/lib/auth";
import { ApiError } from "@/lib/api/fetch";
import { getMe } from "@/lib/api/onboarding";
import { TopBar } from "@/components/ui/sigak";

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

      {/* 본문 — 마케터 정합 (period accent + 700 + maxWidth 480) */}
      <section
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "0 24px",
          maxWidth: 480,
          margin: "0 auto",
          width: "100%",
        }}
      >
        <h1
          className="font-serif"
          style={{
            fontSize: 28,
            fontWeight: 700,
            lineHeight: 1.35,
            letterSpacing: "-0.025em",
            margin: 0,
            color: "var(--color-ink)",
            wordBreak: "keep-all",
          }}
        >
          준비가<br />
          끝났습니다
          <span style={{ color: "var(--color-danger)" }}>.</span>
        </h1>
        <p
          className="font-sans"
          style={{
            marginTop: 14,
            fontSize: 14,
            lineHeight: 1.7,
            color: "var(--color-mute)",
            letterSpacing: "-0.005em",
          }}
        >
          사진 세 장이면 오늘의 한 장을
          <br />
          골라드립니다.
        </p>

        {/* 4스텝 체크 */}
        <ul style={{ marginTop: 32, padding: 0, listStyle: "none" }}>
          {["체형", "얼굴", "추구미", "자기 인식"].map((t, i) => (
            <li
              key={t}
              style={{
                display: "flex",
                alignItems: "baseline",
                gap: 14,
                padding: "13px 0",
                borderBottom: i === 3 ? "none" : "1px solid var(--color-line)",
              }}
            >
              <span
                className="tabular-nums"
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 12,
                  fontWeight: 500,
                  color: "var(--color-danger)",
                  letterSpacing: "0.06em",
                }}
              >
                {String(i + 1).padStart(2, "0")}
              </span>
              <span
                className="font-serif"
                style={{
                  fontSize: 15,
                  fontWeight: 500,
                  letterSpacing: "-0.013em",
                  color: "var(--color-ink)",
                }}
              >
                {t}
              </span>
              <span style={{ flex: 1 }} />
              <span
                className="uppercase"
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 10,
                  letterSpacing: "0.12em",
                  color: "var(--color-mute)",
                }}
              >
                DONE
              </span>
            </li>
          ))}
        </ul>
      </section>

      {/* CTA — 마케터 pill */}
      <div style={{ padding: "20px 24px 32px", maxWidth: 480, margin: "0 auto", width: "100%" }}>
        <button
          type="button"
          onClick={() => router.push("/verdict/new")}
          className="font-sans"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 10,
            width: "100%",
            padding: "17px 24px",
            background: "var(--color-ink)",
            color: "var(--color-paper)",
            border: "none",
            borderRadius: 100,
            fontSize: 15,
            fontWeight: 600,
            letterSpacing: "-0.012em",
            cursor: "pointer",
            transition: "all 0.2s ease",
          }}
        >
          사진 올리러 가기 →
        </button>
      </div>
    </div>
  );
}
