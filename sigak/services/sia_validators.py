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
REQUIRED_SUFFIXES = [
    "합니다",
    "습니다",
    "있습니다",
    "입니다",
    "되십니다",
    "있으십니다",
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
