"""Sia output validators — Hard Rules + tone + structure (v2 Priority 1 D3).

SPEC-ONBOARDING-V2 REQ-SIA-002/002a/002b 자동 검증.
test_sia_samples.py 와 routes/sia.py (post-process) 공용.

Public API:
  validate_sia_output(text)          — 전수 검증, 위반 시 SiaValidationError 발생
  find_violations(text)              — 전수 검증, 위반 목록 dict 반환 (비파괴)
  EMOJI_PATTERN / FORBIDDEN_SUFFIXES — 재사용 가능 상수
"""
from __future__ import annotations

import re
from typing import Optional


class SiaValidationError(ValueError):
    """Sia 응답이 Hard Rules 를 위반했을 때. code: 위반 규칙 식별자 list."""

    def __init__(self, message: str, violations: Optional[list[str]] = None):
        super().__init__(message)
        self.violations = violations or []


# ─────────────────────────────────────────────
#  Patterns
# ─────────────────────────────────────────────

# Hard Rule #1: "Verdict" / "verdict" 금지 (case-insensitive 전수)
VERDICT_RE = re.compile(r"verdict", re.IGNORECASE)

# Hard Rule #2: "판정" 금지
JUDGMENT_RE = re.compile(r"판정")

# Hard Rule #3: 마크다운 구문 — 강조 (**, *), 헤더 (##), 인용 (>), 코드블록 (```)
# 주의: em-dash "—" 는 마크다운 아니라 허용. 별표 "*" 는 "*단독 강조" 패턴만 잡음.
MARKDOWN_BOLD_RE = re.compile(r"\*\*[^*]+\*\*")
MARKDOWN_ITALIC_RE = re.compile(r"(?<!\*)\*[^*\s][^*]*[^*\s]\*(?!\*)")
MARKDOWN_HEADER_RE = re.compile(r"^\s*#{1,6}\s", re.MULTILINE)
MARKDOWN_QUOTE_RE = re.compile(r"^\s*>\s", re.MULTILINE)
MARKDOWN_CODE_RE = re.compile(r"```")

# Hard Rule #4: 별표/불릿 — 별표 또는 중점(•)으로 시작하는 리스트 라인 금지
ASTERISK_BULLET_RE = re.compile(r"^[ \t]*[\*•]\s", re.MULTILINE)

# Hard Rule #5: 이모지 — Unicode emoji 블록 전수
# Ranges: Emoticons, Symbols & Pictographs, Transport, Flags, Misc Symbols,
#         Dingbats, Supplemental Symbols & Pictographs, Symbols-and-Pictographs Extended
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F000-\U0001FFFF"  # supplementary planes (Symbols & Pictographs, Emoticons, Flags 등)
    "☀-⛿"          # Misc Symbols
    "✀-➿"          # Dingbats
    "⌀-⏿"          # Misc Technical (includes ⌚, ⌛)
    "⬀-⯿"          # Misc Symbols & Arrows
    "〰〽"           # Japanese
    "️"                 # Variation Selector-16 (emoji presentation)
    "]"
)

# 톤 — 금지 어미
FORBIDDEN_SUFFIXES = [
    "네요",        # "좋네요", "재밌네요" 등
    "같아요",      # "~같아요"
    "같네요",
    "거든요",
    "이더라고요",
    "시더라고요",
    "드릴게요",
    "있으세요?",
    "해요?",       # "어떻게 해요?" 류 다정 질문
]

FORBIDDEN_SUFFIX_RE = re.compile("|".join(re.escape(s) for s in FORBIDDEN_SUFFIXES))

# 톤 — 서술형 정중체 필수 어미 (최소 1개 필요)
# "십니다" 는 일반 honorific ("분이십니다"/"계십니다"/"하십니다" 전부 커버) 추가.
# 이전엔 "있으십니다"/"되십니다" 만 있어 실제 Haiku 출력 "분이십니다"/"계십니다" 에
# tone_missing false positive 가 발생. Phase F live probe 에서 확인됨.
REQUIRED_SUFFIXES = [
    "합니다",
    "습니다",
    "있습니다",
    "입니다",
    "되십니다",
    "있으십니다",
    "십니다",          # 분이십니다 / 계십니다 / 하십니다 / 드십니다 일반 커버
]
REQUIRED_SUFFIX_RE = re.compile("|".join(re.escape(s) for s in REQUIRED_SUFFIXES))

