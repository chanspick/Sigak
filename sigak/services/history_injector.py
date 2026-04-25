"""LLM prompt 주입용 user_history 요약본 빌더 (STEP 5i).

각 기능 시작 시 build_history_context 로 최근 N개씩 카테고리별 추출 후
system prompt 에 마크다운 블록으로 주입. 토큰 수 측정 및 초과 시
summary 모드 전환 (첫/마지막 문장만).

caller 는 반환 문자열을 적당한 위치에 prepend.
"""
from __future__ import annotations

import logging
from typing import Iterable, Literal, Optional

from sqlalchemy import text


logger = logging.getLogger(__name__)


HistoryType = Literal[
    "conversations",
    "best_shot_sessions",
    "aspiration_analyses",
    "verdict_sessions",
    "pi_history",
]


_EMPTY_CONTEXT = ""


# 대략적 토큰 카운트 — tiktoken 없이 char/3 추정 (한글 1자 ≈ 1.5 토큰)
def _rough_token_count(text_str: str) -> int:
    return max(0, len(text_str) // 3)


def build_history_context(
    db,
    user_id: str,
    *,
    include: Iterable[HistoryType],
    max_per_type: int = 1,
    token_limit: Optional[int] = None,
) -> str:
    """users.user_history 에서 최근 max_per_type 개씩 추출 후 markdown 조립.

    Args:
      db: SQLAlchemy session
      user_id: users.id
      include: 포함할 카테고리 iterable
      max_per_type: 각 카테고리 최신 N 개 (기본 1)
      token_limit: 대략 토큰 상한 — 초과 시 summarize 전환
        (None 이면 config.inject_history_token_limit)

    Returns:
      "" (공백) 또는 마크다운 블록 문자열.
      예외 전부 흡수 — caller 는 빈 문자열 가정 가능.
    """
    try:
        from config import get_settings
        settings = get_settings()
        if token_limit is None:
            token_limit = settings.inject_history_token_limit
    except Exception:
        token_limit = 80_000

    try:
        row = db.execute(
            text("SELECT user_history FROM users WHERE id = :uid"),
            {"uid": user_id},
        ).first()
    except Exception:
        logger.warning("build_history_context: column missing user=%s", user_id)
        return _EMPTY_CONTEXT

    if row is None or not row.user_history:
        return _EMPTY_CONTEXT

    raw = row.user_history
    if not isinstance(raw, dict):
        return _EMPTY_CONTEXT

    # 우선 full-fidelity 로 시도
    full = _compose_context(raw, include, max_per_type=max_per_type, mode="full")
    if _rough_token_count(full) <= token_limit:
        return full

    # 요약 모드 (첫 + 마지막 문장만)
    logger.info("build_history_context: over token limit, summarizing user=%s", user_id)
    summarized = _compose_context(raw, include, max_per_type=max_per_type, mode="summary")
    return summarized


def _compose_context(
    raw: dict,
    include: Iterable[HistoryType],
    *,
    max_per_type: int,
    mode: Literal["full", "summary"],
) -> str:
    """실제 markdown 조립. 빈 부분은 건너뜀. 아무것도 없으면 빈 문자열."""
    blocks: list[str] = []

    for cat in include:
        items = raw.get(cat)
        if not isinstance(items, list) or not items:
            continue
        recent = items[:max_per_type]

        if cat == "conversations":
            block = _render_conversations(recent, mode=mode)
        elif cat == "best_shot_sessions":
            block = _render_best_shot(recent, mode=mode)
        elif cat == "aspiration_analyses":
            block = _render_aspiration(recent, mode=mode)
        elif cat == "verdict_sessions":
            block = _render_verdict(recent, mode=mode)
        elif cat == "pi_history":
            block = _render_pi(recent, mode=mode)
        else:
            continue

        if block:
            blocks.append(block)

    if not blocks:
        return _EMPTY_CONTEXT

    header = "## 이전 맥락 (요약)\n\n"
    return header + "\n\n".join(blocks) + "\n\n## 현재 요청\n\n"


def _render_conversations(items: list[dict], *, mode: str) -> str:
    parts = ["### Sia 대화 이력"]
    for i, entry in enumerate(items):
        started = entry.get("started_at") or "?"
        msgs = entry.get("messages") or []
        ig = entry.get("ig_snapshot") or {}

        tone = None
        if isinstance(ig, dict):
            a = ig.get("analysis")
            if isinstance(a, dict):
                tone = a.get("tone_category")

        lines = [f"- 세션 #{i + 1} (시작 {started})"]
        if tone:
            lines.append(f"  당시 IG 톤: {tone}")
        if msgs:
            if mode == "summary":
                # 첫 user + 마지막 assistant
                user_msg = next(
                    (m.get("content", "") for m in msgs
                     if isinstance(m, dict) and m.get("role") == "user"),
                    "",
                )
                asst_msg = next(
                    (m.get("content", "") for m in reversed(msgs)
                     if isinstance(m, dict) and m.get("role") == "assistant"),
                    "",
                )
                if user_msg:
                    lines.append(f"  유저 시작: {_truncate(user_msg, 80)}")
                if asst_msg:
                    lines.append(f"  Sia 마무리: {_truncate(asst_msg, 80)}")
            else:
                lines.append(f"  총 {len(msgs)} 메시지:")
                for m in msgs[-6:]:  # 최근 6개만
                    if not isinstance(m, dict):
                        continue
                    role = m.get("role", "?")
                    content = _truncate(m.get("content", ""), 120)
                    lines.append(f"    [{role}] {content}")
        parts.append("\n".join(lines))
    return "\n".join(parts)


def _render_best_shot(items: list[dict], *, mode: str) -> str:
    parts = ["### Best Shot 이력"]
    for i, entry in enumerate(items):
        lines = [
            f"- 세션 #{i + 1}: 업로드 {entry.get('uploaded_count', 0)}장, "
            f"선별 {len(entry.get('selected') or [])}장"
        ]
        overall = entry.get("overall_message")
        if overall:
            lines.append(f"  종합: {_truncate(overall, 100)}")
        # mode=full: 선별 상위 3장 Sia 코멘트 — 강화 루프 갭 2 echo
        if mode == "full":
            selected = entry.get("selected") or []
            for j, sel in enumerate(selected[:3]):
                if not isinstance(sel, dict):
                    continue
                comment = sel.get("sia_comment") or ""
                if comment:
                    lines.append(f"  선별#{j + 1}: {_truncate(str(comment), 80)}")
        parts.append("\n".join(lines))
    return "\n".join(parts)


def _render_aspiration(items: list[dict], *, mode: str) -> str:
    parts = ["### 추구미 분석 이력"]
    for i, entry in enumerate(items):
        target = entry.get("target_handle") or entry.get("source") or "?"
        gap = entry.get("gap_narrative") or ""
        lines = [f"- 분석 #{i + 1}: 대상 {target}"]
        if gap:
            lines.append(f"  갭: {_truncate(gap, 120)}")
        if mode == "full":
            overall = entry.get("sia_overall_message") or ""
            if overall:
                lines.append(f"  종합: {_truncate(overall, 120)}")
        parts.append("\n".join(lines))
    return "\n".join(parts)


def _render_verdict(items: list[dict], *, mode: str) -> str:
    parts = ["### 피드 추천 이력"]
    for i, entry in enumerate(items):
        n_photos = len(entry.get("photos_r2_urls") or [])
        rec = entry.get("recommendation") or {}
        lines = [f"- 세션 #{i + 1}: 사진 {n_photos}장"]
        if isinstance(rec, dict):
            top = rec.get("top_action") or rec.get("summary")
            if top:
                lines.append(f"  추천: {_truncate(str(top), 120)}")
        # mode=full: photo_insights 상위 2장 dominant_tone + alignment — 강화 루프 갭 1 echo
        if mode == "full":
            insights = entry.get("photo_insights") or []
            for j, ins in enumerate(insights[:2]):
                if not isinstance(ins, dict):
                    continue
                tone = ins.get("dominant_tone")
                align = ins.get("alignment_with_profile")
                bits: list[str] = []
                if tone:
                    bits.append(f"톤 {_truncate(str(tone), 40)}")
                if align:
                    bits.append(f"매칭 {_truncate(str(align), 60)}")
                if bits:
                    lines.append(f"  사진#{j + 1}: {' / '.join(bits)}")
        parts.append("\n".join(lines))
    return "\n".join(parts)


def _render_pi(items: list[dict], *, mode: str) -> str:
    """Phase I — PI 결과 narrative summary 마크다운 (Backward echo).

    상품명 직접 호명 금지 — "정밀 분석" 우회 표현. matched_type / cluster_label /
    coord_3axis / top_celeb / top_hair / top_action 을 4 기능 prompt 에 carry.
    빈 필드는 줄 자체 스킵. mode=summary 시 matched_type + cluster_label 만.
    """
    parts = ["### 본인 정밀 분석 이력"]
    for i, entry in enumerate(items):
        # 상품명 직접 호명 금지 — "최근 진단" 우회 (version 정보는 내부 추적용)
        lines = [f"- 최근 진단 #{i + 1}"]

        matched_type = entry.get("matched_type")
        cluster_label = entry.get("cluster_label")
        if matched_type or cluster_label:
            bits: list[str] = []
            if matched_type:
                bits.append(f"본질 유형: {_truncate(str(matched_type), 40)}")
            if cluster_label:
                bits.append(f"클러스터: {_truncate(str(cluster_label), 30)}")
            lines.append(f"  {' / '.join(bits)}")

        # mode=full 일 때만 detail (좌표 / 셀럽 / 헤어 / 액션) echo
        if mode == "full":
            coord = entry.get("coord_3axis")
            if isinstance(coord, dict):
                try:
                    lines.append(
                        f"  본질 좌표: shape {float(coord.get('shape', 0.5)):.2f} / "
                        f"volume {float(coord.get('volume', 0.5)):.2f} / "
                        f"age {float(coord.get('age', 0.5)):.2f}"
                    )
                except (TypeError, ValueError):
                    pass

            top_celeb = entry.get("top_celeb_name")
            if top_celeb:
                sim = entry.get("top_celeb_similarity")
                if isinstance(sim, (int, float)):
                    lines.append(f"  닮은꼴 셀럽: {_truncate(str(top_celeb), 30)} ({float(sim):.2f})")
                else:
                    lines.append(f"  닮은꼴 셀럽: {_truncate(str(top_celeb), 30)}")

            top_hair = entry.get("top_hair_name")
            if top_hair:
                lines.append(f"  추천 헤어: {_truncate(str(top_hair), 40)}")

            top_action = entry.get("top_action_text")
            if top_action:
                lines.append(f"  핵심 액션: {_truncate(str(top_action), 100)}")

        parts.append("\n".join(lines))
    return "\n".join(parts)


def _truncate(s: str, n: int) -> str:
    if not isinstance(s, str):
        s = str(s)
    s = s.strip()
    if len(s) <= n:
        return s
    return s[: n - 1].rstrip() + "…"
