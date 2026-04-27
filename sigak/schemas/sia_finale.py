"""Sia Finale 스키마 — SPEC-PI-FINALE-001.

PI 레포트 끝에 들어갈 Sia 페르소나 B 톤의 종합 마무리. 6 필드 JSON.
- headline: 50자 시그니처 한 줄
- lead_paragraph: 200~350자 핵심 단락 (OBSERVATION+INTERPRETATION 융합)
- step_1_observation: 150~250자 — 시각이 본 것 (좌표/타입 등 데이터 근거)
- step_2_interpretation: 150~250자 — 그게 의미하는 것 (재프레임/강점)
- step_3_diagnosis: 200~350자 — 추구 → 가는 길 (gap 핵심)
- step_4_closing: 100~200자 — 다음 한 걸음 (action_plan 1개로 매듭)

UI 매핑:
- Card 1 = headline + lead_paragraph
- Card 2 = step_1 ~ step_4
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# 본문 검증 — Sonnet 가 정확히 안 맞춰도 ±20% 흡수 (재시도 트리거 줄임)
class SiaFinale(BaseModel):
    """Sia Finale 6 필드 — Sonnet 1회 호출 결과."""

    headline: str = Field(..., min_length=8, max_length=70)
    lead_paragraph: str = Field(..., min_length=150, max_length=420)
    step_1_observation: str = Field(..., min_length=120, max_length=300)
    step_2_interpretation: str = Field(..., min_length=120, max_length=300)
    step_3_diagnosis: str = Field(..., min_length=150, max_length=420)
    step_4_closing: str = Field(..., min_length=80, max_length=250)
    # ISO datetime — 갱신 추적용 (Sonnet 응답엔 없음, 서버에서 첨부)
    generated_at: Optional[str] = None


class SiaFinalePreview(BaseModel):
    """`/api/v1/my/reports` 리스트 응답에 포함하는 경량 preview."""

    headline: str
    lead_paragraph_preview: str  # lead_paragraph 의 200자 truncate

    @classmethod
    def from_finale(cls, finale: dict) -> "SiaFinalePreview":
        lead = finale.get("lead_paragraph", "") or ""
        preview = lead[:200].rstrip()
        if len(lead) > 200:
            preview += "…"
        return cls(
            headline=finale.get("headline", "") or "",
            lead_paragraph_preview=preview,
        )
