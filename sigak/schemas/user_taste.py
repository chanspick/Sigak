"""UserTasteProfile — 6 상품 공유 유저 취향 통합 객체 (Phase G4).

CLAUDE.md §4.3 정의.

역할:
- 한 스냅샷에서 유저의 "현재 시각적 좌표 + 추구미 방향 + 증거 + 대화 시그널" 을
  표현. Phase I (PI) / J (추구미) / K (Best Shot) / L (Verdict 확장) 가 공통 소비.

컴포지션:
- UserDataVault.get_user_taste_profile() 에서 생성 (Phase G5 담당).
- 현 모듈은 schema 만 정의. 실 조립 로직은 vault 모듈에서.

strength_score (0.0 ~ 1.0):
- 0.0 = Day 1, IG 수집 전
- ~0.3 = IG Vision 분석 완료
- ~0.5 = Sia 대화 + IG Vision
- ~0.8 = 대화 + IG + 추구미 1회 or Best Shot 1회
- 1.0 = 풀 데이터 (대화 + IG + 추구미 2+ + Best Shot + 이달의 시각 2+)
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from services.coordinate_system import GapVector, VisualCoordinate


PhotoSource = Literal[
    "ig_feed",              # 유저 본인 IG 피드
    "aspiration_target",    # 추구미 대상 (IG/Pinterest)
    "best_shot_upload",     # Best Shot 업로드
    "pi_selected",          # 시각이 본 당신 선별 결과
]


class PhotoReference(BaseModel):
    """취향 증거로 참조 가능한 사진 레퍼런스. URL + 출처 + 좌표."""
    model_config = ConfigDict(extra="ignore")

    photo_id: str
    stored_url: str                 # R2 URL (영구 저장)
    source: PhotoSource
    captured_at: Optional[datetime] = None
    sia_comment: Optional[str] = None
    # 해당 사진에 대한 Vision 분석 좌표 (0-1). 있을 때만.
    coordinate: Optional[VisualCoordinate] = None


class ConversationSignals(BaseModel):
    """Sia 대화에서 수집된 시그널 — Haiku 통합 호출 JSON 의 누적 결과."""
    model_config = ConfigDict(extra="ignore")

    # 외적 수집 4필드 (페르소나 B — EXTRACTION 메시지 타입)
    body_shape: Optional[str] = None          # "상체 있음"|"하체 있음"|"중간"|"보통"
    current_concerns: Optional[str] = None     # 자유 텍스트
    specific_context: Optional[str] = None     # 상황/맥락
    trial_history: Optional[str] = None        # 시도 이력

    # 추구미 키워드 (대화 중 desired_image 추출)
    desired_image_keywords: list[str] = Field(default_factory=list)

    # agreement / pushback 카운트
    agreement_count: int = 0
    pushback_count: int = 0


class TrajectoryPoint(BaseModel):
    """시계열 좌표 포인트 — 이달의 시각 변화 추적용."""
    model_config = ConfigDict(extra="ignore")

    captured_at: datetime
    coordinate: VisualCoordinate
    source: Literal["conversation", "ig_feed", "aspiration", "best_shot", "pi"]
    reference_id: Optional[str] = None         # 해당 이벤트 id (재조회용)


class UserTasteProfile(BaseModel):
    """6 상품 공유 유저 취향 스냅샷.

    Vault.get_user_taste_profile() 가 생성. 생성 시점에 고정. 리포트 저장시
    그 시점 스냅샷을 함께 기록해서 "당시 분석 근거" 가 유지된다.
    """
    model_config = ConfigDict(extra="ignore")

    user_id: str
    snapshot_at: datetime

    # ── 현재 상태
    current_position: Optional[VisualCoordinate] = None
    aspiration_vector: Optional[GapVector] = None

    # ── 증거
    preference_evidence: list[PhotoReference] = Field(default_factory=list)
    conversation_signals: ConversationSignals = Field(default_factory=ConversationSignals)

    # ── 시계열
    trajectory: list[TrajectoryPoint] = Field(default_factory=list)

    # ── 리포트 재활용 (아이작 R2 원칙)
    user_original_phrases: list[str] = Field(default_factory=list)

    # ── 데이터 풍부도 (0.0~1.0). 상품별 UX 분기 (예: Best Shot 경고 < 0.3)
    strength_score: float = Field(ge=0.0, le=1.0, default=0.0)

    def snapshot_summary(self) -> str:
        """로그 / 디버그 용 1 줄 요약."""
        pos = (
            f"pos=({self.current_position.shape:.2f},"
            f"{self.current_position.volume:.2f},"
            f"{self.current_position.age:.2f})"
            if self.current_position else "pos=None"
        )
        return (
            f"UserTasteProfile(user={self.user_id}, {pos}, "
            f"strength={self.strength_score:.2f}, "
            f"evidence={len(self.preference_evidence)}, "
            f"trajectory={len(self.trajectory)})"
        )


# ─────────────────────────────────────────────
#  strength_score 산출 heuristic
# ─────────────────────────────────────────────

def compute_strength_score(
    *,
    has_ig_analysis: bool,
    conversation_field_count: int,    # ConversationSignals 에 채워진 필드 수 (0~5)
    aspiration_count: int,
    best_shot_count: int,
    monthly_report_count: int,
) -> float:
    """CLAUDE.md strength_score 정의 (0.0~1.0) 의 간단 heuristic.

    가중치 (합계 1.0):
      IG Vision 분석 있음             0.3
      대화 필드 수집 (최대 5 필드)      0.2
      추구미 분석 (최대 2회 이상)       0.2
      Best Shot (최대 1회)             0.15
      이달의 시각 (최대 2회 이상)       0.15
    """
    score = 0.0
    if has_ig_analysis:
        score += 0.30
    score += 0.20 * min(conversation_field_count, 5) / 5
    score += 0.20 * min(aspiration_count, 2) / 2
    score += 0.15 * min(best_shot_count, 1)
    score += 0.15 * min(monthly_report_count, 2) / 2
    return round(min(score, 1.0), 3)
