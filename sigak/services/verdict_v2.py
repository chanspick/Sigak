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

import io
import json
import logging
import time
from typing import Any, Literal, Optional, TypedDict

import anthropic
from PIL import Image, ImageOps
from pydantic import ValidationError

from config import get_settings
from schemas.verdict_v2 import VerdictV2Result
from services.sia_validators import find_violations


logger = logging.getLogger(__name__)


class VerdictV2Error(Exception):
    """Verdict 2.0 생성 재시도 후에도 실패."""


class VerdictV2RateLimitedError(VerdictV2Error):
    """Anthropic rate limit 으로 시도 모두 소진. UI 친화 메시지 분기용."""


# ─────────────────────────────────────────────
#  Image downscale — 413 Request Too Large 방어
# ─────────────────────────────────────────────

# Anthropic 서버 측 resize 기준과 맞춤 — 1568px 초과 시 서버가 어차피 축소.
# 긴 변 1568px + JPEG q=85 면 ~200-400KB/장 수준 → 10장도 5MB 이하.
MAX_LONGEST_SIDE_PX = 1568
JPEG_QUALITY = 85


def downscale_image(data: bytes) -> tuple[bytes, str]:
    """원본 이미지 bytes → (downscaled JPEG bytes, "image/jpeg").

    규칙:
      - EXIF orientation 적용 (rotated 이미지 정방향화)
      - RGB 변환 (JPEG 호환 — PNG alpha / CMYK 등 대응)
      - 긴 변 1568px 초과 시 LANCZOS 비율 유지 resize
      - JPEG quality=85 encode

    실패 시 원본 그대로 반환 (best effort). 호출자는 항상 jpeg 로 처리 가능.
    """
    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        w, h = img.size
        longest = max(w, h)
        if longest > MAX_LONGEST_SIDE_PX:
            ratio = MAX_LONGEST_SIDE_PX / longest
            img = img.resize(
                (max(1, int(w * ratio)), max(1, int(h * ratio))),
                Image.Resampling.LANCZOS,
            )
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        return buf.getvalue(), "image/jpeg"
    except Exception:
        logger.exception(
            "downscale_image failed (original_bytes=%d) — using original",
            len(data),
        )
        return data, "image/jpeg"


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
- taste_profile (Phase L): 누적 UserTasteProfile 스냅샷.
    current_position / aspiration_vector / user_original_phrases / strength_score
    → 유저 의도 + 데이터 풍부도 파악용. 과거 대화 핵심 어휘는 user_original_phrases
      에서 읽어 "말 들었구나" 감각 보존에 활용 (직접 인용 금지, 결 녹여 재사용).
- matched_trends (Phase L): KnowledgeBase 매칭 결과 (유저 좌표 호환 순위).
    각 항목 title / action_hints / score 형태. style_direction / cta_pi 작성시
    참조. 단, trend_id 등 내부 식별자는 유저 텍스트에 노출 금지.

[출력 구조 — 엄격 JSON]
{
  "preview": {
    "hook_line": "30자 이내 1문장, 결론 힌트만",
    "reason_summary": "2-3 문장, 판정 근거 30% 공개. 개별 사진 상세 금지.",
    "best_fit_photo_index": 0,
    "best_fit_insight": "best_fit 사진의 insight 와 동일 (full_content.photo_insights[best_fit_photo_index].insight 복사)",
    "best_fit_improvement": "best_fit 사진의 improvement 와 동일 (full_content.photo_insights[best_fit_photo_index].improvement 복사)"
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
    },
    "best_fit_photo_index": 0,
    "cta_pi": {
      "headline": "30자 이내 훅. '시각이 본 나' 를 자연 연결",
      "body": "1-2 문장. 피드 분석에서 드러난 갭을 '시각이 본 나' 가 얼굴·비율·컬러 레벨로 한 단계 더 드러낸다는 교차 설명.",
      "action_label": "20자 이내 버튼 카피 (예: '시각이 본 나 열기')"
    }
  }
}

[best_fit 선정 규칙 — WTP 가설 핵심]
- photo_insights 중 taste_profile (current_position / aspiration_vector) 와
  가장 부합하는 사진의 photo_index 를 best_fit_photo_index 에 명시.
- 동률이면 photo_index 가 작은 쪽.
- 어떤 사진도 부합하지 않으면 best_fit_photo_index 는 null.
- best_fit_photo_index 가 명시되면 해당 photo_insight 의 insight + improvement 를
  preview.best_fit_insight / preview.best_fit_improvement 에도 동일 내용 복사.
