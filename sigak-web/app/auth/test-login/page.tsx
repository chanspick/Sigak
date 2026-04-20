// SIGAK — /auth/test-login
//
// Toss PG 심사용 임시 로그인 화면. email/password 입력 → 백엔드
// POST /api/v1/auth/test-login → JWT 저장 → 피드로.
//
// PG 승인 후:
//   1. Railway env에 TEST_LOGIN_ENABLED=false 추가 (엔드포인트 404)
//   2. 이 파일 + backend 해당 블록 삭제
"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";

import { setAuthData } from "@/lib/auth";
import { TopBar } from "@/components/ui/sigak";
import { SiteFooter } from "@/components/sigak/site-footer";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface TestLoginResponse {
  jwt: string;
  user_id: string;
  name: string;
  email: string;
}

export default function TestLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/auth/test-login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "ngrok-skip-browser-warning": "true",
        },
        body: JSON.stringify({ email, password }),
      });
      if (res.status === 404) {
        throw new Error("테스트 로그인이 비활성화되어 있습니다.");
      }
      if (res.status === 401) {
        throw new Error("이메일 또는 비밀번호가 일치하지 않습니다.");
      }
      if (!res.ok) {
        throw new Error(`서버 오류 (${res.status})`);
      }
      const data = (await res.json()) as TestLoginResponse;
      setAuthData({
        jwt: data.jwt,
        userId: data.user_id,
        name: data.name,
        email: data.email,
      });
      router.replace("/");
    } catch (e) {
      setBusy(false);
      setError(e instanceof Error ? e.message : "로그인 실패");
    }
  }

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

      <main style={{ flex: 1, padding: "48px 28px 24px" }}>
        <h1
          className="font-serif"
          style={{
            fontSize: 28,
            fontWeight: 400,
            lineHeight: 1.3,
            letterSpacing: "-0.01em",
            margin: 0,
            color: "var(--color-ink)",
          }}
        >
          결제 테스트 로그인.
        </h1>
        <p
          className="font-sans"
          style={{
            marginTop: 14,
            fontSize: 13,
            opacity: 0.55,
            lineHeight: 1.7,
            color: "var(--color-ink)",
            letterSpacing: "-0.005em",
          }}
        >
          Toss PG 심사용 임시 계정.
          <br />
          일반 이용자는 홈 화면에서 카카오로 로그인하세요.
        </p>

        <form onSubmit={handleSubmit} style={{ marginTop: 32 }}>
          <label
            className="font-sans uppercase"
            style={{
              display: "block",
              fontSize: 10,
              fontWeight: 600,
              letterSpacing: "1.5px",
              opacity: 0.5,
              marginBottom: 8,
              color: "var(--color-ink)",
            }}
          >
            이메일
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            className="font-sans"
            style={{
              width: "100%",
              padding: "12px 14px",
              fontSize: 14,
              letterSpacing: "-0.005em",
              border: "1px solid rgba(0, 0, 0, 0.15)",
              borderRadius: 0,
              background: "transparent",
              color: "var(--color-ink)",
              outline: "none",
            }}
          />

          <label
            className="font-sans uppercase"
            style={{
              display: "block",
              fontSize: 10,
              fontWeight: 600,
              letterSpacing: "1.5px",
              opacity: 0.5,
              marginTop: 20,
              marginBottom: 8,
              color: "var(--color-ink)",
            }}
          >
            비밀번호
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
            className="font-sans"
            style={{
              width: "100%",
              padding: "12px 14px",
              fontSize: 14,
              letterSpacing: "-0.005em",
              border: "1px solid rgba(0, 0, 0, 0.15)",
              borderRadius: 0,
              background: "transparent",
              color: "var(--color-ink)",
              outline: "none",
            }}
          />

          {error && (
            <p
              className="font-sans"
              role="alert"
              style={{
                marginTop: 16,
                fontSize: 12,
                color: "var(--color-danger)",
                letterSpacing: "-0.005em",
              }}
            >
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={busy || !email || !password}
            className="font-sans"
            style={{
              marginTop: 28,
              width: "100%",
              height: 54,
              background: busy ? "transparent" : "var(--color-ink)",
              color: busy ? "var(--color-ink)" : "var(--color-paper)",
              border: busy ? "1px solid rgba(0, 0, 0, 0.15)" : "none",
              borderRadius: 0,
              fontSize: 14,
              fontWeight: 600,
              letterSpacing: "0.5px",
              cursor: busy || !email || !password ? "default" : "pointer",
              opacity: busy || !email || !password ? 0.5 : 1,
            }}
          >
            {busy ? "로그인 중..." : "로그인"}
          </button>
        </form>

        <p
          className="font-sans"
          style={{
            marginTop: 32,
            fontSize: 11,
            lineHeight: 1.7,
            opacity: 0.4,
            letterSpacing: "-0.005em",
            color: "var(--color-ink)",
          }}
        >
          일반 이용자용 로그인은{" "}
          <Link href="/" style={{ textDecoration: "underline", textUnderlineOffset: 2 }}>
            홈
          </Link>
          에서 카카오로 진행하세요.
        </p>
      </main>

      <SiteFooter />
    </div>
  );
}
