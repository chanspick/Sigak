"""IG Feed Vision Analyzer — Sonnet 4.6 멀티모달 피드 분석 (D6 Phase A, Task 0).

역할:
- Apify 가 수집한 latest_posts 의 display_url 10장 + bio + 댓글 집계를 입력
- Sonnet 4.6 Vision 호출로 structured JSON 산출 (IgFeedAnalysis)
- Sia Haiku 오프닝 데이터 리스트 (톤/채도/환경/포즈) 의 ground-truth 제공

설계:
- sync. verdict_v2 패턴 그대로 복사 (별도 singleton client, 재시도 loop,
  fence strip, json.loads + Pydantic 검증).
- 호출은 반드시 ig_scraper.fetch_ig_profile 내부 동일 트랜잭션.
  Instagram CDN URL TTL 이 24-48h 이므로 저장된 cache 에서 꺼내 나중 호출 금지.
- 실패 (API 오류 / JSON 파싱 실패 / Pydantic 검증 실패) 시 None 반환.
  caller (ig_scraper) 는 analysis=None 으로 cache 저장 → Sia 는 폴백.

비용 (2026-04 기준):
- Sonnet 4.6: input $3/1M, output $15/1M
- 이미지 10장 @ ~1k tokens + 댓글/bio ~500 = ~10.5k input + 500 output
- per call ≈ $0.035

Hard Rules (prompt 내):
- 숫자는 이미지 실측 기반 (환각 금지)
- observed_adjectives 는 제공된 댓글 샘플 내 어휘만 사용
- JSON 외 텍스트 금지 (fence OK)
"""
from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import anthropic
import httpx
from pydantic import ValidationError

from config import get_settings
from schemas.user_profile import IgFeedAnalysis, IgLatestPost


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Anthropic Sonnet client (independent singleton)
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
#  Public API
# ─────────────────────────────────────────────

class IgFeedAnalyzerError(Exception):
    """Vision 분석 복구 불가 오류. caller 는 None 처리로 degrade."""


def analyze_ig_feed(
    posts: list[IgLatestPost],
    biography: Optional[str],
    *,
    max_retries: int = 1,
) -> Optional[IgFeedAnalysis]:
    """피드 이미지 + 메타 → Sonnet Vision 분석 → IgFeedAnalysis.

    Args:
        posts: latest_posts. display_url 누락 항목은 자동 제외.
        biography: IG bio (빈 문자열 / None 허용).
        max_retries: 파싱/검증 실패 시 재시도. default 1.

    Returns:
        IgFeedAnalysis on success, None on failure (any exception path).
        caller 는 cache.analysis=None 으로 저장하고 Sia 폴백에 맡긴다.
    """
    images = [p for p in posts if p.display_url]
    if not images:
        logger.info("analyze_ig_feed skipped: no images with display_url")
        return None

    comment_agg = _aggregate_comments(posts)
    bio = (biography or "").strip()

    prompt = _build_prompt(
        bio=bio,
        comment_agg=comment_agg,
        n_images=len(images),
    )

    last_error: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            raw = _call_sonnet_vision(prompt=prompt, images=images)
            clean = _strip_json_fence(raw)
            parsed = json.loads(clean)
            analysis = IgFeedAnalysis(
                **parsed,
                analyzed_at=datetime.now(timezone.utc),
            )
            return analysis
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = e
            logger.warning(
                "ig_feed_analyzer parse/validate failed (attempt %d): %s",
                attempt + 1, e,
            )
            continue
        except anthropic.APIError as e:
            last_error = e
            logger.warning(
                "ig_feed_analyzer Sonnet API error (attempt %d): %s",
                attempt + 1, e,
            )
            continue
        except Exception as e:
            last_error = e
            logger.exception(
                "ig_feed_analyzer unexpected error (attempt %d)", attempt + 1,
            )
            continue

    logger.error("ig_feed_analyzer all retries failed: %s", last_error)
    return None


# ─────────────────────────────────────────────
#  Comment aggregation (PII already scrubbed upstream)
# ─────────────────────────────────────────────

def _aggregate_comments(posts: list[IgLatestPost]) -> dict:
    """latest_posts 의 댓글 본문을 평탄화.

    posts[].latest_comments 는 이미 _scrub_post_pii 통과 상태 (text only).
    prompt 길이 제한 위해 최근 30개 본문만 샘플링.
    """
    all_texts: list[str] = []
    for p in posts:
        all_texts.extend(p.latest_comments or [])
    return {
        "total_count": len(all_texts),
        "sample_texts": all_texts[:30],
    }


# ─────────────────────────────────────────────
#  Sonnet Vision call
# ─────────────────────────────────────────────

def _call_sonnet_vision(prompt: str, images: list[IgLatestPost]) -> str:
    """Sonnet 4.6 멀티모달 호출.

    Instagram CDN 은 robots.txt 로 Anthropic server-side fetcher 를 차단한다.
    → URL direct 대신 클라이언트에서 이미지를 다운로드 → base64 로 인코딩하여 전달.
    다운로드 실패한 이미지는 건너뛰고, 최소 1 장 이상 성공해야 Sonnet 호출.
    """
    settings = get_settings()
    client = _get_client()

    content_blocks: list[dict] = []
    for p in images[:10]:  # Sonnet per-call image cap = 20, we cap 10
        if not p.display_url:
            continue
        encoded = _download_image_as_base64(p.display_url)
        if not encoded:
            continue
        b64, media_type = encoded
        content_blocks.append({
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": b64},
        })

    n_images = sum(1 for b in content_blocks if b.get("type") == "image")
    if n_images == 0:
        raise IgFeedAnalyzerError("all image downloads failed (CDN TTL 만료 or 네트워크)")

    content_blocks.append({"type": "text", "text": prompt})

    response = client.messages.create(
        model=settings.anthropic_model_sonnet,
        max_tokens=1000,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content_blocks}],
    )
    if not response.content:
        raise IgFeedAnalyzerError("empty Sonnet response")
    text_blocks = [b.text for b in response.content if b.type == "text"]
    if not text_blocks:
        raise IgFeedAnalyzerError("no text block in Sonnet response")
    return "\n".join(text_blocks).strip()


