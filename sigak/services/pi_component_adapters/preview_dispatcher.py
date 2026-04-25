"""PiContent → PiPreview 분배 — Phase I PI-C / PI-D 경계.

혼합 iii 패턴 (CLAUDE.md §0):
  full   : cover / celeb_reference (top1)
  teaser : face_structure / type_reference / gap_analysis / skin_analysis (한 줄)
  locked : coordinate_map / hair_recommendation / action_plan (이름만)

PI_V3_PREVIEW_VISIBILITY 와 의도 일치. PI-D 는 본 함수 결과를 받아 토큰 차감
없이 반환하고, /unlock 시점에 PiContent 자체를 풀 노출 PIv3Section 으로 변환.

순수 함수.
"""
from __future__ import annotations

from schemas.pi_report import PiContent, PiPreview


_TEASER_MAX_CHARS = 80
_TYPE_TEASER_MAX = 60


def to_preview(content: PiContent) -> PiPreview:
    """PiContent → PiPreview 혼합 iii 분배."""
    cover = content.cover

    top1 = None
    if content.celeb_reference and content.celeb_reference.top_celebs:
        top1 = content.celeb_reference.top_celebs[0]

    return PiPreview(
        cover=cover,
        celeb_reference_top1=top1,
        face_structure_teaser=_teaser_face(content),
        type_reference_teaser=_teaser_type(content),
        gap_analysis_teaser=_teaser_gap(content),
        skin_analysis_teaser=_teaser_skin(content),
        locked_components=[
            "coordinate_map",
            "hair_recommendation",
            "action_plan",
        ],
    )


def _teaser_face(content: PiContent) -> str:
    fs = content.face_structure
    if fs and fs.harmony_note:
        return _truncate(fs.harmony_note, _TEASER_MAX_CHARS)
    if fs and fs.metrics:
        m = fs.metrics[0]
        return f"{m.name}: {m.descriptor}"
    return "—"


def _teaser_type(content: PiContent) -> str:
    tr = content.type_reference
    if tr and tr.matched_type_name:
        teaser = tr.matched_type_name
        if tr.cluster_label:
            teaser = f"{teaser} ({tr.cluster_label})"
        return _truncate(teaser, _TYPE_TEASER_MAX)
    return "—"


def _teaser_gap(content: PiContent) -> str:
    ga = content.gap_analysis
    if ga and ga.gap_narrative:
        return _truncate(ga.gap_narrative, _TEASER_MAX_CHARS)
    return "—"


def _teaser_skin(content: PiContent) -> str:
    sa = content.skin_analysis
    if sa and sa.best_colors:
        preview_hex = " · ".join(sa.best_colors[:3])
        return f"BEST {preview_hex}"
    return "—"


def _truncate(s: str, max_chars: int) -> str:
    s = s or ""
    if len(s) > max_chars:
        return s[: max_chars - 1].rstrip() + "…"
    return s
