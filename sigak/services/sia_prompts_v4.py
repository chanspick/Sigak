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

    # RANGE_DISCLOSURE 모드 (limit / reaffirm)
    if msg_type == MsgType.RANGE_DISCLOSURE:
        if range_mode == "reaffirm":
            parts.append(
                "### [ACTIVE] RANGE_REAFFIRM 모드 (세션 #7 §1.6)\n"
                "사업 존재 재선언 톤. 범위 한정 대신 "
                "'막막한 마음 풀어드리려고 제가 온 거니까' 구조. "
                "구조: [공감/수용] + [도움 의도 재선언] + [협력 유도]."
            )
        else:
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
    if secondary_type == MsgType.RANGE_DISCLOSURE and range_mode == "reaffirm":
        return (
            "Secondary = RANGE_REAFFIRM. 막막함 수용 + 사업 존재 재선언 "
            "('막막한 마음 풀어드리려고 제가 온 거'). 질문 부호 없음."
        )
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
    4) 동적 컨텍스트  : user_name / 누적 카운터 / 직전 유저 메시지 / flag / vision

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

    ctx = _build_context(state, user_flags, vision_summary)

    # composition_block 이 빈 문자열이면 생략하고 3 섹션만 조립 (회귀 방지)
    sections = [base, type_md]
    if composition_block:
        sections.append(composition_block)
    sections.append(ctx)
    return "\n\n".join(sections)
