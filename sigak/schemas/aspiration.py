"""추구미 분석 스키마 (Phase J1).

CLAUDE.md §3.5 / §3.6 / §5.4 / §5.5 정의.

상품:
  - 추구미 분석 IG (20 토큰)
  - 추구미 분석 Pinterest (20 토큰)

공통 구조:
  1. 대상 (IG 핸들 or Pinterest 보드 URL) 입력
  2. 공개 여부 + 블록리스트 체크
  3. Apify 수집 → Vision 분석 (Phase A 재사용)
  4. 본인 current_position ↔ 대상 좌표 gap
  5. 좌우 병치 사진 쌍 (3-5)
  6. Knowledge Base 매칭 (추구미 방향 트렌드/방법론)
  7. Sia 종합 메시지
  8. R2 저장 (본인 + 추구미 영구)
  9. vault 누적 (aspiration_history)
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from services.coordinate_system import GapVector, VisualCoordinate


TargetType = Literal["ig", "pinterest"]


class AspirationRequest(BaseModel):
    """라우트 입력 — IG/Pinterest 공통."""
    model_config = ConfigDict(extra="ignore")

    target_type: TargetType
    target_identifier: str     # IG 핸들 ("yuni") 또는 Pinterest URL


class PhotoPair(BaseModel):
    """좌우 병치 1 쌍 — 본인 vs 추구미."""
    model_config = ConfigDict(extra="ignore")

    user_photo_url: str
    user_sia_comment: str

    target_photo_url: str
    target_sia_comment: str

    pair_axis_hint: Optional[str] = None   # 예: "shape 차이 강조"


class AspirationAnalysis(BaseModel):
    """추구미 분석 결과 — aspiration_analyses.result_data JSONB 저장 shape."""
    model_config = ConfigDict(extra="ignore")

    analysis_id: str
    user_id: str
    target_type: TargetType
    target_identifier: str             # IG 핸들 or Pinterest board URL
    target_display_name: Optional[str] = None

    created_at: datetime

    # ── 좌표 분석
    user_coordinate: Optional[VisualCoordinate] = None
    target_coordinate: VisualCoordinate
    gap_vector: GapVector
    gap_narrative: str                 # GapVector.narrative() 결과 선 저장

    # ── 좌우 병치 (3~5 쌍)
    photo_pairs: list[PhotoPair] = Field(default_factory=list)

    # ── Sia 종합 메시지
    sia_overall_message: str

    # ── Knowledge Base 매칭
    matched_trend_ids: list[str] = Field(default_factory=list)
    # STEP 11 — 프론트 노출용 trend 객체 (읽기 시 KB 에서 hydrate, 저장 생략 가능)
    matched_trends: list["MatchedTrendView"] = Field(default_factory=list)

    # ── 디버그/추적용 raw
    target_analysis_snapshot: Optional[dict] = None   # IgFeedAnalysis dump
    images_captured_count: int = 0
    r2_target_dir: Optional[str] = None               # R2 저장 prefix


class MatchedTrendView(BaseModel):
    """STEP 11 — 프론트 노출용 트렌드 뷰. GET 시 KB 에서 hydrate."""
    model_config = ConfigDict(extra="ignore")

    trend_id: str
    title: str
    category: str                       # color_palette / silhouette / mood / styling_method 등
    detailed_guide: Optional[str] = None
    action_hints: list[str] = Field(default_factory=list)
    # 유저 좌표와의 매칭 정도 (없으면 None)
    score: Optional[float] = None


class BlocklistEntry(BaseModel):
    """aspiration_target_blocklist — 대상자 삭제 요청 후 재분석 차단."""
    model_config = ConfigDict(extra="ignore")

    target_type: TargetType
    target_identifier: str             # IG 핸들 or 보드 해시
    blocked_at: datetime
    reason: Optional[str] = None       # "owner_removal_request" / "admin" 등


class AspirationStartResponse(BaseModel):
    """분석 요청 성공 시 라우트 응답."""
    model_config = ConfigDict(extra="ignore")

    analysis_id: str
    status: Literal["completed", "failed_blocked", "failed_private", "failed_scrape"]
    analysis: Optional[AspirationAnalysis] = None
    token_balance: int