# 평가 언어 금지
EVAL_PHRASES = [
    "좋아 보입니다",
    "좋아 보여요",
    "잘 어울립니다",
    "잘 어울려요",
    "예뻐 보",
    "멋집니다",
    "멋있",
]
EVAL_RE = re.compile("|".join(re.escape(p) for p in EVAL_PHRASES))

# 확인 요청 금지
CONFIRMATION_PHRASES = [
    "본인도 그렇게",
    "맞으신가요",
    "맞나요?",
    "어떠세요?",
    "그렇죠?",
]
CONFIRMATION_RE = re.compile("|".join(re.escape(p) for p in CONFIRMATION_PHRASES))


# ─────────────────────────────────────────────
#  v3 — 인격 단정 카운트 + 추상명사 blacklist (Phase B)
# ─────────────────────────────────────────────

# 인격 단정 — 이름(또는 당신) 주어 + 단정 종결.
# "정세현님은 단정한 분입니다" / "당신은 ~한 쪽이십니다" 등.
# [가-힣]+님 이 이미 "정세현님" 을 포함하므로 alternation 중복 제거.
ASSERTION_PATTERN = re.compile(
    r"([가-힣]+님(은|는)|당신(은|는))"
    r".*?"
    r"(입니다|있으십니다|드러납니다|편이십니다|편입니다|분입니다|쪽이십니다)"
)

# 기능 문장 — 인사/전환/질문 유도. 인격 단정으로 카운트하지 않음.
FUNCTION_PATTERNS = [
    re.compile(r"하나만 (먼저 )?확인(하|드리)"),
    re.compile(r"다음 (질문|하나) "),
    re.compile(r"Sia ?입니다"),
    re.compile(r"맞다고 느끼시"),
    re.compile(r"여쭙겠습니다"),
    re.compile(r"[0-9]+(cm|kg)"),          # 수치 범위 선택지 라인
]

# 추상명사 blacklist — 구체 장면 없는 수식.
# "결" 은 다양한 활용형으로 등장하므로 helper 에서 단어 경계로 매칭.
ABSTRACT_NOUN_TOKENS = [
    "결을", "결이", "결입", "결은",
    "무드를", "무드가", "무드입",
    "감도를", "감도가", "감도입",
    "아우라",
    "기운",
]


def count_assertions(text: str) -> int:
    """인격 단정 개수 — "~님은/는 ... 입니다" 구조.

    FUNCTION_PATTERNS 매칭 라인은 기능문으로 제외. 1 line = 최대 1 count
    (한 라인에 여러 단정이 있어도 1로 처리 — MVP 단순화, 과대추출 방지).

    Hard Rule 기준: ≤ 2 per 턴 (프롬프트 준수 확인 용).
    """
    count = 0
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if any(fp.search(line) for fp in FUNCTION_PATTERNS):
            continue
        if ASSERTION_PATTERN.search(line):
            count += 1
    return count


def has_abstract_noun(text: str) -> bool:
    """추상명사 blacklist 히트 여부 — 구체 장면 없는 수식 검출.

    토큰 기반 단순 substring 매칭. 한국어 조사 활용 다양성을 담기 위해
    각 명사의 주요 활용형 (을/이/입/은) 을 개별 등록.
    """
    return any(token in text for token in ABSTRACT_NOUN_TOKENS)


# ─────────────────────────────────────────────
#  Validator
# ─────────────────────────────────────────────

def find_violations(text: str) -> dict[str, list[str]]:
    """비파괴 검증 — 위반 규칙별 매치 목록 dict 반환. 빈 dict 이면 clean.

    Keys:
      HR1_verdict      — "Verdict"/"verdict" 매치
      HR2_judgment     — "판정" 매치
      HR3_markdown     — 마크다운 구문 매치
      HR4_bullet       — 별표 리스트 불릿 매치
      HR5_emoji        — 이모지 매치
      tone_suffix      — 금지 어미 매치
      tone_missing     — 필수 어미 1개도 없음 (empty string 하나)
      eval_language    — 평가 표현 매치
      confirmation     — 확인 요청 매치
    """
    violations: dict[str, list[str]] = {}

    if m := VERDICT_RE.findall(text):
        violations["HR1_verdict"] = m
    if m := JUDGMENT_RE.findall(text):
        violations["HR2_judgment"] = m

    md = []
    if h := MARKDOWN_BOLD_RE.findall(text):
        md.extend(h)
    if h := MARKDOWN_ITALIC_RE.findall(text):
        md.extend(h)
    if h := MARKDOWN_HEADER_RE.findall(text):
        md.extend(h)
    if h := MARKDOWN_QUOTE_RE.findall(text):
        md.extend(h)
    if h := MARKDOWN_CODE_RE.findall(text):
        md.extend(h)
    if md:
        violations["HR3_markdown"] = md

    if m := ASTERISK_BULLET_RE.findall(text):
        violations["HR4_bullet"] = m
    if m := EMOJI_PATTERN.findall(text):
        violations["HR5_emoji"] = m

    if m := FORBIDDEN_SUFFIX_RE.findall(text):
        violations["tone_suffix"] = m

    if not REQUIRED_SUFFIX_RE.search(text):
        violations["tone_missing"] = [""]   # 필수 어미 한 개도 없음

    if m := EVAL_RE.findall(text):
        violations["eval_language"] = m
    if m := CONFIRMATION_RE.findall(text):
        violations["confirmation"] = m

    # v3 — Phase B Hard Rules
    assertion_count = count_assertions(text)
    if assertion_count > 2:
        violations["assertion_excess"] = [f"count={assertion_count}"]
    if has_abstract_noun(text):
        hits = [t for t in ABSTRACT_NOUN_TOKENS if t in text]
        violations["abstract_noun"] = hits

    return violations


