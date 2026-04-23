"""Sia Haiku system prompt 로더 v4 (Phase H4).

PHASE_H_DIRECTIVE §6 / HAIKU_TYPES.

HAIKU_TYPES (7 개) 에 대해 base.md + {msg_type}.md 합성 + state/flags 컨텍스트 주입.
HARDCODED_TYPES 는 sia_hardcoded.render_hardcoded 경유 — 본 로더는 ValueError.

Public API:
  load_haiku_prompt(msg_type, state, user_flags=None, vision_summary="") -> str
  available_types() -> set[MsgType]
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from schemas.sia_state import (
    HAIKU_TYPES,
    HARDCODED_TYPES,
    ConversationState,
    MsgType,
    UserMessageFlags,
)


# ─────────────────────────────────────────────
#  Path 확정
# ─────────────────────────────────────────────

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "haiku_sia"


@lru_cache(maxsize=32)
def _load_markdown(filename: str) -> str:
    """prompts/haiku_sia/{filename} 읽기. 캐시 O. 없으면 FileNotFoundError."""
    path = _PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def available_types() -> set[MsgType]:
    """로더가 지원하는 msg_type 집합 — HAIKU_TYPES 와 동일."""
    return set(HAIKU_TYPES)


# ─────────────────────────────────────────────
#  Context builder
# ─────────────────────────────────────────────

def _format_flags(flags: Optional[UserMessageFlags]) -> str:
    if flags is None:
        return "없음"
    active = [
        name for name, default in [
            ("has_concede", False),
            ("has_emotion_word", False),
            ("has_tt", False),
            ("has_explain_req", False),
            ("has_meta_challenge", False),
            ("has_evidence_doubt", False),
            ("has_self_disclosure", False),
            ("is_defensive", False),
        ] if getattr(flags, name, default)
    ]
    if flags.emotion_word_raw:
        active.append(f"emotion_word_raw={flags.emotion_word_raw!r}")
    return ", ".join(active) if active else "없음"


def _recent_assistant_draft_summary(state: ConversationState, n: int = 3) -> str:
    drafts = state.recent_assistant_drafts(n=n)
    if not drafts:
        return "(아직 없음)"
    return "\n".join(f"- {d}" for d in drafts)


def _build_context(
    state: ConversationState,
    user_flags: Optional[UserMessageFlags],
    vision_summary: str,
) -> str:
    last_user = state.last_user()
    last_user_text = last_user.text if last_user else "(유저 발화 없음)"

    obs = state.observation_count
    recog = state.type_counts.get(MsgType.RECOGNITION, 0)
    diag = state.type_counts.get(MsgType.DIAGNOSIS, 0)

    parts = [
        "## 현재 대화 컨텍스트",
        f"- 유저 이름: {state.user_name or '(없음)'}",
        f"- OBSERVATION 누적: {obs}",
        f"- RECOGNITION 누적: {recog}",
        f"- DIAGNOSIS 누적: {diag}",
        f"- 직전 유저 메시지: {last_user_text}",
        f"- 유저 flag: {_format_flags(user_flags)}",
        "",
        "## 최근 Sia 응답 3개 (반복/단조로움 회피 참고)",
        _recent_assistant_draft_summary(state, n=3),
    ]
    if vision_summary:
        parts.extend(["", "## Vision 요약", vision_summary])
    return "\n".join(parts)


# ─────────────────────────────────────────────
#  Public — prompt assembly
# ─────────────────────────────────────────────

def load_haiku_prompt(
    msg_type: MsgType,
    state: ConversationState,
    user_flags: Optional[UserMessageFlags] = None,
    vision_summary: str = "",
) -> str:
    """HAIKU_TYPES 7개 중 하나에 해당하는 system prompt 조립.

    HARDCODED_TYPES (OPENING/META_REBUTTAL/EVIDENCE_DEFENSE/SOFT_WALKBACK) 는
    ValueError — sia_hardcoded.render_hardcoded 사용하라.

    Assembly order
    --------------
    1) base.md        : 페르소나 B 공통 지침
    2) {type}.md      : 타입별 구조/예시/제약
    3) 동적 컨텍스트   : user_name / 누적 카운터 / 직전 유저 메시지 / flag / vision
    """
    if msg_type in HARDCODED_TYPES:
        raise ValueError(
            f"{msg_type.value} is hardcoded; use sia_hardcoded.render_hardcoded"
        )
    if msg_type not in HAIKU_TYPES:
        raise ValueError(f"unknown msg_type: {msg_type}")

    base = _load_markdown("base.md")
    type_md = _load_markdown(f"{msg_type.value}.md")
    ctx = _build_context(state, user_flags, vision_summary)

    return "\n\n".join([base, type_md, ctx])
