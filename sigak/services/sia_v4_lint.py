"""Sia v4 한국어 lint (2026-04-28).

LLM 슬롯 치환 후 한국어 비문 차단:
  - 조사 (받침/종성) 정합 검증 — "사진은" / "사진는" 오류 검출
  - 관찰 슬롯 형식 — 관형형+명사 ('채도 높은 쪽') 강제, 동사형 ('채도 높아') 차단
  - 사용자 발화 인용 부호 — '방금 나온 X는' 의 X 인용 누락 검출
  - A-30 AI틱 어휘 통합 (sia_validators_v4.check_a30_aitic_words 재사용)

설계:
- LLM 호출 없음. 정규식 + 한글 코드포인트 산수만.
- 슬롯 치환 결과 (render_v4_template 출력) 또는 LLM 출력 양쪽 검증 가능.
- routes/sia.py 는 validate_v4 호출 (A-30/A-34 중심). lint_korean_v4 는
  Phase 5 시뮬레이션 검증 / 디버그용.

Public API:
  has_jongseong(char) -> bool
  check_korean_particle(text) -> list[str]
  check_observation_slot_form(text) -> list[str]
  check_quote_form(text) -> list[str]
  lint_korean_v4(text, turn_id) -> list[str]
"""
from __future__ import annotations

import re


# ─────────────────────────────────────────────
#  한글 종성 (받침) 체크
# ─────────────────────────────────────────────

def has_jongseong(char: str) -> bool:
    """한 글자에 받침 (종성) 있는지.

    한글 음절 코드: 0xAC00 ~ 0xD7A3
    공식: jongseong_index = (code - 0xAC00) % 28
    jongseong_index == 0 → 받침 없음.
    """
    if not char or not ("가" <= char <= "힣"):
        return False
    code = ord(char) - 0xAC00
    return (code % 28) != 0


# ─────────────────────────────────────────────
#  조사 정합 (받침 ↔ 비받침)
# ─────────────────────────────────────────────

# 받침-요구 조사 vs 비받침-요구 조사 (명사+조사 결합 검증)
#
# "고/이고" pair 는 의도적으로 제외 — 동사 활용형 ("좋고", "갖고") 과 충돌해
# false positive 다발. 명사 "학생이고" vs "엄마고" 검증 필요할 시 후속 추가.
_RECEIVER_PARTICLES = ["은", "이", "을", "과"]              # 받침 必
_NO_RECEIVER_PARTICLES = ["는", "가", "를", "와"]          # 받침 X

# 자동 수정 매핑
_PARTICLE_PAIRS: dict[str, str] = {
    "은": "는", "는": "은",
    "이": "가", "가": "이",
    "을": "를", "를": "을",
    "와": "과", "과": "와",
}

# 단어 + 조사 매칭 패턴 (한글 단어 2자+ + 조사 + 단어 경계)
#
# {2,} 로 1-char 매칭 차단 — "있" / "갖" / "되" 등 동사 stem 의 false positive 방지.
# 한국어 명사는 대부분 2자+ 이므로 {2,} 가 실제 noun 검증을 가린다는 우려는 적음.
_PARTICLE_RE = re.compile(
    r"([가-힣]{2,})\s*(은|는|이|가|을|를|과|와)\b"
)

# 합성 명사 — 마지막 글자가 조사처럼 보여 false positive 발생.
# 예: "사이" 가 "사" + "이" (조사) 로 분해되어 사 (받침 X) + 이 (받침 必) → 오탐.
# 명사 + 조사 substring "사이" 가 이 set 에 있으면 검증 skip.
_COMPOUND_NOUN_EXCEPTIONS: frozenset[str] = frozenset({
    "사이", "둘이", "셋이", "넷이",
    "그게", "그래", "이거", "저거",
    "우리", "지금", "조금", "오늘",
    "어디", "여기", "거기", "저기",
    "아이", "마이", "장이", "강이",
})


