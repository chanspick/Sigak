"""GOLD reading generator — short 2-sentence verdict caption (MVP v1.2).

WIRING ONLY. Founder owns the actual prompt. Current implementation returns
a deterministic placeholder so the verdict endpoint returns a non-empty
``gold_reading`` field. When the real prompt is ready, replace the body of
``generate_gold_reading`` with an Anthropic API call using the inputs
documented below.

Expected inputs (already gathered by the caller):
  - winner_photo_coords: {shape, volume, age} of the top-ranked photo
  - chugumi_target:      target coords from interview_interpretation
  - reference_base:      SIGAK 8-type anchor label, e.g. "따뜻한 첫사랑"
  - tone guide:          warm editorial, 2 Korean sentences, no hedging

NOT cached — short, cheap, and the wording should feel fresh per verdict.
"""
from typing import Optional


PLACEHOLDER_READINGS = [
    "구도와 표정의 균형이 좋아요. 내추럴에 잘 맞고요.",
    "눈빛이 자연스럽고 얼굴선이 살아나요. 오늘 가장 당신다운 한 장이에요.",
    "윤곽과 분위기가 조화로워요. 원하는 방향에 가까운 인상이에요.",
]


def generate_gold_reading(
    winner_photo_coords: dict,
    chugumi_target: dict,
    reference_base: Optional[str] = None,
) -> str:
    """Return 2 Korean sentences about the winning photo.

    TODO(founder): Replace with real Anthropic call. Keep 2-sentence budget.
    Recommended: short system prompt + few-shot examples, max_tokens ~200.
    """
    # Cheap deterministic rotation so consecutive verdicts don't always return
    # the same string — purely for UX texture, not semantic correctness.
    # Real impl will base this on target vs photo delta.
    _ = (winner_photo_coords, chugumi_target, reference_base)  # unused in placeholder
    key = sum(
        int(abs(v) * 100)
        for v in (winner_photo_coords or {}).values()
        if isinstance(v, (int, float))
    )
    return PLACEHOLDER_READINGS[key % len(PLACEHOLDER_READINGS)]
