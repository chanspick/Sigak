// SIGAK — Verdict 2.0 types (backend: sigak/schemas/verdict_v2.py).
//
// preview_content 는 무료 공개(결제 전), full_content 는 10 토큰 unlock 후 공개.
// cta_pi 는 PI 엔진 미완으로 백엔드에서 None 강제 주입 중 (services/verdict_v2.py).

export interface PreviewContent {
  /** ≤50자 훅 문구. */
  hook_line: string;
  /** 2-3문장 근거 요약 (결제 전 30% hook). */
  reason_summary: string;
}

export interface PhotoInsight {
  /** 업로드 사진 0-based 순번. */
  photo_index: number;
  /** 사진별 구조/배경/구도 해석. */
  insight: string;
  /** 사진별 개선 방향. */
  improvement: string;
}

export interface Recommendation {
  /** 전체 스타일 방향. */
  style_direction: string;
  /** 실행 가능한 다음 액션. */
  next_action: string;
  /** 방향 제시 이유. */
  why: string;
}

export interface VerdictNumbers {
  photo_count: number | null;
  dominant_tone: string | null;
  dominant_tone_pct: number | null;
  chroma_multiplier: number | null;
  /** "일치" | "부분 일치" | "상충" */
  alignment_with_profile: string | null;
}

export interface FullContent {
  /** 전체 판정 서사 (≤1500자). */
  verdict: string;
  photo_insights: PhotoInsight[];
  recommendation: Recommendation;
  numbers: VerdictNumbers;
  /** PI 엔진 미완으로 백엔드에서 None 주입. UI 무시. */
  cta_pi: null;
}

export interface VerdictV2CreateResponse {
  verdict_id: string;
  version: "v2";
  preview: PreviewContent;
  full_unlocked: boolean;
  photo_count: number;
}

export interface VerdictV2GetResponse {
  verdict_id: string;
  version: "v2";
  full_unlocked: boolean;
  preview: PreviewContent;
  /** full_unlocked=true 일 때만 채워짐. */
  full_content: FullContent | null;
}

export interface VerdictV2UnlockResponse {
  verdict_id: string;
  full_unlocked: boolean;
  full_content: FullContent;
  balance: number;
}
