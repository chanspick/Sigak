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
from schemas.user_taste import UserTasteProfile
from services.aspiration_common import (
    compose_overall_message,
    derive_coordinate_from_analysis,
    generate_analysis_id,
    is_blocked,
    match_trends_for_aspiration_direction,
    materialize_pairs_to_r2,
    select_photo_pairs,
)
from services.aspiration_engine_ig import AspirationRunResult, _ensure_profile
from services.coordinate_system import GapVector, VisualCoordinate, neutral_coordinate
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
    profile: Optional[UserTasteProfile] = None,
    user_name: Optional[str] = None,
    user_analysis_snapshot: Optional[dict] = None,
) -> AspirationRunResult:
    """Pinterest 보드 URL → AspirationAnalysis + narrative.

    Args:
      db: blocklist 체크용
      user_id / user_gender / user_coordinate: 본인 맥락
      board_url: https://www.pinterest.com/{user}/{board}/ 형식 기대
      user_posts: 본인 IG posts (vault.ig_feed_cache.latest_posts).
                  photo_pairs 좌측 채움. None/[] 면 페어 없음.
      profile: UserTasteProfile snapshot — 5 필드 풀 활용 (Phase J5).
               None 이면 user_coordinate 만 들어간 minimal profile 합성.
      user_name: Sia narrative 호명용 (basic_info.name).
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
    # v1.5: tuple unpacking — image_urls + raw_items / board_name 등 메타.
    try:
        image_urls, board_meta = _call_pinterest_actor(
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
    # v1.5: vision_raw 함께 반환 — 추구미 R2 디렉터리에 분리 저장 (LLM 격리).
    target_analysis, target_vision_raw = analyze_ig_feed(
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

    # 8. Sia 종합 narrative — Phase J5: Haiku + vault 5/5 + JSON dict
    # board_meta.board_name 우선, 없으면 "Pinterest 보드" fallback.
    pre_display_name = board_meta.get("board_name") or "Pinterest 보드"
    effective_profile = _ensure_profile(profile, user_id, user_coord)
    target_snapshot_dump = target_analysis.model_dump(mode="json")
    narrative = compose_overall_message(
        target_display_name=pre_display_name,
        gap_vector=gap,
        profile=effective_profile,
        target_analysis_snapshot=target_snapshot_dump,
        user_analysis_snapshot=user_analysis_snapshot,
        matched_trends=None,                 # routes 에서 KB hydrate (저장 후)
        user_name=user_name,
        photo_pairs=[p.model_dump() for p in pairs],
    )

    # 9. R2 materialization — Pinterest 이미지 영구 저장 (analysis_id 선행 발급)
    analysis_id = generate_analysis_id()
    pairs_persisted, r2_target_dir = materialize_pairs_to_r2(
        pairs, user_id=user_id, analysis_id=analysis_id,
    )

    # 9-b. v1.5 — Apify raw + Vision raw R2 분리 저장 (LLM 격리).
    # PII (pinner.username / instagram_data.username 등) 보호 위해 DB 직접 X.
    # 메타분석 시 R2 fetch 로만 활용. 실패는 메인 플로우 무영향.
    from services.aspiration_common import (
        materialize_apify_raw_to_r2, materialize_vision_raw_to_r2,
    )
    r2_apify_raw_key = materialize_apify_raw_to_r2(
        board_meta.get("raw_items") or [],
        user_id=user_id, analysis_id=analysis_id,
    )
    r2_vision_raw_key = materialize_vision_raw_to_r2(
        target_vision_raw, user_id=user_id, analysis_id=analysis_id,
    )

    # 9-c. 작업 9 — matched_trends 분석 시점 스냅샷 (KB 변경 시 행동지침 보존)
    matched_trends_snapshot = _hydrate_matched_trends_snapshot(
        matched_trend_ids,
        profile=effective_profile,
        gap_vector=gap,
        user_name=user_name,
    )

    # 10. 조립
    analysis = AspirationAnalysis(
        analysis_id=analysis_id,
        user_id=user_id,
        target_type="pinterest",
        target_identifier=board_id,
        target_display_name=pre_display_name,
        created_at=datetime.now(timezone.utc),
        user_coordinate=user_coord,
        target_coordinate=target_coord,
        gap_vector=gap,
        gap_narrative=(narrative.get("gap_summary") or gap.narrative()),
        photo_pairs=pairs_persisted,
        sia_overall_message=narrative["overall_message"],
        matched_trend_ids=matched_trend_ids,
        target_analysis_snapshot=target_snapshot_dump,
        images_captured_count=len(image_urls),
        r2_target_dir=r2_target_dir,
        r2_apify_raw_key=r2_apify_raw_key,
        r2_vision_raw_key=r2_vision_raw_key,
        matched_trends_snapshot=matched_trends_snapshot,
    )

    # narrative 에 분석 시점 vault 5 필드 메타 추가 (사용자 명령서 6-B)
    narrative_persisted = dict(narrative)
    narrative_persisted["user_original_phrases_at_time"] = list(
        effective_profile.user_original_phrases
    )
    narrative_persisted["strength_score_at_time"] = effective_profile.strength_score

    return AspirationRunResult(
        "completed",
        analysis=analysis,
        narrative=narrative_persisted,
    )


# ─────────────────────────────────────────────
#  matched_trends 스냅샷 (작업 9) — 후방호환
#  TODO (Phase H+I): Haiku raw response 도 R2 분리 저장 패턴 적용.
#  위치: user_media/{user_id}/aspiration_targets/{analysis_id}/haiku_responses/
#    ├── photo_pair_NN_user.json
#    ├── photo_pair_NN_target.json
#    └── overall_message.json
#  인스턴스 4 (Aspiration narrative 정교화) 또는 후속 작업 범위.
# ─────────────────────────────────────────────

def _hydrate_matched_trends_snapshot(
    trend_ids: list[str],
    *,
    profile: Optional[UserTasteProfile] = None,
    gap_vector: Optional[GapVector] = None,
    user_name: Optional[str] = None,
) -> Optional[list[dict]]:
    """KB 에서 trend hydrate → MatchedTrendView snapshot dict list (분석 시점 동결).

    KB 변경 시 과거 리포트 행동지침 보존 (CLAUDE.md 시계열 보존 원칙).

    Phase J6 — personalize:
      profile 주어지면 SiaWriter.generate_trend_card_narrative() 로
      detailed_guide 를 유저 결 + gap 기반 1-2 문장 narrative 로 덮어씀.
      ThreadPoolExecutor 병렬 호출 (~1-2초).
      profile None / LLM 실패 시 _sanitize_trend_guide() fallback —
      KB raw [score: ±X / 라벨] 프리픽스만 제거 (화면 노출 차단 보장).

    예외/빈값은 None 반환 — 응답 시점 KB hydrate fallback 동작.
    """
    if not trend_ids:
        return None
    try:
        from concurrent.futures import ThreadPoolExecutor
        from schemas.aspiration import MatchedTrendView
        from services.knowledge_base import load_trends
        from services.sia_writer import (
            _sanitize_trend_guide,
            get_sia_writer,
        )

        all_trends = load_trends()
        by_id = {t.trend_id: t for t in all_trends}
        views: list[MatchedTrendView] = []
        for tid in trend_ids:
            t = by_id.get(tid)
            if t is None:
                continue
            views.append(MatchedTrendView(
                trend_id=t.trend_id,
                title=t.title,
                category=str(t.category),
                detailed_guide=t.detailed_guide,
                action_hints=list(t.action_hints or []),
                score=None,
            ))

        if not views:
            return None

        writer = get_sia_writer()

        def _process(v: MatchedTrendView) -> MatchedTrendView:
            try:
                if profile is not None:
                    text = writer.generate_trend_card_narrative(
                        trend=v,
                        profile=profile,
                        gap_vector=gap_vector,
                        user_name=user_name,
                    )
                    v.detailed_guide = (
                        text or _sanitize_trend_guide(v.detailed_guide or "")
                    )
                else:
                    v.detailed_guide = _sanitize_trend_guide(
                        v.detailed_guide or ""
                    )
            except Exception:
                logger.exception(
                    "trend personalize failed (id=%s) — sanitize fallback",
                    v.trend_id,
                )
                v.detailed_guide = _sanitize_trend_guide(
                    v.detailed_guide or ""
                )
            return v

        # 병렬 — 가장 느린 1번 시간만 (~1-2초)
        with ThreadPoolExecutor(max_workers=min(5, len(views))) as ex:
            personalized = list(ex.map(_process, views))

        return [v.model_dump(mode="json") for v in personalized] or None
    except Exception:
        logger.exception(
            "matched_trends snapshot hydrate failed for ids=%s", trend_ids,
        )
        return None


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
) -> tuple[list[str], dict]:
    """devcake~pinterest-data-scraper 실행 → (이미지 URLs, raw 응답 메타).

    v1.5 변경:
      - 반환 list[str] → tuple[list[str], dict]
      - dict 안: board_name / raw_items (필터 후 핀별 dict 전수) /
                 total_pins_raw / pins_after_filter
      - 필터: is_product_pin / 비디오 핀 / 이미지 없는 핀 skip
      - 응답 shape (devcake actor): item.images.{orig, 736x, 474x, 236x}.url
        size_keys 우선순위 fallback (LIVE probe 생략, 방어 로직).

    DEBUG_PINTEREST_RAW_DUMP=1 환경변수 시 첫 호출 응답을 픽스처로 dump
    (tests/fixtures/pinterest_response_sample.json). 본인 (창업자) E2E 검증 시
    환경변수 켜고 1번 호출 → 픽스처 확보 → size_keys 우선순위 검토 후 끄기.

    PII 정책 (이용약관 §11):
      - raw_items 안 pinner.username / instagram_data.username 등 = PII.
      - 본 함수는 raw 를 반환만, R2 분리 저장은 caller (aspiration_common 헬퍼).
      - DB / LLM / SIGAK UI 노출 금지 — caller 격리 책임.

    예외는 caller 에서 흡수.
    """
    import os

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
            raise ValueError(
                f"unexpected Pinterest actor response type: {type(data).__name__}"
            )

    # DEBUG dump — LIVE probe 대용. 본인 E2E 첫 호출 시 환경변수 켜서 픽스처 확보.
    if os.getenv("DEBUG_PINTEREST_RAW_DUMP") == "1":
        try:
            import json as _json
            from pathlib import Path
            fixture_path = Path("tests/fixtures/pinterest_response_sample.json")
            fixture_path.parent.mkdir(parents=True, exist_ok=True)
            with open(fixture_path, "w", encoding="utf-8") as f:
                _json.dump(data, f, ensure_ascii=False, indent=2)
            logger.warning(
                "pinterest raw dumped to fixtures (DEBUG mode): %d items → %s",
                len(data), fixture_path,
            )
        except Exception:
            logger.exception("pinterest raw dump failed")

    urls: list[str] = []
    raw_items: list[dict] = []  # 필터 후 핀별 raw 전수 보존 (R2 저장용)
    board_name: Optional[str] = None

    for item in data:
        if not isinstance(item, dict):
            continue
        # 필터 1: 커머스 핀 skip (추구미 부적절)
        if item.get("is_product_pin") is True:
            continue
        # 필터 2: 비디오 핀 skip (이미지 분석 대상 외)
        if item.get("videos"):
            continue
        # 필터 3: 이미지 없는 핀 skip + size_keys 우선순위 fallback
        images = item.get("images")
        if not isinstance(images, dict):
            continue
        candidate: Optional[str] = None
        for size_key in ("orig", "736x", "474x", "236x"):
            size_obj = images.get(size_key)
            if isinstance(size_obj, dict):
                u = size_obj.get("url")
                if isinstance(u, str) and u.startswith("http"):
                    candidate = u
                    break
        if not candidate:
            logger.warning(
                "pinterest_no_url: keys=%s", list(images.keys()),
            )
            continue

        urls.append(candidate)
        raw_items.append(item)

        # board_name lazy capture (첫 유효 핀의 board.name)
        if board_name is None:
            board = item.get("board")
            if isinstance(board, dict):
                bn = board.get("name")
                if isinstance(bn, str) and bn.strip():
                    board_name = bn.strip()

    return urls, {
        "board_name": board_name,
        "raw_items": raw_items,
        "total_pins_raw": len(data),
        "pins_after_filter": len(urls),
    }


def _wrap_images_as_posts(image_urls: list[str]) -> list[IgLatestPost]:
    """Pinterest 이미지 url list → IgLatestPost 호환 shape.

    Vision analyzer 가 IgLatestPost.display_url 만 사용하므로, caption/comments
    는 빈 값 허용.
    """
    return [
        IgLatestPost(caption="", display_url=url)
        for url in image_urls
    ]
