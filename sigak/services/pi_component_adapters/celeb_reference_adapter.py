"""Celeb Reference 어댑터 — Phase I PI-C.

PI-B 가 Vision/CLIP 으로 산출한 셀럽 매칭 결과를 PIv1 어댑트.
top 3 trim, similarity 정렬, reason ~80자 truncate.
순수 함수.
"""
from __future__ import annotations

from typing import Iterable

from schemas.pi_report import CelebReferenceContent, CelebReferenceMatch


_REASON_MAX_CHARS = 80


def build_celeb_reference(
    matched_celebs: list[dict] | None,
) -> CelebReferenceContent:
    """matched_celebs = [{name, photo_url, similarity, reason}, ...] → top 3.

    Args:
        matched_celebs: PI-B 산출 — 이름/URL/유사도/이유 dict 리스트.

    Returns:
        CelebReferenceContent (top_celebs 0~3개).
    """
    if not matched_celebs:
        return CelebReferenceContent(top_celebs=[])

    cleaned = list(_iter_clean(matched_celebs))
    cleaned.sort(key=lambda m: m.similarity, reverse=True)

    return CelebReferenceContent(top_celebs=cleaned[:3])


def _iter_clean(items: Iterable[dict]) -> Iterable[CelebReferenceMatch]:
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        photo_url = str(item.get("photo_url") or "").strip()
        if not name or not photo_url:
            continue
        try:
            similarity = float(item.get("similarity", 0.0))
        except (TypeError, ValueError):
            similarity = 0.0
        # clamp 0~1
        similarity = max(0.0, min(1.0, similarity))

        reason = str(item.get("reason") or "").strip()
        if len(reason) > _REASON_MAX_CHARS:
            reason = reason[: _REASON_MAX_CHARS - 1].rstrip() + "…"

        yield CelebReferenceMatch(
            name=name,
            photo_url=photo_url,
            similarity=similarity,
            reason=reason,
        )
