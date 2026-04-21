// SIGAK MVP v1.2 — /verdict/[id]
//
// GET /api/v1/verdicts/{id} 로 verdict 조회 후 ResultScreen 렌더.
// gold_reading은 재조회 시 빈 문자열로 오므로, create 시점에 저장한
// sessionStorage 값을 override로 전달 (같은 브라우저 세션 내에서만 보장).
"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { ApiError } from "@/lib/api/fetch";
import { deleteVerdict, getVerdict } from "@/lib/api/verdicts";
import { ResultScreen } from "@/components/sigak/result-screen";
import type { VerdictResponse } from "@/lib/types/mvp";
import { getToken } from "@/lib/auth";

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
    const token = getToken();
    if (!token) {
      router.replace("/auth/login");
      return;
    }
    if (!verdictId) return;

    // sessionStorage에서 create 시점 gold_reading 읽기
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
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/auth/login");
          return;
        }
        if (e instanceof ApiError && e.status === 404) {
          setError("판정을 찾을 수 없습니다.");
          return;
        }
        if (e instanceof ApiError && e.status === 403) {
          setError("본인의 판정만 열람할 수 있습니다.");
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
    <>
      <ResultScreen verdict={verdict} goldReadingOverride={goldReading} />
      <div
        style={{
          padding: "24px 28px 40px",
          textAlign: "center",
          background: "var(--color-paper)",
        }}
      >
        <button
          type="button"
          onClick={handleDelete}
          disabled={deleting}
          className="font-sans"
          style={{
            fontSize: 11,
            opacity: deleting ? 0.2 : 0.4,
            color: "var(--color-ink)",
            background: "transparent",
            border: "none",
            padding: 4,
            textDecoration: "underline",
            textUnderlineOffset: 3,
            cursor: deleting ? "default" : "pointer",
            letterSpacing: "-0.005em",
          }}
        >
          {deleting ? "삭제 중..." : "삭제"}
        </button>
      </div>
    </>
  );
}
