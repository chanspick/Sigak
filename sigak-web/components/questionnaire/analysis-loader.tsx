"use client";

// 분석 진행 상태 로더 컴포넌트
// 설문 제출 후 리포트 준비 상태를 폴링하여 표시

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { getReport, ApiError } from "@/lib/api/client";

type LoaderStatus = "analyzing" | "complete" | "error";

/** 상태별 표시 텍스트 */
const STATUS_TEXT: Record<LoaderStatus, string> = {
  analyzing: "AI가 분석 중입니다...",
  complete: "분석이 완료되었습니다!",
  error: "오류가 발생했습니다",
};

interface AnalysisLoaderProps {
  userId: string;
}

export function AnalysisLoader({ userId }: AnalysisLoaderProps) {
  const [status, setStatus] = useState<LoaderStatus>("analyzing");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const pollCountRef = useRef(0);

  const isComplete = status === "complete";

  /** 리포트 준비 여부 확인 */
  const checkReport = useCallback(async () => {
    try {
      const report = await getReport(userId);
      if (report && report.id) {
        setStatus("complete");
        return true; // 폴링 중지 신호
      }
    } catch (err) {
      // 404: 아직 리포트 미생성 -> 계속 폴링
      if (err instanceof ApiError && err.status === 404) {
        return false;
      }
      // 기타 에러: 일정 횟수까지는 계속 폴링
      pollCountRef.current += 1;
      if (pollCountRef.current >= 60) {
        // 5초 x 60 = 5분 초과 시 에러 처리
        setStatus("error");
        setErrorMessage("분석 시간이 초과되었습니다. 잠시 후 다시 확인해 주세요.");
        return true;
      }
    }
    return false;
  }, [userId]);

  /** 폴링 시작 */
  useEffect(() => {
    if (isComplete) return;
    if (status === "error") return;

    let isActive = true;

    const poll = async () => {
      if (!isActive) return;
      const done = await checkReport();
      if (done || !isActive) return;

      // 5초 후 다시 확인
      setTimeout(poll, 5000);
    };

    // 최초 2초 후 시작 (분석 시작 직후이므로 약간 대기)
    const initialTimer = setTimeout(poll, 2000);

    // 탭 비활성 시 폴링 중지
    const handleVisibility = () => {
      if (!document.hidden && isActive && status === "analyzing") {
        poll();
      }
    };
    document.addEventListener("visibilitychange", handleVisibility);

    return () => {
      isActive = false;
      clearTimeout(initialTimer);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [checkReport, isComplete, status]);

  return (
    <div className="text-center max-w-[400px]">
      {/* 로딩 스피너 (분석 중) */}
      {status === "analyzing" && (
        <div className="flex justify-center mb-6">
          <div className="w-10 h-10 border-2 border-black/10 border-t-[var(--color-fg)] rounded-full animate-spin" />
        </div>
      )}

      {/* 완료 체크 표시 */}
      {isComplete && (
        <div className="flex justify-center mb-6">
          <div className="w-10 h-10 flex items-center justify-center border-2 border-[var(--color-fg)] rounded-full">
            <span className="text-lg font-bold">V</span>
          </div>
        </div>
      )}

      {/* 상태 텍스트 */}
      <h1 className="font-[family-name:var(--font-serif)] text-[24px] font-normal mb-2">
        {STATUS_TEXT[status]}
      </h1>

      {/* 에러 메시지 */}
      {errorMessage && (
        <p className="text-[13px] opacity-60 text-red-600 mb-4">{errorMessage}</p>
      )}

      {/* 예상 소요시간 (분석 중일 때만) */}
      {status === "analyzing" && (
        <p className="text-[13px] opacity-40 mb-8">
          예상 소요시간: 1-2분
        </p>
      )}

      {/* 분석 완료 시 리포트 링크 */}
      {isComplete && (
        <Link
          href={`/report/${userId}`}
          className="inline-block mt-4 px-8 py-3 text-sm font-bold bg-[var(--color-fg)] text-[var(--color-bg)] transition-opacity duration-200 hover:opacity-85"
        >
          리포트 보기
        </Link>
      )}
    </div>
  );
}
