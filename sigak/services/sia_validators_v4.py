"""Sia validator v4 — 페르소나 B + 메시지 단위 규칙 (Phase H3).

PHASE_H_DIRECTIVE §5 + SIA_SESSION4_V2 §5.2 drop-in.

기존 `sia_validators.find_violations` 는 turn-agnostic base (HR1-5 + tone + eval
+ assertion + abstract_noun). v4 는 msg_type + ConversationState 문맥을 받아
A-1 ~ A-8 규칙을 추가로 검증한다.

규칙 요약 (기존):
  A-1  a1_forbidden_suffix     — 네요/군요/같아요/같습니다/것 같/수 있습니다
  A-2  a2_jangayo_window       — 최근 3턴 ~잖아요 합 > 2
  A-3  a3_deoraguyo_window     — 최근 3턴 ~더라구요 합 > 1
  A-4  a4_same_type_streak     — 같은 msg_type 3연속
  A-5  a5_question_missing     — QUESTION_REQUIRED 타입인데 '?' 없음
  A-6  a6_question_forbidden   — QUESTION_FORBIDDEN 타입인데 '?' 있음
  A-7  a7_emotion_mirror_miss  — EMPATHY_MIRROR 인데 유저 emotion_word_raw 미반사
  A-8  a8_too_long             — 60자 초과 절

§5.2 Drop-in 확장 (FN 4건 해소):
  A-1 전역: ㅋ / ~구나 단독 / 반말 종결 / 이중 대비 / 축 라벨 단독 / 승리 표현
            / OBSERVATION 계열 절대 관찰 (거의 전부 / 하나도 없 / 한 번도 없)
  A-4 EMPATHY_MIRROR 에서 ~잖아요 금지 (타입 조건부)
  A-5 RECOGNITION 단정 ~예요 금지 (타입 조건부)
  A-2 cross-turn: ~잖아요 3 메시지 창 합 > 2, ~예요 연타 시 softener 필요
                   EMPATHY_MIRROR 누적 비율 > 15% 경고 (A-3 트리거 우선 시 허용)

공개 API:
  find_violations_v4(text, msg_type, state, emotion_word_raw) -> dict   # 기존 dict 통합
  validate(draft, msg_type, state) -> ValidationResult                    # 마케터 §5.2 공식

어미 카운트 헬퍼:
  count_jangayo / count_deoraguyo / count_neyo / count_yeyo
    → AssistantTurn.*_count populate 용
"""
from __future__ import annotations

import re
from typing import Optional

from schemas.sia_state import (
    QUESTION_FORBIDDEN,
    QUESTION_REQUIRED,
    AssistantTurn,
    ConversationState,
    MsgType,
)
from services.sia_validators import (
    find_violations as _find_violations_base,
    long_sentences,
)


# ─────────────────────────────────────────────
#  어미 카운트 패턴 (cross-turn A-2/A-3 용)
# ─────────────────────────────────────────────

_JANGAYO_RE = re.compile(r"잖아요")
_DEORAGUYO_RE = re.compile(r"더라구요")
_NEYO_RE = re.compile(r"네요")
_YEYO_RE = re.compile(r"(예요|에요)")  # 평서체 종결 — 참고용 카운트


def count_jangayo(text: str) -> int:
    return len(_JANGAYO_RE.findall(text))


def count_deoraguyo(text: str) -> int:
    return len(_DEORAGUYO_RE.findall(text))


def count_neyo(text: str) -> int:
    return len(_NEYO_RE.findall(text))


def count_yeyo(text: str) -> int:
    """~예요/~에요 — 참고용 카운트. 반드시 금지는 아님."""
    return len(_YEYO_RE.findall(text))


# ─────────────────────────────────────────────
#  A-1 금지 어미 (페르소나 B 신규 강화)
#
#  기존 sia_validators.FORBIDDEN_SUFFIXES 는 페르소나 A 기준.
#  v4 는 페르소나 B-친밀형에 맞춘 강화 list.
# ─────────────────────────────────────────────

A1_FORBIDDEN_SUFFIXES = [
    "네요",
    "군요",
    "같아요",
    "같습니다",
    "같네요",
    "것 같아",           # "것 같아요" / "것 같아서" / "것 같았"
    "것 같습",           # "것 같습니다" / "것 같습니까"
    "것 같네",           # "것 같네요"
    "수 있습니다",
    "수 있어요",
]
_A1_PATTERN = re.compile("|".join(re.escape(s) for s in A1_FORBIDDEN_SUFFIXES))


