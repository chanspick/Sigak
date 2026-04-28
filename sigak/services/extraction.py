"""Sonnet 4.6 conversation → structured fields extraction (v2 Priority 1 D4).

Flow:
  Redis 세션 종료 후 routes.sia.chat_end 가 BackgroundTask 로 호출
    → extract_structured_fields(messages)
    → ExtractionResult 반환
    → routes.sia 가 mark_extracted (성공) / mark_failed (실패) 분기

설계 원칙:
  1. 대화 증거에 근거해서만 추출. 유저가 직접 말하지 않은 것 추정/환각 금지.
  2. confidence 낮은 (<0.4) 필드는 null 로 저장 + fallback_needed 리스트에 추가.
  3. 재시도 1회 후 실패 시 ExtractionError 발생. caller 가 mark_failed 호출.
  4. 출력은 JSON 만. Pydantic (ExtractionResult) 로 shape 보장.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

import anthropic
from pydantic import ValidationError

from config import get_settings
from schemas.user_profile import (
    ConversationMessage,
    ExtractionResult,
    StructuredFields,
    StructuredFieldsConfidence,
)


logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """Extraction 재시도 후에도 실패. Caller (routes/sia) 가 mark_failed 호출해야 함."""


# ─────────────────────────────────────────────
#  System Prompt
# ─────────────────────────────────────────────

EXTRACTION_SYSTEM_PROMPT = """당신은 SIGAK 의 대화 분석 엔진입니다.
Sia (AI 미감 분석가) 와 유저의 대화 로그를 분석해 structured fields 를 추출합니다.

[역할]
- 대화 증거에 근거해서만 추출한다.
- 유저가 직접 말하지 않은 것을 추정하거나 환각하지 않는다.
- 모호한 답변은 confidence 를 낮게 매기고 null 처리한다.
- 출력은 JSON 만. 다른 텍스트 금지.

[출력 스키마 — 엄격 준수]
{
  "fields": {
    "desired_image": string | null,
    "reference_style": string | null,
    "current_concerns": [string, ...] | null,
    "self_perception": string | null,
    "lifestyle_context": string | null,
    "height": one of ["under_155","155_160","160_165","165_170","170_175","175_180","180_185","185_190","over_190"] | null,
    "weight": one of ["under_45","45_50","50_55","55_60","60_65","65_70","70_80","80_90","over_90"] | null,
    "shoulder_width": one of ["narrow","medium","wide"] | null,
    "confidence": {
      "desired_image": 0.0~1.0,
      "reference_style": 0.0~1.0,
      "current_concerns": 0.0~1.0,
      "self_perception": 0.0~1.0,
      "lifestyle_context": 0.0~1.0,
      "height": 0.0~1.0,
      "weight": 0.0~1.0,
      "shoulder_width": 0.0~1.0
    }
  },
  "fallback_needed": [string, ...]
}

[필드별 spec]

desired_image — 유저가 추구하는 이미지/인상.
  형식: 1-2 문장 요약, 유저 단어 가능하면 그대로.
  예: "편안하고 친밀한 인상, 세련된 거리감보다 접근성 우선"

reference_style — 유저가 T2 답변에서 언급한 사람 (연예인/주변 사람) 또는 사진/장면.
  형식: 없으면 null. 있으면 쉼표 구분 문자열.
  예: "한소희 초반, 카리나 일부" / "친구 지은이가 입은 베이지 코트"
  v4 변경 (2026-04-28): 셀럽/브랜드/이미지 소스 → "딱 떠오르는 사람 / 사진이나 장면"
  으로 spec 갱신 (T2 템플릿과 정합).

current_concerns — 유저가 표명한 현재 고민.
  형식: list[string], 각 항목 1 문장.
  예: ["추구미와 피드 보여지는 방향 갭", "톤이 너무 어둡게만 보이는 것"]

self_perception — 유저가 본인 현재 이미지를 어떻게 보는지.
  형식: 1 문장.
  예: "정돈된 인상이라는 말을 자주 듣는다"

lifestyle_context — 직업/일상/주요 활동.
  형식: 1-2 문장.
  예: "프리랜서 기획자, 주말은 친구들과 캐주얼 활동"

height / weight / shoulder_width — 체형.
  height: 유저가 cm 숫자 또는 구간 직접 언급한 경우만 해당 enum.
      "165" → "165_170", "163" → "160_165", "170대 초반" → "170_175"
  weight: 유저가 kg 숫자 직접 언급한 경우만. "50 초반" → "50_55".
  shoulder_width: 유저가 "좁은/보통/넓은" 또는 narrow/medium/wide 직접 언급.
  **추정 금지**. 유저가 해당 정보를 제공하지 않으면 null.

confidence — 각 필드별 추출 신뢰도:
  - 0.8~1.0: 유저가 명확하게 직접 언급
  - 0.5~0.8: 문맥상 추론 가능하지만 정확성 확신 어려움
  - 0.4~0.5: 모호한 단서만 있음
  - <0.4: 증거 부족 (null 처리 + fallback_needed 에 필드명 추가)

fallback_needed — 아래 조건에 해당하는 필드명 리스트:
  - confidence < 0.4
  - 유저가 질문을 회피/거부한 경우
  - 유저가 "모르겠다" / "어색하다" 등 응답한 경우

