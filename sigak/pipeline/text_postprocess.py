"""
SIGAK 리포트 텍스트 후처리 — LLM 출력 품질 안전망

프롬프트로 1차 통제하고, 후처리로 2차 검수.
LLM이 지시를 어기고 뱉은 금지 표현, 오탈자, 톤 이탈을 잡아낸다.
"""
import re


# ─────────────────────────────────────────────
#  1. 오탈자 수정
# ─────────────────────────────────────────────

TYPO_MAP = {
    "코등": "콧등",
    "코볼": "콧볼",
    "코뼈": "콧뼈",
    "코날": "콧날",
    "코대": "콧대",
    "눈꼬리가": "눈꼬리가",  # 정상 — 무시용 방어
    "잇몸": "잇몸",          # 정상
}


def fix_typos(text: str) -> str:
    for wrong, correct in TYPO_MAP.items():
        if wrong != correct:
            text = text.replace(wrong, correct)
    return text


# ─────────────────────────────────────────────
#  2. 금지 표현 치환
# ─────────────────────────────────────────────

BANNED_REPLACEMENTS = [
    # 게이밍/캐주얼
    ("치트키", "포인트"),
    ("꿀팁", "팁"),
    ("핵꿀", "핵심"),
    ("간지", "분위기"),
    # "느낌" 남발 — "느낌표", "느낌이" 등은 보존, "~느낌" 패턴만
    # regex로 처리
]

# "느낌" 치환용 패턴: "부드러운 느낌" → "부드러운 무드", "시크한 느낌" → "시크한 인상"
_FEELING_PATTERN = re.compile(r"(\S+(?:운|한|스러운|적인))\s*느낌")


def _replace_feeling(match: re.Match) -> str:
    adj = match.group(1)
    return f"{adj} 인상"


def fix_banned_expressions(text: str) -> str:
    for banned, replacement in BANNED_REPLACEMENTS:
        text = text.replace(banned, replacement)
    # "~느낌" → "~인상" (단, "느낌표" 등은 건드리지 않음)
    text = _FEELING_PATTERN.sub(_replace_feeling, text)
    return text


# ─────────────────────────────────────────────
#  3. 톤 수정 (유보적 → 단정적)
# ─────────────────────────────────────────────

TONE_REPLACEMENTS = [
    # 유보적 표현
    (re.compile(r"경향이 있(습니다|어요|다)"), lambda m: {"습니다": "합니다", "어요": "아요", "다": "다"}.get(m.group(1), m.group(0))),
    (re.compile(r"([가-힣]+)할 수 있(습니다|어요)"), lambda m: m.group(1) + {"습니다": "합니다", "어요": "해요"}.get(m.group(2), m.group(0))),
    # 허락형
    ("해도 돼요", "해도 좋아요"),
    ("해도 됩니다", "해도 좋습니다"),
    ("괜찮아요", "좋아요"),
    ("나쁘지 않아요", "좋아요"),
    ("나쁘지 않습니다", "좋습니다"),
    # "~보일 수 있어요" → "~보여요"
    (re.compile(r"보일 수 있(어요|습니다)"), lambda m: "보여요" if m.group(1) == "어요" else "보입니다"),
    # "~만들 수 있어요" → "~만들어요"
    (re.compile(r"만들 수 있(어요|습니다)"), lambda m: "만들어요" if m.group(1) == "어요" else "만듭니다"),
]


def fix_tone(text: str) -> str:
    for pattern, replacement in TONE_REPLACEMENTS:
        if isinstance(pattern, re.Pattern):
            text = pattern.sub(replacement, text)
        else:
            text = text.replace(pattern, replacement)
    return text


# ─────────────────────────────────────────────
#  4. 한영 동어반복 제거
# ─────────────────────────────────────────────

REDUNDANT_PAIRS = [
    (re.compile(r"소프트한\s*부드러운"), "부드러운"),
    (re.compile(r"부드러운\s*소프트한"), "부드러운"),
    (re.compile(r"볼드한\s*강렬한"), "강렬한"),
    (re.compile(r"강렬한\s*볼드한"), "강렬한"),
    (re.compile(r"샤프한\s*날카로운"), "날카로운"),
    (re.compile(r"날카로운\s*샤프한"), "날카로운"),
    (re.compile(r"내추럴한\s*자연스러운"), "자연스러운"),
    (re.compile(r"자연스러운\s*내추럴한"), "자연스러운"),
    (re.compile(r"매튜어한\s*성숙한"), "성숙한"),
    (re.compile(r"성숙한\s*매튜어한"), "성숙한"),
    (re.compile(r"프레시한\s*발랄한"), "발랄한"),
    (re.compile(r"클린한\s*깨끗한"), "깨끗한"),
    (re.compile(r"깨끗한\s*클린한"), "깨끗한"),
]


def fix_redundant_pairs(text: str) -> str:
    for pattern, replacement in REDUNDANT_PAIRS:
        text = pattern.sub(replacement, text)
    return text


# ─────────────────────────────────────────────
#  5. 통합 파이프라인
# ─────────────────────────────────────────────

def sanitize_report_text(text: str) -> str:
    """단일 텍스트에 모든 후처리 적용."""
    if not text or not isinstance(text, str):
        return text
    text = fix_typos(text)
    text = fix_banned_expressions(text)
    text = fix_tone(text)
    text = fix_redundant_pairs(text)
    # 공백 정리
    text = re.sub(r" {2,}", " ", text).strip()
    return text


def sanitize_report_json(data):
    """JSON 구조 안의 모든 문자열 값에 sanitize_report_text 적용.
    키(_로 시작하는 내부 필드)는 건드리지 않음."""
    if isinstance(data, str):
        return sanitize_report_text(data)
    elif isinstance(data, dict):
        return {
            k: (data[k] if k.startswith("_") else sanitize_report_json(v))
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [sanitize_report_json(item) for item in data]
    return data