- best_fit insight / improvement 는 풀 노출 예외 (개별 사진 상세 금지 룰 면제).
- best_fit insight / improvement 는 photo_insights[best_fit_photo_index] 와
  완전 동일해야 함 (재서술 금지 — 일관성 보장).
- preview.best_fit_photo_index 와 full_content.best_fit_photo_index 는 동일 값.

[cta_pi 작성 규칙 — Sia 톤 + 용어 안전]
- "시각이 본 나" 라는 고유 명사로 노출 (유저에겐 우리 제품 이름).
- "PI" / "Personal Image" 영문 단일 단어 노출 금지.
- 판정어 / 평가어 / 확인 요청 금지 (상위 Hard Rules 동일).
- headline 은 강권/명령 아닌 제시형 (예: "시각이 본 나, 같이 살펴보시겠습니까" ❌
  대신 "피드 분석 너머 얼굴 단위까지 이어집니다" 류).
- body 는 verdict 결과 (alignment / 갭 / 추구미 방향) 를 한 문장으로 짚고,
  "시각이 본 나" 가 어떤 추가 정보를 주는지 한 문장으로 연결.

✅ cta_pi 허용 예시:
  {
    "headline": "피드 분석에서 본 톤, 얼굴 단위로 이어집니다",
    "body": "평소 추구미와 피드 분위기의 맞물림은 보셨습니다. 시각이 본 나 에서는 얼굴 비율·언더톤·라인까지 같은 방향인지 확인하실 수 있습니다.",
    "action_label": "시각이 본 나 열기"
  }

❌ cta_pi 금지 예시:
  - "PI 리포트로 이동하세요" (PI 단어 노출 + 명령형)
  - "판정 결과를 자세히 보시겠습니까?" (판정 사용 + 확인 요청)
  - "당신의 이미지를 멋지게 분석해드립니다" (평가 + 확인 요청)

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

[best_fit 풀 노출 — 위 reason_summary 룰의 명시 예외]
- best_fit_insight / best_fit_improvement 는 1 장만 (best_fit_photo_index)
  결제 전 풀 공개. 위 "개별 사진 상세 금지" 룰의 단일 예외.
- best_fit_insight 는 photo_insights[best_fit_photo_index].insight 와 완전 동일.
- best_fit_improvement 는 photo_insights[best_fit_photo_index].improvement 와
  완전 동일. 풀 공개 영역의 톤 / 길이 / 표현 모두 photo_insights 항목과 동일.
- 위 텍스트도 상위 Hard Rules (HR1~HR5, eval_language, confirmation) 동일 적용.

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


def _render_matched_trends(matched_trends: Optional[list]) -> str:
    """KnowledgeMatcher 결과 → prompt 텍스트 (Phase L).

    matched_trends 요소는 MatchedTrend (pydantic) 또는 dict 호환.
    """
    if not matched_trends:
        return "(KB 매칭 없음)"
    lines: list[str] = []
    for m in matched_trends[:5]:
        trend = m.trend if hasattr(m, "trend") else m.get("trend", {})
        trend_id = getattr(trend, "trend_id", None) or trend.get("trend_id", "?") if isinstance(trend, dict) else getattr(trend, "trend_id", "?")
        title = getattr(trend, "title", None) or (trend.get("title", "?") if isinstance(trend, dict) else "?")
        action_hints = getattr(trend, "action_hints", None) if not isinstance(trend, dict) else trend.get("action_hints", [])
        action_hints = action_hints or []
        score = getattr(m, "score", None) if not isinstance(m, dict) else m.get("score", 0.0)
        score_str = f"{float(score):.2f}" if score is not None else "0.00"
        hints_str = " / ".join(action_hints[:3]) if action_hints else "-"
        lines.append(f"- [{trend_id}] {title} (score={score_str}) · hints: {hints_str}")
    return "\n".join(lines)


def _render_taste_profile(taste_profile: Optional[dict]) -> str:
    """UserTasteProfile snapshot → prompt 텍스트 (Phase L).

    pydantic 인스턴스거나 model_dump 결과 dict 둘 다 허용.
    """
    if taste_profile is None:
        return "(유저 취향 프로필 없음 — 현 profile 만으로 분석)"
    dump = (
        taste_profile.model_dump(mode="json")
        if hasattr(taste_profile, "model_dump")
        else taste_profile
    )
    # 노출 필드 선별 — 프롬프트에 꼭 필요한 것만
    slim = {
        "current_position": dump.get("current_position"),
        "aspiration_vector": dump.get("aspiration_vector"),
        "conversation_signals": dump.get("conversation_signals"),
        "user_original_phrases": dump.get("user_original_phrases"),
        "strength_score": dump.get("strength_score"),
    }
    return json.dumps(slim, ensure_ascii=False, indent=2)


