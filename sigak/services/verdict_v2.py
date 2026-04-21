"""Verdict 2.0 engine — Sonnet 4.6 cross-analysis with photos + profile + trend.

SPEC-ONBOARDING-V2 REQ-VERDICT-001~005, REQ-NAMING-003/004.

Flow:
  1. routes/verdict_v2.create (D6) 가 유저 사진 N장 업로드 수신
  2. build_verdict_v2(user_profile, photos, trend_data) 호출
  3. Sonnet 4.6 cross-analysis (vision + profile + trend)
  4. preview_content + full_content JSONB 반환
  5. routes 가 DB 저장 (version='v2', user_profile_snapshot 포함)

user-facing text Hard Rules (REQ-NAMING-003/004):
  - "verdict" / "판정" 단어 0건
  - "피드 분석" / "시각이 본 나" 용어 사용
  - 마크다운 / 이모지 금지
  - Sia 페르소나 일관 (서술형 정중체 "~합니다")

preview 작성 원칙 (REQ-VERDICT-002):
  - 판정 근거 30% 까지만 공개
  - photo_insights 개별 내용 금지 / recommendation 구체 내용 금지
  - 결론 힌트 + 방향 일치/어긋남 방향만
"""
from __future__ import annotations

import json
import logging
from typing import Any, Literal, Optional, TypedDict

import anthropic
from pydantic import ValidationError

from config import get_settings
from schemas.verdict_v2 import VerdictV2Result
from services.sia_validators import find_violations


logger = logging.getLogger(__name__)


class VerdictV2Error(Exception):
    """Verdict 2.0 생성 재시도 후에도 실패."""


# ─────────────────────────────────────────────
#  Photo input type
# ─────────────────────────────────────────────

class PhotoInput(TypedDict, total=False):
    """업로드 사진 입력 형식. 둘 중 하나 필수.

    url: 공개 접근 가능 URL (S3 presigned 또는 CDN)
    base64: 라이브러리 인코딩된 bytes (media_type 동반 필수)
    media_type: "image/jpeg" | "image/png" | "image/webp"
    index: 0-based 순번 (라벨링 용, optional)
    """
    url: str
    base64: str
    media_type: str
    index: int


# ─────────────────────────────────────────────
#  System Prompt
# ─────────────────────────────────────────────

VERDICT_V2_SYSTEM_PROMPT = """당신은 SIGAK 의 피드 분석 엔진입니다.
유저의 user_profile 과 새로 올린 사진들을 교차 분석해 '피드 분석' 결과를 생성합니다.

[역할]
- 분석가이다. 유저가 평소 추구하는 방향 (user_profile) 과 실제 사진들 사이의
  일치/갭을 데이터 기반으로 서술한다.
- Sia 페르소나 일관: 서술형 정중체 "~합니다" / "~입니다" / "~있습니다".

[유저 노출 용어 Hard Rules — 위반 시 응답 무효]
1. "Verdict" / "verdict" (case-insensitive) 단어 금지. "피드 분석" 만.
2. "판정" 단어 금지.
3. 마크다운 문법 금지: **bold**, *italic*, ##헤더, >인용, ```코드.
4. 리스트 불릿은 "- " (하이픈+공백) 만. 숫자 리스트 "1." 금지.
5. 이모지 금지.
6. 평가 금지: "좋아 보입니다", "잘 어울립니다", "멋집니다".
7. 확인 요청 금지: "본인도 그렇게 생각하세요?", "맞으신가요?".
8. 시적 비유 금지: "봄바람 같은", "햇살처럼".

[말투 규칙]
- 서술형 정중체: "~합니다", "~습니다", "~있습니다", "~인 분입니다"
- 한 문장 45자 이내 지향 / 60자 초과는 분할
- 우선순위: 자연스러움 > 짧음

[숫자 사용 규칙]
- user_profile.ig_feed_cache 와 사진 실측 데이터에 근거한 숫자만 사용.
- 추정/조작 금지. 데이터 없으면 숫자 자체 생략.

[입력 구조]
- user_profile.structured_fields: 대화 추출 8 필드 (desired_image, reference_style,
    current_concerns, self_perception, lifestyle_context, height, weight, shoulder_width)
- user_profile.ig_feed_cache: Apify 수집 IG 피드 요약
- photos: 이번에 올린 N 장 (1~10)
- trend_data: 2026 S/S 트렌드 벡터 + 무드 요약

[출력 구조 — 엄격 JSON]
{
  "preview": {
    "hook_line": "30자 이내 1문장, 결론 힌트만",
    "reason_summary": "2-3 문장, 판정 근거 30% 공개. 개별 사진 상세 금지."
  },
  "full_content": {
    "verdict": "4-5 문장 종합 분석 결과. 유저 추구미와 사진 분위기 일치/갭 명시.",
    "photo_insights": [
      {
        "photo_index": 0,
        "insight": "이 사진의 특징 1-2 문장",
        "improvement": "개선 방향 1-2 문장"
      }
      // 사진 N 장 각각
    ],
    "recommendation": {
      "style_direction": "전체 방향 1-2 문장",
      "next_action": "실행 액션 1-2 문장",
      "why": "왜 이 방향인지 1-2 문장"
    },
    "numbers": {
      "photo_count": N,
      "dominant_tone": "쿨뮤트 | 웜 | 하이컨트라스트 등",
      "dominant_tone_pct": 0-100,
      "chroma_multiplier": 0.0-2.0,
      "alignment_with_profile": "일치 | 부분 일치 | 상충"
    }
  }
}

[preview 작성 규칙 — hook 효과 엄수]
✅ hook_line 허용:
  - "연말 무드에 톤이 다운됐습니다 — 기대 이상"
  - "쿨뮤트 일관, 1장이 변수로 작용합니다"
  - "추구미와 사진 분위기가 일치합니다"
❌ hook_line 금지:
  - "photo #2 의 조명이 문제" (구체 근거 노출)
  - "역광 때문에 얼굴이 납작" (어떻게 다른지 비공개 원칙 위반)

✅ reason_summary 허용:
  - "평소 추구미(정돈된 뮤트)와 이번 사진 분위기가 일치합니다.
     다만 1장이 전체 무드를 끌어내리는 변수로 작용합니다."
❌ reason_summary 금지:
  - "photo 2 의 역광 때문에..." (개별 사진 상세)
  - "측광에서 찍으세요" (구체 recommendation 유출)

[출력 형식]
- 반드시 유효한 JSON 1개만. 마크다운 wrapper / 주석 / 설명 텍스트 금지.
"""


