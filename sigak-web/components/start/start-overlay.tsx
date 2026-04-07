"use client";

// 시작 오버레이 - 티어 선택 + 이름/연락처 입력
// /start 페이지에서 사용

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { TIERS } from "@/lib/constants/tiers";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { createBooking, ApiError } from "@/lib/api/client";
import type { Tier } from "@/lib/types/tier";

/** 시작 오버레이 (티어 선택 + 기본 정보 입력) */
type Gender = "female" | "male";

export function StartOverlay() {
  const router = useRouter();
  const [tier, setTier] = useState<Tier["id"] | null>(null);
  const [gender, setGender] = useState<Gender | null>(null);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isValid = tier && gender && name.trim().length > 0 && phone.trim().length > 0;

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!isValid || !tier || !gender) return;
      setSubmitting(true);
      setError(null);

      try {
        // 백엔드 API로 예약 생성
        const result = await createBooking({
          name: name.trim(),
          phone: phone.trim(),
          gender,
          tier,
        });

        router.push(
          "/questionnaire?user_id=" + result.user_id + "&tier=" + tier + "&gender=" + gender,
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
    [isValid, tier, gender, name, phone, router],
  );

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg)] text-[var(--color-fg)] px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)]">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-[480px] py-12"
      >
        {/* 헤더 */}
        <h1 className="font-[family-name:var(--font-serif)] text-[28px] font-normal mb-2 text-center">
          시작하기
        </h1>
        <p className="text-[13px] opacity-40 text-center mb-10">
          진단 유형을 선택하고 기본 정보를 입력해 주세요
        </p>

        {/* 티어 선택 */}
        <div className="mb-8">
          <p className="text-[11px] font-semibold tracking-[1.5px] uppercase opacity-40 mb-3">
            진단 선택
          </p>
          <div className="flex flex-col gap-2">
            {TIERS.filter((t) => t.id === "basic").map((t) => {
              const isActive = tier === t.id;
              return (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setTier(t.id)}
                  className={
                    isActive
                      ? "w-full py-4 px-5 text-left border cursor-pointer transition-all duration-150 border-[var(--color-fg)] bg-[var(--color-fg)] text-[var(--color-bg)]"
                      : "w-full py-4 px-5 text-left border cursor-pointer transition-all duration-150 border-black/[0.12] bg-transparent hover:border-black/40"
                  }
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="block text-sm font-bold tracking-[0.5px]">
                        {t.name}
                      </span>
                      <span
                        className={
                          isActive
                            ? "block text-[11px] mt-0.5 opacity-70"
                            : "block text-[11px] mt-0.5 opacity-40"
                        }
                      >
                        {t.sub}
                      </span>
                    </div>
                    <span className="font-[family-name:var(--font-serif)] text-base font-normal">
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
                { id: "male" as Gender, label: "남성" },
              ]).map((g) => {
                const isActive = gender === g.id;
                return (
                  <button
                    key={g.id}
                    type="button"
                    onClick={() => setGender(g.id)}
                    className={
                      isActive
                        ? "flex-1 py-3 text-center border cursor-pointer transition-all duration-150 border-[var(--color-fg)] bg-[var(--color-fg)] text-[var(--color-bg)] text-sm font-bold tracking-[0.5px]"
                        : "flex-1 py-3 text-center border cursor-pointer transition-all duration-150 border-black/[0.12] bg-transparent hover:border-black/40 text-sm font-bold tracking-[0.5px]"
                    }
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
            />
            <Input
              label="연락처"
              required
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="010-0000-0000"
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
          <Button
            type="submit"
            variant="primary"
            size="lg"
            className="w-full"
            disabled={!isValid || submitting}
          >
            {submitting ? "이동 중..." : "설문 시작하기"}
          </Button>
        )}
      </form>
    </div>
  );
}
