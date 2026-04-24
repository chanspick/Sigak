"""user_profiles CRUD service (v2 Priority 1 D2).

Contracts (SPEC-ONBOARDING-V2):
  #1 row 생성 시점 = Step 0 완료 직후 (gender + birth_date NOT NULL 보장)
  #2 v1 → v2 마이그레이션 시 users.gender → user_profiles.gender 복사
  #4 JSONB 는 Pydantic schema 로 application-level validation

Route layer 는 이 서비스만 호출, 직접 SQL 작성 금지.
Transaction 소유권: 서비스는 commit 하지 않음. 라우트 레이어가 묶어서 commit.

Raw SQL (sa.text) 사용 — 프로젝트 컨벤션 (services/tokens.py 와 동일).
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime
from typing import Optional

from sqlalchemy import text

from schemas.user_profile import IgFeedCache, StructuredFields
from services.ig_scraper import IgFetchStatus, fetch_ig_profile, is_stale


logger = logging.getLogger(__name__)


class UserProfileNotFoundError(Exception):
    """user_profiles 에 해당 user_id row 없음."""


# ─────────────────────────────────────────────
#  Contract #1: Step 0 제출 시 row 생성
# ─────────────────────────────────────────────

def create_profile_on_onboarding(
    db,
    *,
    user_id: str,
    gender: str,
    birth_date: date,
    ig_handle: Optional[str] = None,
) -> None:
    """Step 0 폼 제출 직후 호출. gender + birth_date 필수.

    동시에 users 테이블의 birth_date / ig_handle 도 동기화 (v2 ALTER 컬럼).

    Raises:
        IntegrityError: 이미 user_profiles row 존재 (user_id PK 중복)
    """
    if gender not in ("female", "male"):
        raise ValueError(f"invalid gender: {gender!r}")

    db.execute(
        text(
            "INSERT INTO user_profiles "
            "  (user_id, gender, birth_date, ig_handle, "
            "   structured_fields, onboarding_completed, created_at, updated_at) "
            "VALUES "
            "  (:uid, :gender, :bd, :ih, "
            "   '{}'::jsonb, FALSE, NOW(), NOW())"
        ),
        {"uid": user_id, "gender": gender, "bd": birth_date, "ih": ig_handle},
    )
    # users 테이블 동기화 (v2 ALTER 컬럼)
    db.execute(
        text("UPDATE users SET birth_date = :bd, ig_handle = :ih WHERE id = :uid"),
        {"uid": user_id, "bd": birth_date, "ih": ig_handle},
    )


# ─────────────────────────────────────────────
#  Contract #2: v1 → v2 마이그레이션 시 gender 복사
# ─────────────────────────────────────────────

def migrate_v1_user_to_v2(
    db,
    *,
    user_id: str,
    birth_date: date,
    ig_handle: Optional[str] = None,
) -> None:
    """v1 유저가 재온보딩 수락 시 호출.

    users.gender 값을 user_profiles.gender 로 복사 (v1 수집된 값 유지).
    birth_date / ig_handle 은 Step 0 에서 새로 수집한 값.

    Raises:
        UserProfileNotFoundError: users.id 존재하지 않음
        ValueError: users.gender 가 female/male 이 아님
        IntegrityError: 이미 user_profiles row 존재
    """
    row = db.execute(
        text("SELECT gender FROM users WHERE id = :uid"),
        {"uid": user_id},
    ).first()
    if row is None:
        raise UserProfileNotFoundError(f"users.id={user_id} not found")

    v1_gender = row.gender
    if v1_gender not in ("female", "male"):
        # v1 default 는 "female" 이어야 함. 외계 값이면 안전하게 실패.
        raise ValueError(
            f"users.id={user_id} gender={v1_gender!r} invalid for v2 migration"
        )

    create_profile_on_onboarding(
        db,
        user_id=user_id,
        gender=v1_gender,
        birth_date=birth_date,
        ig_handle=ig_handle,
    )


# ─────────────────────────────────────────────
#  Read
# ─────────────────────────────────────────────

def get_profile(db, user_id: str) -> Optional[dict]:
    """user_profiles row 를 dict 로 반환. 없으면 None.

    JSONB 필드는 파싱된 dict (PostgreSQL JSONB → Python dict 자동 변환).
    시간 필드는 datetime (timezone-aware UTC).
    """
    row = db.execute(
        text(
            "SELECT user_id, gender, birth_date, ig_handle, "
            "       ig_feed_cache, ig_fetch_status, ig_fetched_at, "
            "       structured_fields, onboarding_completed, created_at, updated_at "
            "FROM user_profiles WHERE user_id = :uid"
        ),
        {"uid": user_id},
    ).first()
    if row is None:
        return None
    return {
        "user_id": row.user_id,
        "gender": row.gender,
        "birth_date": row.birth_date,
        "ig_handle": row.ig_handle,
        "ig_feed_cache": row.ig_feed_cache,
        "ig_fetch_status": row.ig_fetch_status,
        "ig_fetched_at": row.ig_fetched_at,
        "structured_fields": row.structured_fields or {},
        "onboarding_completed": bool(row.onboarding_completed),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def require_profile(db, user_id: str) -> dict:
    """get_profile 의 raise 변형."""
    profile = get_profile(db, user_id)
    if profile is None:
        raise UserProfileNotFoundError(f"user_profiles.user_id={user_id} not found")
    return profile


# ─────────────────────────────────────────────
#  IG Feed Cache
# ─────────────────────────────────────────────

def upsert_ig_feed_cache(
    db,
    *,
    user_id: str,
    cache: Optional[IgFeedCache],
    status: IgFetchStatus,
) -> None:
    """IG 수집 결과 저장. cache=None 은 failed/skipped 케이스.

    ig_feed_cache JSONB 는 Pydantic 모델의 `.model_dump(mode="json")` 결과.
    ig_fetched_at 은 cache 가 있을 때만 NOW() 로 갱신.
    """
    cache_json = json.dumps(cache.model_dump(mode="json")) if cache else None
    fetched_at_sql = "NOW()" if cache is not None else "NULL"
    db.execute(
        text(
            f"UPDATE user_profiles SET "
            f"  ig_feed_cache = CAST(:cache AS jsonb), "
            f"  ig_fetch_status = :status, "
            f"  ig_fetched_at = {fetched_at_sql}, "
            f"  updated_at = NOW() "
            f"WHERE user_id = :uid"
        ),
        {"uid": user_id, "cache": cache_json, "status": status},
    )


def refresh_ig_feed(db, user_id: str, *, force: bool = False) -> IgFetchStatus:
    """IG 피드 refresh. stale (>=2주) 이거나 force=True 일 때만 Apify 호출.

    Returns: fetch status (success/failed/skipped/private/"not_stale").
    "not_stale" — refresh 조건 불충족 (아직 신선함), 기존 cache 유지.
    """
    profile = require_profile(db, user_id)
    if not force and not is_stale(profile.get("ig_fetched_at")):
        logger.info("IG refresh skipped (not stale): user_id=%s", user_id)
        return "skipped"   # caller 에게 "신선함" 시그널

    ig_handle = profile.get("ig_handle")
    status, cache = fetch_ig_profile(ig_handle)
    upsert_ig_feed_cache(db, user_id=user_id, cache=cache, status=status)
    return status


# ─────────────────────────────────────────────
#  Structured Fields (대화 추출 결과 merge)
# ─────────────────────────────────────────────

def merge_structured_fields(
    db,
    *,
    user_id: str,
    fields: StructuredFields,
) -> None:
    """Shallow merge — 기존 유저 수동 수정분 보존, 새 키만 덮어씀.

    PostgreSQL JSONB `||` 연산자 사용. Pydantic dump 시 `exclude_none=True`
    로 None 필드 제외 → 기존 값 그대로 유지 (확률적 덮어쓰기 방지).
    """
    merge_payload = fields.as_merge_dict()
    if not merge_payload:
        logger.debug("merge_structured_fields noop: empty payload user_id=%s", user_id)
        return

    db.execute(
        text(
            "UPDATE user_profiles SET "
            "  structured_fields = COALESCE(structured_fields, '{}'::jsonb) || CAST(:patch AS jsonb), "
            "  updated_at = NOW() "
            "WHERE user_id = :uid"
        ),
        {"uid": user_id, "patch": json.dumps(merge_payload)},
    )


def mark_onboarding_completed(db, user_id: str) -> None:
    """extraction 성공 + 필수 필드 확보 시 호출. onboarding_completed=TRUE.

    users 와 user_profiles 양쪽 동기화 — 게이트 체크(routes/auth.py::/me,
    routes/verdicts.py, routes/sigak_report.py)가 users 테이블을 읽으므로
    둘 다 업데이트하지 않으면 Sia 완료 후에도 프론트 useOnboardingGuard 가
    모든 라우트를 /sia 로 redirect 하는 데드락이 발생한다.
    """
    db.execute(
        text(
            "UPDATE user_profiles SET "
            "  onboarding_completed = TRUE, updated_at = NOW() "
            "WHERE user_id = :uid"
        ),
        {"uid": user_id},
    )
    db.execute(
        text(
            "UPDATE users SET onboarding_completed = TRUE WHERE id = :uid"
        ),
        {"uid": user_id},
    )


# ─────────────────────────────────────────────
#  대화 재실행 (유저 trigger)
# ─────────────────────────────────────────────

def restart_conversation(db, user_id: str) -> None:
    """유저가 설정 페이지에서 "Sia와 다시 대화하기" 누를 때.

    structured_fields 를 {} 로 초기화 + onboarding_completed=FALSE.
    mark_onboarding_completed 와 대칭 — users/user_profiles 양쪽 동기화.
    기존 conversations row 는 archive (status 유지, 지우지 않음 — 조회 가능).
    새 conversation 생성은 route 레이어에서 sia/chat/start 호출로 수행.
    """
    db.execute(
        text(
            "UPDATE user_profiles SET "
            "  structured_fields = '{}'::jsonb, "
            "  onboarding_completed = FALSE, "
            "  updated_at = NOW() "
            "WHERE user_id = :uid"
        ),
        {"uid": user_id},
    )
    db.execute(
        text(
            "UPDATE users SET onboarding_completed = FALSE WHERE id = :uid"
        ),
        {"uid": user_id},
    )
