// SIGAK MVP v1.2 — /verdict/[id]
//
// GET /api/v1/verdicts/{id} 로 verdict 조회 후 ResultScreen 렌더.
// 공유 링크 지원: 비로그인/타유저도 열람 가능. 백엔드가 is_owner=false 시
// GOLD + reading 만 내려주고, 프론트는 ResultScreen 내부에서 owner 전용 UI
// (kebab 삭제/진단 CTA 등)를 숨김.
"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { ApiError } from "@/lib/api/fetch";
import { deleteVerdict, getVerdict } from "@/lib/api/verdicts";
import { ResultScreen } from "@/components/sigak/result-screen";
import type { VerdictResponse } from "@/lib/types/mvp";

export default function VerdictPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const verdictId = params.id;

  const [verdict, setVerdict] = useState<VerdictResponse | null>(null);
  const [goldReading, setGoldReading] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  async function handleDelete() {
    if (!verdictId || deleting) return;
    if (typeof window !== "undefined") {
      const ok = window.confirm(
        "이 판정을 삭제하시겠어요?\n되돌릴 수 없습니다.",
      );
      if (!ok) return;
    }
    setDeleting(true);
    try {
      await deleteVerdict(verdictId);
      try {
        sessionStorage.removeItem(`sigak_gold_reading:${verdictId}`);
      } catch {
        // ignore
      }
      router.replace("/");
    } catch (e) {
      setDeleting(false);
      if (e instanceof ApiError && e.status === 401) {
        router.replace("/auth/login");
        return;
      }
      const msg =
        e instanceof ApiError && e.status === 403
          ? "본인의 판정만 삭제할 수 있습니다."
          : e instanceof ApiError && e.status === 404
            ? "이미 삭제된 판정입니다."
            : e instanceof Error
              ? e.message
              : "삭제 실패";
      if (typeof window !== "undefined") window.alert(msg);
    }
  }

  useEffect(() => {
    if (!verdictId) return;

    // sessionStorage에서 create 시점 gold_reading 읽기 (20260425 이전 레거시 fallback).
    // 신규 verdict는 백엔드 응답에 포함되므로 override 불필요.
    try {
      const cached = sessionStorage.getItem(`sigak_gold_reading:${verdictId}`);
      if (cached) setGoldReading(cached);
    } catch {
      // ignore
    }

    let cancelled = false;
    (async () => {
      try {
        const data = await getVerdict(verdictId);
        if (!cancelled) setVerdict(data);
      } catch (e) {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 404) {
          setError("판정을 찾을 수 없습니다.");
          return;
        }
        setError(e instanceof Error ? e.message : "판정 로드 실패");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [verdictId, router]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-paper">
        <div className="px-6 text-center">
          <p
            className="mb-4 font-sans"
            style={{
              fontSize: 13,
              color: "var(--color-danger)",
              letterSpacing: "-0.005em",
              lineHeight: 1.6,
            }}
            role="alert"
          >
            {error}
          </p>
          <button
            type="button"
            onClick={() => router.push("/")}
            className="font-sans font-medium text-ink underline underline-offset-2"
            style={{
              fontSize: 13,
              border: "none",
              background: "transparent",
              cursor: "pointer",
            }}
          >
            홈으로
          </button>
        </div>
      </div>
    );
  }

  if (!verdict) {
    return (
      <div className="min-h-screen bg-paper" aria-busy aria-label="로딩 중" />
    );
  }

  return (
    <ResultScreen
      verdict={verdict}
      goldReadingOverride={goldReading}
      onDelete={verdict.is_owner ? handleDelete : undefined}
      deleting={deleting}
    />
  );
}
