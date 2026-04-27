// SIGAK — /verdict/[id]
//
// v2 우선, v1 fallback 라우팅:
//   1. GET /api/v2/verdict/{id} 시도
//   2. 409 (v1 verdict) → GET /api/v1/verdicts/{id} 로 v1 ResultScreen 렌더
//   3. 404 / 403 → 에러 화면
//
// v2 ↔ v1 판별은 백엔드 응답으로. 프론트는 version 미고려.

"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { ApiError } from "@/lib/api/fetch";
import {
  deleteVerdict,
  getVerdict,
  getVerdictV2,
} from "@/lib/api/verdicts";
import { ResultScreen } from "@/components/sigak/result-screen";
import { VerdictV2Screen } from "@/components/sigak/verdict-v2-screen";
import { SigakLoading } from "@/components/ui/sigak";
import type { VerdictResponse } from "@/lib/types/mvp";
import type { VerdictV2GetResponse } from "@/lib/types/verdict_v2";

type Loaded =
  | { kind: "v2"; data: VerdictV2GetResponse }
  | { kind: "v1"; data: VerdictResponse };

export default function VerdictPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const verdictId = params.id;

  const [loaded, setLoaded] = useState<Loaded | null>(null);
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
    let cancelled = false;

    (async () => {
      // 1. v2 시도
      try {
        const v2 = await getVerdictV2(verdictId);
        if (!cancelled) setLoaded({ kind: "v2", data: v2 });
        return;
      } catch (e) {
        if (e instanceof ApiError && e.status === 409) {
          // v1 레거시 verdict — v1 fallback
        } else if (e instanceof ApiError && e.status === 404) {
          if (!cancelled) setError("판정을 찾을 수 없습니다.");
          return;
        } else if (e instanceof ApiError && e.status === 403) {
          if (!cancelled) setError("본인의 판정만 열람할 수 있습니다.");
          return;
        } else if (e instanceof ApiError && e.status === 401) {
          router.replace("/auth/login");
          return;
        } else {
          // 네트워크 / 기타 오류는 v1 fallback 시도
        }
      }

      // 2. v1 fallback
      try {
        const v1 = await getVerdict(verdictId);
        if (!cancelled) setLoaded({ kind: "v1", data: v1 });
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

  if (!loaded) {
    return <SigakLoading message="결과를 불러오는 중이에요" hint="잠시만 기다려 주세요" />;
  }

  if (loaded.kind === "v2") {
    return <VerdictV2Screen initial={loaded.data} />;
  }

  // v1 레거시
  let cachedReading = "";
  try {
    cachedReading =
      sessionStorage.getItem(`sigak_gold_reading:${verdictId}`) ?? "";
  } catch {
    // ignore
  }
  return (
    <ResultScreen
      verdict={loaded.data}
      goldReadingOverride={cachedReading}
      onDelete={loaded.data.is_owner ? handleDelete : undefined}
      deleting={deleting}
    />
  );
}
