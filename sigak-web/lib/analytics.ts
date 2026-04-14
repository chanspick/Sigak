// SIGAK 커스텀 이벤트 트래킹
// PostHog capture 래퍼 — posthog-js 없어도 안전하게 동작

import posthog from "posthog-js";

function capture(event: string, properties?: Record<string, unknown>) {
  if (typeof window === "undefined") return;
  try {
    posthog.capture(event, properties);
  } catch {
    // PostHog 미초기화 시 무시
  }
}

// 유저 식별 (카카오 로그인 후)
export function identifyUser(userId: string, properties?: Record<string, unknown>) {
  try {
    posthog.identify(userId, properties);
  } catch {
    // 무시
  }
}

// ── 퍼널 이벤트 ──

// 홈 → 시작
export function trackStartClick() {
  capture("start_click");
}

// 설문 시작
export function trackQuestionnaireStart(tier: string) {
  capture("questionnaire_start", { tier });
}

// 설문 완료 + 주문 생성
export function trackOrderCreated(orderId: string, tier: string, amount: number) {
  capture("order_created", { order_id: orderId, tier, amount });
}

// 리포트 조회
export function trackReportViewed(reportId: string, accessLevel: string) {
  capture("report_viewed", { report_id: reportId, access_level: accessLevel });
}

// 풀 업그레이드 요청
export function trackUpgradeRequested(reportId: string) {
  capture("upgrade_requested", { report_id: reportId });
}

// ── 캐스팅 이벤트 ──

export function trackCastingOptIn() {
  capture("casting_opt_in");
}

export function trackCastingOptOut() {
  capture("casting_opt_out");
}

// ── 공유 이벤트 ──

export function trackShareClick(method: string, reportId: string) {
  capture("share_click", { method, report_id: reportId });
}

// ── 카카오 로그인 ──

export function trackKakaoLogin(isNewUser: boolean) {
  capture("kakao_login", { is_new_user: isNewUser });
}
