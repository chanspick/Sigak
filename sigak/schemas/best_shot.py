"""Best Shot 스키마 (Phase K1).

CLAUDE.md §3.4 / §5.3 + 본인 확정 스펙:
  - 최소 50장, 최대 500장 업로드
  - 30 토큰 (₩3,000)
  - target_count = uploaded // 15
  - max_count    = uploaded // 10
  - 1차 heuristic 필터 (uploaded → max * 3 축소)
  - 2차 Sonnet Vision 정밀 선별 (target 최소, max 최대)
  - strength_score < 0.3 시 경고 모달 + 진행 선택
  - 원본 24h TTL, 선별 결과 30일 보관

상품 범위 안내:
  3-10장 → 피드 추천 (Verdict v2, 10토큰)
  50+장 → Best Shot (30토큰)
  10-50장 중간 구간은 피드 추천 반복 이용으로 안내.

Session 상태 머신:
  uploading     → 업로드 진행 중 (resume 가능)
  ready_to_run  → 업로드 완료, run 대기 (토큰 차감 전)
  running       → 엔진 실행 중 (heuristic+Sonnet)
  ready         → 선별 완료 (유저 열람 가능)
  failed        → 엔진 실패 (refund 수행됨)
  aborted       → 유저 취소 (원본 삭제됨)
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


BestShotStatus = Literal[
    "uploading", "ready_to_run", "running", "ready", "failed", "aborted",
]


class SelectedPhoto(BaseModel):
    """선별된 한 장 — 리포트 렌더링 단위."""
    model_config = ConfigDict(extra="ignore")

    photo_id: str
    stored_url: str                          # R2 (24h TTL 해제 후 30일 보관)
    rank: int                                # 1 이 최고
    quality_score: float = Field(ge=0.0, le=1.0)    # heuristic 점수
    profile_match_score: float = Field(ge=0.0, le=1.0)  # Sonnet 판정
    trend_match_score: float = Field(ge=0.0, le=1.0)    # Knowledge Base
    sia_comment: str
    associated_trend_id: Optional[str] = None


class BestShotResult(BaseModel):
    """run 완료 후 세션에 저장되는 선별 결과 JSONB."""
    model_config = ConfigDict(extra="ignore")

    selected_photos: list[SelectedPhoto] = Field(default_factory=list)
    sia_overall_message: str
    matched_trend_ids: list[str] = Field(default_factory=list)

    # 엔진 집계 통계
    heuristic_survived_count: int = 0         # 1차 필터 통과한 장 수
    heuristic_cutoff: float = 0.0
    sonnet_selected_count: int = 0            # 실제 최종 선별 수
    target_count: int = 0                     # uploaded // 15
    max_count: int = 0                        # uploaded // 10


class BestShotSession(BaseModel):
    """best_shot_sessions DB row 도메인 모델."""
    model_config = ConfigDict(extra="ignore")

    session_id: str
    user_id: str
    status: BestShotStatus

    uploaded_count: int = 0
    target_count: int = 0
    max_count: int = 0

    strength_score_snapshot: float = Field(ge=0.0, le=1.0, default=0.0)
    strength_warning_acknowledged: bool = False

    result: Optional[BestShotResult] = None
    failure_reason: Optional[str] = None

    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────
#  Request / Response schemas
# ─────────────────────────────────────────────

class InitRequest(BaseModel):
    """POST /api/v2/best-shot/init — 업로드 세션 시작."""
    model_config = ConfigDict(extra="ignore")

    expected_count: int = Field(ge=50, le=500)
    acknowledge_strength_warning: bool = False


class InitResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    session_id: str
    status: BestShotStatus
    target_count: int
    max_count: int
    strength_score: float
    strength_warning_required: bool          # True 면 프론트가 모달 띄우고 acknowledge 재요청
    upload_limit: int = 500
    upload_minimum: int = 50


class UploadAck(BaseModel):
    """POST /api/v2/best-shot/upload/{session_id} — 단일 청크 업로드 결과."""
    model_config = ConfigDict(extra="ignore")

    session_id: str
    status: BestShotStatus
    uploaded_count: int
    remaining_to_upload: int


class RunResponse(BaseModel):
    """POST /api/v2/best-shot/run/{session_id} — 선별 실행 결과."""
    model_config = ConfigDict(extra="ignore")

    session_id: str
    status: BestShotStatus
    result: Optional[BestShotResult] = None
    token_balance: int
    failure_reason: Optional[str] = None


class GetSessionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    session: BestShotSession