def _render_latest_pi_for_verdict(taste_profile: Optional[Any]) -> str:
    """taste_profile.latest_pi → Verdict v2 prompt 우회 block.

    Phase I Backward echo: 본인 본질 좌표 (coord_3axis) + 닮은꼴 셀럽 (top_celeb)
    을 Verdict v2 가 IG 추구미 좌표 vs 본질 좌표 비교 시 활용. 상품명 직접 호명
    금지 — "지난번 정밀 분석" 우회 표현. None / 빈 latest_pi → "" (회귀 0).
    """
    if taste_profile is None:
        return ""
    latest_pi = getattr(taste_profile, "latest_pi", None)
    if latest_pi is None:
        return ""

    lines: list[str] = []
    coord = getattr(latest_pi, "coord_3axis", None)
    if isinstance(coord, dict):
        try:
            lines.append(
                f"  본질 좌표: shape {float(coord.get('shape', 0.5)):.2f} / "
                f"volume {float(coord.get('volume', 0.5)):.2f} / "
                f"age {float(coord.get('age', 0.5)):.2f}"
            )
        except (TypeError, ValueError):
            pass
    top_celeb = getattr(latest_pi, "top_celeb_name", None)
    if top_celeb:
        sim = getattr(latest_pi, "top_celeb_similarity", None)
        if isinstance(sim, (int, float)):
            lines.append(
                f"  닮은꼴 셀럽: {top_celeb} (유사도 {float(sim):.2f})"
            )
        else:
            lines.append(f"  닮은꼴 셀럽: {top_celeb}")

    if not lines:
        return ""

    return (
        "[본질 분석 — 본인 정합 좌표]\n"
        "지난번 정밀 분석에서:\n"
        + "\n".join(lines)
        + "\n\n"
    )


def _build_user_message(
    user_profile: dict,
    photos: list[PhotoInput],
    trend_data: dict,
    matched_trends: Optional[list] = None,
    taste_profile: Optional[Any] = None,
    history_context: str = "",
) -> list[dict]:
    """Claude API `messages[0]["content"]` 용 블록 리스트.

    Phase L 확장:
      - matched_trends: KnowledgeMatcher 결과 (유저 좌표에 맞춘 KB 트렌드)
      - taste_profile: UserTasteProfile snapshot (대화+IG 기반 누적 취향)

    Phase I Backward echo:
      - taste_profile.latest_pi → 본질 좌표 + 닮은꼴 셀럽 우회 inject (직접)
    """
    blocks: list[dict] = []

    # 사진 블록 N 개 (max 10)
    for i, photo in enumerate(photos[:10]):
        pcopy: PhotoInput = dict(photo)  # type: ignore
        pcopy.setdefault("index", i)
        blocks.append(_photo_to_content_block(pcopy))

    # Phase I — Backward echo block (None / 빈 latest_pi 시 "")
    pi_block = _render_latest_pi_for_verdict(taste_profile)

    # 텍스트 블록 (analysis instruction)
    text_body = (
        "아래 user_profile 과 위 사진들을 교차 분석해 피드 분석 결과를 "
        "JSON 으로 반환하십시오.\n\n"
        f"[user_profile]\n{_render_profile_for_prompt(user_profile)}\n\n"
        + pi_block
        + f"[taste_profile — 누적 취향 스냅샷]\n{_render_taste_profile(taste_profile)}\n\n"
        f"[matched_trends — KB 매칭 (최신 시즌, 유저 좌표 호환)]\n"
        f"{_render_matched_trends(matched_trends)}\n\n"
        f"[trend_data — 시즌 베이스라인]\n{_render_trend_for_prompt(trend_data)}\n\n"
        f"[사진 수]\n{len(photos)} 장\n\n"
        "recommendation.style_direction 과 cta_pi 작성 시 matched_trends 와 "
        "taste_profile 을 참조하되, 숫자/출처 노출 없이 자연스러운 내러티브로 "
        "녹여 주십시오. system prompt 의 Hard Rules + 출력 JSON 스키마를 "
        "엄격 준수하십시오."
    )
    # STEP 5i — cross-session 맥락 주입 (Sia/추구미/BestShot 이전 세션)
    if history_context:
        text_body = history_context + "---\n\n" + text_body
    blocks.append({"type": "text", "text": text_body})
    return blocks


