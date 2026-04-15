"use client";

// 시작 오버레이 - 카카오 로그인 → 티어 선택(₩2.9K/₩29K) + 이름/연락처 입력

import { useState, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import { TIERS } from "@/lib/constants/tiers";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { createBooking, getKakaoLoginUrl, ApiError } from "@/lib/api/client";
import type { Tier } from "@/lib/types/tier";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Gender = "female" | "male";

export function StartOverlay() {
  const router = useRouter();
  const [tier, setTier] = useState<Tier["id"] | null>(null);
  const [gender, setGender] = useState<Gender | null>(null);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 카카오 로그인 상태
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loggedInUserId, setLoggedInUserId] = useState<string | null>(null);
  const [kakaoLoading, setKakaoLoading] = useState(false);

  // 이메일 로그인 상태 (심사용)
  const [testEmail, setTestEmail] = useState("");
  const [testPassword, setTestPassword] = useState("");
  const [emailLoading, setEmailLoading] = useState(false);

  // localStorage에서 로그인 상태 확인
  useEffect(() => {
    const userId = localStorage.getItem("sigak_user_id");
    const userName = localStorage.getItem("sigak_user_name");
    const userPhone = localStorage.getItem("sigak_user_phone");

    if (userId) {
      setIsLoggedIn(true);
      setLoggedInUserId(userId);
      if (userName) setName(userName);
      if (userPhone) setPhone(userPhone);
    }
  }, []);

  // 카카오 로그인 핸들러
  const handleKakaoLogin = useCallback(async () => {
    setKakaoLoading(true);
    setError(null);
    try {
      const { auth_url } = await getKakaoLoginUrl();
      window.location.href = auth_url;
    } catch (err) {
      setKakaoLoading(false);
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("카카오 로그인 연결에 실패했습니다. 잠시 후 다시 시도해 주세요.");
      }
    }
  }, []);

  // 이메일 로그인 핸들러 (심사용)
  const handleEmailLogin = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!testEmail || !testPassword) return;
    setEmailLoading(true);
    setError(null);
    try {
      const resp = await fetch(`${API_URL}/api/v1/auth/email-login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: testEmail, password: testPassword }),
      });
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw new Error(body.detail || "로그인 실패");
      }
      const result = await resp.json();
      localStorage.setItem("sigak_user_id", result.user_id);
      localStorage.setItem("sigak_user_name", result.name);
      if (result.email) localStorage.setItem("sigak_user_email", result.email);
      localStorage.setItem("sigak_kakao_id", result.kakao_id);
      if (result.reports && result.reports.length > 0) {
        const latest = result.reports[result.reports.length - 1];
        router.replace(`/report/${latest.id}`);
      } else {
        window.location.reload();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "로그인 실패");
      setEmailLoading(false);
    }
  }, [testEmail, testPassword, router]);

  // 전화번호 자동 포맷: 숫자만 추출 → 010-0000-0000
  const formatPhone = (raw: string) => {
    const digits = raw.replace(/\D/g, "").slice(0, 11);
    if (digits.length <= 3) return digits;
    if (digits.length <= 7) return `${digits.slice(0, 3)}-${digits.slice(3)}`;
    return `${digits.slice(0, 3)}-${digits.slice(3, 7)}-${digits.slice(7)}`;
  };
  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPhone(formatPhone(e.target.value));
  };

  // 유효성 검증
  const phoneDigits = phone.replace(/\D/g, "");
  const nameValid = name.trim().length >= 2;
  const phoneValid = phoneDigits.length >= 10 && phoneDigits.length <= 11 && phoneDigits.startsWith("01");
  const isValid = tier && gender && nameValid && phoneValid;

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!isValid || !tier || !gender) return;
      setSubmitting(true);
      setError(null);

      try {
        // 로그인된 유저는 booking 생략, 바로 설문으로 이동
        if (loggedInUserId) {
          router.push(
            `/questionnaire?user_id=${loggedInUserId}&tier=${tier}&gender=${gender}&name=${encodeURIComponent(name.trim())}&phone=${encodeURIComponent(phone.trim())}`,
          );
          return;
        }

        // 비로그인 유저는 기존 booking 플로우
        const result = await createBooking({
          name: name.trim(),
          phone: phone.trim(),
          gender,
          tier,
        });

        router.push(
          "/questionnaire?user_id=" + result.user_id + "&tier=" + tier + "&gender=" + gender + "&name=" + encodeURIComponent(name.trim()) + "&phone=" + encodeURIComponent(phone.trim()),
        );
      } catch (err) {
        setSubmitting(false);
        if (err instanceof ApiError) {
          setError(err.message);
        } else {
          setError("서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.");
        }
      }
    },
    [isValid, tier, gender, name, phone, router, loggedInUserId],
  );

  // 로그인 전: 카카오 로그인 화면
  if (!isLoggedIn) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg)] text-[var(--color-fg)] px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)]">
        <div className="w-full max-w-[480px] py-12">
          {/* 헤더 */}
          <h1 className="font-[family-name:var(--font-serif)] text-[28px] font-normal mb-2 text-center">
            시작하기
          </h1>
          <p className="text-[13px] opacity-40 text-center mb-10">
            카카오 계정으로 로그인하여 시작해 주세요
          </p>

          {/* 에러 메시지 */}
          {error && (
            <div className="mb-4 p-3 border border-red-300 bg-red-50 text-red-700 text-[13px]">
              {error}
            </div>
          )}

          {/* 카카오 로그인 버튼 */}
          <button
            onClick={handleKakaoLogin}
            disabled={kakaoLoading}
            className="flex items-center justify-center gap-2 w-full py-3.5 rounded-lg bg-[#FEE500] text-[#191919] text-sm font-semibold hover:brightness-95 transition-all disabled:opacity-60"
          >
            {kakaoLoading ? (
              <div className="w-4 h-4 border-2 border-[#191919] border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                <path
                  d="M9 1C4.582 1 1 3.79 1 7.207c0 2.21 1.47 4.152 3.684 5.248l-.937 3.467a.225.225 0 00.339.243l4.07-2.684c.276.025.557.04.844.04 4.418 0 8-2.79 8-6.314C17 3.79 13.418 1 9 1z"
                  fill="#191919"
                />
              </svg>
            )}
            {kakaoLoading ? "연결 중..." : "카카오로 시작하기"}
          </button>

          {/* 이메일 로그인 — 심사용 */}
          <form onSubmit={handleEmailLogin} className="mt-12 flex flex-col gap-2">
            <input
              type="email"
              value={testEmail}
              onChange={(e) => setTestEmail(e.target.value)}
              placeholder="email"
              className="w-full px-3 py-2 text-[11px] bg-transparent border border-black/[0.08] text-[var(--color-fg)] placeholder:text-black/20 focus:border-black/20 outline-none transition-all rounded"
            />
            <input
              type="password"
              value={testPassword}
              onChange={(e) => setTestPassword(e.target.value)}
              placeholder="password"
              className="w-full px-3 py-2 text-[11px] bg-transparent border border-black/[0.08] text-[var(--color-fg)] placeholder:text-black/20 focus:border-black/20 outline-none transition-all rounded"
            />
            <button
              type="submit"
              disabled={emailLoading || !testEmail || !testPassword}
              className="w-full py-2 text-[11px] bg-transparent text-black/20 hover:text-black/40 transition-all disabled:opacity-30"
            >
              {emailLoading ? "..." : "sign in"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  // 로그인 후: 티어 선택 + 기본 정보 입력 폼
  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg)] text-[var(--color-fg)] px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)]">
      <form onSubmit={handleSubmit} className="w-full max-w-[480px] py-12">
        {/* 헤더 */}
        <h1 className="font-[family-name:var(--font-serif)] text-[28px] font-normal mb-2 text-center">
          시작하기
        </h1>
        <p className="text-[13px] opacity-40 text-center mb-10">
          리포트 유형을 선택하고 기본 정보를 입력해 주세요
        </p>

        {/* 티어 선택 */}
        <div className="mb-8">
          <p className="text-[11px] font-semibold tracking-[1.5px] uppercase opacity-40 mb-3">
            리포트 선택
          </p>
          <div className="flex flex-col gap-2">
            {TIERS.map((t) => {
              const isActive = tier === t.id;
              return (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setTier(t.id)}
                  className={[
                    "w-full py-4 px-5 text-left border cursor-pointer transition-all duration-150 relative",
                    isActive
                      ? "border-[var(--color-fg)] bg-[var(--color-fg)] text-[var(--color-bg)]"
                      : "border-black/[0.12] bg-transparent hover:border-black/40",
                  ].join(" ")}
                >
                  {t.badge && (
                    <span className={[
                      "absolute top-2 right-3 text-[10px] font-bold tracking-[1px] uppercase px-2 py-0.5",
                      isActive ? "bg-[var(--color-bg)] text-[var(--color-fg)]" : "bg-[var(--color-fg)] text-[var(--color-bg)]",
                    ].join(" ")}>
                      {t.badge}
                    </span>
                  )}
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="block text-sm font-bold tracking-[0.5px]">
                        {t.name}
                      </span>
                      <span className={isActive ? "block text-[11px] mt-0.5 opacity-70" : "block text-[11px] mt-0.5 opacity-40"}>
                        {t.sub}
                      </span>
                    </div>
                    <span className="font-[family-name:var(--font-serif)] text-base font-normal">
                      {t.originalPrice && (
                        <span className="line-through opacity-30 mr-1.5 text-sm">
                          {"\u20A9"}{t.originalPrice.toLocaleString()}
                        </span>
                      )}
                      {"\u20A9"}{t.price.toLocaleString()}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* 성별 선택 */}
        {tier && (
          <div className="mb-8">
            <p className="text-[11px] font-semibold tracking-[1.5px] uppercase opacity-40 mb-3">
              성별
            </p>
            <div className="flex gap-2">
              {([
                { id: "female" as Gender, label: "여성" },
                { id: "male" as Gender, label: "남성 (준비중)", disabled: true },
              ]).map((g) => {
                const isActive = gender === g.id;
                return (
                  <button
                    key={g.id}
                    type="button"
                    onClick={() => !(g as any).disabled && setGender(g.id)}
                    disabled={(g as any).disabled}
                    className={[
                      "flex-1 py-3 text-center border transition-all duration-150 text-sm font-bold tracking-[0.5px]",
                      (g as any).disabled
                        ? "border-black/[0.06] opacity-30 cursor-not-allowed"
                        : isActive
                          ? "border-[var(--color-fg)] bg-[var(--color-fg)] text-[var(--color-bg)] cursor-pointer"
                          : "border-black/[0.12] bg-transparent hover:border-black/40 cursor-pointer",
                    ].join(" ")}
                  >
                    {g.label}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* 기본 정보 입력 */}
        {tier && gender && (
          <div className="mb-8 flex flex-col gap-4">
            <p className="text-[11px] font-semibold tracking-[1.5px] uppercase opacity-40 mb-1">
              기본 정보
            </p>
            <Input
              label="이름"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="홍길동"
              minLength={2}
              maxLength={20}
              error={name.length > 0 && !nameValid ? "이름을 2자 이상 입력해주세요" : undefined}
            />
            <Input
              label="연락처"
              required
              value={phone}
              onChange={handlePhoneChange}
              placeholder="010-0000-0000"
              type="tel"
              inputMode="numeric"
              error={phone.length > 0 && !phoneValid ? "휴대폰 번호 형식을 확인해주세요" : undefined}
            />
          </div>
        )}

        {/* 에러 메시지 */}
        {error && (
          <div className="mb-4 p-3 border border-red-300 bg-red-50 text-red-700 text-[13px]">
            {error}
          </div>
        )}

        {/* 제출 버튼 */}
        {tier && gender && (
          <Button type="submit" variant="primary" size="lg" className="w-full" disabled={!isValid || submitting}>
            {submitting ? "이동 중..." : "설문 시작하기"}
          </Button>
        )}
      </form>
    </div>
  );
}