[환각 금지 — 엄격]
- 대화에 없는 직업/나이/체형 추정 금지.
- "친구와 술자리" 언급만 있으면 lifestyle_context 에 활동만 기록, 직업은 null.
- Sia 가 유저에게 제시한 선택지 문구를 유저 발화로 오인해서 반영하지 말 것.
  (예: Sia 가 "편안하고 기대고 싶은 인상" 선택지 제시 → 유저 "1번" 선택 →
   desired_image 는 "편안하고 기대고 싶은 인상" 기반 요약 OK, 하지만 유저가
   말하지 않은 추가 뉘앙스 덧붙임 금지.)

[출력 형식]
- 반드시 유효한 JSON 하나만 반환. 마크다운 코드 블록 감싸지 말 것.
- 주석, 설명 텍스트, 머리말 금지.
- ```json ... ``` 같은 wrapper 금지.
"""


# ─────────────────────────────────────────────
#  Anthropic Client (Sonnet 4.6, separate from Haiku)
# ─────────────────────────────────────────────

_client: Optional[anthropic.Anthropic] = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not configured")
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def reset_client() -> None:
    """테스트 격리 용."""
    global _client
    _client = None


# ─────────────────────────────────────────────
#  Message log rendering
# ─────────────────────────────────────────────

def _render_messages_for_prompt(messages: list[ConversationMessage]) -> str:
    """대화 로그 → Sonnet 에 전달할 텍스트.

    role 별 태그 사용 — user: / assistant (Sia): 구분.
    ts 는 포함하지 않음 (추출에 불필요).
    """
    lines = []
    for i, m in enumerate(messages):
        tag = "사용자" if m.role == "user" else "Sia"
        # 다중라인 content 는 그대로 보존 (4지선다 포맷 등)
        lines.append(f"[턴 {i+1} · {tag}]\n{m.content}")
    return "\n\n".join(lines)


# ─────────────────────────────────────────────
#  Low-level Sonnet call
# ─────────────────────────────────────────────

def _call_sonnet(messages: list[ConversationMessage], max_tokens: int = 2000) -> str:
    """Sonnet 4.6 호출 — JSON 텍스트 응답 반환.

    Raises:
        anthropic.APIError: 네트워크/API 오류
    """
    settings = get_settings()
    client = _get_client()

    user_prompt = (
        "다음 Sia ↔ 유저 대화 로그를 분석해서 structured fields JSON 을 생성해 "
        "주십시오.\n\n"
        "[대화 로그]\n"
        f"{_render_messages_for_prompt(messages)}\n\n"
        "위 대화 증거만 사용해서 스키마에 맞는 JSON 을 반환하십시오. "
        "증거 부족한 필드는 null + fallback_needed 에 추가합니다."
    )

    response = client.messages.create(
        model=settings.anthropic_model_sonnet,
        max_tokens=max_tokens,
        system=EXTRACTION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    if not response.content:
        raise ExtractionError("empty Sonnet response")
    text_blocks = [b.text for b in response.content if b.type == "text"]
    if not text_blocks:
        raise ExtractionError("no text block in Sonnet response")
    return "\n".join(text_blocks).strip()


# ─────────────────────────────────────────────
#  Post-processing
# ─────────────────────────────────────────────

def _strip_json_fence(text: str) -> str:
    """혹시 Sonnet 이 ```json ... ``` 래핑하면 제거 (방어적)."""
    t = text.strip()
    if t.startswith("```"):
        # 첫 줄 제거 (```json 또는 ```)
        lines = t.split("\n")
        if len(lines) > 1:
            lines = lines[1:]
        # 마지막 ``` 라인 제거
        while lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t


def _enforce_confidence_nulls(result: ExtractionResult) -> ExtractionResult:
    """confidence <0.4 인 필드를 null 로 정규화 + fallback_needed 보강.

    Sonnet 이 규칙을 안 지킬 수도 있으므로 application layer 에서 재확인.
    """
    fields = result.fields
    confidence = fields.confidence
    if confidence is None:
        return result

    fallback_set = set(result.fallback_needed)

    # 각 필드 체크
    field_names = [
        "desired_image", "reference_style", "current_concerns",
        "self_perception", "lifestyle_context",
        "height", "weight", "shoulder_width",
    ]
    for fname in field_names:
        conf = getattr(confidence, fname, 0.0)
        current_val = getattr(fields, fname)
        if conf < 0.4 and current_val is not None:
            logger.info(
                "extraction: demoting %s to null (confidence=%.2f < 0.4)",
                fname, conf,
            )
            setattr(fields, fname, None)
            fallback_set.add(fname)

    return ExtractionResult(
        fields=fields,
        fallback_needed=sorted(fallback_set),
    )


# ─────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────

def extract_structured_fields(
    messages: list[ConversationMessage],
    *,
    max_retries: int = 1,
) -> ExtractionResult:
    """대화 로그 → ExtractionResult.

    Raises:
        ExtractionError: max_retries 초과 후에도 실패 (parse/validation/API 오류).
    """
    if not messages:
        raise ExtractionError("empty messages — cannot extract")

    last_error: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            raw_text = _call_sonnet(messages)
            clean_text = _strip_json_fence(raw_text)
            parsed = json.loads(clean_text)
            result = ExtractionResult.model_validate(parsed)
            result = _enforce_confidence_nulls(result)
            logger.info(
                "extraction success: attempt=%d turns=%d fallback_needed=%s",
                attempt + 1, len(messages), result.fallback_needed,
            )
            return result
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = e
            logger.warning(
                "extraction parse/validation failed (attempt %d): %s",
                attempt + 1, e,
            )
            continue
        except anthropic.APIError as e:
            last_error = e
            logger.warning(
                "Sonnet API error (attempt %d): %s", attempt + 1, e,
            )
            continue

    raise ExtractionError(f"extraction failed after {max_retries + 1} attempts: {last_error}")
