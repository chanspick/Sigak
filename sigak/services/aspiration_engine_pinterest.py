"""Aspiration engine — Pinterest 경로 (Phase J4).

Pinterest 보드 URL 입력 → Apify Pinterest scraper 수집 → 이미지 Vision 분석 →
본인 좌표와 gap 비교.

IG 와 flow 동일하되 다음 차이:
  - 입력: 보드 URL
  - 수집: apify/pinterest-scraper (액터 id config)
  - 대상 = 이미지 큐레이션 (사람 아님) — "유저가 좋아하는 이미지들의 공통 결"
  - profile_basics 없음 (핸들 X). target_display_name 은 보드 제목 사용.

MVP 범위:
  - Apify 스키마 실검증 전 단계 → 현재는 skeleton + pinterest_enabled flag.
  - Vision 분석은 IG Vision analyzer 재사용 (이미지 list 만 들어오면 됨).
  - 상용 착수 전 Apify Pinterest actor 실 응답 shape 로 어댑터 튜닝 필요.
"""
from __future__ import annotations

import hashlib
import logging
import urllib.parse
from datetime import datetime, timezone
from typing import Optional

import httpx

from schemas.aspiration import AspirationAnalysis
from schemas.user_profile import IgLatestPost
from services.aspiration_common import (
    compose_overall_message,
    derive_coordinate_from_analysis,
    generate_analysis_id,
    is_blocked,
    match_trends_for_aspiration_direction,
    materialize_pairs_to_r2,
    select_photo_pairs,
)
from services.aspiration_engine_ig import AspirationRunResult
from services.coordinate_system import VisualCoordinate, neutral_coordinate
from services.ig_feed_analyzer import analyze_ig_feed
from config import get_settings


logger = logging.getLogger(__name__)


APIFY_PINTEREST_ENDPOINT_TMPL = (
    "https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items"
)


# ─────────────────────────────────────────────
#  Main entry
# ─────────────────────────────────────────────

def run_aspiration_pinterest(
    db,
    *,
    user_id: str,
    user_gender: Optional[str],
    user_coordinate: Optional[VisualCoordinate],
    board_url: str,
    user_posts: Optional[list[IgLatestPost]] = None,
) -> AspirationRunResult:
    """Pinterest 보드 URL → AspirationAnalysis.

    Args:
      db: blocklist 체크용
      user_id / user_gender / user_coordinate: 본인 맥락
      board_url: https://www.pinterest.com/{user}/{board}/ 형식 기대
      user_posts: 본인 IG posts (vault.ig_feed_cache.latest_posts).
                  photo_pairs 좌측 채움. None/[] 면 페어 없음.
    """
    normalized_url = _normalize_board_url(board_url)
    if not normalized_url:
        return AspirationRunResult("failed_skipped", error_detail="invalid board url")

    board_id = _board_hash(normalized_url)

    # 1. 블록리스트 — target_identifier 로 hash 사용 (URL 원문 직접 저장 대신)
    if is_blocked(db, target_type="pinterest", target_identifier=board_id):
        return AspirationRunResult("failed_blocked")

    settings = get_settings()
    if not settings.pinterest_enabled:
        # Pinterest 추구미는 MVP 기본 off. 별도 Apify 계약 후 on.
        return AspirationRunResult("failed_skipped", error_detail="pinterest_enabled=false")
    if not settings.apify_api_key:
        return AspirationRunResult("failed_scrape", error_detail="apify_api_key missing")

    # 2. Apify 수집 (Pinterest actor)
    try:
        image_urls = _call_pinterest_actor(
            board_url=normalized_url,
            api_key=settings.apify_api_key,
            actor_id=settings.apify_pinterest_actor_id,
            timeout=settings.ig_fetch_timeout,
        )
    except Exception as e:
        logger.exception("Apify Pinterest call failed: url=%s", normalized_url)
        return AspirationRunResult("failed_scrape", error_detail=str(e))

    if not image_urls:
        return AspirationRunResult("failed_scrape", error_detail="board returned 0 images")

    # 3. 이미지 list → IgLatestPost 로 wrap (Vision analyzer 재사용)
    synthetic_posts = _wrap_images_as_posts(image_urls[:10])

    # 4. Vision 분석 (Sonnet)
    target_analysis = analyze_ig_feed(
        posts=synthetic_posts,
        biography=None,      # Pinterest 는 bio 개념 없음
    )
    if target_analysis is None:
        return AspirationRunResult(
            "failed_scrape",
            error_detail="Pinterest vision analysis failed",
        )

    # 5. 좌표 + gap
    target_coord = derive_coordinate_from_analysis(target_analysis)
    user_coord = user_coordinate or neutral_coordinate()
    gap = user_coord.gap_vector(target_coord)

    # 6. Photo pairs (vault 본인 IG 사진 + Pinterest 타깃 1:1 인덱스)
    user_posts_effective: list[IgLatestPost] = list(user_posts or [])
    pairs = select_photo_pairs(
        user_posts=user_posts_effective,
        target_posts=synthetic_posts,
        gap=gap,
        max_pairs=5,
    )

    # 7. Knowledge Base 매칭
    matched_trend_ids = match_trends_for_aspiration_direction(
        gap=gap,
        user_coord=user_coord,
        gender=user_gender or "female",
    )

    # 8. Sia 종합
    overall = compose_overall_message(
        target_display_name=f"Pinterest 보드",
        gap=gap,
        matched_trend_count=len(matched_trend_ids),
    )

    # 9. R2 materialization — Pinterest 이미지 영구 저장 (analysis_id 선행 발급)
    analysis_id = generate_analysis_id()
    pairs_persisted, r2_target_dir = materialize_pairs_to_r2(
        pairs, user_id=user_id, analysis_id=analysis_id,
    )

    # 10. 조립
    analysis = AspirationAnalysis(
        analysis_id=analysis_id,
        user_id=user_id,
        target_type="pinterest",
        target_identifier=board_id,
        target_display_name="Pinterest 보드",
        created_at=datetime.now(timezone.utc),
        user_coordinate=user_coord,
        target_coordinate=target_coord,
        gap_vector=gap,
        gap_narrative=gap.narrative(),
        photo_pairs=pairs_persisted,
        sia_overall_message=overall,
        matched_trend_ids=matched_trend_ids,
        target_analysis_snapshot=target_analysis.model_dump(mode="json"),
        images_captured_count=len(image_urls),
        r2_target_dir=r2_target_dir,
    )
    return AspirationRunResult("completed", analysis=analysis)