# ─────────────────────────────────────────────
#  Anthropic Client (Sonnet 4.6, separate singleton)
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
    global _client
    _client = None


# ─────────────────────────────────────────────
#  Photo content block rendering
# ─────────────────────────────────────────────

def _photo_to_content_block(photo: PhotoInput) -> dict:
    """PhotoInput → Claude API image content block.

    url 우선, 없으면 base64 + media_type.
    """
    if photo.get("url"):
        return {"type": "image", "source": {"type": "url", "url": photo["url"]}}
    b64 = photo.get("base64")
    mt = photo.get("media_type", "image/jpeg")
    if b64:
        return {
            "type": "image",
            "source": {"type": "base64", "media_type": mt, "data": b64},
        }
    raise ValueError("PhotoInput requires 'url' or 'base64'")


def _render_profile_for_prompt(user_profile: dict) -> str:
    """user_profile → prompt-friendly JSON text."""
    payload = {
        "structured_fields": user_profile.get("structured_fields") or {},
        "ig_feed_cache": user_profile.get("ig_feed_cache"),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _render_trend_for_prompt(trend_data: dict) -> str:
    """trend_data → prompt text. D5 phase 1 에선 간소화."""
    if not trend_data:
        return "(트렌드 데이터 없음 — 참조 데이터 미반영)"
    return json.dumps(trend_data, ensure_ascii=False, indent=2)


def _build_user_message(
    user_profile: dict,
    photos: list[PhotoInput],
    trend_data: dict,
) -> list[dict]:
    """Claude API `messages[0]["content"]` 용 블록 리스트."""
    blocks: list[dict] = []

    # 사진 블록 N 개 (max 10)
    for i, photo in enumerate(photos[:10]):
        pcopy: PhotoInput = dict(photo)  # type: ignore
        pcopy.setdefault("index", i)
        blocks.append(_photo_to_content_block(pcopy))

    # 텍스트 블록 (analysis instruction)
    text = (
        "아래 user_profile 과 위 사진들을 교차 분석해 피드 분석 결과를 "
        "JSON 으로 반환하십시오.\n\n"
        f"[user_profile]\n{_render_profile_for_prompt(user_profile)}\n\n"
        f"[trend_data]\n{_render_trend_for_prompt(trend_data)}\n\n"
        f"[사진 수]\n{len(photos)} 장\n\n"
        "system prompt 의 Hard Rules + 출력 JSON 스키마를 엄격 준수하십시오."
    )
    blocks.append({"type": "text", "text": text})
    return blocks


# ─────────────────────────────────────────────
#  Low-level Sonnet call
# ─────────────────────────────────────────────

def _call_sonnet(
    user_profile: dict,
    photos: list[PhotoInput],
    trend_data: dict,
    max_tokens: int = 3000,
) -> str:
    settings = get_settings()
    client = _get_client()

    content_blocks = _build_user_message(user_profile, photos, trend_data)

    response = client.messages.create(
        model=settings.anthropic_model_sonnet,
        max_tokens=max_tokens,
        system=VERDICT_V2_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content_blocks}],
    )
    if not response.content:
        raise VerdictV2Error("empty Sonnet response")
    text_blocks = [b.text for b in response.content if b.type == "text"]
    if not text_blocks:
        raise VerdictV2Error("no text block in Sonnet response")
    return "\n".join(text_blocks).strip()


