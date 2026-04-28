"""Sia Haiku system prompt 로더 v4 (Phase H4, 14 타입 확정판).

SPEC 출처: .moai/specs/SPEC-SIA/
  - 세션 #4 v2 §9 (Jinja 템플릿 기본)
  - 세션 #6 v2 §8 (decide_next_message state 전달)
  - 세션 #7 §1-8 (Composition 플래그별 조건부 주입)

HAIKU_TYPES (7 개) 에 대해 base.md + {msg_type}.md 합성 +
state/flags/Composition 플래그 컨텍스트 주입.

HARDCODED_TYPES (7 개) 는 sia_hardcoded.render_hardcoded 경유 — 본 로더는 ValueError.

Public API:
  load_haiku_prompt(
      msg_type, state, user_flags, vision_summary,
      *, is_first_turn, is_combined, secondary_type,
      confrontation_block, apply_self_pr_prefix, range_mode,
  ) -> str
  available_types() -> set[MsgType]
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

from schemas.sia_state import (
    HAIKU_TYPES,
    HARDCODED_TYPES,
    ConversationState,
    MsgType,
    RangeMode,
    UserMessageFlags,
)
from schemas.user_history import UserHistory


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
#  Context builder — 상수 컨텍스트
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
    vault_history: Optional[UserHistory] = None,
    user_phrases: Optional[list[str]] = None,
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

    # 재대화 시 본인 누적 데이터 주입 (4 기능: PI/Verdict/Best Shot/Aspiration).
    # vault_history None / 모든 list 비어있으면 vault_block == "" → 섹션 추가 skip
    # → 첫 진입 유저 회귀 0건.
    vault_block = _format_vault_history_block(vault_history, user_phrases)
    if vault_block:
        parts.extend(["", "## 본인 누적 데이터 (재대화 시)", vault_block])
    return "\n".join(parts)


# ─────────────────────────────────────────────
#  Vault history block — 재대화 누적 데이터 주입
# ─────────────────────────────────────────────

# 길이 가드 상수 (스펙 1-F)
_VAULT_FIRST_SENTENCE_MAX = 100      # 각 history message 첫 문장 ≤ 100자
_VAULT_PHRASE_MAX = 30               # user_original_phrase 각 ≤ 30자
_VAULT_BLOCK_MAX = 500               # 전체 블록 ≤ 500자
_VAULT_PHRASE_LIMIT = 3              # 상위 3개만 노출


# 첫 문장 분리 패턴 — 한국어 마침표(. ) / 일본어 / 종결 기호 / 줄바꿈 우선.
# `re.split` 으로 구분자와 함께 분리한 뒤 [0] 사용.
_FIRST_SENTENCE_SPLIT = re.compile(r"(?<=[.!?。!?])\s+|\n+")


def _first_sentence(text: str, max_chars: int = _VAULT_FIRST_SENTENCE_MAX) -> str:
    """첫 문장 추출 + 길이 truncate. 빈/None 입력 → ""."""
    if not text or not isinstance(text, str):
        return ""
    head = _FIRST_SENTENCE_SPLIT.split(text.strip(), maxsplit=1)[0].strip()
    if not head:
        return ""
    if len(head) > max_chars:
        head = head[: max_chars - 1].rstrip() + "…"
    return head


def _truncate_phrase(phrase: str, max_chars: int = _VAULT_PHRASE_MAX) -> str:
    s = (phrase or "").strip()
    if not s:
        return ""
    if len(s) > max_chars:
        s = s[: max_chars - 1].rstrip() + "…"
    return s


def _format_vault_history_block(
    vault_history: Optional[UserHistory],
    user_phrases: Optional[list[str]] = None,
) -> str:
    """본인 누적 데이터를 prompt 주입용 마크다운 블록으로 직렬화.

    빈 history (모든 list 빈) AND 빈 phrases → "" 반환 → 첫 진입 유저 회귀 0.
    개별 항목 None-safe. 전체 블록 ≤ 500자 (초과 시 후반 truncate).
    """
    if vault_history is None and not user_phrases:
        return ""

    bs_count = len(vault_history.best_shot_sessions) if vault_history else 0
    vd_count = len(vault_history.verdict_sessions) if vault_history else 0
    asp_count = len(vault_history.aspiration_analyses) if vault_history else 0
    pi_count = len(vault_history.pi_history) if vault_history else 0
    phrases = user_phrases or []

    if (
        bs_count == 0 and vd_count == 0 and asp_count == 0
        and pi_count == 0 and not phrases
    ):
        return ""

    lines: list[str] = []

    # 카운트 한 줄 — 0 인 카테고리는 스킵하지 않고 일관 표기 (유저가 이력 인지).
    # PI 는 상품명 직접 호명 금지 — "정밀 분석" 우회 표현 사용.
    lines.append(
        f"- 본인 사용 이력: Best Shot {bs_count}회 / 피드 추천 {vd_count}회 / "
        f"추구미 분석 {asp_count}회 / 정밀 분석 {pi_count}회"
    )

    # Phase I — Backward echo: pi_history[0].matched_type + cluster_label
    # Sia 재대화 시 "지난번 정밀 분석에서 ㅇㅇ님은 'Soft Fresh' 인상이세요" 자연 발화 carry.
    if pi_count > 0 and vault_history is not None:
        pi0 = vault_history.pi_history[0]
        pi_bits: list[str] = []
        if pi0.matched_type:
            pi_bits.append(f"본질 유형 '{_truncate_phrase(str(pi0.matched_type), 40)}'")
        if pi0.cluster_label:
            pi_bits.append(f"클러스터 {_truncate_phrase(str(pi0.cluster_label), 30)}")
        if pi_bits:
            lines.append(f"- 지난 정밀 분석: {' · '.join(pi_bits)}")
        # 닮은꼴 셀럽 1명 (있으면)
        if pi0.top_celeb_name:
            lines.append(f"- 닮은꼴 셀럽: {_truncate_phrase(str(pi0.top_celeb_name), 30)}")

    # 최신 피드 추천 방향 — verdict_sessions[0].recommendation.get("style_direction", "")
    if vd_count > 0 and vault_history is not None:
        vd0 = vault_history.verdict_sessions[0]
        rec = vd0.recommendation or {}
        style_dir = rec.get("style_direction", "") if isinstance(rec, dict) else ""
        head = _first_sentence(style_dir)
        if head:
            lines.append(f"- 최신 피드 추천 방향: {head}")
        # 최신 추천 사진 핵심 — photo_insights[0] dominant_tone + alignment
        # (강화 루프 갭 1 echo — Verdict v2 detail 이 Sia 재대화에 흘러감)
        insights = vd0.photo_insights or []
        if insights and isinstance(insights[0], dict):
            first = insights[0]
            tone = first.get("dominant_tone")
            align = first.get("alignment_with_profile")
            bits: list[str] = []
            if tone:
                bits.append(f"톤 {_truncate_phrase(str(tone), 30)}")
            if align:
                bits.append(f"매칭 {_truncate_phrase(str(align), 40)}")
            if bits:
                lines.append(f"- 최신 추천 사진#1: {' / '.join(bits)}")

    # 최신 Best Shot 종합 — best_shot_sessions[0].overall_message
    if bs_count > 0 and vault_history is not None:
        bs0 = vault_history.best_shot_sessions[0]
        head = _first_sentence(bs0.overall_message or "")
        if head:
            lines.append(f"- 최신 Best Shot 종합: {head}")
        # 최신 Best Shot 1등 — selected[0].sia_comment
        # (강화 루프 갭 2 echo — Best Shot 선택 사진 narrative 가 Sia 재대화에 흘러감)
        selected = bs0.selected or []
        if selected:
            first_sel = selected[0]
            comment = getattr(first_sel, "sia_comment", None) or ""
            head_c = _first_sentence(str(comment))
            if head_c:
                lines.append(f"- 최신 Best Shot 1등: {head_c}")

    # 최신 추구미 갭 — aspiration_analyses[0].gap_narrative
    if asp_count > 0 and vault_history is not None:
        head = _first_sentence(vault_history.aspiration_analyses[0].gap_narrative or "")
        if head:
            lines.append(f"- 최신 추구미 갭: {head}")

    # 본인 자주 쓰는 표현 — 상위 3개, 각 30자 truncate
    if phrases:
        truncated = [_truncate_phrase(p) for p in phrases[:_VAULT_PHRASE_LIMIT]]
        cleaned = [p for p in truncated if p]
        if cleaned:
            quoted = ", ".join(f"\"{p}\"" for p in cleaned)
            lines.append(f"- 본인 자주 쓰는 표현: {quoted}")

    block = "\n".join(lines)

    # 전체 블록 ≤ 500자 — 초과 시 후반부 잘라내고 표시.
    if len(block) > _VAULT_BLOCK_MAX:
        block = block[: _VAULT_BLOCK_MAX - 1].rstrip() + "…"

    return block


# ─────────────────────────────────────────────
#  Composition 기반 조건부 지시 블록 (세션 #7)
# ─────────────────────────────────────────────

def _build_composition_instructions(
    msg_type: MsgType,
    state: ConversationState,
    *,
    is_first_turn: bool,
    is_combined: bool,
    secondary_type: Optional[MsgType],
    confrontation_block: Optional[str],
    apply_self_pr_prefix: bool,
    range_mode: RangeMode,
) -> str:
    """Composition 플래그에 따른 조건부 모드 지시문 생성.

    플래그가 모두 기본값이면 빈 문자열 반환 — prompt 에 noise 추가 안 함.
    """
    parts: list[str] = []

    # M1 결합 출력 (세션 #4 v2 §6)
    if is_first_turn and msg_type == MsgType.OBSERVATION:
        parts.append(
            "### [ACTIVE] M1 결합 출력 모드\n"
            "이번 턴은 첫 번째 Sia 턴입니다. 하드코딩된 OPENING_DECLARATION 문장이 "
            "앞에 배치되고, 그 뒤에 이어질 OBSERVATION 1-2 문장을 생성하세요. "
            "OPENING 에 이미 유저 이름 호명이 있으므로 본 OBSERVATION 에서 재호명은 생략."
        )

    # EMPATHY 결합 출력 (세션 #7 §1)
    if is_combined and msg_type == MsgType.EMPATHY_MIRROR:
        sec_label = secondary_type.value if secondary_type else "probe"
        sec_guide = _secondary_guide(secondary_type, confrontation_block, range_mode)
        parts.append(
            f"### [ACTIVE] EMPATHY 결합 출력 모드 (secondary = {sec_label})\n"
            f"EMPATHY 2문장 뒤에 secondary_type 에 맞는 문장 1개 추가. "
            f"secondary 문장만 `?` 허용 (A-6 예외). A-4 `~잖아요` 는 전체 금지 유지.\n"
            f"{sec_guide}"
        )

    # A-13 자기 PR prefix 모드 (세션 #7 §5)
    if apply_self_pr_prefix:
        parts.append(
            "### [ACTIVE] A-13 Prefix 모드\n"
            "본문 앞에 짧은 인정 prefix 1문장 허용 (세션당 1-2회 한정). "
            "형태 (a) 칭찬 prefix: '운동 정말 열심히 하시나봐요!' / "
            "형태 (b) 유저 가설 부분 동의: '맞아요 위에서 찍으면 그 효과 있죠'. "
            "가식적 칭찬 / 평가 동조 / 무관한 칭찬 금지."
        )

    # CONFRONTATION 블록 지정 (C1~C7)
    if confrontation_block and msg_type == MsgType.CONFRONTATION:
        parts.append(
            f"### [ACTIVE] CONFRONTATION 블록: {confrontation_block}\n"
            f"{_confrontation_block_hint(confrontation_block)}"
        )

    # RANGE_DISCLOSURE 모드 (limit only — 베타 hotfix 2026-04-28 로 reaffirm 가이드 폐기)
    # range_mode="reaffirm" 진입해도 limit (severe/mild) 가이드로 fallback.
    # 막막함 가정 진앙 (sia_hardcoded.py / sia_decision.py 참조).
    if msg_type == MsgType.RANGE_DISCLOSURE:
        sev = state.overattachment_severity
        if sev == "severe":
            parts.append(
                "### [ACTIVE] RANGE_LIMIT (severe) 모드\n"
                "고립/의존 신호 감지. 외부 자원 권유 필수. "
                "금지: 자기부정, 진단 철회, 관계 형성 허용."
            )
        else:
            parts.append(
                "### [ACTIVE] RANGE_LIMIT (mild) 모드\n"
                "범위 명시 필수 ('피드 N장 / 피드 안'). "
                "한계 인정 + 진단 유효성 보존."
            )

    # A-16 유저 무지 명시 활성 (최근 N턴 내)
    disclaimer_active = state.user_disclaimer_memory.get("recent", 0) > 0
    if disclaimer_active:
        remaining = state.user_disclaimer_memory["recent"]
        parts.append(
            f"### [ACTIVE] A-16 유저 무지 영역 (남은 {remaining}턴)\n"
            "유저가 최근 '잘 몰라 / 신경 안 써 / 관심 없' 명시. "
            "해당 영역 의식/의도 질문 금지. "
            "대신 (a) 관찰 제시 서술 (DIAGNOSIS 영역) or (b) 무지 영역 외 다른 축으로 질문 전환."
        )

    if not parts:
        return ""
    return "## 조건부 모드 지시 (Composition 반영)\n\n" + "\n\n".join(parts)


def _secondary_guide(
    secondary_type: Optional[MsgType],
    confrontation_block: Optional[str],
    range_mode: RangeMode,
) -> str:
    """EMPATHY 결합 출력의 secondary 문장 작성 가이드."""
    if secondary_type == MsgType.CONFRONTATION and confrontation_block == "C6":
        return (
            "Secondary = CONFRONTATION(C6). 유저 자기개시 내 두 기준 추출 → 재프레임 → "
            "'이미 갖고 계신 거 아닐까요?' 류 질문 종결. 평가 직접 답변 금지."
        )
    # secondary RANGE_DISCLOSURE + reaffirm 분기 — 베타 hotfix (2026-04-28) 로 폐기.
    # 1-B sia_decision.py 에서 호출 자체 차단 (PROBE 재라우팅). default PROBE 가이드 사용.
    if secondary_type == MsgType.RECOGNITION:
        return (
            "Secondary = RECOGNITION. 누적 관찰 + 유저 자기개시를 한 축으로 묶어 "
            "`~잖아요` 동의 유도 반문 (A-4 예외: EMPATHY 결합 2문장까지는 `~잖아요` 금지 유지)."
        )
    # 기본 PROBE
    return (
        "Secondary = PROBE. 직전 관찰을 한 계단 좁히는 탐색 질문. "
        "A-12 / A-15 / A-16 게이트 통과 필수."
    )


def _confrontation_block_hint(block: str) -> str:
    """C1~C7 블록별 짧은 리마인더. 상세는 confrontation.md 참조."""
    hints = {
        "C1": "외부 권위 회귀 돌파. 권위 인정 + 유저 실제 감각 분리 + 레이어 구분.",
        "C2": "자기 축소/체념 돌파. 체념 속 선택 드러내기 + 일관성 증거 제시.",
        "C3": "반문 공격 돌파. 질문 반사 후 원 관찰 재진술.",
        "C4": "주제 이탈 돌파. 이탈 인정 + 원 축 복귀.",
        "C6": (
            "평가 의존 돌파 (세션 #7 §2). 유저 자기개시 내 기준 추출 → 재프레임. "
            "평가 직접 답변/무조건 칭찬/회피 금지."
        ),
        "C7": (
            "일반화 회피 돌파 (세션 #7 §3). 일반화 부분 인정 + 본인 specifics 재제시 + "
            "질문 종결 OR 진단 예고 ('이 부분이 진단에서 풀어드릴 핵심'). "
            "위로형/전면 부정 금지."
        ),
    }
    return hints.get(block, f"블록 {block} 상세는 confrontation.md 참조.")


# ─────────────────────────────────────────────
#  Public — prompt assembly
# ─────────────────────────────────────────────

def load_haiku_prompt(
    msg_type: MsgType,
    state: ConversationState,
    user_flags: Optional[UserMessageFlags] = None,
    vision_summary: str = "",
    *,
    is_first_turn: bool = False,
    is_combined: bool = False,
    secondary_type: Optional[MsgType] = None,
    confrontation_block: Optional[str] = None,
    apply_self_pr_prefix: bool = False,
    range_mode: RangeMode = "limit",
    vault_history: Optional[UserHistory] = None,
    user_phrases: Optional[list[str]] = None,
) -> str:
    """HAIKU_TYPES 7개 중 하나에 해당하는 system prompt 조립.

    HARDCODED_TYPES (7개: OPENING/META/EVIDENCE/SOFT_WALKBACK/CHECK_IN/RE_ENTRY/
    RANGE_DISCLOSURE) 는 ValueError — sia_hardcoded.render_hardcoded 사용.

    Assembly order
    --------------
    1) base.md        : 페르소나 B 공통 지침 + A-12/A-15/A-16 self-check
    2) {type}.md      : 타입별 구조/예시/제약
    3) 조건부 지시    : Composition 플래그 (is_first_turn / is_combined /
                       secondary_type / confrontation_block / apply_self_pr_prefix /
                       range_mode / user_disclaimer_memory) 기반 활성화된 모드만
    4) 동적 컨텍스트  : user_name / 누적 카운터 / 직전 유저 메시지 / flag / vision /
                       vault_history (재대화 누적 데이터) / user_phrases

    재대화 시 본인 누적 데이터 주입 (1-A ~ 1-F):
      vault_history    UserHistory — 4 기능 누적 (Best Shot / 피드 추천 / 추구미 분석 /
                       Sia 대화). None or 모든 list 빈 → 첫 진입 유저 회귀 0.
      user_phrases     UserTasteProfile.user_original_phrases — 상위 3개 노출.
                       caller (routes/sia.py) 가 vault.get_user_taste_profile()
                       에서 추출 후 전달.

    플래그 기본값은 기존 호출부 회귀 방지 — 전부 기본값이면 기존 동작과 동일.
    """
    if msg_type in HARDCODED_TYPES:
        raise ValueError(
            f"{msg_type.value} is hardcoded; use sia_hardcoded.render_hardcoded"
        )
    if msg_type not in HAIKU_TYPES:
        raise ValueError(f"unknown msg_type: {msg_type}")

    base = _load_markdown("base.md")
    type_md = _load_markdown(f"{msg_type.value}.md")

    composition_block = _build_composition_instructions(
        msg_type, state,
        is_first_turn=is_first_turn,
        is_combined=is_combined,
        secondary_type=secondary_type,
        confrontation_block=confrontation_block,
        apply_self_pr_prefix=apply_self_pr_prefix,
        range_mode=range_mode,
    )

    ctx = _build_context(
        state, user_flags, vision_summary,
        vault_history=vault_history,
        user_phrases=user_phrases,
    )

    # composition_block 이 빈 문자열이면 생략하고 3 섹션만 조립 (회귀 방지)
    sections = [base, type_md]
    if composition_block:
        sections.append(composition_block)
    sections.append(ctx)
    return "\n\n".join(sections)