# ─────────────────────────────────────────────
#  Low-level Sonnet call
# ─────────────────────────────────────────────

def _call_sonnet(
    user_profile: dict,
    photos: list[PhotoInput],
    trend_data: dict,
    matched_trends: Optional[list] = None,
    taste_profile: Optional[Any] = None,
    max_tokens: int = 3000,
    history_context: str = "",
) -> str:
    settings = get_settings()
    client = _get_client()

    content_blocks = _build_user_message(
        user_profile, photos, trend_data,
        matched_trends=matched_trends,
        taste_profile=taste_profile,
        history_context=history_context,
    )

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
    """Hard Rules 검증 대상 — 유저 노출 텍스트 전량 합체.

    D5 Phase 3: cta_pi (headline/body/action_label) 포함.
    WTP 가설: preview.best_fit_insight / best_fit_improvement 도 포함
              (결제 전 풀 노출이므로 동일 검증 대상).
    """
    parts: list[str] = []
    parts.append(result.preview.hook_line)
    parts.append(result.preview.reason_summary)
    if result.preview.best_fit_insight is not None:
        parts.append(result.preview.best_fit_insight)
    if result.preview.best_fit_improvement is not None:
        parts.append(result.preview.best_fit_improvement)
    parts.append(result.full_content.verdict)
    for pi in result.full_content.photo_insights:
        parts.append(pi.insight)
        parts.append(pi.improvement)
    rec = result.full_content.recommendation
    parts.append(rec.style_direction)
    parts.append(rec.next_action)
    parts.append(rec.why)
    cta = result.full_content.cta_pi
    if cta is not None:
        parts.append(cta.headline)
        parts.append(cta.body)
        parts.append(cta.action_label)
    return "\n".join(parts)


