"""PI (시각이 본 당신) 전용 validator — Phase I PI-D.

페르소나 분리:
  Sia 친밀체    : ~잖아요 / ~더라구요 / ~인가봐요?      → PI 영역 차단
  Verdict 정중체 : ~합니다 / ~입니다 / ~습니다           → PI 영역 차단
  PI 리포트체    : ~있어요 / ~세요 / ~해요 / ~이에요    → PI 영역 허용

체크 항목 (4종 통합 hard reject):
  1. PI-A17 영업 차단    — 가격/구독/매장 추천 차단. "리포트"/"진단"/"추천" 어휘는 PI 한정 허용
  2. PI-A18 길이         — 컴포넌트별 (cover 80-150 / gap 100-200 / action item 30-80 / default 100-300)
  3. PI-A20 추상 칭찬어  — 매력/독특/특별/센스 차단. 객관 뷰티 어휘 (얼굴형/비율/톤/무게감/골격/윤곽) 허용
  4. PI-MD  마크다운     — `*`, `**`, `##`, `>`, ``` 전수 차단

페르소나 톤:
  5. PI-친밀체 차단      — Sia 어미 (~잖아요 / ~더라구요 등) hard reject
  6. PI-정중체 차단      — Verdict 어미 (~합니다 / ~입니다 / ~습니다) hard reject

sia_writer._call_with_retry 호환:
  collect_pi_violations(text, component='default') → list[str]
  validate_pi_text(text, component='default') → PIValidationResult

sia_validators_v4 와 분리한 이유:
  - PI 는 Sia 와 발화 톤 자체가 다름 (리포트체)
  - "리포트"/"진단" 어휘는 PI 본질이라 v4 _COMMERCE_PATTERNS 적용 불가
  - 컴포넌트별 길이 budget 이 다름 (cover 80자 vs hair 300자)

CLAUDE.md §6.3 (Sia 페르소나 B 어미) + §7.1 (PI 25장 스토리 톤) 분리.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────
#  PI-A17 — 영업/제품 추천 차단 (PI 한정 어휘 허용)
#
#  v4 _COMMERCE_PATTERNS 와 차이:
#    제외:  "리포트"  → PI 자체가 리포트
#    제외:  "진단"     → PI 영역에서 "진단" 사용 자연
#    제외:  "추천"     → hair_styles.json 카탈로그 인용 허용 ("추천해드릴" 만 차단)
#    유지:  "구독"/"티어"/"프리미엄"/"컨설팅"/매장/가격 수치
# ─────────────────────────────────────────────

_PI_COMMERCE_PATTERNS = [
    # 영업성 표현 — "추천해드릴" 만 차단 (단순 "추천" 은 허용)
    re.compile(r"추천해드릴"),
    re.compile(r"정리해드릴"),
    re.compile(r"풀어드릴"),
    re.compile(r"다음\s*단계"),
    re.compile(r"핵심\s*포인트"),
    # 상품/구독 어휘 (PI 자체는 단일 결제이므로 구독 어휘 사용 안 함)
    re.compile(r"컨설팅"),
    re.compile(r"구독"),
    re.compile(r"티어"),
    re.compile(r"프리미엄"),
    re.compile(r"Premium", re.IGNORECASE),
    # 매장/구매 권유
    re.compile(r"헤어샵"),
    re.compile(r"미용실에서"),
    re.compile(r"매장에서"),
    re.compile(r"구매하"),
    re.compile(r"구입하"),
    re.compile(r"방문하시"),
    # 가격 수치 — PI 본문에서 가격 노출 자체가 부적절 (paywall 은 별도 UI)
    re.compile(r"₩\s*\d"),
    re.compile(r"\d[\d,]*\s*원"),
    re.compile(r"\d+\s*토큰"),
    re.compile(r"\d+\s*만원"),
]


def check_pi_a17_commerce(draft: str) -> list[str]:
    """PI-A17 영업 어휘 차단.

    PI 영역 한정 허용:
      - "리포트"      (PI = 시각이 본 당신 리포트)
      - "진단"/"분석"  (PI 의 핵심 분석 행위)
      - "추천"         (hair_styles 카탈로그 인용 시 자연)
    """
    errors: list[str] = []
    for pat in _PI_COMMERCE_PATTERNS:
        m = pat.search(draft)
        if m:
            errors.append(f"PI-A17: 영업 어휘 — '{m.group(0)}'")
    return errors


# ─────────────────────────────────────────────
#  PI-A18 — 컴포넌트별 길이 budget
# ─────────────────────────────────────────────

# (min_chars, max_chars) — empty draft 는 min 검증 면제 (정상 placeholder).
#
# 정책:
#   max  : hard reject — LLM 응답 길이 폭주 차단
#   min  : 너무 짧은 stub 차단 — 각 필드 개별 검증 시 자연스러운 짧은 답변 허용
#
# 컴포넌트 budget = sections 안의 user-facing 단일 필드 검증 기준.
# content dict 검증 시 (validate_pi_content) 각 필드별로 동일 budget 적용.
PI_LENGTH_BUDGETS: dict[str, tuple[int, int]] = {
    "cover":               (40, 200),     # cover 는 user_summary / needs / overall 3 필드 분할
    "celeb_reference":     (40, 300),
    "face_structure":      (40, 300),
    "type_reference":      (40, 300),
    "gap_analysis":        (40, 250),
    "skin_analysis":       (40, 300),
    "coordinate_map":      (40, 300),
    "hair_recommendation": (40, 300),
    # action_plan 내 개별 item — engine 호출 시 component='action_item' 명시
    "action_item":         (15,  80),
    # default — 일반 narrative
    "default":             (40, 300),
}


def check_pi_a18_length(draft: str, component: str = "default") -> list[str]:
    """PI-A18 컴포넌트별 길이 검증.

    너무 짧음 (< min) = warning 성격이지만 hard reject 로 분류 (Haiku 가 빈 응답 반환 시
    fallback 으로 보내야 함 → validator 가 reject → retry).
    너무 김 (> max) = hard reject.
    """
    errors: list[str] = []
    text = draft.strip()
    n = len(text)
    if n == 0:
        # 완전 비어있는 경우는 _call_with_retry 가 fallback 처리 — validator 단계는 통과
        return errors

    min_chars, max_chars = PI_LENGTH_BUDGETS.get(component, PI_LENGTH_BUDGETS["default"])
    if n > max_chars:
        errors.append(
            f"PI-A18: {component} {n}자 > {max_chars}자 hard reject"
        )
    if n < min_chars:
        errors.append(
            f"PI-A18: {component} {n}자 < {min_chars}자 (너무 짧음)"
        )
    return errors


# ─────────────────────────────────────────────
#  PI-A20 — 추상 칭찬어 차단 (객관 뷰티 어휘 허용)
#
#  v4 _ABSTRACT_PRAISE_PATTERNS 동일 list. 차이점:
#    - PI 영역에서 객관 뷰티 어휘 (얼굴형/비율/톤/무게감/골격/윤곽) 는 허용 → list 에 없음
#    - "분석" 어휘 PI 한정 허용 → list 에 없음
# ─────────────────────────────────────────────

_PI_ABSTRACT_PRAISE_PATTERNS = [
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


def check_pi_a20_abstract_praise(draft: str) -> list[str]:
    """PI-A20 추상 칭찬 차단. 대체는 구체 관찰 + 유저다움 + 행동 짚기."""
    errors: list[str] = []
    for pat in _PI_ABSTRACT_PRAISE_PATTERNS:
        m = pat.search(draft)
        if m:
            errors.append(f"PI-A20: 추상 칭찬 — '{m.group(0)}'")
    return errors


# ─────────────────────────────────────────────
#  PI-MD — 마크다운 차단
# ─────────────────────────────────────────────

_PI_MARKDOWN_PATTERNS = [
    re.compile(r"\*\*[^*\n]+\*\*"),                          # **text**
    re.compile(r"(?<![*\w])\*(?!\s)[^*\n]+?\*(?!\w)"),       # *italic* (non-bullet)
    re.compile(r"^#{1,6}\s", re.MULTILINE),                  # # heading
    re.compile(r"^>\s", re.MULTILINE),                       # > blockquote
    re.compile(r"```"),                                       # ``` code fence
]


def check_pi_markdown(draft: str) -> list[str]:
    """PI-MD 마크다운 차단. 프론트는 순수 텍스트 렌더 전제."""
    errors: list[str] = []
    for pat in _PI_MARKDOWN_PATTERNS:
        if pat.search(draft):
            errors.append(f"PI-MD: 마크다운 — {pat.pattern}")
    return errors


# ─────────────────────────────────────────────
#  PI 페르소나 톤 — 리포트체 강제
#
#  허용 어미 패밀리:
#    ~있어요 / ~없어요 / ~돼요 / ~해요 / ~이에요 / ~예요 / ~세요
#  차단:
#    [Sia 친밀체]   ~잖아요 / ~더라구요 / ~인가봐요 / ~이시잖아요 / ~이시
#    [Verdict 정중체] ~합니다 / ~입니다 / ~습니다 (문장 종결 한정)
# ─────────────────────────────────────────────

# Sia 친밀체 어미 — PI 영역 hard reject
_PI_FORBIDDEN_FRIENDLY_SUFFIXES = [
    "잖아요",
    "더라구요",
    "인가봐요",
    "이신가봐요",
    "이시잖아요",
    "이세요",          # "정세현이세요" 류 — PI 는 호명 X
    "이세",            # "정세현이세" 어간
    "더라고요",        # "더라구요" 변종
]
_PI_FORBIDDEN_FRIENDLY_RE = re.compile(
    "|".join(re.escape(s) for s in _PI_FORBIDDEN_FRIENDLY_SUFFIXES)
)


def check_pi_persona_friendly(draft: str) -> list[str]:
    """PI 페르소나 톤 — Sia 친밀체 어미 차단."""
    errors: list[str] = []
    if hits := _PI_FORBIDDEN_FRIENDLY_RE.findall(draft):
        # 중복 제거 — 빈도는 메시지에 합치지 않고 first 3 개만 노출
        unique = list(dict.fromkeys(hits))[:3]
        errors.append(f"PI-톤: Sia 친밀체 어미 차단 — {unique}")
    return errors


# Verdict 정중체 어미 — "~ㅂ니다" 종결 일반화.
#   매치: 합니다 / 입니다 / 습니다 / 됩니다 / 갑니다 / 옵니다 등 모든 "~니다" 종결
#   문장 종결 위치만 (다음에 공백/구두점/EOL) — "다만" 같은 연결 어미 회피
_PI_FORBIDDEN_FORMAL_END_RE = re.compile(
    r"(?<=[가-힣])(니다)(?=[\s.!?]|$)"
)


def check_pi_persona_formal(draft: str) -> list[str]:
    """PI 페르소나 톤 — Verdict 정중체 어미 차단.

    "~ㅂ니다" / "~습니다" 종결 전수 차단. 첫 매치의 좌측 글자까지 포함해 원어 노출.
    """
    errors: list[str] = []
    matches: list[str] = []
    for m in _PI_FORBIDDEN_FORMAL_END_RE.finditer(draft):
        # 매치 위치 직전 글자까지 포함해서 원어 노출 ("됩니다" / "있습니다" 등)
        start = max(0, m.start() - 2)
        matches.append(draft[start:m.end()])
    if matches:
        unique = list(dict.fromkeys(matches))[:3]
        errors.append(f"PI-톤: Verdict 정중체 어미 차단 — {unique}")
    return errors


# ─────────────────────────────────────────────
#  통합 ValidationResult + 진입점
# ─────────────────────────────────────────────

@dataclass
class PIValidationResult:
    """PI 검증 결과. errors = hard reject. warnings = sub-rule (현재 사용 안 함, 확장 예약)."""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


def validate_pi_text(
    draft: str,
    *,
    component: str = "default",
) -> PIValidationResult:
    """PI 텍스트 4종 + 페르소나 통합 검증.

    Parameters
    ----------
    draft : 검증 대상 텍스트.
    component : PI_LENGTH_BUDGETS key — cover / gap_analysis / action_item / default 등.
    """
    result = PIValidationResult()
    result.errors.extend(check_pi_a17_commerce(draft))
    result.errors.extend(check_pi_a18_length(draft, component))
    result.errors.extend(check_pi_a20_abstract_praise(draft))
    result.errors.extend(check_pi_markdown(draft))
    result.errors.extend(check_pi_persona_friendly(draft))
    result.errors.extend(check_pi_persona_formal(draft))
    return result


def collect_pi_violations(
    draft: str,
    *,
    component: str = "default",
) -> list[str]:
    """sia_writer._call_with_retry validator 인자 호환 형태.

    list[str] (errors) 만 반환. warnings 는 별도로 sia_writer 가 다루지 않음.
    """
    return list(validate_pi_text(draft, component=component).errors)


def make_pi_validator(
    component: str = "default",
) -> "callable[[str], list[str]]":
    """component 를 partial-bind 한 validator. _call_with_retry 에 깔끔히 주입.

    Example:
        from services.sia_writer import HaikuSiaWriter
        from services.sia_validators_pi import make_pi_validator
        v = make_pi_validator("cover")
        # writer 가 _call_with_retry(..., validator=v) 호출
    """
    def _validator(draft: str) -> list[str]:
        return collect_pi_violations(draft, component=component)
    return _validator


# ─────────────────────────────────────────────
#  PI-A 호환 진입점 — section_id 기반 dict / text 검증
#
#  PI-A 가 generate_pi_report_v1 안에서 호출:
#    from services.sia_validators_pi import validate_pi_content
#    res = validate_pi_content(content=section_dict, section_id="cover")
#    if not res.ok: ... fallback / retry
# ─────────────────────────────────────────────

# 9 컴포넌트별 user-facing 텍스트 필드 (LLM 응답 검증 대상).
# PI-C 가 9 컴포넌트 schema 정착 시 키셋이 변경되면 이 매핑만 update 하면 됨.
PI_USER_FACING_KEYS: dict[str, tuple[str, ...]] = {
    "cover": (
        "user_summary",
        "needs_statement",
        "sia_overall_message",
    ),
    "celeb_reference": ("narrative", "summary"),
    "face_structure": ("narrative", "summary"),
    "type_reference": ("narrative", "summary"),
    "gap_analysis": ("narrative", "gap_summary"),
    "skin_analysis": ("narrative", "summary"),
    "coordinate_map": ("narrative",),
    "hair_recommendation": ("narrative", "reason", "summary"),
    "action_plan": ("boundary_message", "narrative"),
    # action_plan 내 개별 item 검증은 component='action_item' 로 별도 호출
}


def validate_pi_content(
    *,
    section_id: str,
    content: Optional[dict] = None,
    text: Optional[str] = None,
) -> PIValidationResult:
    """PI-A 호환 진입점. content dict 또는 단일 text 검증.

    호출 패턴:
      content + section_id : 9 컴포넌트 content dict 안의 user-facing 필드 전수 검증
      text + section_id     : 단일 텍스트 검증 (action item 등)

    section_id 가 PI_USER_FACING_KEYS 에 없으면 default budget 적용.

    Returns:
      PIValidationResult — errors empty 이면 ok.

    Examples:
      >>> r = validate_pi_content(
      ...     section_id="cover",
      ...     content={"user_summary": "정세현님 본인다움이 또렷하게 ..."},
      ... )
      >>> r.ok
      True

      >>> r = validate_pi_content(
      ...     section_id="action_item",
      ...     text="레이어드 컷을 한 번 시도해보세요",
      ... )
    """
    result = PIValidationResult()

    # 단일 text 모드
    if text is not None:
        sub = validate_pi_text(text, component=section_id)
        result.errors.extend(sub.errors)
        result.warnings.extend(sub.warnings)
        return result

    # content dict 모드
    if not isinstance(content, dict):
        return result   # 비어있으면 통과 (LLM 호출 전 stub)

    keys = PI_USER_FACING_KEYS.get(section_id, ())
    if not keys:
        # default — content 의 모든 string value 를 default budget 으로 검증
        keys = tuple(
            k for k, v in content.items()
            if isinstance(v, str) and v.strip()
        )

    for key in keys:
        v = content.get(key)
        if not isinstance(v, str) or not v.strip():
            continue
        sub = validate_pi_text(v, component=section_id)
        # 에러 메시지에 key 정보 prefix
        for e in sub.errors:
            result.errors.append(f"{section_id}.{key}: {e}")
        for w in sub.warnings:
            result.warnings.append(f"{section_id}.{key}: {w}")

    # action_plan.items[].narrative 검증 — component='action_item' budget
    if section_id == "action_plan":
        items = content.get("items") or content.get("action_items")
        if isinstance(items, list):
            for idx, item in enumerate(items):
                if not isinstance(item, dict):
                    continue
                item_text = (
                    item.get("narrative")
                    or item.get("text")
                    or item.get("hint")
                )
                if not isinstance(item_text, str) or not item_text.strip():
                    continue
                sub = validate_pi_text(item_text, component="action_item")
                for e in sub.errors:
                    result.errors.append(f"action_plan.items[{idx}]: {e}")
                for w in sub.warnings:
                    result.warnings.append(f"action_plan.items[{idx}]: {w}")

    return result


def collect_pi_content_violations(
    *,
    section_id: str,
    content: Optional[dict] = None,
    text: Optional[str] = None,
) -> list[str]:
    """sia_writer._call_with_retry validator 호환 — list[str] 반환.

    PI-A 가 LLM 응답 (JSON) 을 dict 로 파싱한 후 validator 인자에 partial 형태로
    이 함수를 주입할 때 사용:
      from functools import partial
      validator = partial(collect_pi_content_violations, section_id="cover")
      writer._call_with_retry(..., validator=lambda raw: validator(content=json.loads(raw)))
    """
    return list(
        validate_pi_content(
            section_id=section_id,
            content=content,
            text=text,
        ).errors
    )