def validate_sia_output(text: str) -> None:
    """엄격 검증 — 위반 시 SiaValidationError 발생.

    LLM post-process 단계에서 사용. 통과하면 None 반환, 실패하면 raise.
    """
    violations = find_violations(text)
    if not violations:
        return
    summary = ", ".join(f"{k}:{len(v)}" for k, v in violations.items())
    raise SiaValidationError(
        f"Sia output violated rules: {summary}",
        violations=list(violations.keys()),
    )


# ─────────────────────────────────────────────
#  Structure helpers (sentence count + length)
# ─────────────────────────────────────────────

# 종결부호 (문장 수 카운트 용 — 마침표/물음표/느낌표만)
_TERMINAL_RE = re.compile(r"[.!?。！？]\s*")
# 절 경계 (길이 검증 용 — 종결부호 + em-dash/en-dash + 개행)
# 개행은 4지선다 bullet 라인 각각 독립 절로 측정하기 위함 (2차 iteration 후 추가)
_CLAUSE_SPLIT_RE = re.compile(r"[.!?。！？]\s*|\s+[—–]\s+|\n+")

# 문장 길이 정책 (2차 iteration 후 완화):
#   ≤ 45자: ideal
#   46–60자: warning (metric 수집, 차단 X)
#   > 60자: hard violation (fallback 발동)
WARN_CHARS = 45
HARD_CHARS = 60


def count_sentences(text: str) -> int:
    """문장 수 — 종결부호 기준. em-dash/개행 은 단일 문장 내 절 연결 취급.

    AC-SIA-006 검증 (턴당 ≤3 문장, 오프닝 예외 4).
    """
    parts = _TERMINAL_RE.split(text.strip())
    return sum(1 for p in parts if p.strip())


def _clauses(text: str) -> list[str]:
    """내부 helper — 마크다운 문자 제거 + 절 단위 분할.

    Bullet 라인 ("- 편안하고 기대고 싶은 인상") 의 하이픈 prefix 는
    제거 후 내용만 카운트 (18자 → "편안하고 기대고 싶은 인상" 12자).
    """
    cleaned = re.sub(r"[*#>`]", "", text)
    raw = _CLAUSE_SPLIT_RE.split(cleaned.strip())
    out = []
    for c in raw:
        s = c.strip()
        if not s:
            continue
        # bullet prefix 제거: "- 편안하고..." → "편안하고..."
        if s.startswith("- "):
            s = s[2:].strip()
        out.append(s)
    return out


def long_sentences(text: str, max_chars: int = HARD_CHARS) -> list[str]:
    """max_chars 초과 '절' 목록 반환 — hard violation.

    2026-04-22 정책 완화: 기본 한도 60자 (기존 35자).
    개행도 절 경계로 취급 (bullet 라인 false positive 제거).
    markdown 문자 제거 + hyphen bullet prefix 제거 후 측정.
    """
    return [c for c in _clauses(text) if len(c) > max_chars]


def warn_sentences(text: str, warn_chars: int = WARN_CHARS,
                   hard_chars: int = HARD_CHARS) -> list[str]:
    """warn_chars ~ hard_chars 범위 절 목록 — warning only (차단 X).

    45-60자는 "가능하면 분할 권장" 영역. metric 수집용.
    """
    return [c for c in _clauses(text) if warn_chars < len(c) <= hard_chars]