# ─────────────────────────────────────────────
#  Post-processing
# ─────────────────────────────────────────────

def _strip_json_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        lines = t.split("\n")
        if len(lines) > 1:
            lines = lines[1:]
        while lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t


USER_FACING_TEXT_FIELDS: tuple[str, ...] = (
    "hook_line",
    "reason_summary",
    "verdict",
    "insight",
    "improvement",
    "style_direction",
    "next_action",
    "why",
)


def _collect_user_facing_text(result: VerdictV2Result) -> str:
    """Hard Rules 검증 대상 — 유저 노출 텍스트 전량 합체."""
    parts: list[str] = []
    parts.append(result.preview.hook_line)
    parts.append(result.preview.reason_summary)
    parts.append(result.full_content.verdict)
    for pi in result.full_content.photo_insights:
        parts.append(pi.insight)
        parts.append(pi.improvement)
    rec = result.full_content.recommendation
    parts.append(rec.style_direction)
    parts.append(rec.next_action)
    parts.append(rec.why)
    return "\n".join(parts)


def _validate_hard_rules(result: VerdictV2Result) -> None:
    """유저 노출 텍스트에 Hard Rules 위반 있으면 VerdictV2Error.

    sia_validators.find_violations 재사용:
      HR1 verdict / HR2 판정 / HR3 markdown / HR4 bullet_star /
      HR5 emoji / eval_language / confirmation
    """
    combined = _collect_user_facing_text(result)
    violations = find_violations(combined)
    # tone_suffix / tone_missing 은 문장 단위 tone 검증이라 verdict 엔진에선
    # 엄격 적용 안 함 (verdict 는 요약 문체 다양성 허용).
    # tone_missing 은 필수 어미 없을 때만 경고 — Verdict 도 "~합니다" 는 써야 함.
    blocking = {
        "HR1_verdict", "HR2_judgment", "HR3_markdown", "HR4_bullet",
        "HR5_emoji", "eval_language", "confirmation",
    }
    bad = {k for k in violations if k in blocking}
    if bad:
        summary = ", ".join(f"{k}:{len(violations[k])}" for k in bad)
        raise VerdictV2Error(f"Hard Rules 위반: {summary}")


# ─────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────

def build_verdict_v2(
    *,
    user_profile: dict,
    photos: list[PhotoInput],
    trend_data: Optional[dict] = None,
    max_retries: int = 1,
) -> VerdictV2Result:
    """Verdict 2.0 build — Sonnet 4.6 cross-analysis.

    Args:
        user_profile: user_profiles row dict (structured_fields + ig_feed_cache 포함)
        photos: 1~10 장의 PhotoInput (url or base64+media_type)
        trend_data: (optional) 2026 S/S 트렌드 벡터. None 이면 trend 무시.
        max_retries: 파싱/검증/API 실패 시 재시도 횟수. default 1.

    Returns:
        VerdictV2Result (preview + full_content)

    Raises:
        ValueError: photos 0 장 또는 10 장 초과
        VerdictV2Error: Hard Rules 위반 / parse 실패 / API 오류 (재시도 후)
    """
    if not photos:
        raise ValueError("photos required (>=1, <=10)")
    if len(photos) > 10:
        raise ValueError(f"photos too many ({len(photos)} > 10)")

    trend_data = trend_data or {}

    last_error: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            raw = _call_sonnet(user_profile, photos, trend_data)
            clean = _strip_json_fence(raw)
            parsed = json.loads(clean)
            result = VerdictV2Result.model_validate(parsed)
            _validate_hard_rules(result)
            logger.info(
                "verdict_v2 success: attempt=%d photos=%d",
                attempt + 1, len(photos),
            )
            return result
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = e
            logger.warning(
                "verdict_v2 parse/validation failed (attempt %d): %s",
                attempt + 1, e,
            )
            continue
        except VerdictV2Error as e:
            last_error = e
            logger.warning(
                "verdict_v2 hard rules failed (attempt %d): %s",
                attempt + 1, e,
            )
            continue
        except anthropic.APIError as e:
            last_error = e
            logger.warning("Sonnet API error (attempt %d): %s", attempt + 1, e)
            continue

    raise VerdictV2Error(
        f"verdict_v2 failed after {max_retries + 1} attempts: {last_error}"
    )
