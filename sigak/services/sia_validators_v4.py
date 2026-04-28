"""Sia validator v4 — 페르소나 C + 메시지 단위 규칙 (Phase H3, 14 타입 확정판).

페르소나 C "겸손한 경력 디자이너 친구" 전환 (2026-04-27) 에 따른 신규 차단:
  A-21 자기과시·자존심 어휘 hard reject — "직설적으로 말씀드릴게요",
       "사실은 ~인 거", "제가 보기엔", "본질은 ~", "분명히/확실히" 등
  A-22 닫힌 어미 hard reject — `~한 편이세요?`, `~이시잖아요?`,
       `~가봐요?`, `~이신 것 같은데`, `~으시죠?`, `~잖아요?` 등
       네/아니오 답이 가능하거나 동의 강요하는 모든 어미

SPEC 출처: .moai/specs/SPEC-SIA/
  - 세션 #4 v2 §5.2 (A-1~A-8 base + §5.2 drop-in)
  - 세션 #6 v2 §9.1-9.3 (CHECK_IN / RE_ENTRY / RANGE_DISCLOSURE 전용 체크)
  - 세션 #7 §1.3 (EMPATHY 결합 출력 — is_combined 시 `?` 허용)
  - 세션 #7 §2.8 (C6 draft 검증 — 평가 직접 답변 금지)
  - 세션 #7 §3.8 (C7 draft 검증 — 위로형/전면 부정 금지)
  - 세션 #7 §8.3 (check_haiku_naturalness — 분석 jargon + 어색 종결)
  - 페르소나 C 전환 (2026-04-27) — A-21 자기과시 / A-22 닫힌 어미

규칙 요약 (기존 유지):
  A-1  전역 금지 어미 + §5.2 확장
  A-2  ~잖아요 3턴 창 / ~예요 연타 softener / EMPATHY 누적 비율 경고
  A-3  ~더라구요 3턴 창
  A-4  같은 msg_type 3연속
  A-5  RECOGNITION 단정 ~예요 금지
  A-6  QUESTION_REQUIRED 질문 종결 누락 / QUESTION_FORBIDDEN 질문 부호 금지
       (세션 #7 §1.3: EMPATHY is_combined=True 시 `?` 허용)
  A-7  EMPATHY_MIRROR 감정 원어 미반사
  A-8  60자 초과 절

신규 (세션 #6 v2 / 세션 #7):
  CHECK_IN           전용 — 속도 옵션 + 이탈 옵션 필수 + 금지 표현
  RE_ENTRY           전용 — 직전 CHECK_IN + 완화 표현 필수
  RANGE_DISCLOSURE   전용 — 범위 명시 (limit 모드만) + 자기부정/관계형성 금지
  C6                 블록 — 평가 직접 답변 / 무조건 칭찬 / 해석 회피 금지
  C7                 블록 — 위로형 부정 / 전면 부정 금지
  ~구나 solo         — 뒤에 서술 연결 없으면 위반 (세션 #4 v2 §9.5 정확 해석)
  Haiku naturalness  — 분석 jargon (모드/포지셔닝/디퓨전/메타인지/클러스터링/매핑/프로파일) +
                      어색 종결 (~면요/~이긴 한데요/~인 셈이죠)

공개 API:
  find_violations_v4(text, msg_type, state, emotion_word_raw, *, range_mode,
                     confrontation_block, is_combined) -> dict
  validate(draft, msg_type, state, *, range_mode, confrontation_block,
           is_combined) -> ValidationResult
  check_haiku_naturalness(draft) -> list[str]
"""
from __future__ import annotations

# ─────────────────────────────────────────────
# v4 QUARANTINE (2026-04-28) — 페르소나 C 시대 코드.
# Phase 3 재작성 정책:
#   - A-17 (가격/결제) 보존
#   - A-23 (환각 가드) 보존
#   - A-30 (AI틱 어휘 차단) 신설
#   - A-34 (MI 원칙 + 매턴 anchor) 신설
#   - A-1~A-22 본문 폐기 (시그니처는 호환 위해 유지 가능)
# 런타임 보호: SIA_V4_MAINTENANCE=true 시 /sia/* 503 응답.
# Archive: sigak/services/_legacy_persona_c/README.md 참조.
# ─────────────────────────────────────────────

import re
from typing import Optional