def _sync_best_fit_fields(result: VerdictV2Result) -> None:
    """preview.best_fit_* 와 full_content.best_fit_photo_index 일관성 보장.

    LLM 산출이 일관성 부족할 때 안전망:
      1. full_content.best_fit_photo_index 가 valid (photo_insights 범위 안) 이면
         그 값을 source of truth 로 채택.
      2. preview.best_fit_photo_index 도 동일 값으로 sync.
      3. preview.best_fit_insight / best_fit_improvement 를 photo_insights 의
         실제 insight / improvement 로 덮어쓰기 (풀 노출 정합성).
      4. full_content.best_fit_photo_index 가 None / 범위 밖이면 best_fit_*
         3 필드 모두 None 으로 정리 (preview 슬롯 비활성).
      5. full_content.best_fit_photo_index 가 None 인데 preview 만 명시된 경우
         preview 값을 source of truth 로 (대칭).

    이 함수는 in-place 수정. 반환값 없음.
    """
    fc = result.full_content
    pv = result.preview

    fc_idx = fc.best_fit_photo_index
    pv_idx = pv.best_fit_photo_index
    insights = fc.photo_insights

    def _valid(idx: Optional[int]) -> bool:
        return idx is not None and 0 <= idx < len(insights)

    # 우선순위 1: full_content.best_fit_photo_index 유효
    if _valid(fc_idx):
        target = insights[fc_idx]   # type: ignore[index]
        pv.best_fit_photo_index = fc_idx
        pv.best_fit_insight = target.insight
        pv.best_fit_improvement = target.improvement
        return

    # 우선순위 2: preview.best_fit_photo_index 만 유효 (full 누락 시 sync)
    if _valid(pv_idx):
        target = insights[pv_idx]   # type: ignore[index]
        fc.best_fit_photo_index = pv_idx
        pv.best_fit_insight = target.insight
        pv.best_fit_improvement = target.improvement
        return

    # 우선순위 3: 둘 다 무효 → 슬롯 정리
    fc.best_fit_photo_index = None
    pv.best_fit_photo_index = None
    pv.best_fit_insight = None
    pv.best_fit_improvement = None


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
    matched_trends: Optional[list] = None,
    taste_profile: Optional[Any] = None,
    max_retries: int = 4,
    history_context: str = "",
) -> VerdictV2Result:
    """Verdict 2.0 build — Sonnet 4.6 cross-analysis.

    Args:
        user_profile: user_profiles row dict (structured_fields + ig_feed_cache 포함)
        photos: 1~10 장의 PhotoInput (url or base64+media_type)
        trend_data: (optional) 2026 S/S 트렌드 벡터. None 이면 trend 무시.
        matched_trends: (Phase L, optional) KnowledgeMatcher 매칭 결과 list[MatchedTrend].
            유저 좌표에 맞춘 KB 트렌드. style_direction / cta_pi 내러티브에 참조.
        taste_profile: (Phase L, optional) UserTasteProfile snapshot. 대화+IG 누적 취향.
        max_retries: 파싱/검증/API 실패 시 재시도 횟수. default 4 (= 총 5 attempts).
            Rate limit (429) 발생 시 exponential backoff 으로 자동 대기 (15s/30s/60s/120s).

    Returns:
        VerdictV2Result (preview + full_content)

    Raises:
        ValueError: photos 0 장 또는 10 장 초과
        VerdictV2RateLimitedError: 429 rate limit 으로 모든 시도 실패 (UI 친화 메시지 분기)
        VerdictV2Error: Hard Rules 위반 / parse 실패 / 일반 API 오류 (재시도 후)
    """
    if not photos:
        raise ValueError("photos required (>=1, <=10)")
    if len(photos) > 10:
        raise ValueError(f"photos too many ({len(photos)} > 10)")

    trend_data = trend_data or {}

    last_error: Optional[Exception] = None
    last_was_rate_limit = False
    # Rate limit backoff schedule (sec). Anthropic minute-window = 60s, double-safety.
    backoff_schedule = [15, 30, 60, 120]

    for attempt in range(max_retries + 1):
        try:
            raw = _call_sonnet(
                user_profile, photos, trend_data,
                matched_trends=matched_trends,
                taste_profile=taste_profile,
                history_context=history_context,
            )
            clean = _strip_json_fence(raw)
            parsed = json.loads(clean)
            result = VerdictV2Result.model_validate(parsed)
            # WTP 가설 — best_fit 일관성 보장 (HR 검증 이전).
            _sync_best_fit_fields(result)
            _validate_hard_rules(result)
            result.full_content.cta_pi = None
            logger.info(
                "verdict_v2 success: attempt=%d photos=%d best_fit_idx=%s (cta_pi suppressed)",
                attempt + 1, len(photos), result.full_content.best_fit_photo_index,
            )
            return result
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = e
            last_was_rate_limit = False
            logger.warning(
                "verdict_v2 parse/validation failed (attempt %d): %s",
                attempt + 1, e,
            )
            continue
        except VerdictV2Error as e:
            last_error = e
            last_was_rate_limit = False
            logger.warning(
                "verdict_v2 hard rules failed (attempt %d): %s",
                attempt + 1, e,
            )
            continue
        except anthropic.RateLimitError as e:
            # 429 rate limit — exponential backoff 후 재시도. 사용자 노출 X.
            last_error = e
            last_was_rate_limit = True
            if attempt < max_retries:
                wait_s = backoff_schedule[min(attempt, len(backoff_schedule) - 1)]
                logger.warning(
                    "verdict_v2 rate limited (attempt %d) — backoff %ds before retry",
                    attempt + 1, wait_s,
                )
                time.sleep(wait_s)
            else:
                logger.error(
                    "verdict_v2 rate limited (attempt %d) — exhausted retries",
                    attempt + 1,
                )
            continue
        except anthropic.APIStatusError as e:
            # 일반 API status error — 429 외 (502/503 등) 도 짧은 backoff 후 재시도
            last_error = e
            status = getattr(e, "status_code", None)
            last_was_rate_limit = (status == 429)
            if attempt < max_retries:
                wait_s = (
                    backoff_schedule[min(attempt, len(backoff_schedule) - 1)]
                    if last_was_rate_limit else min(5 * (attempt + 1), 30)
                )
                logger.warning(
                    "verdict_v2 API status error %s (attempt %d) — backoff %ds",
                    status, attempt + 1, wait_s,
                )
                time.sleep(wait_s)
            continue
        except anthropic.APIError as e:
            last_error = e
            last_was_rate_limit = False
            if attempt < max_retries:
                wait_s = min(5 * (attempt + 1), 30)
                logger.warning(
                    "verdict_v2 API error (attempt %d) — backoff %ds: %s",
                    attempt + 1, wait_s, e,
                )
                time.sleep(wait_s)
            continue

    if last_was_rate_limit:
        raise VerdictV2RateLimitedError(
            f"verdict_v2 rate limited after {max_retries + 1} attempts"
        )
    raise VerdictV2Error(
        f"verdict_v2 failed after {max_retries + 1} attempts: {last_error}"
    )
