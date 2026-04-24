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


class VerdictHistoryEntry(BaseModel):
    """피드 추천 1세션 요약 (unlock 시점)."""
    model_config = ConfigDict(extra="ignore")

    session_id: str
    created_at: Optional[datetime] = None
    photos_r2_urls: list[str] = Field(default_factory=list)
    photo_insights: list[dict[str, Any]] = Field(default_factory=list)
    recommendation: Optional[dict[str, Any]] = None


# ─────────────────────────────────────────────
#  Top-level container
# ─────────────────────────────────────────────

class UserHistory(BaseModel):
    """users.user_history JSONB 전체 구조. MVP 4 리스트."""
    model_config = ConfigDict(extra="ignore")

    conversations: list[ConversationHistoryEntry] = Field(default_factory=list)
    best_shot_sessions: list[BestShotHistoryEntry] = Field(default_factory=list)
    aspiration_analyses: list[AspirationHistoryEntry] = Field(default_factory=list)
    verdict_sessions: list[VerdictHistoryEntry] = Field(default_factory=list)
