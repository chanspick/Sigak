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
from schemas.user_profile import IgFeedCache, IgFeedProfileBasics, IgLatestPost


logger = logging.getLogger(__name__)

IgFetchStatus = Literal[
    "success",          # 공개 계정 + Vision 완료
    "failed",           # Apify 오류 / 타임아웃 / 빈 응답
    "skipped",          # ig_enabled off 또는 handle 빈값
    "private",          # 비공개 계정 (profile_basics 만)
    "pending",          # essentials 직후, BackgroundTask 미실행/대기
    "pending_vision",   # Apify 성공 직후 preview flush, Vision 진행 중
]

APIFY_ENDPOINT_TMPL = (
    "https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items"
)


# ─────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────

def fetch_ig_profile(
    ig_handle: Optional[str],
    *,
    results_limit: int = 10,
) -> tuple[IgFetchStatus, Optional[IgFeedCache]]:
    """Fetch Instagram profile + recent posts via Apify Actor.

    Args:
      ig_handle: IG 핸들 ("@yuni" / "yuni" / None 허용)
      results_limit: Apify 수집 포스트 수. 기본 10 (Sia 오프닝 고정 샘플).
        PI 리포트 전용은 fetch_ig_profile_for_pi() 사용 → 30.

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
            results_limit=results_limit,
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

    # addParentData=True 사용 시 모든 items 가 포스트이고, 각 포스트의 top-level 에
    # 프로필 메타(username, followersCount, postsCount, private 등) 가 임베딩됨.
    # profile_raw 는 items[0] 의 top-level 에서 꺼내 쓰되, posts_raw 는 items 전체.
    profile_raw = raw_items[0]

    # 비공개 계정 분기 — 이 경우 posts 수집 불가, profile meta 만 남김.
    if bool(profile_raw.get("private", False)) or bool(profile_raw.get("is_private", False)):
        cache = _build_private_cache(profile_raw)
        return ("private", cache)

    # 공개 계정: items 전체를 posts 로 사용 (첫 포스트 손실 금지).
    # 본 흐름은 단발 fetch_ig_profile 호출 — vision_raw 보존 X (호출처 user_id 모름).
    # 본인 IG vision_raw 보존은 분리 흐름 (fetch_ig_raw → attach_vision_analysis)
    # 의 onboarding 라우트가 처리.
    cache, _vision_raw = _build_full_cache(
        profile_raw,
        posts_raw=raw_items,
        posts_limit=results_limit,
    )
    return ("success", cache)


def fetch_ig_profile_for_pi(ig_handle: Optional[str]) -> tuple[IgFetchStatus, Optional[IgFeedCache]]:
    """PI 리포트 전용 IG 수집 — Apify limit=30.

    Phase I (CLAUDE.md §5.1) 에서 결정: Sia 대화용 10장과 별도로
    PI 선별 풀을 30장까지 확장. 비용 +$0.06/유저, 가격 ₩5,000 마진 내.
    """
    return fetch_ig_profile(ig_handle, results_limit=30)


# ─────────────────────────────────────────────
#  분리 저장 (STEP IG-Wiring) — Apify 수집 선 flush + Vision 후 flush
#
#  온보딩 UX: essentials 직후 BackgroundTask 가
#    (1) fetch_ig_raw → preview cache (status=pending_vision) 먼저 DB flush
#        → 프론트 폴링에서 preview_urls 보이기 시작
#    (2) attach_vision_analysis → analysis 첨부 → 최종 flush (status=success)
# ─────────────────────────────────────────────

def fetch_ig_raw(
    ig_handle: Optional[str],
    *,
    results_limit: int = 10,
) -> tuple[IgFetchStatus, Optional[IgFeedCache]]:
    """Apify 수집 only — Vision 미실행. 분리 저장 워크플로용.

    `fetch_ig_profile` 와 동일한 status 분기 (success / private / skipped / failed)
    이지만 success 케이스에서 `analysis=None` 인 preview cache 반환.

    이후 caller 가 `attach_vision_analysis(cache)` 로 Vision 을 덧붙여 최종 저장.
    """
    settings = get_settings()

    if not settings.ig_enabled:
        logger.info("fetch_ig_raw skipped: IG_ENABLED=false")
        return ("skipped", None)

    handle = _normalize_handle(ig_handle)
    if not handle:
        logger.info("fetch_ig_raw skipped: empty handle")
        return ("skipped", None)

    if not settings.apify_api_key:
        logger.warning(
            "fetch_ig_raw: APIFY_API_KEY missing — failed (check Railway env)"
        )
        return ("failed", None)

    try:
        raw_items = _call_apify_actor(
            handle=handle,
            api_key=settings.apify_api_key,
            actor_id=settings.apify_actor_id,
            timeout=settings.ig_fetch_timeout,
            results_limit=results_limit,
        )
    except httpx.TimeoutException:
        logger.warning(
            "fetch_ig_raw timeout (>%.1fs) for handle=%s",
            settings.ig_fetch_timeout, handle,
        )
        return ("failed", None)
    except httpx.HTTPStatusError as e:
        logger.warning(
            "fetch_ig_raw HTTP %d for handle=%s: %s",
            e.response.status_code, handle, e,
        )
        return ("failed", None)
    except Exception:
        logger.exception("fetch_ig_raw unexpected error for handle=%s", handle)
        return ("failed", None)

    if not raw_items:
        logger.warning(
            "fetch_ig_raw returned 0 items for handle=%s (handle may not exist)",
            handle,
        )
        return ("failed", None)

    profile_raw = raw_items[0]
    if bool(profile_raw.get("private", False)) or bool(profile_raw.get("is_private", False)):
        cache = _build_private_cache(profile_raw)
        return ("private", cache)

    # 공개 계정 — preview cache (Vision 미실행)
    cache = _build_preview_cache(
        profile_raw,
        posts_raw=raw_items,
        posts_limit=results_limit,
    )
    return ("success", cache)


def _build_preview_cache(
    profile_raw: dict,
    posts_raw: list[dict],
    *,
    posts_limit: int = 10,
) -> IgFeedCache:
    """공개 계정 preview cache — profile + posts 만 정제. analysis=None.

    `_build_full_cache` 에서 Vision 호출부를 분리한 버전. 동일 정제/scrub
    경로 사용. 이후 `attach_vision_analysis` 로 analysis 첨부 가능.
    """
    profile_basics = _extract_profile_basics(profile_raw)
    scrubbed_posts = [_scrub_post_pii(p) for p in posts_raw[:posts_limit]]
    highlights = _extract_feed_highlights(scrubbed_posts, limit=posts_limit)
    latest_posts = _extract_latest_posts(scrubbed_posts, limit=posts_limit)

    return IgFeedCache(
        scope="full",
        profile_basics=profile_basics,
        current_style_mood=None,
        style_trajectory=None,
        feed_highlights=highlights,
        latest_posts=latest_posts,
        analysis=None,                     # ← preview 단계에선 Vision 미수행
        last_analyzed_post_count=None,
        raw={"profile": profile_raw, "posts": scrubbed_posts},
        fetched_at=datetime.now(timezone.utc),
    )


def attach_vision_analysis(cache: IgFeedCache) -> tuple[IgFeedCache, Optional[str]]:
    """Preview cache 에 Sonnet Vision 분석을 덧붙인 (new_cache, vision_raw_text) 반환.

    v1.5 변경 (raw 보존):
      - 시그니처 IgFeedCache → tuple[IgFeedCache, Optional[str]]
      - 두 번째 반환값 = Sonnet response raw text. caller (onboarding 라우트)
        가 R2 분리 저장하고 cache.r2_vision_raw_key 채움.
      - LLM 격리 — vision_raw 는 prompt 에 절대 들어가지 말 것.

    - scope == "full" + latest_posts 유효한 경우에만 Vision 호출
    - Vision 실패 / None 시 원본 cache + None 반환 (degrade)
    - display_url TTL (24-48h) 이슈: preview flush 직후 호출 전제 — 지연 시 이미지
      다운로드 실패할 수 있음
    """
    if cache.scope != "full":
        return cache, None
    if not cache.latest_posts:
        return cache, None

    try:
        from services.ig_feed_analyzer import analyze_ig_feed  # lazy
        analysis, vision_raw = analyze_ig_feed(
            posts=cache.latest_posts,
            biography=cache.profile_basics.bio,
        )
    except Exception:
        logger.exception("attach_vision_analysis failed")
        return cache, None

    if analysis is None:
        return cache, None

    new_cache = cache.model_copy(update={
        "analysis": analysis,
        "last_analyzed_post_count": cache.profile_basics.post_count,
    })
    return new_cache, vision_raw


def is_stale(ig_fetched_at: Optional[datetime]) -> bool:
    """True 이면 2주 경과로 refresh 대상. `ig_fetched_at=None` 도 stale."""
    if ig_fetched_at is None:
        return True
    settings = get_settings()
    age_seconds = (datetime.now(timezone.utc) - ig_fetched_at).total_seconds()
    return age_seconds > (settings.ig_refresh_days * 24 * 3600)


# ─────────────────────────────────────────────
#  STEP 2 — IG 스냅샷 R2 영구 저장
# ─────────────────────────────────────────────
#  Apify 수집 결과 (display_url = IG CDN, TTL 24-48h) 를 R2 로 복사 후
#  latest_posts 의 display_url 을 R2 public URL 로 교체. 이후 cache 재열람 시
#  CDN 만료 무관. aspiration / history 등 하위 파이프라인 자동 정합.
# ─────────────────────────────────────────────

def materialize_snapshot_to_r2(
    cache: "IgFeedCache",
    *,
    user_id: str,
    snapshot_ts: Optional[str] = None,
) -> "IgFeedCache":
    """IG 피드 스냅샷을 R2 영구 저장 + cache 업데이트.

    Args:
      cache: fetch_ig_profile / fetch_ig_raw / attach_vision_analysis 결과.
        scope != 'full' 또는 latest_posts 없으면 원본 그대로 반환.
      user_id: R2 key prefix 소유자.
      snapshot_ts: R2 디렉토리명 (None 이면 cache.fetched_at 기반 YYYYMMDDTHHMMSSZ).

    Returns:
      새 IgFeedCache 인스턴스. latest_posts 의 display_url 이 R2 URL 로 교체됨
      (업로드 실패한 사진은 CDN URL 유지). r2_snapshot_dir 필드 채워짐.
    """
    if cache.scope != "full" or not cache.latest_posts:
        return cache

    ts = snapshot_ts or cache.fetched_at.strftime("%Y%m%dT%H%M%SZ")

    updated_posts, r2_dir = _materialize_latest_posts_to_r2(
        list(cache.latest_posts), user_id=user_id, snapshot_ts=ts,
    )
    return cache.model_copy(update={
        "latest_posts": updated_posts,
        "r2_snapshot_dir": r2_dir,
    })


def _materialize_latest_posts_to_r2(
    posts: list[IgLatestPost],
    *,
    user_id: str,
    snapshot_ts: str,
) -> tuple[list[IgLatestPost], Optional[str]]:
    """CDN URL → R2 업로드 + display_url 교체. 실패 개별은 CDN 유지.

    반환 tuple:
      - updated posts (순서 유지)
      - r2_dir (최소 1장 성공 시 dir prefix, 전체 실패 시 None)
    """
    if not posts:
        return posts, None

    import httpx
    from services import r2_client

    r2_dir = r2_client.ig_snapshot_dir(user_id, snapshot_ts)

    updated: list[IgLatestPost] = []
    any_success = False
    with httpx.Client(timeout=8.0, follow_redirects=True) as client:
        for idx, p in enumerate(posts):
            if not p.display_url:
                updated.append(p)
                continue
            new_url = _upload_snapshot_photo_to_r2(
                client, p.display_url,
                user_id=user_id, snapshot_ts=snapshot_ts, index=idx,
            )
            if new_url:
                updated.append(p.model_copy(update={"display_url": new_url}))
                any_success = True
            else:
                updated.append(p)

    return updated, (r2_dir if any_success else None)


def _upload_snapshot_photo_to_r2(
    http_client,
    src_url: str,
    *,
    user_id: str,
    snapshot_ts: str,
    index: int,
) -> Optional[str]:
    """IG CDN 이미지 1장 → R2 put → public URL.

    데이터 기업 원칙 (raw 손실 0):
      - R2 put 실패 시 services.r2_persistence dead-letter 로 raw bytes 보존.
      - 이 함수가 None 반환 = R2 에 아직 없음 (dead-letter 또는 bytes fetch 실패).
        호출처는 그 사진 1장만 CDN URL 유지 (24-48h 후 만료 가능) — 단,
        raw bytes 자체는 dead-letter 에 보존되어 운영자/cron retry 가능.

      bytes fetch 실패 (IG CDN 4xx/5xx/timeout) 는 영구 손실 — IG 측 이슈로
      재현 불가. 이는 정책 한계.
    """
    if not src_url:
        return None
    from services import r2_client, r2_persistence

    key = r2_client.ig_snapshot_photo_key(user_id, snapshot_ts, index)
    try:
        resp = http_client.get(src_url)
        resp.raise_for_status()
    except Exception:
        # IG CDN fetch 실패 — bytes 자체를 못 받았으므로 dead-letter 도 불가.
        # 이 케이스는 정책 한계 (raw 가 외부에서 안 오는 것).
        logger.exception(
            "[ig_snapshot] CDN fetch failed (raw 미수령): user=%s key=%s",
            user_id, key,
        )
        return None

    content_type = (
        resp.headers.get("content-type", "image/jpeg")
        .split(";")[0]
        .strip()
        .lower()
    )
    if not content_type.startswith("image/"):
        content_type = "image/jpeg"

    try:
        _, durable = r2_persistence.put_bytes_durable_isolated(
            user_id=user_id,
            purpose="ig_snapshot",
            r2_key=key,
            data=resp.content,
            content_type=content_type,
            src_url=src_url,
        )
        if not durable:
            # dead-letter 에는 들어갔지만 R2 엔 아직 없음 — caller 는 이 사진의
            # display_url 을 R2 URL 로 못 바꿈. CDN URL 유지가 최선.
            return None
    except Exception:
        logger.exception("IG snapshot R2 put failed: key=%s", key)
        return None

    return r2_client.public_url(key) or f"r2://{key}"


def is_analysis_stale(
    cache: Optional[IgFeedCache],
    current_post_count: int,
    *,
    delta_threshold: int = 3,
) -> bool:
    """Vision 재호출 필요 여부 — refresh 정책 B (delta 기반).

    True cases:
      - cache is None (최초 수집)
      - cache.analysis is None (이전 호출 실패/스킵)
      - cache.last_analyzed_post_count is None (레거시 cache)
      - |current_post_count - last_analyzed_post_count| >= delta_threshold

    False: 피드 변동 미미 → Vision 스킵, 기존 analysis 재사용.

    14일 is_stale 은 Apify 재호출 트리거. Apify 후 post_count 확인하고
    이 함수로 Vision 재호출 여부 최종 판정한다.
    """
    if cache is None:
        return True
    if cache.analysis is None:
        return True
    if cache.last_analyzed_post_count is None:
        return True
    return abs(current_post_count - cache.last_analyzed_post_count) >= delta_threshold


# ─────────────────────────────────────────────
#  Internal — Apify HTTP
# ─────────────────────────────────────────────

def _call_apify_actor(
    handle: str,
    api_key: str,
    actor_id: str,
    timeout: float,
    *,
    results_limit: int = 10,
) -> list[dict]:
    """Low-level Apify Actor 호출. 유닛 테스트에서 monkey-patch 대상.

    Actor: apify/instagram-scraper (또는 config.apify_actor_id)
    Payload: directUrls (profile URL) + resultsType="posts" + addParentData.
    `usernames` 필드는 현 actor 스키마에 없음 — 무시됨. 반드시 directUrls.

    results_limit: Apify 수집 포스트 수. Sia 10 / PI 30.

    Returns: list of dataset items. addParentData=True 이면 모든 item 이
             포스트이고 top-level 에 프로필 메타가 임베딩된 상태.
    Raises: httpx.TimeoutException, httpx.HTTPStatusError, 기타 네트워크 예외.
    """
    url = APIFY_ENDPOINT_TMPL.format(actor_id=actor_id)
    payload = {
        "directUrls": [f"https://www.instagram.com/{handle}/"],
        "resultsType": "posts",
        "resultsLimit": int(results_limit),
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


def _build_full_cache(
    profile_raw: dict,
    posts_raw: list[dict],
    *,
    posts_limit: int = 10,
) -> tuple[IgFeedCache, Optional[str]]:
    """공개 계정: profile + posts 로부터 cache + Vision raw 반환.

    v1.5 변경 (raw 보존):
      - 시그니처 IgFeedCache → tuple[IgFeedCache, Optional[str]]
      - 두 번째 반환값 = Sonnet Vision raw text. caller 가 R2 저장 결정
        (본인 IG = ig_snapshots/{ts}/, 추구미 IG = aspiration_targets/{analysis_id}/).

    current_style_mood (DEPRECATED D6): 이제 analysis.observed_adjectives 로 대체.
    style_trajectory: Phase B 시계열 예약, 현재 None 유지.
    analysis: Sonnet Vision 호출. 실패 시 None 으로 degrade, cache 자체는 저장.

    Privacy:
      - latest_posts 의 comments 는 본문만 보존. 댓글 작성자(타인) username /
        profile pic / user id 는 전부 제거.
      - raw 에서도 동일하게 scrub — 제3자 개인정보 DB 영구저장 방지.
      - vision_raw 는 LLM 격리 — DB / prompt 에 절대 노출 X. R2 만.

    Vision 호출 타이밍 (CRITICAL):
      - display_url 은 Instagram CDN URL 로 TTL 24-48h.
      - 이 함수 내 즉시 호출 필수. 저장된 cache 에서 꺼내 나중 호출 금지.
    """
    profile_basics = _extract_profile_basics(profile_raw)
    scrubbed_posts = [_scrub_post_pii(p) for p in posts_raw[:posts_limit]]
    highlights = _extract_feed_highlights(scrubbed_posts, limit=posts_limit)
    latest_posts = _extract_latest_posts(scrubbed_posts, limit=posts_limit)

    # Sonnet Vision — 동일 트랜잭션. 실패는 삼키고 analysis=None 으로 degrade.
    analysis, vision_raw = _run_vision_analysis(
        posts=latest_posts,
        biography=profile_basics.bio,
    )

    cache = IgFeedCache(
        scope="full",
        profile_basics=profile_basics,
        current_style_mood=None,           # DEPRECATED (D6)
        style_trajectory=None,             # Phase B 예약
        feed_highlights=highlights,
        latest_posts=latest_posts,
        analysis=analysis,
        last_analyzed_post_count=(
            profile_basics.post_count if analysis is not None else None
        ),
        raw={"profile": profile_raw, "posts": scrubbed_posts},
        fetched_at=datetime.now(timezone.utc),
    )
    return cache, vision_raw


def _run_vision_analysis(
    posts: list[IgLatestPost],
    biography: Optional[str],
) -> tuple[Optional[IgFeedAnalysis], Optional[str]]:
    """Sonnet Vision 호출 래퍼. (analysis, raw_text) 반환. 임포트 순환 회피 위해 지연 임포트.

    v1.5 변경: 시그니처 (analysis,) → (analysis, raw_text).
    실패는 전부 흡수. caller 는 (None, None) 으로 degrade.
    """
    try:
        from services.ig_feed_analyzer import analyze_ig_feed  # lazy
        return analyze_ig_feed(posts=posts, biography=biography)
    except Exception:
        logger.exception("Vision analysis wrapper failed — degrading to (None, None)")
        return None, None


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


def _extract_feed_highlights(posts_raw: list[dict], *, limit: int = 10) -> list[str]:
    """최근 포스트 캡션에서 짧은 텍스트 하이라이트 추출.

    - 각 캡션 200자 이하로 잘라서 저장
    - 빈 캡션/광고성 반복 텍스트 filter 는 D5+ LLM 단계로 미룸
    """
    highlights: list[str] = []
    for post in posts_raw[:limit]:
        caption = post.get("caption") or ""
        if isinstance(caption, str) and caption.strip():
            highlights.append(caption[:200].strip())
    return highlights


def _extract_latest_posts(posts_raw: list[dict], *, limit: int = 10) -> list[IgLatestPost]:
    """최근 포스트 → IgLatestPost 스냅샷 (limit 최대).

    Sia Haiku 의 뒷단 분석 input. 댓글은 본문(text) 만. 타인 식별자 제외.
    입력은 이미 `_scrub_post_pii` 로 정제된 상태 가정.
    """
    result: list[IgLatestPost] = []
    for post in posts_raw[:limit]:
        caption = (post.get("caption") or "").strip()
        ts = _parse_ig_timestamp(post.get("timestamp"))
        hashtags = post.get("hashtags") or []
        display_url = post.get("displayUrl") or None  # Sonnet Vision 입력, TTL 24-48h

        comment_texts: list[str] = []
        for c in post.get("latestComments") or []:
            if not isinstance(c, dict):
                continue
            text = (c.get("text") or "").strip()
            if text:
                comment_texts.append(text)

        result.append(IgLatestPost(
            caption=caption[:500],
            timestamp=ts,
            hashtags=[h for h in hashtags if isinstance(h, str)][:20],
            latest_comments=comment_texts[:10],
            display_url=display_url if isinstance(display_url, str) else None,
        ))
    return result


def _parse_ig_timestamp(ts_raw) -> Optional[datetime]:
    """Apify ISO-8601 문자열 → datetime. 실패 시 None."""
    if not ts_raw or not isinstance(ts_raw, str):
        return None
    try:
        # "2026-01-07T13:27:39.000Z" 형태
        return datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


# 댓글 작성자 식별 필드 — Apify 응답에서 전부 제거해야 하는 키 목록
_COMMENT_PII_KEYS = {
    "ownerUsername", "ownerProfilePicUrl", "owner",
    "id",  # 댓글 고유 id 도 식별자로 쓰일 수 있음
}


def _scrub_post_pii(post: dict) -> dict:
    """포스트 dict 에서 제3자 PII 를 제거한 사본 반환.

    Apify 가 댓글 객체에 ownerUsername / ownerProfilePicUrl / owner.id 등
    타인 식별자를 넣어주는데, Sigak 은 본인 데이터만 저장해야 한다.
    본 함수는 non-destructive: 원본 변형 없이 scrubbed 복제 반환.

    Scrub 대상:
      - post.latestComments[]: text/timestamp/repliesCount 만 유지, owner* 제거
      - post.taggedUsers[]: 전체 제거 (본인이 태그한 친구들 정보)
      - post.owner: 본인이므로 유지 (profile_basics 에서 이미 쓰고 있음)
    """
    if not isinstance(post, dict):
        return {}

    scrubbed = dict(post)  # shallow copy

    # 댓글 배열 scrub
    comments = scrubbed.get("latestComments")
    if isinstance(comments, list):
        scrubbed["latestComments"] = [_scrub_comment(c) for c in comments]

    # 태그된 유저들 제거
    scrubbed.pop("taggedUsers", None)

    # child posts 도 재귀 scrub (Sidecar 캐러셀)
    children = scrubbed.get("childPosts")
    if isinstance(children, list):
        scrubbed["childPosts"] = [_scrub_post_pii(c) for c in children]

    return scrubbed


def _scrub_comment(comment: dict) -> dict:
    """댓글 dict 에서 본문(text) + 메타(timestamp, repliesCount) 만 보존."""
    if not isinstance(comment, dict):
        return {}
    text = comment.get("text") or ""
    # replies 안에도 owner 정보 있을 수 있어 같이 정제
    replies_raw = comment.get("replies") or []
    replies_scrubbed = []
    if isinstance(replies_raw, list):
        for r in replies_raw:
            if isinstance(r, dict) and r.get("text"):
                replies_scrubbed.append({
                    "text": r.get("text") or "",
                    "timestamp": r.get("timestamp"),
                })
    return {
        "text": text,
        "timestamp": comment.get("timestamp"),
        "repliesCount": comment.get("repliesCount", 0),
        "replies": replies_scrubbed,
    }
