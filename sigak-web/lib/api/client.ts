// API 클라이언트 - 백엔드 FastAPI 통신
// 모든 엔드포인트는 NEXT_PUBLIC_API_URL 환경변수 기반

import type { ReportData } from "@/lib/types/report";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// API 에러 클래스
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// 공통 응답 처리
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `서버 오류 (${response.status})`;
    try {
      const body = await response.json();
      if (body.detail) message = body.detail;
      else if (body.message) message = body.message;
    } catch {
      // JSON 파싱 실패 시 기본 메시지 사용
    }
    throw new ApiError(response.status, message);
  }
  return response.json() as Promise<T>;
}

// --- 타입 정의 ---

export interface BookingRequest {
  name: string;
  phone: string;
  gender: string;
  tier: string;
  booking_date: string;
  booking_time: string;
}

export interface BookingResponse {
  user_id: string;
  status: string;
  price: number;
}

export interface InterviewResponse {
  status: string;
  interview_id: string;
}

export interface PhotoUploadResponse {
  status: string;
  faces_detected: number;
  primary_face_shape: string;
}

export interface AnalysisResponse {
  status: string;
  report_id: string;
  current_coords: Record<string, number>;
  aspiration_coords: Record<string, number>;
  gap_magnitude: number;
}

// --- API 함수 ---

/** 예약 생성 (POST /api/v1/booking) */
export async function createBooking(data: {
  name: string;
  phone: string;
  gender: string;
  tier: string;
}): Promise<BookingResponse> {
  // UI에서 날짜/시간을 수집하지 않으므로 기본값 사용 (셀프서비스 플로우)
  const today = new Date().toISOString().split("T")[0];
  const body: BookingRequest = {
    ...data,
    booking_date: today,
    booking_time: "00:00",
  };

  const response = await fetch(`${API_URL}/api/v1/booking`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  return handleResponse<BookingResponse>(response);
}

/** 설문 답변 제출 (POST /api/v1/interview/{userId}) */
export async function submitInterview(
  userId: string,
  answers: Record<string, string>,
): Promise<InterviewResponse> {
  const response = await fetch(`${API_URL}/api/v1/interview/${userId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(answers),
  });

  return handleResponse<InterviewResponse>(response);
}

/** 사진 업로드 (POST /api/v1/photos/{userId}) — multipart/form-data */
export async function uploadPhotos(
  userId: string,
  files: File[],
): Promise<PhotoUploadResponse> {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }

  const response = await fetch(`${API_URL}/api/v1/photos/${userId}`, {
    method: "POST",
    body: formData,
    // Content-Type은 브라우저가 자동 설정 (boundary 포함)
  });

  return handleResponse<PhotoUploadResponse>(response);
}

/** 분석 파이프라인 실행 (POST /api/v1/analyze/{userId}) */
export async function runAnalysis(
  userId: string,
): Promise<AnalysisResponse> {
  const response = await fetch(`${API_URL}/api/v1/analyze/${userId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });

  return handleResponse<AnalysisResponse>(response);
}

/** 리포트 조회 (GET /api/v1/report/{userId}) */
export async function getReport(userId: string): Promise<ReportData> {
  const response = await fetch(`${API_URL}/api/v1/report/${userId}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });

  return handleResponse<ReportData>(response);
}

/**
 * 리포트 조회 (서버 사이드용)
 * 서버 컴포넌트에서는 브라우저 API를 사용하지 않으므로 fetch 직접 사용
 */
export async function getReportServerSide(
  userId: string,
): Promise<ReportData | null> {
  try {
    const response = await fetch(`${API_URL}/api/v1/report/${userId}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      // 서버 사이드에서 캐시 방지
      cache: "no-store",
    });

    if (!response.ok) return null;
    return response.json() as Promise<ReportData>;
  } catch {
    return null;
  }
}
