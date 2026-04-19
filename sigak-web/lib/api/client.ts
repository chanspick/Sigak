// API 클라이언트 - 백엔드 FastAPI 통신
// 모든 엔드포인트는 NEXT_PUBLIC_API_URL 환경변수 기반

import type { ReportData } from "@/lib/types/report";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ngrok free 브라우저 경고 우회 헤더
const COMMON_HEADERS: Record<string, string> = {
  "ngrok-skip-browser-warning": "true",
};

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

/** 새 /submit 응답 */
export interface SubmitResponse {
  order_id: string;
  user_id: string;
  status: string;
  payment_info: {
    amount: number;
    bank: string;
    account: string;
    holder: string;
    toss_deeplink: string;
    kakao_deeplink: string;
  };
}

/** 주문 상태 */
export interface OrderStatus {
  order_id: string;
  status: "pending_payment" | "processing" | "completed" | "error";
  tier: string;
  amount: number;
  report_id?: string;
  report_url?: string;
}

// --- 인증 관련 타입 ---

export interface KakaoLoginUrlResponse {
  auth_url: string;
}

export interface KakaoTokenResponse {
  user_id: string;
  kakao_id: string;
  name: string;
  nickname: string;
  email: string;
  profile_image: string;
  reports: Array<{ id: string; access_level: string; created_at: string }>;
  /** MVP v1.1 phase B — HS256 JWT, 7일 만료. 빈 문자열이면 서버가 JWT_SECRET 미설정 */
  jwt: string;
}

export interface MeResponse {
  user_id: string;
  name: string;
  phone: string;
  kakao_id: string;
  reports: Array<{ id: string; access_level: string; created_at: string }>;
}

// --- 인증 API 함수 ---

/** 카카오 로그인 URL 가져오기 */
export async function getKakaoLoginUrl(): Promise<KakaoLoginUrlResponse> {
  const response = await fetch(`${API_URL}/api/v1/auth/kakao/login`, {
    headers: COMMON_HEADERS,
  });
  return handleResponse<KakaoLoginUrlResponse>(response);
}

/** 카카오 인증 코드로 토큰 교환 */
export async function exchangeKakaoToken(
  code: string,
): Promise<KakaoTokenResponse> {
  const response = await fetch(`${API_URL}/api/v1/auth/kakao/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...COMMON_HEADERS },
    body: JSON.stringify({ code }),
  });
  return handleResponse<KakaoTokenResponse>(response);
}

/** 현재 로그인된 유저 정보 */
export async function getMe(userId: string): Promise<MeResponse> {
  const response = await fetch(`${API_URL}/api/v1/auth/me?user_id=${userId}`, {
    headers: COMMON_HEADERS,
  });
  return handleResponse<MeResponse>(response);
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
    headers: { "Content-Type": "application/json", ...COMMON_HEADERS },
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
    headers: { ...COMMON_HEADERS },
    body: formData,
  });

  return handleResponse<PhotoUploadResponse>(response);
}

/** 분석 파이프라인 실행 (POST /api/v1/analyze/{userId}) */
export async function runAnalysis(
  userId: string,
): Promise<AnalysisResponse> {
  const response = await fetch(`${API_URL}/api/v1/analyze/${userId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...COMMON_HEADERS },
  });

  return handleResponse<AnalysisResponse>(response);
}

/** 리포트 조회 (GET /api/v1/report/{userId}) */
export async function getReport(userId: string): Promise<ReportData> {
  const response = await fetch(`${API_URL}/api/v1/report/${userId}`, {
    method: "GET",
    headers: { "Content-Type": "application/json", ...COMMON_HEADERS },
  });

  return handleResponse<ReportData>(response);
}

/** 통합 제출 — 사진+질문지 → order 생성 (POST /api/v1/submit) */
export async function submitAll(
  answers: Record<string, string>,
  files: File[],
): Promise<SubmitResponse> {
  const formData = new FormData();
  formData.append("data", JSON.stringify(answers));
  for (const file of files) {
    formData.append("files", file);
  }

  const response = await fetch(`${API_URL}/api/v1/submit`, {
    method: "POST",
    headers: { ...COMMON_HEADERS },
    body: formData,
  });

  return handleResponse<SubmitResponse>(response);
}

/** 주문 상태 조회 (GET /api/v1/order/{orderId}) */
export async function getOrderStatus(
  orderId: string,
): Promise<OrderStatus> {
  const response = await fetch(`${API_URL}/api/v1/order/${orderId}`, {
    method: "GET",
    headers: { ...COMMON_HEADERS },
  });

  return handleResponse<OrderStatus>(response);
}

/** 풀 업그레이드 요청 (POST /api/v1/upgrade-request/{reportId}) — 주문 생성 + 웹훅 */
export async function requestUpgrade(
  reportId: string,
): Promise<{ status: string; order_id?: string; report_id: string; payment_info?: { amount: number; bank: string; account: string; holder: string; toss_deeplink?: string; kakao_deeplink?: string } }> {
  const response = await fetch(`${API_URL}/api/v1/upgrade-request/${reportId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...COMMON_HEADERS },
  });

  return handleResponse(response);
}

/** 내 리포트 목록 조회 (GET /api/v1/my/reports?user_id=xxx) */
export async function getMyReports(
  userId: string,
): Promise<{ reports: Array<{ id: string; access_level: string; created_at: string; url: string }> }> {
  const response = await fetch(`${API_URL}/api/v1/my/reports?user_id=${userId}`, {
    headers: COMMON_HEADERS,
  });
  return handleResponse(response);
}

/** 캐스팅 풀 상태 조회 (GET /api/v1/casting/status?user_id=xxx) */
export async function getCastingStatus(
  userId: string,
): Promise<{ opted_in: boolean; opted_at: string | null }> {
  const response = await fetch(`${API_URL}/api/v1/casting/status?user_id=${userId}`, {
    headers: COMMON_HEADERS,
  });
  return handleResponse(response);
}

/** 캐스팅 풀 탈퇴 (POST /api/v1/casting/opt-out?user_id=xxx) */
export async function castingOptOut(userId: string): Promise<{ status: string }> {
  const response = await fetch(`${API_URL}/api/v1/casting/opt-out?user_id=${userId}`, {
    method: "POST",
    headers: COMMON_HEADERS,
  });
  return handleResponse(response);
}

/** 토스페이먼츠 결제 승인 요청 */
export async function confirmTossPayment(params: {
  paymentKey: string;
  orderId: string;
  amount: number;
}): Promise<{ status: string; order_id: string; report_id?: string; report_url?: string }> {
  const response = await fetch(`${API_URL}/api/v1/payments/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...COMMON_HEADERS },
    body: JSON.stringify({
      payment_key: params.paymentKey,
      order_id: params.orderId,
      amount: params.amount,
    }),
  });
  return handleResponse(response);
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
