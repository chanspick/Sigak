"""Apify Instagram Profile Scraper wrapper (v2 Priority 1 D2).

Feature flag: `config.ig_enabled`. Off 상태면 즉시 skipped 반환.
실 API 키: `config.apify_api_key`. 미설정 + flag on = failed.
Timeout: `config.ig_fetch_timeout` (초).

Usage:
    status, cache = fetch_ig_profile("@yuni")
    if status == "success":
        # cache: IgFeedCache (full scope)
    elif status == "private":
        # cache: IgFeedCache (public_profile_only scope)
    elif status == "failed":
        # API 오류/타임아웃/부적합 handle
    elif status == "skipped":
        # flag off 또는 handle 빈값

유닛 테스트: `_call_apify_actor` 를 monkey-patch 해서 raw 응답 주입.
실 API 호출 검증은 D3-D4 E2E 에서 수행.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Literal, Optional

import httpx

from config import get_settings
from schemas.user_profile import IgFeedCache, IgFeedProfileBasics


logger = logging.getLogger(__name__)

IgFetchStatus = Literal["success", "failed", "skipped", "private"]

APIFY_ENDPOINT_TMPL = (
    "https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items"
)


# ─────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────

def fetch_ig_profile(ig_handle: Optional[str]) -> tuple[IgFetchStatus, Optional[IgFeedCache]]:
    """Fetch Instagram profile + recent posts via Apify Actor.

    Returns (status, cache). `cache` is None unless status in {success, private}.
    Never raises — all exceptions converted to ("failed", None) with logging.

    Status semantics:
      success — public 계정, 피드 수집 완료
      private — 비공개 계정, profile_basics 만 수집
      skipped — IG_ENABLED=false OR ig_handle 빈값
      failed  — API 오류/타임아웃/APIFY_API_KEY 미설정/응답 파싱 실패
    """
    settings = get_settings()

    # Feature flag 1순위 체크
    if not settings.ig_enabled:
        logger.info("IG scraper skipped: IG_ENABLED=false")
        return ("skipped", None)

    # handle 정규화 + 빈값 체크
    handle = _normalize_handle(ig_handle)
    if not handle:
        logger.info("IG scraper skipped: empty handle")
        return ("skipped", None)

    # API 키 체크
    if not settings.apify_api_key:
        logger.warning(
            "IG_ENABLED=true but APIFY_API_KEY missing — failed (check Railway env)"
        )
        return ("failed", None)

    # Apify 호출
    try:
        raw_items = _call_apify_actor(
            handle=handle,
            api_key=settings.apify_api_key,
            actor_id=settings.apify_actor_id,
            timeout=settings.ig_fetch_timeout,
        )
    except httpx.TimeoutException:
        logger.warning("Apify timeout (>%.1fs) for handle=%s", settings.ig_fetch_timeout, handle)
        return ("failed", None)
    except httpx.HTTPStatusError as e:
        logger.warning("Apify HTTP %d for handle=%s: %s", e.response.status_code, handle, e)
        return ("failed", None)
    except Exception:
        logger.exception("Apify unexpected error for handle=%s", handle)
        return ("failed", None)

    if not raw_items:
        logger.warning("Apify returned 0 items for handle=%s (handle may not exist)", handle)
        return ("failed", None)

    # 첫 item 이 profile. 나머지는 posts (actor 설정에 따라 다름 — defensive parse)
    profile_raw = raw_items[0]

    # 비공개 계정 분기
    if bool(profile_raw.get("private", False)) or bool(profile_raw.get("is_private", False)):
        cache = _build_private_cache(profile_raw)
        return ("private", cache)

    # 공개 계정: 피드 함께 수집
    cache = _build_full_cache(profile_raw, posts_raw=raw_items[1:] if len(raw_items) > 1 else [])
    return ("success", cache)


def is_stale(ig_fetched_at: Optional[datetime]) -> bool:
    """True 이면 2주 경과로 refresh 대상. `ig_fetched_at=None` 도 stale."""
    if ig_fetched_at is None:
        return True
    settings = get_settings()
    age_seconds = (datetime.now(timezone.utc) - ig_fetched_at).total_seconds()
    return age_seconds > (settings.ig_refresh_days * 24 * 3600)


# ─────────────────────────────────────────────
#  Internal — Apify HTTP
# ─────────────────────────────────────────────

def _call_apify_actor(
    handle: str,
    api_key: str,
    actor_id: str,
    timeout: float,
) -> list[dict]:
    """Low-level Apify Actor 호출. 유닛 테스트에서 monkey-patch 대상.

    Actor: apify/instagram-scraper (또는 config.apify_actor_id)
    Payload: usernames, resultsLimit (최근 9~12 포스트)

    Returns: list of dataset items. 첫 item 이 profile metadata, 나머지는 posts.
    Raises: httpx.TimeoutException, httpx.HTTPStatusError, 기타 네트워크 예외.
    """
    url = APIFY_ENDPOINT_TMPL.format(actor_id=actor_id)
    payload = {
        "usernames": [handle],
        "resultsLimit": 9,
        "addParentData": True,
    }
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(
            url,
            json=payload,
            params={"token": api_key},
        )
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            raise ValueError(f"Apify response not a list: {type(data).__name__}")
        return data


# ─────────────────────────────────────────────
#  Internal — Parsing
# ─────────────────────────────────────────────

def _normalize_handle(raw: Optional[str]) -> str:
    """'@yuni' / 'yuni' / '  yuni ' → 'yuni'. None/빈값 → ''."""
    if not raw:
        return ""
    return raw.strip().lstrip("@").lower()


def _build_private_cache(profile_raw: dict) -> IgFeedCache:
    """비공개 계정: profile_basics 만 채우고 나머지는 None."""
    return IgFeedCache(
        scope="public_profile_only",
        profile_basics=_extract_profile_basics(profile_raw),
        current_style_mood=None,
        style_trajectory=None,
        feed_highlights=None,
        raw={"profile": profile_raw},
        fetched_at=datetime.now(timezone.utc),
    )


def _build_full_cache(profile_raw: dict, posts_raw: list[dict]) -> IgFeedCache:
    """공개 계정: profile + posts 로부터 feed_highlights 추출.

    current_style_mood / style_trajectory 는 LLM 기반 추출이므로 D2 에선 None.
    D5+ 에서 Sia 대화 엔진이 feed_highlights + 유저 응답을 종합해 채움.
    """
    highlights = _extract_feed_highlights(posts_raw)
    return IgFeedCache(
        scope="full",
        profile_basics=_extract_profile_basics(profile_raw),
        current_style_mood=None,       # D5+ LLM 추출
        style_trajectory=None,         # D5+ LLM 추출
        feed_highlights=highlights,
        raw={"profile": profile_raw, "posts": posts_raw[:9]},
        fetched_at=datetime.now(timezone.utc),
    )


def _extract_profile_basics(profile_raw: dict) -> IgFeedProfileBasics:
    """Apify Actor 응답 profile 객체 → 정규화된 profile_basics.

    Apify 의 필드 이름은 actor 버전에 따라 다름. Fallback 체인으로 defensive.
    """
    return IgFeedProfileBasics(
        username=str(profile_raw.get("username") or profile_raw.get("userName") or ""),
        profile_picture=profile_raw.get("profilePicUrl") or profile_raw.get("profile_pic_url"),
        bio=profile_raw.get("biography") or profile_raw.get("bio"),
        follower_count=int(profile_raw.get("followersCount") or profile_raw.get("follower_count") or 0),
        following_count=int(profile_raw.get("followsCount") or profile_raw.get("following_count") or 0),
        post_count=int(profile_raw.get("postsCount") or profile_raw.get("media_count") or 0),
        is_private=bool(profile_raw.get("private") or profile_raw.get("is_private") or False),
        is_verified=bool(profile_raw.get("verified") or profile_raw.get("is_verified") or False),
    )


def _extract_feed_highlights(posts_raw: list[dict]) -> list[str]:
    """최근 포스트 캡션에서 짧은 텍스트 하이라이트 추출.

    - 각 캡션 200자 이하로 잘라서 저장
    - 빈 캡션/광고성 반복 텍스트 filter 는 D5+ LLM 단계로 미룸
    """
    highlights: list[str] = []
    for post in posts_raw[:9]:
        caption = post.get("caption") or ""
        if isinstance(caption, str) and caption.strip():
            highlights.append(caption[:200].strip())
    return highlights