from schemas.sia_state import (
    QUESTION_FORBIDDEN,
    QUESTION_REQUIRED,
    AssistantTurn,
    ConversationState,
    MsgType,
    OverattachmentSeverity,
    RangeMode,
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
    *,
    range_mode: RangeMode = "limit",
    confrontation_block: Optional[str] = None,
    is_combined: bool = False,
    exit_confirmed: bool = False,
) -> dict[str, list[str]]:
    """Phase H 14 타입 전수 검증. base violations + A-1~A-8 + 세션 #6/7 결과 dict 병합.

    Parameters
    ----------
    text : 검증 대상 Sia 응답.
    msg_type : 현재 생성 타입 (A-5/A-6/A-7 맥락).
    state : 누적 state — A-2/A-3/A-4 창 체크에 필요. None 이면 스킵.
    emotion_word_raw : 최근 유저 메시지의 첫 감정 원어 — A-7 체크에 필요.
    range_mode : RANGE_DISCLOSURE 모드 게이팅.
    confrontation_block : CONFRONTATION 세부 블록 (C1~C7). C6/C7 이면 블록 체크.
    is_combined : EMPATHY 결합 출력 — 질문 부호 허용.
    exit_confirmed : RE_ENTRY V5 (향후 확장용).

    Returns
    -------
    dict — base + A-1~A-8 + marketer_errors + marketer_warnings +
           type_specific / block_specific / haiku_naturalness 키. 빈 dict = clean.
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
    # + 세션 #6/7 전용 체크 (CHECK_IN/RE_ENTRY/RANGE/C6/C7/naturalness)
    # ─────────────────────────────────────────────
    m_errors: list[str] = []
    m_errors.extend(check_global_forbidden(text, msg_type))
    m_errors.extend(
        check_type_conditional(
            text, msg_type,
            is_combined=is_combined,
            confrontation_block=confrontation_block,
        )
    )

    # 관리 3 타입 전용
    if msg_type == MsgType.CHECK_IN:
        m_errors.extend(check_check_in(text))
    elif msg_type == MsgType.RE_ENTRY:
        m_errors.extend(
            check_re_entry(text, state=state, exit_confirmed=exit_confirmed)
        )
    elif msg_type == MsgType.RANGE_DISCLOSURE:
        sev = state.overattachment_severity if state is not None else ""
        m_errors.extend(
            check_range_disclosure(text, range_mode=range_mode, severity=sev)
        )

    # CONFRONTATION 블록
    if msg_type == MsgType.CONFRONTATION:
        if confrontation_block == "C6":
            m_errors.extend(check_confrontation_c6(text))
        elif confrontation_block == "C7":
            m_errors.extend(check_confrontation_c7(text))

    # Haiku naturalness 전 타입 공통
    m_errors.extend(check_haiku_naturalness(text))

    # A-17/A-20/A-18/Markdown hard reject (유저 실측 피드백)
    m_errors.extend(check_a17_commerce(text))
    m_errors.extend(check_a20_abstract_praise(text))
    m_errors.extend(check_a18_length(text))
    m_errors.extend(check_markdown_markup(text))
    # A-21/A-22 hard reject (페르소나 C 전환)
    m_errors.extend(check_a21_self_promotion(text))
    m_errors.extend(check_a22_closed_endings(text))

    m_warnings: list[str] = []
    m_warnings.extend(check_a18_length_warning(text))
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

# 세션 #4 v2 §9.5: "단독 'X구나' 금지 (뒤에 서술 연결 필수)".
# 정확 해석 — 구나 뒤에 실질 서술이 이어지면 허용. 단독이면 위반.
# 검출 2단계:
#   (a) 구나 어간 위치 탐색 (_GUNNA_STEM_RE.finditer)
#   (b) 각 매치 뒤 텍스트에 실질 content 있는지 확인 (_is_gunna_solo)
_GUNNA_STEM_RE = re.compile(
    r"(했|했었|었|였|셨|느꼈|느끼셨|봤|보셨|들었|들으셨|먹었|갔|가셨)구나(?!요)"
)
_BANMAL_END_PATTERN = re.compile(
    # (?<!구) — "구나" 어미는 _GUNNA_STEM_RE 가 전담 (solo vs connected 분기).
    # BANMAL 은 "구나" 를 무조건 반말로 처리하지 않음 (세션 #6 v2 RE_ENTRY "아 그러셨구나." 허용).
    r"(?<=[가-힣])(?<!구)[네나야지군](?=[.!?]|\s*$)(?!요)"
)


def _is_gunna_solo(draft: str) -> bool:
    """구나 종결 후 실질 서술 연결이 없으면 True (단독 위반).

    뒤 텍스트에서 공백/구두점 제외한 내용이 있으면 "연결" — 허용.
    RE_ENTRY V0 "아 그러셨구나. 그럼 제가 본 걸 정리해서..." 같은 케이스 보호.
    """
    for m in _GUNNA_STEM_RE.finditer(draft):
        after = draft[m.end():]
        stripped = re.sub(r"[.!?,\s]", "", after)
        if not stripped:
            return True
    return False
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
    """§5.2 전역 A-1 확장 체크. 타입 독립.

    Note: `_is_gunna_solo` 는 세션 #4 v2 §9.5 "단독 금지" 규정 정확 반영 — 구나
    뒤 서술 연결이 있으면 허용 (RE_ENTRY V0 등 정상 케이스 보호).
    """
    errors: list[str] = []
    if _KU_PATTERN.search(draft):
        errors.append("A-1: ㅋ 전역 금지")
    if _is_gunna_solo(draft):
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


def check_type_conditional(
    draft: str,
    msg_type: MsgType,
    *,
    is_combined: bool = False,
    confrontation_block: Optional[str] = None,
) -> list[str]:
    """§5.2 타입 조건부 체크. A-4 EMPATHY ~잖아요 / A-5 RECOGNITION ~예요 단정.

    is_combined (세션 #7 §1.3 + §1.5 일반화):
      결합 출력 시 primary 타입의 질문 종결 규정이 완화됨 — secondary 문장이
      `?` 유/무를 정할 수 있으므로.
      - QUESTION_REQUIRED + is_combined: `?` 누락 허용 (secondary 가 서술 마감 가능)
      - QUESTION_FORBIDDEN + is_combined: `?` 허용 (secondary 가 질문 마감 가능)
      - EMPATHY_MIRROR `~잖아요` + is_combined: 허용 (secondary RECOGNITION 등 자연)

    confrontation_block == "C7" (세션 #7 §3.7):
      일반화 회피 돌파 블록은 질문 종결 OR 진단 예고 둘 다 허용. 진단 예고 시
      `?` 없어도 A-8 에러 아님.
    """
    errors: list[str] = []
    if msg_type in QUESTION_REQUIRED and "?" not in draft:
        # is_combined: secondary 가 서술 마감 가능
        # C7: 진단 예고 모드
        if is_combined:
            pass
        elif msg_type == MsgType.CONFRONTATION and confrontation_block == "C7":
            pass
        else:
            errors.append(f"A-8: {msg_type.value} 질문 종결 누락")
    if msg_type in QUESTION_FORBIDDEN and "?" in draft:
        # is_combined: secondary 가 질문 마감 가능
        if not is_combined:
            errors.append(f"A-8: {msg_type.value} 질문 부호 금지")
    if msg_type == MsgType.EMPATHY_MIRROR and "잖아요" in draft:
        # is_combined: secondary 문장에 잖아요 허용
        if not is_combined:
            errors.append("A-4: EMPATHY_MIRROR 에서 ~잖아요 금지")
    if msg_type == MsgType.RECOGNITION and _RECOGNITION_YEYO_RE.search(draft):
        errors.append("A-5: RECOGNITION 에서 단정 ~예요 금지")
    return errors


# ─────────────────────────────────────────────
#  세션 #6 v2 §9.1-9.3 — 관리 3 타입 전용 체크
# ─────────────────────────────────────────────

# CHECK_IN 필수 표현 (§9.1)
_CHECK_IN_PACE_MARKERS = ("편한 속도", "천천히", "편하신 만큼")
_CHECK_IN_EXIT_MARKERS = ("그만", "여기까지", "나중에", "다음에", "멈추")
_CHECK_IN_FORBIDDEN = ("조금만 더", "벌써요", "아쉽네요", "왜 그러세요")

# RE_ENTRY 반응 기준 완화 표현 (§9.2)
_RE_ENTRY_RELAXED_MARKERS = (
    "맞다 아니다만", "편하신 만큼", "반응만 주셔도", "반응해주셔도",
    "반응 주셔도", "그냥 들으셔도", "들으셔도 되고", "들으셔도 돼",
    "언제든 돌아오시면",   # V5 이탈 종결 — 재진입 경로도 완화 의미 포함
)

# RANGE_DISCLOSURE 범위 명시 (§9.3, limit 모드 전용)
_RANGE_SCOPE_RE = re.compile(r"피드\s*(만|을|에서|안|\d+장)")

# RANGE_DISCLOSURE 자기부정 금지 (§9.3)
_RANGE_SELF_NEGATE = (
    "별 의미 없", "저는 AI 라서",
    "한 건 아무것도", "무시하셔도",
)

# RANGE_DISCLOSURE 관계 형성 금지 (§9.3)
# 주의: "언제든 돌아오시면" (RE_ENTRY V5) 과 "언제든 말씀" 구별 위해 정확 매치
_RANGE_RELATIONAL = (
    "저도 좋아", "언제든 말씀", "친구처럼",
)


def check_check_in(draft: str) -> list[str]:
    """CHECK_IN 구조 검증 (세션 #6 v2 §9.1).

    요구사항: 속도 옵션 + 이탈 옵션 둘 다 필수. 금지 표현 불가.
    """
    errors: list[str] = []
    has_pace = any(m in draft for m in _CHECK_IN_PACE_MARKERS)
    has_exit = any(m in draft for m in _CHECK_IN_EXIT_MARKERS)
    if not has_pace:
        errors.append("CHECK_IN: 속도 옵션 누락 (편한 속도 / 천천히 / 편하신 만큼)")
    if not has_exit:
        errors.append(
            "CHECK_IN: 이탈 옵션 누락 (그만 / 여기까지 / 나중에 / 다음에 / 멈추)"
        )
    for forbidden in _CHECK_IN_FORBIDDEN:
        if forbidden in draft:
            errors.append(f"A-10: CHECK_IN 금지 표현 ({forbidden})")
    return errors


def check_re_entry(
    draft: str,
    state: Optional[ConversationState] = None,
    *,
    exit_confirmed: bool = False,
) -> list[str]:
    """RE_ENTRY 구조 검증 (세션 #6 v2 §9.2).

    요구사항:
      - 직전 assistant 턴이 CHECK_IN (state 전달 시 확인)
      - 반응 기준 완화 표현 필수 (V0~V4) 또는 종결 V5 표현 ("언제든 돌아오시면")
    """
    errors: list[str] = []
    if state is not None:
        a_turns = state.assistant_turns()
        if not a_turns or a_turns[-1].msg_type != MsgType.CHECK_IN:
            errors.append("RE_ENTRY: 직전 assistant 턴이 CHECK_IN 이어야 함")
    if not any(m in draft for m in _RE_ENTRY_RELAXED_MARKERS):
        errors.append(
            "RE_ENTRY: 반응 기준 완화 표현 필요 "
            "(맞다 아니다만 / 편하신 만큼 / 반응만 주셔도 / 들으셔도)"
        )
    return errors


def check_range_disclosure(
    draft: str,
    *,
    range_mode: RangeMode = "limit",
    severity: OverattachmentSeverity = "",
) -> list[str]:
    """RANGE_DISCLOSURE 구조 검증 (세션 #6 v2 §9.3).

    limit + non-severe: 범위 명시 ("피드 N장" / "피드 안" 등) 필수.
    limit + severe (세션 #6 v2 §10.4 SV0 등): 외부 자원 권유가 주 목적이라 범위 명시
      우회 가능 — 체크 제외.
    reaffirm (세션 #7 §1.6): 범위 명시 불필요 — 사업 존재 재선언이 핵심.
    공통: 자기부정 금지 + 관계 형성 금지.
    """
    errors: list[str] = []
    if (
        range_mode == "limit"
        and severity != "severe"
        and not _RANGE_SCOPE_RE.search(draft)
    ):
        errors.append("RANGE_DISCLOSURE(limit): 범위 명시 필요 (피드 N장 / 피드 안)")
    for neg in _RANGE_SELF_NEGATE:
        if neg in draft:
            errors.append(f"A-11: RANGE_DISCLOSURE 자기부정 금지 ({neg})")
    for rel in _RANGE_RELATIONAL:
        if rel in draft:
            errors.append(f"A-11: RANGE_DISCLOSURE 관계 형성 금지 ({rel})")
    return errors


# ─────────────────────────────────────────────
#  세션 #7 §2.8 / §3.8 — C6 / C7 블록별 체크
# ─────────────────────────────────────────────

# C6 평가 직접 답변 금지 (§2.6)
_C6_EVAL_ANSWER_PATTERNS = [
    re.compile(r"(네|예)\s*(예뻐|매력\s*있|과한|부족|어색|이상)"),
    re.compile(r"예뻐요"),
    re.compile(r"과한\s*(부분|게)"),
    re.compile(r"부족한\s*(부분|게)"),
    # "본인만의 매력" substring — 조사/어미 상관없이 무조건 칭찬 예시 커버
    re.compile(r"본인만의\s*매력"),
    re.compile(r"답할\s*수\s*없"),
    re.compile(r"진단\s*결과에서"),
]

# C7 위로형 / 전면 부정 금지 (§3.6)
_C7_PLACATE_PATTERNS = [
    re.compile(r"(특별해요|특별하세요|특별하신)"),
    re.compile(r"다들\s*그런\s*게\s*아니"),
    re.compile(r"다들이?\s*아니라"),   # "다들이 아니라 X님의 정답" 류
]


def check_confrontation_c6(draft: str) -> list[str]:
    """C6 평가 의존 돌파 블록 검증 (세션 #7 §2.8).

    금지:
      - 평가 직접 답변 ("네 매력 있어요" / "좀 과해요")
      - 무조건 칭찬 ("본인만의 매력이 있어요")
      - 해석 회피 ("그건 제가 답할 수 없어요")
      - 진단 회피로 후퇴 ("그건 진단 결과에서 보여드릴게요")
    """
    errors: list[str] = []
    for pat in _C6_EVAL_ANSWER_PATTERNS:
        if pat.search(draft):
            errors.append(f"C6: 평가 직접 답변/회피 금지 ({pat.pattern})")
    return errors


def check_confrontation_c7(draft: str) -> list[str]:
    """C7 일반화 회피 돌파 블록 검증 (세션 #7 §3.8).

    금지:
      - 위로형 부정 ("도윤님은 특별해요")
      - 전면 부정 ("다들 그런 게 아니에요")
      - 일반화 부정 후 정답 제시 ("다들이 아니라 X님의 정답은 ~예요")
    """
    errors: list[str] = []
    for pat in _C7_PLACATE_PATTERNS:
        if pat.search(draft):
            errors.append(f"C7: 위로형/전면 부정 금지 ({pat.pattern})")
    return errors


# ─────────────────────────────────────────────
#  세션 #7 §8.3 — Haiku 어휘 자연스러움 (A-2 확장)
# ─────────────────────────────────────────────

# 분석 jargon (base.jinja 금지 목록)
# "모드" 는 복합 단어 ("다른 모드로", "모드 전환" 등) 에서도 jargon 으로 본다 —
# lookbehind 로 단어 시작 경계만 체크 ("모두" 는 매치 안 됨, 첫 글자 다름).
_JARGON_PATTERNS = [
    re.compile(r"(?<![\w가-힣])모드"),
    re.compile(r"포지셔닝"),
    re.compile(r"디퓨전"),
    re.compile(r"메타인지"),
    re.compile(r"클러스터링"),
    re.compile(r"매핑"),
    re.compile(r"프로파일"),
]

# 어색 종결
_AWKWARD_END_PATTERNS = [
    re.compile(r"면요\s*[.!?]?\s*$"),
    re.compile(r"이긴\s*한데요\s*[.!?]?\s*$"),
    re.compile(r"인\s*셈이죠\s*[.!?]?\s*$"),
]


def check_haiku_naturalness(draft: str) -> list[str]:
    """A-2 Haiku 어휘 자연스러움 — 분석 jargon + 어색 종결 검출.

    세션 #7 §8.3 validator 추가. A-14 사족 금지는 의미 판정이라 Haiku self-check
    로만 처리 (validator 자동 불가).
    """
    errors: list[str] = []
    for pat in _JARGON_PATTERNS:
        if pat.search(draft):
            errors.append(f"A-2: 분석 jargon ({pat.pattern})")
    for pat in _AWKWARD_END_PATTERNS:
        if pat.search(draft):
            errors.append(f"A-2: 어색한 종결 ({pat.pattern})")
    return errors


# ─────────────────────────────────────────────
#  A-17 가격/결제/상품 응대 hard reject (유저 실측 피드백)
# ─────────────────────────────────────────────

_COMMERCE_PATTERNS = [
    # 영업 어휘 (실 유저 대화에서 검출됨)
    re.compile(r"다음\s*단계"),
    re.compile(r"풀어드릴"),
    re.compile(r"정리해드릴"),
    re.compile(r"추천해드릴"),
    re.compile(r"핵심\s*포인트"),
    # 상품명 직접 호명
    re.compile(r"리포트"),
    re.compile(r"컨설팅"),
    re.compile(r"구독"),
    re.compile(r"티어"),
    re.compile(r"프리미엄"),
    re.compile(r"Premium", re.IGNORECASE),
    # 진단 상품화 어휘
    re.compile(r"진단에서"),
    re.compile(r"진단을\s"),
    re.compile(r"진단으로"),
    # 가격 수치
    re.compile(r"₩\s*\d"),
    re.compile(r"\d[\d,]*\s*원"),   # "49,000원", "49,000원에" 모두 매칭 (가격 전수 차단)
    re.compile(r"\d+\s*토큰"),
    re.compile(r"\d+\s*만원"),
]


def check_a17_commerce(draft: str) -> list[str]:
    """A-17 — 가격/결제/상품 응대 hard reject.

    유저 실측 대화에서 Sia 가 "피드 진단 리포트(₩49,000)", "구독 상품", "다음 단계"
    류 영업 어휘 사용 → 페르소나 B 친구 포지션 정면 위반. 전수 hard block.
    """
    errors: list[str] = []
    for pat in _COMMERCE_PATTERNS:
        m = pat.search(draft)
        if m:
            errors.append(f"A-17: 영업/상품 어휘 금지 — '{m.group(0)}'")
    return errors


# ─────────────────────────────────────────────
#  A-20 추상 칭찬어 hard reject (유저 실측 피드백)
# ─────────────────────────────────────────────

_ABSTRACT_PRAISE_PATTERNS = [
    re.compile(r"매력적"),
    re.compile(r"매력(이|을|은|있|이에|이세|있으|있는)"),
    re.compile(r"독특(한|해|하|이)"),
    re.compile(r"특별(한|해|하|이)"),
    re.compile(r"흥미로(운|워|우)"),
    re.compile(r"인상적(인|이)"),
    re.compile(r"센스\s*(있|있는|있으세|이\s*있)"),
    re.compile(r"안목\s*(이|을|있)"),
    re.compile(r"감각\s*이\s*있"),
]


def check_a20_abstract_praise(draft: str) -> list[str]:
    """A-20 — 추상 칭찬어 hard reject.

    "매력 / 독특 / 특별 / 흥미로운 / 인상적 / 센스 / 안목" 류 AI 티 나는 추상
    찬사 전수 금지. 대체는 구체 관찰 / 유저다움 표현 / 행동 짚기 (base.md 참조).
    """
    errors: list[str] = []
    for pat in _ABSTRACT_PRAISE_PATTERNS:
        m = pat.search(draft)
        if m:
            errors.append(f"A-20: 추상 칭찬어 금지 — '{m.group(0)}'")
    return errors


# ─────────────────────────────────────────────
#  A-18 발화 길이 원칙 (유저 실측 피드백)
# ─────────────────────────────────────────────

A18_MAX_CHARS_HARD = 300          # 이 이상 hard reject
A18_MAX_CHARS_WARNING = 200       # 이 이상 warning
A18_MAX_SENTENCES = 3             # 초과 시 warning (hard reject 까지는 아님)

_SENTENCE_SPLIT_RE = re.compile(r"[.!?]+[\s\n]+|[.!?]+$")


def _count_sentences(draft: str) -> int:
    text = draft.strip()
    if not text:
        return 0
    parts = [p for p in _SENTENCE_SPLIT_RE.split(text) if p.strip()]
    return len(parts)


def check_a18_length(draft: str) -> list[str]:
    """A-18 — 발화 길이 원칙. 300자 초과 hard reject. 4문장 이상 warning-only 는
    check_a18_length_warning 별도."""
    errors: list[str] = []
    total = len(draft)
    if total > A18_MAX_CHARS_HARD:
        errors.append(
            f"A-18: 발화 길이 {total}자 > {A18_MAX_CHARS_HARD}자 hard reject"
        )
    return errors


def check_a18_length_warning(draft: str) -> list[str]:
    """A-18 warning — 200자 초과 또는 4문장 이상 경고 (hard reject 아님)."""
    warnings: list[str] = []
    total = len(draft)
    if A18_MAX_CHARS_WARNING < total <= A18_MAX_CHARS_HARD:
        warnings.append(
            f"A-18: 발화 길이 {total}자 > {A18_MAX_CHARS_WARNING}자 (권장 초과)"
        )
    sents = _count_sentences(draft)
    if sents > A18_MAX_SENTENCES:
        warnings.append(
            f"A-18: 문장 수 {sents} > {A18_MAX_SENTENCES} (연설 회피 권장)"
        )
    return warnings


# ─────────────────────────────────────────────
#  마크다운 강조 hard reject (유저 실측 피드백 — 프론트 별 하나도 X)
# ─────────────────────────────────────────────

_MARKDOWN_PATTERNS = [
    re.compile(r"\*\*[^*\n]+\*\*"),             # **text**
    re.compile(r"(?<![*\w])\*(?!\s)[^*\n]+?\*(?!\w)"),  # *text* (소개 bullet 제외)
    re.compile(r"^#{1,6}\s", re.MULTILINE),     # heading
    re.compile(r"^>\s", re.MULTILINE),          # blockquote
    re.compile(r"```"),                          # code block
]


def check_markdown_markup(draft: str) -> list[str]:
    """마크다운 강조 hard reject.

    프론트는 순수 텍스트 렌더 전제. `*`, `**`, `##`, `>`, ``` 는 AI 티 내며
    조판 깨짐. base.md 에서 이미 금지했지만 Haiku 가 어기는 경우 validator 차단.
    """
    errors: list[str] = []
    for pat in _MARKDOWN_PATTERNS:
        if pat.search(draft):
            errors.append(f"마크다운 강조 금지 ({pat.pattern})")
    return errors


# ─────────────────────────────────────────────
#  A-21 자기과시·자존심 어휘 hard reject (페르소나 C 전환, 2026-04-27)
#
#  소비자 FGI: "직설적으로 말씀드릴게요" / "사실은 ~인 거" / "제가 보기엔" /
#  "본질은 ~" / "분명히/확실히" 류가 "MZ 사원 자존심" / "통찰 자랑" 으로
#  체감됨. 페르소나 C "겸손한 경력 디자이너" 정신과 정면 충돌 → 전수 차단.
# ─────────────────────────────────────────────

_A21_SELF_PROMOTION_PATTERNS = [
    # 가식 직설
    re.compile(r"직설적으로\s*(말씀\s*드릴|말씀드릴|말할|얘기)"),
    re.compile(r"솔직히\s*(말해|말씀)"),
    # 재프레임 단정
    re.compile(r"사실은\s*[가-힣]+인\s*거"),
    re.compile(r"본질은\s*[가-힣]"),
    re.compile(r"본질이\s*[가-힣]"),
    # 자기 권위 호명
    re.compile(r"제가\s*보기엔"),
    re.compile(r"제가\s*본\s*바"),
    # 단정 강도
    re.compile(r"(?<![\w가-힣])분명히\s*[가-힣]"),
    re.compile(r"(?<![\w가-힣])확실히\s*[가-힣]"),
    re.compile(r"(?<![\w가-힣])명백히\s*[가-힣]"),
    # 통찰 자랑
    re.compile(r"그게\s*핵심"),
]


def check_a21_self_promotion(draft: str) -> list[str]:
    """A-21 — 자기과시·자존심 톤 hard reject (페르소나 C 전환).

    유저가 "MZ 사원 자존심" / "통찰 자랑" 으로 체감하는 어휘 차단.
    대안: 본 것을 담담히 진술 + 유저에게 풀어달라는 열린 질문.
    """
    errors: list[str] = []
    for pat in _A21_SELF_PROMOTION_PATTERNS:
        m = pat.search(draft)
        if m:
            errors.append(f"A-21: 자기과시 어휘 금지 — '{m.group(0)}'")
    return errors


# ─────────────────────────────────────────────
#  A-22 닫힌 어미 hard reject (페르소나 C 전환, 2026-04-27)
#
#  네/아니오 답이 가능하거나 동의를 강요하는 모든 어미 차단.
#  페르소나 B 시절 핵심 무기 (`~가봐요?`, `~이시잖아요?`, `~한 편이세요?`)
#  가 소비자에게 "잘못 번역된 MBTI 검사" / "맞추려고 함" 으로 체감됨.
#  대안: 유저 원어 반사 + 구체 관찰 + 열린 질문 3단 구조 (base.md A-22).
# ─────────────────────────────────────────────

_A22_CLOSED_ENDING_PATTERNS = [
    # ~편이세요? / ~편이신가요? (카테고라이징 — MBTI 톤 핵심).
    # "X한 편이세요" 외에도 "좋아하시는 편이세요" / "쓰시는 편이세요" 등
    # 다양한 활용형 모두 차단 — "편이세요?" 자체가 닫힌 카테고라이징 신호.
    re.compile(r"편이세요\s*\?"),
    re.compile(r"편이신가요\s*\?"),
    re.compile(r"편이신지\s*\?"),
    # ~이시잖아요? / ~이신 거잖아요? / ~잖아요? (닫힌 동의 유도)
    re.compile(r"이시잖아요\s*\?"),
    re.compile(r"이신\s*거잖아요\s*\?"),
    re.compile(r"잖아요\s*\?"),
    # ~가봐요? / ~이신가봐요? (추정 반문 — B 무기)
    re.compile(r"가\s*봐요\s*\?"),
    re.compile(r"가봐요\s*\?"),
    re.compile(r"이신가봐요\s*\?"),
    # ~이신 것 같은데 / ~이신 것 같 (단정 추측)
    re.compile(r"이신\s*것\s*같은데"),
    re.compile(r"이신\s*것\s*같"),
    # ~으시죠? / ~시죠? (동의 강요)
    re.compile(r"으시죠\s*\?"),
    re.compile(r"(?<![\w가-힣])시죠\s*\?"),
]


def check_a22_closed_endings(draft: str) -> list[str]:
    """A-22 — 닫힌 어미 hard reject (페르소나 C 전환).

    "~한 편이세요?" / "~이시잖아요?" / "~가봐요?" / "~이신 것 같은데" 등
    네/아니오 단답이 가능하거나 동의를 강요하는 어미 전면 차단.

    EMPATHY 결합 출력 (is_combined=True) 의 secondary 문장에서도 차단 —
    페르소나 C 에서는 어떤 컨텍스트에서도 닫힌 어미 사용 X.
    """
    errors: list[str] = []
    for pat in _A22_CLOSED_ENDING_PATTERNS:
        m = pat.search(draft)
        if m:
            errors.append(f"A-22: 닫힌 어미 금지 — '{m.group(0).strip()}'")
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
    *,
    range_mode: RangeMode = "limit",
    confrontation_block: Optional[str] = None,
    is_combined: bool = False,
    exit_confirmed: bool = False,
) -> ValidationResult:
    """14 타입 드롭인 validator API.

    Parameters
    ----------
    draft : 검증 대상 Sia 응답 텍스트.
    msg_type : 현재 생성 타입.
    state : 누적 state — cross-turn 체크에 필요. None 이면 cross-turn 생략.
    range_mode : RANGE_DISCLOSURE 모드 (limit | reaffirm). limit 에서만 범위 명시 강제.
    confrontation_block : CONFRONTATION 세부 블록 ("C1"..."C7"). C6 / C7 이면 블록 체크.
    is_combined : EMPATHY 결합 출력 (세션 #7 §1.3). True 이면 질문 부호 허용.
    exit_confirmed : RE_ENTRY V5 종결 플래그. 현재 체크에 사용 안 됨 (향후 확장용).
    """
    result = ValidationResult()
    result.errors.extend(check_global_forbidden(draft, msg_type))
    result.errors.extend(
        check_type_conditional(
            draft, msg_type,
            is_combined=is_combined,
            confrontation_block=confrontation_block,
        )
    )

    # 관리 3 타입 전용 체크 (세션 #6 v2 §9.1-9.3)
    if msg_type == MsgType.CHECK_IN:
        result.errors.extend(check_check_in(draft))
    elif msg_type == MsgType.RE_ENTRY:
        result.errors.extend(
            check_re_entry(draft, state=state, exit_confirmed=exit_confirmed)
        )
    elif msg_type == MsgType.RANGE_DISCLOSURE:
        sev = state.overattachment_severity if state is not None else ""
        result.errors.extend(
            check_range_disclosure(draft, range_mode=range_mode, severity=sev)
        )

    # CONFRONTATION 블록 체크 (세션 #7 §2.8, §3.8)
    if msg_type == MsgType.CONFRONTATION:
        if confrontation_block == "C6":
            result.errors.extend(check_confrontation_c6(draft))
        elif confrontation_block == "C7":
            result.errors.extend(check_confrontation_c7(draft))

    # Haiku 어휘 자연스러움 (세션 #7 §8.3) — 전 타입 공통
    result.errors.extend(check_haiku_naturalness(draft))

    # A-17/A-20 hard reject — 전 타입 공통 (유저 실측 피드백)
    result.errors.extend(check_a17_commerce(draft))
    result.errors.extend(check_a20_abstract_praise(draft))
    # A-18 발화 길이 — hard reject (300자+)
    result.errors.extend(check_a18_length(draft))
    # A-18 길이 warning (200-300자, 4+ 문장)
    result.warnings.extend(check_a18_length_warning(draft))
    # 마크다운 강조 hard reject (프론트 별 하나도 X)
    result.errors.extend(check_markdown_markup(draft))
    # A-21 자기과시 / A-22 닫힌 어미 hard reject — 페르소나 C 전환
    result.errors.extend(check_a21_self_promotion(draft))
    result.errors.extend(check_a22_closed_endings(draft))

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


# ─────────────────────────────────────────────
#  v4 A-30 / A-34  —  페르소나 C → "미감 비서" 전환 (2026-04-28)
#
#  A-30: AI틱 어휘 차단 (HARD reject)
#    - 차단 명사: 결 / 무드 / 결로 가다 / 느낌이 ~다
#    - 차단 약화: 같아요 / 살짝 / 혹시
#    - 차단 안전망: 단정은 아니고 / 잘못 본 걸 수도
#    - 예외 자리 (turn_id 별): T6 좀 / T6 제가 보기엔 / T11 좋을 것 같아요
#
#  A-34: MI 매턴 anchor (시점 / 유니크 / 격차 / 같이 톤 4 중 1+ 필요)
#    - T1 (오프닝) 예외
# ─────────────────────────────────────────────

# A-30 차단 명사 — 두 그룹:
#   1. _A30_NOUN_REGEX: "결" 류 — 단독 명사 또는 "결+조사" 만 차단
#      ("결국" / "결과" / "결혼" 등 합성어는 false positive 회피)
#   2. _A30_NOUN_LITERAL: 고정 phrase
_A30_NOUN_REGEX = [
    # 결: 단독 또는 결+조사 (이/을/은/의/로). "결국" / "결정" 등 단어 일부일 때 미매칭.
    re.compile(r"(?<![\w가-힣])결(?=[이을은의로])"),
]
_A30_NOUN_LITERAL = ["느낌이 들어요", "느낌도 보여요", "무드"]

# "살짝" / "혹시" 는 base.md "살짝 ~ 보여요" / "혹시 ~" 패턴 차단인데 단독 어휘는
# 정상 사용 (예: T5-A "살짝 걸리는 포인트"). 단독 차단 X — 패턴 차단만 유지.
_A30_BLOCKED_WEAKENERS = ["같아요", "같습니다", "같은데"]
_A30_BLOCKED_WEAKENER_PATTERNS = ["살짝 보여요", "살짝 보이", "혹시 ~인가"]
_A30_BLOCKED_SAFETY = ["단정은 아니고", "잘못 본 걸 수도", "제가 잘 모르겠지만"]

# turn_id 별 예외 어휘 (template 에 의도적으로 등장하는 표현)
_A30_EXCEPTIONS: dict[str, list[str]] = {
    "T6": ["좀", "제가 보기엔"],          # "좀 어긋나요?" / "제가 보기엔 ~ 쪽이에요"
    "T10": ["좋을 것 같아요"],            # "들고 있어도 좋을 것 같아요" (Callback)
    "T11": ["좋을 것 같아요"],            # "슬쩍 떠올려보셔도 좋을 것 같아요" (마무리)
    "T2-C": [],                           # 깊이 turn (A-18 5문장 예외)
}


def _blocked_term_in_exception_context(
    term: str, text: str, exceptions: list[str],
) -> bool:
    """차단 어휘가 예외 phrase 의 일부로 등장하는지 확인.

    예: weak="같아요" / exc="좋을 것 같아요". text 에 "좋을 것 같아요" 가 있으면
    그 안의 "같아요" 는 허용. 이 함수가 True → 차단 skip.

    조건:
      - exception phrase 에 term 이 substring 으로 포함
      - text 에도 그 exception phrase 가 substring 으로 포함
    """
    for exc in exceptions:
        if term in exc and exc in text:
            return True
    return False


def check_a30_aitic_words(text: str, turn_id: str) -> list[str]:
    """A-30 — AI틱 어휘 차단 (HARD reject).

    명사 / 약화 어휘 / 안전망 3 카테고리 차단. turn_id 별 예외 자리 허용.

    예외 매칭 (2026-04-28 fix):
      차단 어휘가 예외 phrase 의 substring 으로 등장하면 허용.
      예: T11 의 "같아요" (차단 약화) 가 "좋을 것 같아요" (예외) 의 일부 → 허용.
    """
    errors: list[str] = []
    exceptions = _A30_EXCEPTIONS.get(turn_id, [])

    # 결 등 — regex 매칭 (word boundary)
    for pattern in _A30_NOUN_REGEX:
        for m in pattern.finditer(text):
            matched = m.group(0)
            if not _blocked_term_in_exception_context(
                matched, text, exceptions,
            ):
                errors.append(f"A-30 차단 명사: '{matched}' in {turn_id}")

    # 무드 등 — 리터럴 매칭
    for noun in _A30_NOUN_LITERAL:
        if noun in text and not _blocked_term_in_exception_context(
            noun, text, exceptions,
        ):
            errors.append(f"A-30 차단 명사: '{noun}' in {turn_id}")

    for weak in _A30_BLOCKED_WEAKENERS:
        if weak in text and not _blocked_term_in_exception_context(
            weak, text, exceptions,
        ):
            errors.append(f"A-30 차단 약화: '{weak}' in {turn_id}")

    # "살짝 보여요" 패턴 차단 (단독 "살짝" 은 허용, 추측 prefix 만 차단)
    for pattern in _A30_BLOCKED_WEAKENER_PATTERNS:
        if pattern in text:
            errors.append(f"A-30 차단 약화 패턴: '{pattern}' in {turn_id}")

    for safety in _A30_BLOCKED_SAFETY:
        if safety in text and not _blocked_term_in_exception_context(
            safety, text, exceptions,
        ):
            errors.append(f"A-30 차단 안전망: '{safety}' in {turn_id}")

    return errors


# A-34 anchor 4 카테고리 (매턴 1+ 필요, T1 제외)
_A34_ANCHORS_TEMPORAL = ["처음에", "아까", "방금", "지난번"]            # 시점 짚기
_A34_ANCHORS_UNIQUE = ["본인", "다른 사람", "거예요", "스타일"]         # 유니크 강조
_A34_ANCHORS_GAP = ["추구미", "그때", "지금"]                            # 격차 명시
_A34_ANCHORS_TOGETHER = ["같이", "우리"]                                  # "같이" 톤


def check_a34_mi_anchors(text: str, turn_id: str) -> list[str]:
    """A-34 — MI 매턴 anchor (4 카테고리 중 1+ 필요).

    T1 (오프닝) 예외 — 첫 만남 라포 형성 turn.
    """
    if turn_id == "T1":
        return []

    anchors_found = 0
    if any(a in text for a in _A34_ANCHORS_TEMPORAL):
        anchors_found += 1
    if any(a in text for a in _A34_ANCHORS_UNIQUE):
        anchors_found += 1
    if any(a in text for a in _A34_ANCHORS_GAP):
        anchors_found += 1
    if any(a in text for a in _A34_ANCHORS_TOGETHER):
        anchors_found += 1

    if anchors_found == 0:
        return [
            f"A-34: {turn_id} anchor 0 (시점/유니크/격차/같이 4 중 1+ 필요)"
        ]
    return []


def validate_v4(text: str, turn_id: str) -> dict:
    """v4 통합 validator.

    A-30 (AI틱 어휘) + A-34 (MI anchor) + A-17 (영업/상품 보존) +
    A-20 (추상 칭찬 보존) + A-18 (300자 hard) + 마크다운 차단.

    페르소나 C 시대 A-1~A-22 본문 (validate 함수) 은 별도 보존. v4 라우터
    (routes/sia.py) 는 본 함수만 호출.

    Returns
    -------
    dict : {"errors": [...], "passed": bool}
    """
    errors: list[str] = []
    errors.extend(check_a30_aitic_words(text, turn_id))
    errors.extend(check_a34_mi_anchors(text, turn_id))
    # 페르소나 C 보존 — 영업/추상 칭찬/길이/마크다운 (전 turn 공통)
    errors.extend(check_a17_commerce(text))
    errors.extend(check_a20_abstract_praise(text))
    errors.extend(check_a18_length(text))
    errors.extend(check_markdown_markup(text))
    return {"errors": errors, "passed": len(errors) == 0}
