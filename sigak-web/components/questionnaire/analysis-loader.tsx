"use client";

// 분석 진행 상태 로더 컴포넌트
// 설문 제출 후 AI 분석 상태를 폴링하여 표시

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { getQuestionnaireStatus } from "@/lib/api/questionnaire";
import type { QuestionnaireStatus } from "@/lib/types/questionnaire";

/** 상태별 표시 텍스트 */
const STATUS_TEXT: Record<QuestionnaireStatus, string> = {
  registered: "등록이 완료되었습니다. 잠시만 기다려주세요...",
  submitted: "제출이 완료되었습니다. 분석을 시작합니다...",
  analyzing: "AI가 분석 중입니다... 약 1-2분 소요됩니다",
  reported: "분석이 완료되었습니다!",
  feedback_done: "피드백이 완료되었습니다.",
};

interface AnalysisLoaderProps {
  userId: string;
}

export function AnalysisLoader({ userId }: AnalysisLoaderProps) {
  const [status, setStatus] = useState<QuestionnaireStatus>("submitted");
  const [reportId, setReportId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isComplete = status === "reported";

  /** 상태 조회 */
  const fetchStatus = useCallback(async () => {
    try {
      const result = await getQuestionnaireStatus(userId);
      setStatus(result.status);
      if (result.report_id) {
        setReportId(result.report_id);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "상태 조회 중 오류가 발생했습니다",
      );
    }
  }, [userId]);

  /** 폴링 시작 */
  useEffect(() => {
    // 초기 호출
    fetchStatus();

    // 완료 시 폴링 중지
    if (isComplete) return;

    const timer = setInterval(() => {
      fetchStatus();
    }, 3000);

    // 탭 비활성 시 폴링 중지
    const handleVisibility = () => {
      if (document.hidden) {
        clearInterval(timer);
      }
    };

    document.addEventListener("visibilitychange", handleVisibility);

    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [fetchStatus, isComplete]);

  return (
    <div className="text-center max-w-[400px]">
      {/* 로딩 스피너 (완료 시 숨김) */}
      {!isComplete && !error && (
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
        {error ? "오류가 발생했습니다" : STATUS_TEXT[status]}
      </h1>

      {/* 에러 메시지 */}
      {error && (
        <p className="text-[13px] opacity-60 text-red-600 mb-4">{error}</p>
      )}

      {/* 예상 소요시간 (분석 중일 때만) */}
      {!isComplete && !error && (
        <p className="text-[13px] opacity-40 mb-8">
          예상 소요시간: 1-2분
        </p>
      )}

      {/* 분석 완료 시 리포트 링크 */}
      {isComplete && reportId && (
        <Link
          href={`/report/${reportId}`}
          className="inline-block mt-4 px-8 py-3 text-sm font-bold bg-[var(--color-fg)] text-[var(--color-bg)] transition-opacity duration-200 hover:opacity-85"
        >
          리포트 보기
        </Link>
      )}
    </div>
  );
}