# ─────────────────────────────────────────────
#  창 임계치 (A-2 / A-3)
# ─────────────────────────────────────────────

A2_JANGAYO_WINDOW_MAX = 2     # 최근 3턴 합 ≤ 2
A3_DEORAGUYO_WINDOW_MAX = 1   # 최근 3턴 합 ≤ 1
A4_SAME_TYPE_MAX_STREAK = 2   # 같은 msg_type 3연속 → 위반


# ─────────────────────────────────────────────
#  페르소나 B 축소 추상명사 list
#
#  base validator 의 ABSTRACT_NOUN_TOKENS 는 페르소나 A 기준이라 "결*" 토큰
#  (결이/결을/결입/결은) 을 blacklist. 페르소나 B 는 "결" 을 의도 어휘로 사용.
#  v4 는 "결*" 제외하고 나머지 공허 단정 어휘만 체크.
# ─────────────────────────────────────────────

_A_ABSTRACT_NOUN_TOKENS: list[str] = [
    "무드를", "무드가", "무드입",
    "감도를", "감도가", "감도입",
    "아우라",
    "기운",
]


# ─────────────────────────────────────────────
#  Public — find_violations_v4
# ─────────────────────────────────────────────

def find_violations_v4(
    text: str,
    msg_type: MsgType,
    state: Optional[ConversationState] = None,
    emotion_word_raw: Optional[str] = None,
) -> dict[str, list[str]]:
    """Phase H 전수 검증. base violations + A-1~A-8 결과 dict 병합.

    Parameters
    ----------
    text : 검증 대상 Sia 응답.
    msg_type : 현재 생성 타입 (A-5/A-6/A-7 맥락).
    state : 누적 state — A-2/A-3/A-4 창 체크에 필요. None 이면 스킵.
    emotion_word_raw : 최근 유저 메시지의 첫 감정 원어 — A-7 체크에 필요.

    Returns
    -------
    dict — base (페르소나 A tone 제외) + A-1 ~ A-8 키. 빈 dict 면 clean.
    """
    base = _find_violations_base(text)
    # 페르소나 A 전제 규칙 제외 — v4 는 해요체 허용.
    #   tone_missing : 정중체 어미 의무 (A 전용)
    #   tone_suffix  : A-1 과 일부 중복. A-1 이 대체.
    #   abstract_noun: "결*" 토큰이 페르소나 B 핵심 어휘와 충돌. 아래에서 축소판 재계산.
    for drop_key in ("tone_missing", "tone_suffix", "abstract_noun"):
        base.pop(drop_key, None)
    violations: dict[str, list[str]] = dict(base)

    # 페르소나 B 전용 축소 추상명사 체크 ("결*" 제외)
    if hits := [t for t in _A_ABSTRACT_NOUN_TOKENS if t in text]:
        violations["abstract_noun"] = hits

    # A-1 금지 어미
    if m := _A1_PATTERN.findall(text):
        violations["a1_forbidden_suffix"] = m

    # A-2 잖아요 창 (직전 2턴 + 현재 메시지)
    jangayo_this = count_jangayo(text)
    jangayo_window = jangayo_this + (
        sum(t.jangayo_count for t in state.last_k_assistant(2))
        if state is not None else 0
    )
    if jangayo_window > A2_JANGAYO_WINDOW_MAX:
        violations["a2_jangayo_window"] = [
            f"window_sum={jangayo_window} > {A2_JANGAYO_WINDOW_MAX}"
        ]

    # A-3 더라구요 창
    deoraguyo_this = count_deoraguyo(text)
    deoraguyo_window = deoraguyo_this + (
        sum(t.deoraguyo_count for t in state.last_k_assistant(2))
        if state is not None else 0
    )
    if deoraguyo_window > A3_DEORAGUYO_WINDOW_MAX:
        violations["a3_deoraguyo_window"] = [
            f"window_sum={deoraguyo_window} > {A3_DEORAGUYO_WINDOW_MAX}"
        ]

    # A-4 같은 msg_type 3연속 — 직전 2턴 + 현재 = 3 same
    if state is not None:
        last_two = state.last_k_assistant(2)
        if (
            len(last_two) == 2
            and all(t.msg_type == msg_type for t in last_two)
        ):
            violations["a4_same_type_streak"] = [
                f"type={msg_type.value} streak>=3"
            ]

    # A-5 질문 누락
    has_question_mark = "?" in text
    if msg_type in QUESTION_REQUIRED and not has_question_mark:
        violations["a5_question_missing"] = [msg_type.value]

    # A-6 질문 금지
    if msg_type in QUESTION_FORBIDDEN and has_question_mark:
        violations["a6_question_forbidden"] = [msg_type.value]

    # A-7 EMPATHY_MIRROR 원어 반사
    if (
        msg_type == MsgType.EMPATHY_MIRROR
        and emotion_word_raw
        and emotion_word_raw not in text
    ):
        violations["a7_emotion_mirror_miss"] = [emotion_word_raw]

    # A-8 문장 길이
    if longs := long_sentences(text):
        violations["a8_too_long"] = longs

    # ─────────────────────────────────────────────
    # §5.2 drop-in: 마케터 FN 4건 해소 + A-1 확장 + 타입 조건부 + cross-turn
    # ─────────────────────────────────────────────
    m_errors: list[str] = []
    m_errors.extend(check_global_forbidden(text, msg_type))
    m_errors.extend(check_type_conditional(text, msg_type))
    m_warnings: list[str] = []
    if state is not None:
        ce, cw = check_cross_turn_rules(text, msg_type, state)
        m_errors.extend(ce)
        m_warnings.extend(cw)
    if m_errors:
        violations["marketer_errors"] = m_errors
    if m_warnings:
        violations["marketer_warnings"] = m_warnings

    return violations


