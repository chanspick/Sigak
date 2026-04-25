"""Action Plan 어댑터 — Phase I PI-C.

services.pi_methodology.ActionMethodologyEntry → ActionItem (axis 룰 기반).
KbMatchResult.mood / styling_method 의 action_hints → 보강 ActionItem.
vault_phrases echo 매칭으로 자연스러운 연결.

순수 함수.
"""
from __future__ import annotations

from typing import Optional

from schemas.pi_report import ActionItem, ActionPlanContent
from services.pi_methodology import ActionMethodologyEntry


_DESCRIPTION_MAX_CHARS = 120


def build_action_plan(
    action_methodology: Optional[list[ActionMethodologyEntry]] = None,
    mood_trends: Optional[list] = None,
    styling_trends: Optional[list] = None,
    vault_phrases: Optional[list[str]] = None,
    *,
    limit: int = 5,
) -> ActionPlanContent:
    """axis 룰 + KB hints + vault echo → ActionPlanContent.

    우선순위:
      1. axis 룰 (ActionMethodologyEntry) — 좌표 기반 보정 액션 우선.
      2. mood / styling 트렌드 action_hints — 빈자리 채움.
    """
    safe_phrases = [p for p in (vault_phrases or []) if isinstance(p, str) and p.strip()]

    actions: list[ActionItem] = []
    seen_titles: set[str] = set()

    for entry in (action_methodology or []):
        title = (entry.title or entry.method or entry.zone or "").strip()
        if not title or title in seen_titles:
            continue
        description = entry.description or ""
        if len(description) > _DESCRIPTION_MAX_CHARS:
            description = description[: _DESCRIPTION_MAX_CHARS - 1].rstrip() + "…"
        actions.append(
            ActionItem(
                title=title,
                description=description,
                source=entry.source or "",
                vault_echo=_match_phrase(f"{title} {entry.method} {entry.zone}", safe_phrases),
            )
        )
        seen_titles.add(title)
        if len(actions) >= limit:
            break

    if len(actions) < limit:
        for matched in (mood_trends or []) + (styling_trends or []):
            try:
                hints = list(matched.trend.action_hints or [])
                trend_id = matched.trend.trend_id
                trend_title = matched.trend.title or trend_id
            except AttributeError:
                continue
            for hint in hints:
                if not isinstance(hint, str) or not hint.strip() or hint in seen_titles:
                    continue
                description = f"{hint} ({trend_title} 트렌드)"
                if len(description) > _DESCRIPTION_MAX_CHARS:
                    description = description[: _DESCRIPTION_MAX_CHARS - 1].rstrip() + "…"
                actions.append(
                    ActionItem(
                        title=hint,
                        description=description,
                        source=f"kb:{trend_id}",
                        vault_echo=_match_phrase(hint, safe_phrases),
                    )
                )
                seen_titles.add(hint)
                if len(actions) >= limit:
                    break
            if len(actions) >= limit:
                break

    return ActionPlanContent(actions=actions)


def _match_phrase(target_text: str, phrases: list[str]) -> Optional[str]:
    """target_text 에 부분 일치하는 phrase 1개 반환.

    공백으로 분리한 토큰 단위 부분 일치. 매칭 없으면 None.
    """
    if not phrases:
        return None
    text = (target_text or "").strip()
    if not text:
        return None
    for phrase in phrases:
        # phrase 의 단어 중 어느 하나라도 target 에 등장하면 echo
        for token in phrase.split():
            if len(token) >= 2 and token in text:
                return phrase
    return None