# ─────────────────────────────────────────────
#  Image download (Instagram CDN → base64)
# ─────────────────────────────────────────────

_ALLOWED_MEDIA_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_MAX_IMAGE_BYTES = 5 * 1024 * 1024  # Anthropic vision per-image 5MB 한도


def _download_image_as_base64(
    url: str,
    *,
    timeout: float = 8.0,
) -> Optional[tuple[str, str]]:
    """Instagram CDN URL → (base64_str, media_type).

    실패 케이스:
      - TTL 만료 (403/410)
      - 네트워크 타임아웃
      - 5MB 초과
      - 지원 안 되는 media type (image/* 외)
    실패 시 None 반환. caller 는 해당 이미지 skip.
    """
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            if len(resp.content) > _MAX_IMAGE_BYTES:
                logger.warning(
                    "image too large (%d bytes > 5MB): %s",
                    len(resp.content), url[:80],
                )
                return None
            content_type = (
                resp.headers.get("content-type", "image/jpeg")
                .split(";")[0]
                .strip()
                .lower()
            )
            if content_type not in _ALLOWED_MEDIA_TYPES:
                # Instagram 은 content-type 을 종종 octet-stream 으로 내림 —
                # URL 확장자로 재추론
                lower = url.lower().split("?")[0]
                if lower.endswith(".png"):
                    content_type = "image/png"
                elif lower.endswith(".webp"):
                    content_type = "image/webp"
                elif lower.endswith(".gif"):
                    content_type = "image/gif"
                else:
                    content_type = "image/jpeg"
            b64 = base64.b64encode(resp.content).decode("ascii")
            return b64, content_type
    except httpx.HTTPStatusError as e:
        logger.warning(
            "image download HTTP %d for %s: %s",
            e.response.status_code, url[:80], e,
        )
    except httpx.TimeoutException:
        logger.warning("image download timeout: %s", url[:80])
    except Exception:
        logger.exception("image download unexpected error: %s", url[:80])
    return None


def _strip_json_fence(text: str) -> str:
    """```json ``` 래퍼 있으면 제거. verdict_v2._strip_json_fence 동일."""
    t = text.strip()
    if t.startswith("```"):
        lines = t.split("\n")
        if len(lines) > 1:
            lines = lines[1:]
        while lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t


# ─────────────────────────────────────────────
#  Prompts
# ─────────────────────────────────────────────

_SYSTEM_PROMPT = """당신은 SIGAK 의 피드 분석 엔진입니다.
유저의 Instagram 피드 이미지를 분석하여 structured JSON 을 반환하십시오.

[역할]
- 입력: 최근 포스트 이미지 N 장 (순서대로 최신 → 오래된 순) + bio + 댓글 샘플
- 출력: 단일 JSON 객체 (아래 스키마 엄격 준수)

[Hard Rules]
1. 숫자 (tone_percentage, style_consistency) 는 반드시 이미지 실측 근거로 뽑습니다.
   환각 금지. 확신 못 하면 중간값 (50, 0.5) 선택.
2. observed_adjectives 는 제공된 댓글 sample_texts 내에서만 추출.
   없으면 빈 배열.
3. 정중체 서술 — mood_signal 은 "~입니다" / "~습니다" 로 끝나는 1 문장.
4. three_month_shift 는 포스트 순서 (최근 → 오래된) 에서 시각적 변화가
   읽히면 채우고, 일관되면 null.
5. JSON 외 텍스트 출력 금지. ```json fence 허용.

[출력 스키마]
{
  "tone_category": "쿨뮤트" | "웜뮤트" | "쿨비비드" | "웜비비드" | "중성",
  "tone_percentage": 0-100 정수,
  "saturation_trend": "감소" | "안정" | "증가",
  "environment": "<짧은 문구, 예: '실내 + 자연광', '외부 야외', '혼합'>",
  "pose_frequency": "<짧은 문구, 예: '측면 > 정면', '정면 > 측면'>",
  "observed_adjectives": ["<최대 5개, 댓글에서 실제 등장한 형용사>"],
  "style_consistency": 0.0-1.0 실수,
  "mood_signal": "<1 문장 정중체>",
  "three_month_shift": "<변화 설명 or null>"
}
"""


def _build_prompt(bio: str, comment_agg: dict, n_images: int) -> str:
    """유저 메시지 프롬프트 본문. 이미지는 content block 으로 별도 전달."""
    bio_block = bio if bio else "(bio 없음)"
    samples = comment_agg.get("sample_texts") or []
    samples_block = (
        "\n".join(f"- {t}" for t in samples) if samples else "(댓글 없음)"
    )
    return (
        f"[이미지 수] {n_images} 장 (첨부 content block 참조)\n\n"
        f"[bio]\n{bio_block}\n\n"
        f"[댓글 집계 — total={comment_agg.get('total_count', 0)}, sample 최대 30]\n"
        f"{samples_block}\n\n"
        "system prompt 의 Hard Rules + 출력 JSON 스키마를 엄격 준수하십시오.\n"
        "JSON 단일 객체만 출력."
    )