# ─────────────────────────────────────────────
#  §5.2 Drop-in — 패턴 / 체크 함수 / ValidationResult
#
#  출처: SIA_SESSION4_V2 §5.2 코드 (마케터 완결판).
#  수정 사항:
#    - _BANMAL_END_PATTERN 를 "문장 끝 앵커" 로 tighten.
#      원문 `(?=[\s.!?]|$)` 는 공백 뒤 다른 단어가 이어지는 간접 의문 (`~는지 살펴`)
#      에서 false positive 발생 → `(?=[.!?]|\s*$)` 로 좁힘. 반말 종결 의도 유지.
# ─────────────────────────────────────────────

# A-1 전역
_KU_PATTERN = re.compile(r"ㅋ+")
_GUNNA_PATTERN = re.compile(
    r"(했|했었|었|였|셨|느꼈|느끼셨|봤|보셨|들었|들으셨|먹었|갔|가셨)구나(?!요)"
)
_BANMAL_END_PATTERN = re.compile(
    r"(?<=[가-힣])[네나야지군](?=[.!?]|\s*$)(?!요)"
)
_DOUBLE_CONTRAST_PATTERN = re.compile(r"인 거예요[,\s.]*\S*\s*아니")
_AXIS_LABEL_PATTERN = re.compile(
    r"(?<![\w가-힣])(색깔|구도|표정|체형)요(?![\w가-힣])"
)
_VICTORY_PATTERNS = [
    re.compile(r"잡았어요"),
    re.compile(r"말해주던데요"),
    re.compile(r"알고 계셨던 거잖아요"),
    re.compile(r"이미 아시는"),
    re.compile(r"본인도 느끼는"),
]
_ABSOLUTE_OBSERVATION = [
    re.compile(r"거의 전부"),
    re.compile(r"하나도 없"),
    re.compile(r"한 번도 없"),
]

# A-5 RECOGNITION 단정 ~예요 금지 (질문 부호 없는 예요 단독)
_RECOGNITION_YEYO_RE = re.compile(r"예요(?![?])")

_COLLECTION_TYPES = {MsgType.OBSERVATION, MsgType.PROBE, MsgType.EXTRACTION}


def check_global_forbidden(draft: str, msg_type: MsgType) -> list[str]:
    """§5.2 전역 A-1 확장 체크. 타입 독립."""
    errors: list[str] = []
    if _KU_PATTERN.search(draft):
        errors.append("A-1: ㅋ 전역 금지")
    if _GUNNA_PATTERN.search(draft):
        errors.append("A-1: ~구나 단독 사용 금지")
    if _BANMAL_END_PATTERN.search(draft):
        errors.append("A-1: 반말 종결 금지")
    if _DOUBLE_CONTRAST_PATTERN.search(draft):
        errors.append("A-1: 이중 대비 결론 금지")
    if _AXIS_LABEL_PATTERN.search(draft):
        errors.append("A-1: 축 라벨 단독 호명 금지")
    for pat in _VICTORY_PATTERNS:
        if pat.search(draft):
            errors.append(f"A-1: 승리 표현 금지 ({pat.pattern})")
    if msg_type in _COLLECTION_TYPES:
        for pat in _ABSOLUTE_OBSERVATION:
            if pat.search(draft):
                errors.append(f"A-1: 관찰 절대 표현 금지 ({pat.pattern})")
    return errors


