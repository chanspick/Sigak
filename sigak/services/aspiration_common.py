"""Aspiration 공통 헬퍼 — IG/Pinterest 경로 공유 (Phase J2).

책임 분리:
  aspiration_common (본 모듈):
    - coordinate 도출 (IgFeedAnalysis → VisualCoordinate)
    - gap vector 산출
    - photo pair 선택 (본인 10장 ↔ 대상 10장에서 3-5쌍)
    - blocklist DB 조회 + 저장
    - persist_analysis (aspiration_analyses INSERT)

  aspiration_engine_ig / aspiration_engine_pinterest:
    - Apify 호출 + AspirationAnalysis 조립 (common 을 consume)
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text

from schemas.aspiration import (
    AspirationAnalysis,
    BlocklistEntry,
    PhotoPair,
    TargetType,
)
from schemas.user_profile import IgFeedAnalysis, IgLatestPost
from services.coordinate_system import (
    GapVector,
    VisualCoordinate,
    neutral_coordinate,
)
from services.knowledge_base import load_trends
from services.knowledge_matcher import match_trends_for_user
from services.sia_writer import get_sia_writer
from schemas.user_taste import UserTasteProfile


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Coordinate derivation
# ─────────────────────────────────────────────

# tone_category → (shape delta, age delta) 대략 매핑.
# CLAUDE.md 확정에 따른 heuristic — 이후 Phase H에서 Haiku 재산출로 교체 가능.
_TONE_HEURISTICS: dict[str, tuple[float, float]] = {
    # (shape delta, age delta). volume 은 pose_frequency 에서 별도 산출.
    "쿨뮤트":  (+0.10, +0.05),   # 차분/정돈 → 살짝 샤프, 살짝 성숙
    "웜뮤트":  (-0.10, +0.05),   # 부드럽/따뜻 → 소프트, 살짝 성숙
    "쿨비비드": (+0.20, -0.05),   # 샤프 강조, 프레시
    "웜비비드": (-0.05, -0.15),   # 프레시 + 살짝 소프트
    "중성":    (+0.00, +0.00),   # 중립
}


def derive_coordinate_from_analysis(analysis: IgFeedAnalysis) -> VisualCoordinate:
    """IgFeedAnalysis → VisualCoordinate.

    heuristic:
      shape  ← tone_category + style_consistency (가중)
      volume ← pose_frequency 힌트
      age    ← tone_category + three_month_shift 영향

    이 함수는 MVP heuristic. Phase H 이후 Haiku 재산출 가능.
    """
    # tone 기반 baseline (0.5 중앙 + heuristic 편차)
    tone_shape_d, tone_age_d = _TONE_HEURISTICS.get(
        analysis.tone_category, (0.0, 0.0),
    )

    # style_consistency 가 높으면 tone 편차 증폭 (일관성 = 의도성)
    weight = 0.5 + min(max(analysis.style_consistency, 0.0), 1.0) * 0.5

    shape_raw = 0.5 + tone_shape_d * weight
    age_raw = 0.5 + tone_age_d * weight

    # pose_frequency 에서 volume 추정 (정면 > 측면 = 입체 작음)
    pose = analysis.pose_frequency or ""
    if "정면 > 측면" in pose:
        volume_raw = 0.45
    elif "측면 > 정면" in pose:
        volume_raw = 0.60
    else:
        volume_raw = 0.50

    return VisualCoordinate(
        shape=_clamp01(shape_raw),
        volume=_clamp01(volume_raw),
        age=_clamp01(age_raw),
    )


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


# ─────────────────────────────────────────────
#  Photo pair selection
# ─────────────────────────────────────────────

def select_photo_pairs(
    user_posts: list[IgLatestPost],
    target_posts: list[IgLatestPost],
    gap: GapVector,
    *,
    max_pairs: int = 5,
) -> list[PhotoPair]:
    """본인 × 대상 사진을 쌍으로 묶어 3~5 쌍 반환.

    MVP 전략 (단순, Phase J 이후 Sonnet Vision 세밀 매칭으로 업그레이드 가능):
      - user_posts 에서 display_url 있는 것 중 앞 max_pairs 장
      - target_posts 에서 display_url 있는 것 중 앞 max_pairs 장
      - 1:1 인덱스 매칭
      - pair_axis_hint 는 gap.primary_axis 고정 (3-5쌍 모두 주 이동축 강조)
    """
    user_urls = [p.display_url for p in user_posts if p.display_url][:max_pairs]
    target_urls = [p.display_url for p in target_posts if p.display_url][:max_pairs]

    n = min(len(user_urls), len(target_urls))
    if n < 1:
        return []

    writer = get_sia_writer()
    # Stub writer 는 photo 별 코멘트를 간단 생성. Phase H+I 에서 Haiku 기반 풍부화.
    pairs: list[PhotoPair] = []
    for i in range(n):
        pairs.append(PhotoPair(
            user_photo_url=user_urls[i],
            user_sia_comment=writer.generate_comment_for_photo(
                photo_url=user_urls[i],
                photo_context={"category": "user", "rank": i, "gap_axis": gap.primary_axis},
                profile=_empty_profile(),
            ),
            target_photo_url=target_urls[i],
            target_sia_comment=writer.generate_comment_for_photo(
                photo_url=target_urls[i],
                photo_context={"category": "target", "rank": i, "gap_axis": gap.primary_axis},
                profile=_empty_profile(),
            ),
            pair_axis_hint=f"{gap.primary_axis} 축 차이",
        ))

    return pairs


def _empty_profile() -> UserTasteProfile:
    """Stub writer 에 넣을 최소 profile — 실 구현 Phase H/I 에서 교체."""
    return UserTasteProfile(
        user_id="stub",
        snapshot_at=datetime.now(timezone.utc),
    )


# ─────────────────────────────────────────────
#  R2 materialization — 추구미 타깃 사진 영구 보존 (Track Aspiration STEP 3)
# ─────────────────────────────────────────────

def materialize_pairs_to_r2(
    pairs: list[PhotoPair],
    *,
    user_id: str,
    analysis_id: str,
) -> tuple[list[PhotoPair], Optional[str]]:
    """PhotoPair 의 target_photo_url 을 R2 에 영구 저장 + URL 교체.

    user_photo_url 은 vault.ig_feed_cache 의 기존 URL 그대로 유지 — STEP 2
    완료 후엔 이미 R2 URL, 미완이면 IG CDN URL (최종 전환 시 자동 정합).
    별도 aspiration_users/ 복사 없음 (비용 절감, 플랜 3.2 권장안).

    R2 key: user_media/{user_id}/aspiration_targets/{analysis_id}/photo_NN.jpg
    (r2_client.aspiration_target_photo_key 헬퍼 사용)

    Args:
      pairs: select_photo_pairs 결과.
      user_id: R2 key prefix 소유자.
      analysis_id: 분석 식별자.

    Returns:
      (업데이트된 pairs, r2_target_dir prefix 또는 None)
      개별 업로드 실패 시 해당 target URL 은 원본 유지. 전체 실패 시 None prefix.
    """
    if not pairs:
        return pairs, None

    import httpx
    from services import r2_client

    r2_dir_key = r2_client.aspiration_target_dir(user_id, analysis_id)

    updated: list[PhotoPair] = []
    with httpx.Client(timeout=8.0, follow_redirects=True) as client:
        for idx, pair in enumerate(pairs):
            target_url_new = _upload_target_to_r2(
                client, pair.target_photo_url,
                user_id=user_id, analysis_id=analysis_id, index=idx,
            )
            updated.append(pair.model_copy(update={
                # user_photo_url 유지 (vault 에서 온 R2 또는 CDN URL)
                "target_photo_url": target_url_new or pair.target_photo_url,
            }))

    return updated, r2_dir_key


def _upload_target_to_r2(
    http_client,
    src_url: str,
    *,
    user_id: str,
    analysis_id: str,
    index: int,
) -> Optional[str]:
    """단일 추구미 타깃 이미지 다운로드 → R2 저장 → public URL 반환.

    실패 시 None — caller 는 원본 URL 유지.
    """
    if not src_url:
        return None
    from services import r2_client

    key = r2_client.aspiration_target_photo_key(user_id, analysis_id, index)
    try:
        resp = http_client.get(src_url)
        resp.raise_for_status()
        content_type = (
            resp.headers.get("content-type", "image/jpeg")
            .split(";")[0]
            .strip()
            .lower()
        )
        if not content_type.startswith("image/"):
            content_type = "image/jpeg"
        r2_client.put_bytes(key, resp.content, content_type=content_type)
    except Exception:
        logger.exception("aspiration target R2 put failed: key=%s", key)
        return None

    return r2_client.public_url(key) or f"r2://{key}"


def extract_user_posts_from_vault(vault) -> list[IgLatestPost]:
    """vault.ig_feed_cache.latest_posts → IgLatestPost 리스트.

    essentials 단계 (ig_scraper.fetch_ig_profile) 에서 저장된 본인 IG 사진 메타.
    photo_pairs 좌측 채우는 데 사용. display_url 없는 항목은 제외.
    """
    if vault is None or not vault.ig_feed_cache:
        return []
    raw = vault.ig_feed_cache.get("latest_posts") or []
    out: list[IgLatestPost] = []
    for p in raw:
        if not isinstance(p, dict):
            continue
        url = p.get("display_url")
        if not url:
            continue
        try:
            out.append(IgLatestPost(
                caption=p.get("caption") or "",
                display_url=url,
            ))
        except Exception:
            continue
    return out


# ─────────────────────────────────────────────
#  Blocklist (DB)
# ─────────────────────────────────────────────

def is_blocked(
    db,
    *,
    target_type: TargetType,
    target_identifier: str,
) -> bool:
    """aspiration_target_blocklist 조회. 차단이면 True.

    테이블 없으면 False (마이그레이션 전 dev 환경). 예외 삼킴.
    """
    try:
        row = db.execute(
            text(
                "SELECT 1 FROM aspiration_target_blocklist "
                "WHERE target_type = :t AND target_identifier = :id LIMIT 1"
            ),
            {"t": target_type, "id": target_identifier},
        ).first()
        return row is not None
    except Exception:
        logger.exception(
            "blocklist check failed — treating as unblocked (dev/migration 미적용?)"
        )
        return False


def add_to_blocklist(
    db,
    *,
    target_type: TargetType,
    target_identifier: str,
    reason: Optional[str] = None,
) -> None:
    """대상자 삭제 요청 처리. PK 충돌 시 idempotent."""
    db.execute(
        text(
            "INSERT INTO aspiration_target_blocklist "
            "  (target_type, target_identifier, blocked_at, reason) "
            "VALUES (:t, :id, NOW(), :r) "
            "ON CONFLICT (target_type, target_identifier) DO NOTHING"
        ),
        {"t": target_type, "id": target_identifier, "r": reason},
    )


# ─────────────────────────────────────────────
#  Persistence
# ─────────────────────────────────────────────

def persist_analysis(
    db,
    analysis: AspirationAnalysis,
) -> None:
    """aspiration_analyses INSERT. Transaction ownership 은 caller."""
    db.execute(
        text(
            "INSERT INTO aspiration_analyses "
            "  (id, user_id, target_type, target_identifier, result_data, created_at) "
            "VALUES (:id, :uid, :t, :ti, CAST(:rd AS jsonb), :ca)"
        ),
        {
            "id": analysis.analysis_id,
            "uid": analysis.user_id,
            "t": analysis.target_type,
            "ti": analysis.target_identifier,
            "rd": json.dumps(analysis.model_dump(mode="json"), ensure_ascii=False, default=str),
            "ca": analysis.created_at,
        },
    )


def generate_analysis_id() -> str:
    return f"asp_{uuid.uuid4().hex[:24]}"


# ─────────────────────────────────────────────
#  Knowledge Base 매칭
# ─────────────────────────────────────────────

def match_trends_for_aspiration_direction(
    gap: GapVector,
    user_coord: VisualCoordinate,
    gender: str,
    *,
    season: Optional[str] = None,
    limit: int = 3,
) -> list[str]:
    """추구미 이동 방향에 맞는 트렌드 ID 반환.

    간단 heuristic: user_coord + gap 적용한 '도착 좌표' 기준으로 KnowledgeMatcher 조회.
    """
    target_coord = VisualCoordinate(
        shape=_clamp01(user_coord.shape + _axis_delta(gap, "shape")),
        volume=_clamp01(user_coord.volume + _axis_delta(gap, "volume")),
        age=_clamp01(user_coord.age + _axis_delta(gap, "age")),
    )
    # UserTasteProfile 에 target 좌표를 current_position 으로 넣어 매칭 재사용
    stub_profile = UserTasteProfile(
        user_id="__aspiration_target_stub__",
        snapshot_at=datetime.now(timezone.utc),
        current_position=target_coord,
    )
    matched = match_trends_for_user(
        stub_profile, gender=gender if gender in ("female", "male") else "female",
        season=season, limit=limit,
    )
    return [m.trend.trend_id for m in matched]


def _axis_delta(gap: GapVector, axis: str) -> float:
    if gap.primary_axis == axis:
        return gap.primary_delta
    if gap.secondary_axis == axis:
        return gap.secondary_delta
    if gap.tertiary_axis == axis:
        return gap.tertiary_delta
    return 0.0


# ─────────────────────────────────────────────
#  Overall message (Sia writer)
# ─────────────────────────────────────────────

def compose_overall_message(
    *,
    target_display_name: str,
    gap: GapVector,
    matched_trend_count: int,
) -> str:
    """추구미 리포트 종합 메시지 — stub writer 의 간결한 정리.

    Phase H 이후 SiaWriter concrete 에서 Haiku 기반 풍부화.
    """
    return (
        f"{target_display_name} 쪽 결을 살펴봤어요.\n"
        f"본인 좌표에서 {gap.narrative()}\n"
        f"이 방향으로 잇는 트렌드 {matched_trend_count}건을 같이 정리했습니다."
    )
