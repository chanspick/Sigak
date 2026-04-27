"""LLM 출력 한국어 자연성 정정 (post-process).

Sonnet/Haiku 가 한국어 생성 시 받침 있는 동사/형용사 어간에 명사용 어미
(`이에요`/`이세요`) 를 잘못 결합하는 케이스 + 흔한 어휘 표기 오류를
deterministic 정정. 페르소나 B/C 모두 공통 적용.

원칙: false positive 0 — 명시적 패턴만. 문맥 바꾸지 않음. 보수적.

사용처:
  - services.sia_writer.generate_finale
  - main.py 옛 SIGAK_V3 PI 의 LLM 출력 (face_structure / gap / type_match ...)
  - 향후 다른 LLM 응답 후처리 path 공통

설계 결정:
  - regex 패턴은 word boundary 대신 (?=[^가-힣]|$) — 한글 음절 다음 비한글
    또는 끝일 때만 매칭. "있이에요체" 같은 것까지 잡지 않음.
  - 어휘 dict 는 단순 replace — 부분 매칭이라 잘못된 over-replace 위험.
    명백한 오타만 등재.
"""
from __future__ import annotations

import re
from typing import Any


# ─────────────────────────────────────────────
#  어미 결합 오류 — 동사/형용사 어간 + 이에요/이세요
# ─────────────────────────────────────────────

_ENDING_TYPO_PATTERNS: list[tuple[str, str]] = [
    # "있다" 동사 — 가장 흔함
    (r"있이에요(?=[^가-힣]|$)", "있어요"),
    (r"있이세요(?=[^가-힣]|$)", "있으세요"),
    (r"있이에서(?=[^가-힣]|$)", "있어서"),

    # "되다" 동사
    (r"되이에요(?=[^가-힣]|$)", "돼요"),
    (r"되었이에요(?=[^가-힣]|$)", "됐어요"),

    # 흔한 형용사 어간 + 이에요 (받침 있음 — 양성/음성 모음 따라 어/아)
    (r"좋이에요(?=[^가-힣]|$)", "좋아요"),
    (r"많이에요(?=[^가-힣]|$)", "많아요"),
    (r"작이에요(?=[^가-힣]|$)", "작아요"),
    (r"높이에요(?=[^가-힣]|$)", "높아요"),
    (r"낮이에요(?=[^가-힣]|$)", "낮아요"),
    (r"같이에요(?=[^가-힣]|$)", "같아요"),
    (r"맞이에요(?=[^가-힣]|$)", "맞아요"),
    (r"넓이에요(?=[^가-힣]|$)", "넓어요"),
    (r"깊이에요(?=[^가-힣]|$)", "깊어요"),
    (r"짙이에요(?=[^가-힣]|$)", "짙어요"),
    (r"옅이에요(?=[^가-힣]|$)", "옅어요"),

    # 명사형 어근 + 이에요 → 해요 (활용)
    (r"유연이에요(?=[^가-힣]|$)", "유연해요"),
    (r"필요이에요(?=[^가-힣]|$)", "필요해요"),
    (r"가능이에요(?=[^가-힣]|$)", "가능해요"),
    (r"중요이에요(?=[^가-힣]|$)", "중요해요"),
    (r"안정이에요(?=[^가-힣]|$)", "안정적이에요"),
    (r"세련이에요(?=[^가-힣]|$)", "세련됐어요"),
    (r"부드러움이에요(?=[^가-힣]|$)", "부드러워요"),
]


# ─────────────────────────────────────────────
#  어휘 표기 오류 — LLM 이 자주 흘리는 typo
# ─────────────────────────────────────────────

_WORD_TYPO_DICT: dict[str, str] = {
    # "쿨톤" 의 잘못된 모음 늘어뜨림
    "쿠울톤": "쿨톤",
    "쿠울 톤": "쿨톤",
    # "웜톤" 의 잘못된 표기
    "워엄톤": "웜톤",
    "워엄 톤": "웜톤",
    "왐톤": "웜톤",
    # 기타 자주 나오는 typo (운영하면서 추가)
}


def normalize_korean_text(text: str) -> str:
    """LLM 출력 한국어 정정.

    1. 동사/형용사 어간 + 이에요/이세요 잘못 결합 → 올바른 어미.
    2. 흔한 어휘 표기 오류 정정.

    안전 (false positive 0) 한 명시 패턴만 적용. 입력 그대로 string 아니면
    그대로 반환.
    """
    if not isinstance(text, str) or not text:
        return text
    out = text
    for pat, repl in _ENDING_TYPO_PATTERNS:
        out = re.sub(pat, repl, out)
    for wrong, right in _WORD_TYPO_DICT.items():
        if wrong in out:
            out = out.replace(wrong, right)
    return out


def normalize_value(value: Any) -> Any:
    """임의 값 normalize — string 만 정정, 그 외엔 그대로.

    dict / list 는 재귀 처리.
    """
    if isinstance(value, str):
        return normalize_korean_text(value)
    if isinstance(value, dict):
        return {k: normalize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize_value(item) for item in value]
    return value


def normalize_dict_strings(d: dict) -> dict:
    """dict 의 모든 string 값 정정 (재귀). 새 dict 반환 (입력 비파괴).

    LLM 응답 dict 후처리 entry point. 사용:
        result = generate_finale(...)
        result = normalize_dict_strings(result)
    """
    if not isinstance(d, dict):
        return d
    return {k: normalize_value(v) for k, v in d.items()}


# ─────────────────────────────────────────────
#  detection (validator 용 — retry trigger)
# ─────────────────────────────────────────────

def find_korean_typos(text: str) -> list[str]:
    """text 에서 알려진 typo 패턴 발견. validator 가 retry trigger 에 사용.

    Returns: 발견된 raw typo 토큰 list (정정 전).
    """
    if not isinstance(text, str) or not text:
        return []
    found: list[str] = []
    for pat, _ in _ENDING_TYPO_PATTERNS:
        m = re.search(pat, text)
        if m:
            found.append(m.group(0))
    for wrong in _WORD_TYPO_DICT:
        if wrong in text:
            found.append(wrong)
    return found
