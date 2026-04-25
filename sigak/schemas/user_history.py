"""user_history JSONB — 4 기능 raw 누적 스키마.

users.user_history 컬럼 (JSONB DEFAULT '{}') 에 저장되는 구조.
각 기능 완료 시점에 해당 리스트 head 에 append. 최대 HISTORY_MAX_ENTRIES
(기본 10) 개 유지, 초과 시 tail pop.

LLM 주입용 요약본 (원본 테이블 유지). 사진은 R2 URL 만 저장.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


HISTORY_MAX_ENTRIES: int = 10

# 주입 시 토큰 상한. 초과 시 summarized 모드로 전환 (각 세션 첫+마지막 문장만).
INJECT_HISTORY_TOKEN_LIMIT: int = 80_000


# ─────────────────────────────────────────────
#  Sub-entries
# ─────────────────────────────────────────────

class HistoryMessage(BaseModel):
    """Sia 대화 메시지 1건. 원본 conversations.messages JSONB 스냅샷."""
    model_config = ConfigDict(extra="ignore")

    role: Literal["user", "assistant", "system"]
    content: str
    msg_type: Optional[str] = None  # Phase H 메시지 타입 (observation/interpretation/...)


class HistoryIgSnapshot(BaseModel):
    """Sia 세션 시점 IG 피드 스냅샷 (R2 URL 고정)."""
    model_config = ConfigDict(extra="ignore")

    r2_dir: str                        # "user_media/{user_id}/ig_snapshots/{ts}/"
    photo_r2_urls: list[str] = Field(default_factory=list)
    analysis: Optional[dict[str, Any]] = None   # Sonnet Vision IgFeedAnalysis JSON


class HistoryPhotoPair(BaseModel):
    """추구미 분석 좌우 병치 사진 쌍 (R2 URL 고정)."""
    model_config = ConfigDict(extra="ignore")

    user_photo_r2_url: str
    target_photo_r2_url: str
    pair_comment: Optional[str] = None


class HistorySelectedPhoto(BaseModel):
    """Best Shot 선별 A컷 1장 (R2 URL 고정)."""
    model_config = ConfigDict(extra="ignore")

    r2_url: str
    sonnet_rationale: Optional[str] = None
    sia_comment: Optional[str] = None


# ─────────────────────────────────────────────
#  Top-level entries (each: list head append)
# ─────────────────────────────────────────────

class ConversationHistoryEntry(BaseModel):
    """Sia 대화 1세션 요약."""
    model_config = ConfigDict(extra="ignore")

    session_id: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    messages: list[HistoryMessage] = Field(default_factory=list)
    ig_snapshot: Optional[HistoryIgSnapshot] = None


class BestShotHistoryEntry(BaseModel):
    """Best Shot 1세션 요약."""
    model_config = ConfigDict(extra="ignore")

    session_id: str
    created_at: Optional[datetime] = None
    uploaded_count: int = 0
    uploaded_r2_dir: Optional[str] = None
    selected: list[HistorySelectedPhoto] = Field(default_factory=list)
    overall_message: Optional[str] = None


class AspirationHistoryEntry(BaseModel):
    """추구미 분석 1건 요약 (IG / Pinterest 공통)."""
    model_config = ConfigDict(extra="ignore")

    analysis_id: str
    created_at: Optional[datetime] = None
    source: Literal["instagram", "pinterest"] = "instagram"
    target_handle: Optional[str] = None
    photo_pairs: list[HistoryPhotoPair] = Field(default_factory=list)
    gap_narrative: Optional[str] = None
    sia_overall_message: Optional[str] = None
    target_analysis_snapshot: Optional[dict[str, Any]] = None
    # Phase J5 — 분석 시점 gap_vector dump 보존 (좌표 메타, raw 아님).
    # 다음 분석 진입 시 "이전 갭 방향" 비교 가능. raw 격리 테스트 통과 필드.
    aspiration_vector_snapshot: Optional[dict[str, Any]] = None


class VerdictHistoryEntry(BaseModel):
    """피드 추천 1세션 요약 (unlock 시점)."""
    model_config = ConfigDict(extra="ignore")

    session_id: str
    created_at: Optional[datetime] = None
    photos_r2_urls: list[str] = Field(default_factory=list)
    photo_insights: list[dict[str, Any]] = Field(default_factory=list)
    recommendation: Optional[dict[str, Any]] = None


class PiHistoryEntry(BaseModel):
    """PI 1 리포트 unlock 시점 narrative 요약 — Phase I Backward echo 소스.

    Phase I PI 엔진이 unlock 후 vault append (services.user_history.append_history
    category="pi_history"). 4 기능 prompt 에서 read 해서 PI → Sia / Verdict v2 /
    Best Shot / Aspiration narrative 흘림.

    필드 = LLM 노출용 narrative summary. report_id 로 pi_reports 테이블 재조회 가능.
    raw 영역 (sonnet_raw / haiku_raw / clip_embedding) 은 R2 영구 보존, 본 entry 미포함.
    """
    model_config = ConfigDict(extra="ignore")

    report_id: str
    version: int = 1
    created_at: Optional[datetime] = None

    # Phase I 진단 결과 — Backward echo 핵심 필드
    matched_type: Optional[str] = None              # "Soft Fresh" 등 8 type 중 1
    cluster_label: Optional[str] = None             # 4 클러스터 keyword
    coord_3axis: Optional[dict[str, float]] = None  # {shape, volume, age}
    top_celeb_name: Optional[str] = None            # matched_celebs[0].name
    top_celeb_similarity: Optional[float] = None    # matched_celebs[0].similarity
    top_hair_name: Optional[str] = None             # hair_recommendation.top_hairs[0]
    top_action_text: Optional[str] = None           # action_plan.actions[0]


class TrajectoryEvent(BaseModel):
    """5 기능 진입 시점 시계열 이벤트 1건.

    append_history() 가 5 카테고리 추가 시 자동으로 동시 누적.
    UserDataVault.get_user_taste_profile() 의 trajectory[] 소스.
    coordinate_snapshot 은 좌표 산출 가능 시점만 채움 (현재는 aspiration / pi).
    """
    model_config = ConfigDict(extra="ignore")

    captured_at: datetime
    event_type: Literal["conversation", "verdict", "best_shot", "aspiration", "pi"]
    reference_id: str
    coordinate_snapshot: Optional[dict[str, float]] = None  # {shape, volume, age}
    score_at_time: Optional[float] = None


# ─────────────────────────────────────────────
#  Top-level container
# ─────────────────────────────────────────────

class UserHistory(BaseModel):
    """users.user_history JSONB 전체 구조. 5 카테고리 + trajectory_events."""
    model_config = ConfigDict(extra="ignore")

    conversations: list[ConversationHistoryEntry] = Field(default_factory=list)
    best_shot_sessions: list[BestShotHistoryEntry] = Field(default_factory=list)
    aspiration_analyses: list[AspirationHistoryEntry] = Field(default_factory=list)
    verdict_sessions: list[VerdictHistoryEntry] = Field(default_factory=list)
    # Phase I — PI 결과 narrative 누적 (Backward echo 소스). routes/pi.py:unlock 후 append.
    pi_history: list[PiHistoryEntry] = Field(default_factory=list)
    # trajectory[] populate — append_history() 가 5 카테고리 추가 시 동시 누적.
    # 통합 시계열 (모든 5 기능). max = HISTORY_MAX_ENTRIES * 5 (50 기본).
    trajectory_events: list[TrajectoryEvent] = Field(default_factory=list)