def check_korean_particle(text: str) -> list[str]:
    """조사 결합 정합 검증.

    "사진은 (받침 ㄴ)" → 정합. "사진는 (받침 X 단어 + 비받침 조사)" → 오류.

    합성 명사 ("사이" / "그래" 등) 는 _COMPOUND_NOUN_EXCEPTIONS 로 false positive
    회피.
    """
    errors: list[str] = []
    for match in _PARTICLE_RE.finditer(text or ""):
        word = match.group(1)
        particle = match.group(2)

        # 합성 명사 예외 — "사이" 류
        compound = f"{word}{particle}"
        if compound in _COMPOUND_NOUN_EXCEPTIONS:
            continue

        last_char = word[-1]
        has_recv = has_jongseong(last_char)

        if has_recv and particle in _NO_RECEIVER_PARTICLES:
            correct = _PARTICLE_PAIRS.get(particle, particle)
            errors.append(
                f"조사 오류: '{word}{particle}' → '{word}{correct}' (받침)"
            )
        elif not has_recv and particle in _RECEIVER_PARTICLES:
            correct = _PARTICLE_PAIRS.get(particle, particle)
            errors.append(
                f"조사 오류: '{word}{particle}' → '{word}{correct}' (비받침)"
            )

    return errors


# ─────────────────────────────────────────────
#  관찰 슬롯 형식 검증 (관형형+명사)
# ─────────────────────────────────────────────

# 동사형 어미 뒤에 직접 "쪽/분위기/결" 명사가 오면 비문
# 예: "채도 높아 쪽" / "조용하 분위기" / "톤 정돈됐 결"
_OBSERVATION_BAD_VERB_ENDINGS = [
    "높아", "낮아", "많아", "적아",
    "밝아", "어두워",
    "있어", "없어",
    "정돈됐", "정돈됨",
]

_OBSERVATION_BAD_PATTERN = re.compile(
    r"\s+(" + "|".join(_OBSERVATION_BAD_VERB_ENDINGS) + r")\s+(쪽이에요|분위기예요|결이에요|쪽\b|분위기\b|결\b)"
)


def check_observation_slot_form(text: str) -> list[str]:
    """관찰 슬롯이 관형형+명사 형식인지 검증.

    ✅ 좋음: "채도 높은 쪽" / "톤 정돈된 분위기" / "조용한 인상의 결"
    ❌ 나쁨: "채도 높아 쪽" / "톤 정돈됐 분위기" (동사형 직결)
    """
    errors: list[str] = []
    if _OBSERVATION_BAD_PATTERN.search(text or ""):
        errors.append("관찰 슬롯 비문: 동사형 어미 + 쪽/분위기/결 (관형형+명사 사용)")
    return errors


# ─────────────────────────────────────────────
#  사용자 발화 인용 부호 검증
# ─────────────────────────────────────────────

# T7/T9 슬롯 패턴: "방금 나온 [발화]는" / "방금 나온 [발화]가" 등
# render_v4_template 가 quote_user_phrase 로 처리해 "'발화'" 형태이어야.
# 누락 시 "방금 나온 색깔이 좀 그래요는" 같이 비문 가능성.
_QUOTE_REQUIRED_PATTERN = re.compile(
    r"방금\s*나온\s+([^']{2,}?)(?=\s*(는|이|가|을|를|이라|라|이라는|라는))"
)


def check_quote_form(text: str) -> list[str]:
    """T8 등에서 '방금 나온 X는' 패턴의 X 인용 부호 누락 검출.

    quote_user_phrase 가 정상 작동하면 "'X'" 가 들어가 패턴 매칭 X.
    슬롯 누락 시 빈 문자열로 치환되어 "방금 나온  는" 형태도 가능 — 별도 매칭 X (공백만).
    """
    errors: list[str] = []
    for match in _QUOTE_REQUIRED_PATTERN.finditer(text or ""):
        quoted = match.group(1).strip()
        if not quoted:
            continue
        if not (quoted.startswith("'") or quoted.startswith('"')):
            errors.append(
                f"인용 부호 누락: '방금 나온 {quoted}{match.group(2)}' "
                "(quote_user_phrase 처리 필요)"
            )
    return errors


# ─────────────────────────────────────────────
#  통합 lint
# ─────────────────────────────────────────────

def lint_korean_v4(text: str, turn_id: str) -> list[str]:
    """v4 한국어 통합 lint — 조사 / 관찰 슬롯 / 인용 부호 / A-30.

    Phase 5 시뮬레이션 검증 / 디버그용. routes/sia.py 는 validate_v4
    (A-30/A-34 중심) 사용.
    """
    # A-30 import 는 함수 내부에서 — 모듈 순환 의존 회피
    from services.sia_validators_v4 import check_a30_aitic_words

    errors: list[str] = []
    errors.extend(check_korean_particle(text))
    errors.extend(check_observation_slot_form(text))
    errors.extend(check_quote_form(text))
    errors.extend(check_a30_aitic_words(text, turn_id))
    return errors