# ─────────────────────────────────────────────
#  URL normalization + board hash
# ─────────────────────────────────────────────

def _normalize_board_url(raw: str) -> str:
    """Pinterest 보드 URL 정규화.

    허용 shape:
      https://www.pinterest.com/{user}/{board}/
      https://pinterest.com/{user}/{board}/
      https://pin.it/...  (shortlink — MVP 거부)
    """
    if not raw:
        return ""
    parsed = urllib.parse.urlparse(raw.strip())
    host = (parsed.hostname or "").lower()
    if host not in ("www.pinterest.com", "pinterest.com"):
        return ""
    path = parsed.path.strip("/")
    parts = path.split("/")
    if len(parts) < 2:
        return ""
    return f"https://www.pinterest.com/{parts[0]}/{parts[1]}/"


def _board_hash(normalized_url: str) -> str:
    """보드 URL → blocklist / DB 용 short hash (충돌 무시할 정도 충분)."""
    return hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()[:24]


# ─────────────────────────────────────────────
#  Apify Pinterest call (actor 응답 shape 어댑터)
# ─────────────────────────────────────────────

def _call_pinterest_actor(
    *,
    board_url: str,
    api_key: str,
    actor_id: str,
    timeout: float,
) -> list[str]:
    """apify~pinterest-scraper 실행 → 이미지 URL list.

    MVP 가정 payload (actor 문서 확인 전, placeholder):
      {"startUrls": [{"url": board_url}], "maxPins": 10}
    응답 각 item 의 "imageUrl" or "image.url" 필드 추출.

    실 actor 사용 전 스키마 검증 + 어댑터 튜닝 필요. 예외는 caller 에서 흡수.
    """
    url = APIFY_PINTEREST_ENDPOINT_TMPL.format(actor_id=actor_id)
    payload = {
        "startUrls": [{"url": board_url}],
        "maxPins": 10,
    }
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, json=payload, params={"token": api_key})
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            raise ValueError(f"unexpected Pinterest actor response type: {type(data).__name__}")

    urls: list[str] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        candidate = (
            item.get("imageUrl")
            or (item.get("image") or {}).get("url")
            or item.get("image_large_url")
            or item.get("url")
        )
        if isinstance(candidate, str) and candidate.startswith("http"):
            urls.append(candidate)
    return urls


def _wrap_images_as_posts(image_urls: list[str]) -> list[IgLatestPost]:
    """Pinterest 이미지 url list → IgLatestPost 호환 shape.

    Vision analyzer 가 IgLatestPost.display_url 만 사용하므로, caption/comments
    는 빈 값 허용.
    """
    return [
        IgLatestPost(caption="", display_url=url)
        for url in image_urls
    ]
