"use client";

// 시작 오버레이 - 티어 선택 + 이름/연락처 입력
// /start 페이지에서 사용

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { TIERS } from "@/lib/constants/tiers";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type { Tier } from "@/lib/types/tier";

/** 시작 오버레이 (티어 선택 + 기본 정보 입력) */
export function StartOverlay() {
  const router = useRouter();
  const [tier, setTier] = useState<Tier["id"] | null>(null);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const isValid = tier && name.trim().length > 0 && phone.trim().length > 0;

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!isValid) return;
      setSubmitting(true);
      // 유저 ID 생성 (mock)
      const userId = Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
      router.push(
        "/questionnaire?user_id=" + userId + "&tier=" + tier,
      );
    },
    [isValid, tier, router],
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
            {TIERS.map((t) => {
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

        {/* 기본 정보 입력 */}
        {tier && (
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

        {/* 제출 버튼 */}
        {tier && (
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