def check_type_conditional(draft: str, msg_type: MsgType) -> list[str]:
    """§5.2 타입 조건부 체크. A-4 EMPATHY ~잖아요 / A-5 RECOGNITION ~예요 단정."""
    errors: list[str] = []
    if msg_type in QUESTION_REQUIRED and "?" not in draft:
        errors.append(f"A-8: {msg_type.value} 질문 종결 누락")
    if msg_type in QUESTION_FORBIDDEN and "?" in draft:
        errors.append(f"A-8: {msg_type.value} 질문 부호 금지")
    if msg_type == MsgType.EMPATHY_MIRROR and "잖아요" in draft:
        errors.append("A-4: EMPATHY_MIRROR 에서 ~잖아요 금지")
    if msg_type == MsgType.RECOGNITION and _RECOGNITION_YEYO_RE.search(draft):
        errors.append("A-5: RECOGNITION 에서 단정 ~예요 금지")
    return errors


def check_cross_turn_rules(
    draft: str, msg_type: MsgType, state: ConversationState,
) -> tuple[list[str], list[str]]:
    """§5.2 cross-turn: ~잖아요 창 합 / ~예요 연타 / EMPATHY 누적 비율 경고."""
    errors: list[str] = []
    warnings: list[str] = []
    recent = state.recent_assistant_drafts(n=3)
    jangayo_count = sum(1 for d in recent if "잖아요" in d)
    jangayo_count += draft.count("잖아요")
    if jangayo_count > 2:
        errors.append(f"A-2: ~잖아요 3 메시지 창 {jangayo_count}회 초과")
    if recent and "예요" in recent[-1] and "예요" in draft:
        soft_forms = ["네요", "더라구요", "던데요"]
        soft_count = sum(
            any(f in d for f in soft_forms) for d in recent + [draft]
        )
        if soft_count == 0:
            errors.append("A-2: ~예요 연타, ~네요/~더라구요/~던데요 필요")
    if msg_type == MsgType.EMPATHY_MIRROR:
        type_counts = state.type_distribution()
        total = sum(type_counts.values()) + 1
        em_pct = (type_counts.get(MsgType.EMPATHY_MIRROR, 0) + 1) / total
        if em_pct > 0.15:
            warnings.append(
                f"A-2 sub-rule: EMPATHY_MIRROR {em_pct:.1%} > 15% "
                "(A-3 트리거 우선이면 허용)"
            )
    return errors, warnings


class ValidationResult:
    """§5.2 공식 결과 타입. errors = 하드 위반, warnings = sub-rule 경고."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


def validate(
    draft: str,
    msg_type: MsgType,
    state: Optional[ConversationState] = None,
) -> ValidationResult:
    """§5.2 공식 drop-in API.

    state None 허용 (테스트 편의). state 없으면 cross-turn 체크 생략.
    """
    result = ValidationResult()
    result.errors.extend(check_global_forbidden(draft, msg_type))
    result.errors.extend(check_type_conditional(draft, msg_type))
    if state is not None:
        ce, cw = check_cross_turn_rules(draft, msg_type, state)
        result.errors.extend(ce)
        result.warnings.extend(cw)
    return result


# ─────────────────────────────────────────────
#  Turn 어미 카운트 충전 (AssistantTurn.*_count populate)
# ─────────────────────────────────────────────

def populate_turn_counts(turn: AssistantTurn) -> AssistantTurn:
    """생성된 AssistantTurn 의 어미 카운트 필드를 text 로부터 충전.

    validator 와 동일 regex 재사용 — count 가 state 카운터와 일관.
    같은 turn 객체를 반환 (mutation + return).
    """
    turn.jangayo_count = count_jangayo(turn.text)
    turn.deoraguyo_count = count_deoraguyo(turn.text)
    turn.neyo_count = count_neyo(turn.text)
    turn.yeyo_count = count_yeyo(turn.text)
    return turn
