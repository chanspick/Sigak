// Best Shot 타입 — 백엔드 schemas/best_shot.py 동기화 (Phase K).
//
// 백엔드 소스:
//   - schemas/best_shot.py (Pydantic)
//   - routes/best_shot.py (엔드포인트)
//   - CLAUDE.md §3.4 / §5.3

export type BestShotStatus =
  | "uploading"
  | "ready_to_run"
  | "running"
  | "ready"
  | "failed"
  | "aborted";

export type PhotoCategoryBestShot = "best_shot_selected";

export interface SelectedPhoto {
  photo_id: string;
  stored_url: string;
  rank: number;
  quality_score: number;         // 0-1
  profile_match_score: number;   // 0-1
  trend_match_score: number;     // 0-1
  sia_comment: string;
  associated_trend_id: string | null;
}

export interface BestShotResult {
  selected_photos: SelectedPhoto[];
  sia_overall_message: string;
  matched_trend_ids: string[];
  heuristic_survived_count: number;
  heuristic_cutoff: number;
  sonnet_selected_count: number;
  target_count: number;
  max_count: number;
}

export interface BestShotSession {
  session_id: string;
  user_id: string;
  status: BestShotStatus;
  uploaded_count: number;
  target_count: number;
  max_count: number;
  strength_score_snapshot: number;
  strength_warning_acknowledged: boolean;
  result: BestShotResult | null;
  failure_reason: string | null;
  created_at: string;    // ISO
  updated_at: string;
}

// ── Request / Response

export interface BestShotInitRequest {
  expected_count: number;               // 50-500
  acknowledge_strength_warning?: boolean;
}

export interface BestShotInitResponse {
  session_id: string;
  status: BestShotStatus;
  target_count: number;
  max_count: number;
  strength_score: number;
  strength_warning_required: boolean;
  upload_limit: number;
  upload_minimum: number;
}

export interface BestShotUploadAck {
  session_id: string;
  status: BestShotStatus;
  uploaded_count: number;
  remaining_to_upload: number;
}

export interface BestShotRunResponse {
  session_id: string;
  status: BestShotStatus;
  result: BestShotResult | null;
  token_balance: number;
  failure_reason: string | null;
}

/** 400 응답 — 50장 미만 업로드 시도 (피드 추천 유도). */
export interface TooFewPhotosError {
  code: "too_few_photos";
  message: string;
  suggestion: string;
  redirect: string;                     // "/verdict/new"
}

/** 409 응답 — strength < 0.3 경고 필요. 프론트가 모달 후 acknowledge_strength_warning=true 재요청. */
export interface StrengthLowWarning {
  code: "strength_low";
  message: string;
  strength_score: number;
  suggestion: string;
  acknowledge_required: true;
}
