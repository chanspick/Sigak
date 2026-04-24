"""user_profiles CRUD tests (v2 Priority 1 D2).

D2 계약 검증:
  #1 create_profile_on_onboarding — Step 0 직후 row 생성, gender+birth_date NOT NULL
  #2 migrate_v1_user_to_v2 — users.gender → user_profiles.gender 복사

DB 는 mock 으로 대체 (sqlalchemy Session 인터페이스 모사).
실 DB 검증은 D6~D7 integration + D14 staging.
"""
import sys
import os
import json
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, call

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schemas.user_profile import (
    IgFeedCache,
    IgFeedProfileBasics,
    StructuredFields,
)
from services import ig_scraper, user_profiles
from services.user_profiles import UserProfileNotFoundError


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _fake_db():
    """최소 DB mock — db.execute 만 제공. 호출 기록 검증용."""
    db = MagicMock()
    return db


def _exec_calls_sql(db) -> list[str]:
    """db.execute 에 전달된 SQL 문자열 목록 (stripped)."""
    return [
        str(c.args[0]).replace("\n", " ").strip()
        for c in db.execute.call_args_list
    ]


# ─────────────────────────────────────────────
#  Contract #1: create_profile_on_onboarding
# ─────────────────────────────────────────────

def test_create_profile_on_onboarding_inserts_user_profile():
    db = _fake_db()
    user_profiles.create_profile_on_onboarding(
        db,
        user_id="u1",
        gender="female",
        birth_date=date(1999, 3, 15),
        ig_handle="@yuni",
    )
    # 2 개 execute: user_profiles INSERT + users UPDATE
    assert db.execute.call_count == 2
    sqls = _exec_calls_sql(db)
    assert "INSERT INTO user_profiles" in sqls[0]
    assert "UPDATE users SET birth_date" in sqls[1]

    # 바인딩 파라미터 검증
    insert_params = db.execute.call_args_list[0].args[1]
    assert insert_params == {
        "uid": "u1",
        "gender": "female",
        "bd": date(1999, 3, 15),
        "ih": "@yuni",
    }


def test_create_profile_on_onboarding_without_ig_handle():
    db = _fake_db()
    user_profiles.create_profile_on_onboarding(
        db, user_id="u2", gender="male", birth_date=date(1990, 1, 1),
    )
    insert_params = db.execute.call_args_list[0].args[1]
    assert insert_params["ih"] is None


def test_create_profile_on_onboarding_rejects_invalid_gender():
    db = _fake_db()
    with pytest.raises(ValueError, match="invalid gender"):
        user_profiles.create_profile_on_onboarding(
            db, user_id="u1", gender="other", birth_date=date(2000, 1, 1),
        )
    # 잘못된 값이면 SQL 호출 전에 실패
    assert db.execute.call_count == 0


# ─────────────────────────────────────────────
#  Contract #2: migrate_v1_user_to_v2
# ─────────────────────────────────────────────

def _mock_users_gender_result(gender_value):
    """db.execute(...).first() 가 gender 를 가진 Row mock 를 반환하도록 설정."""
    row = MagicMock()
    row.gender = gender_value
    result = MagicMock()
    result.first.return_value = row
    return result


def test_migrate_v1_user_copies_gender_female():
    db = _fake_db()
    # 첫 execute: SELECT gender (v1 유저 female)
    # 이후 execute: create_profile_on_onboarding 내부 INSERT + UPDATE
    db.execute.side_effect = [
        _mock_users_gender_result("female"),  # SELECT
        MagicMock(),                          # INSERT user_profiles
        MagicMock(),                          # UPDATE users
    ]
    user_profiles.migrate_v1_user_to_v2(
        db,
        user_id="v1_user",
        birth_date=date(1995, 6, 1),
        ig_handle=None,
    )
    # 3 execute: SELECT + INSERT + UPDATE
    assert db.execute.call_count == 3
    # INSERT 파라미터의 gender 가 v1 값이어야 함
    insert_params = db.execute.call_args_list[1].args[1]
    assert insert_params["gender"] == "female"
    assert insert_params["uid"] == "v1_user"


def test_migrate_v1_user_copies_gender_male():
    db = _fake_db()
    db.execute.side_effect = [
        _mock_users_gender_result("male"),
        MagicMock(),
        MagicMock(),
    ]
    user_profiles.migrate_v1_user_to_v2(
        db, user_id="v1_male_user", birth_date=date(1995, 6, 1),
    )
    insert_params = db.execute.call_args_list[1].args[1]
    assert insert_params["gender"] == "male"


def test_migrate_v1_user_raises_when_user_missing():
    db = _fake_db()
    result = MagicMock()
    result.first.return_value = None
    db.execute.return_value = result

    with pytest.raises(UserProfileNotFoundError):
        user_profiles.migrate_v1_user_to_v2(
            db, user_id="ghost", birth_date=date(2000, 1, 1),
        )


def test_migrate_v1_user_raises_on_invalid_gender_in_users():
    db = _fake_db()
    db.execute.return_value = _mock_users_gender_result("other")
    with pytest.raises(ValueError, match="invalid for v2 migration"):
        user_profiles.migrate_v1_user_to_v2(
            db, user_id="u", birth_date=date(2000, 1, 1),
        )


# ─────────────────────────────────────────────
#  get_profile
# ─────────────────────────────────────────────

def test_get_profile_returns_dict():
    db = _fake_db()
    row = MagicMock()
    row.user_id = "u1"
    row.gender = "female"
    row.birth_date = date(1999, 3, 15)
    row.ig_handle = "@yuni"
    row.ig_feed_cache = {"scope": "full"}
    row.ig_fetch_status = "success"
    row.ig_fetched_at = datetime(2026, 4, 23, tzinfo=timezone.utc)
    row.structured_fields = {"desired_image": "뮤트"}
    row.onboarding_completed = True
    row.created_at = datetime(2026, 4, 20, tzinfo=timezone.utc)
    row.updated_at = datetime(2026, 4, 23, tzinfo=timezone.utc)
    result = MagicMock()
    result.first.return_value = row
    db.execute.return_value = result

    profile = user_profiles.get_profile(db, "u1")
    assert profile is not None
    assert profile["gender"] == "female"
    assert profile["structured_fields"] == {"desired_image": "뮤트"}
    assert profile["onboarding_completed"] is True


def test_get_profile_returns_none_when_missing():
    db = _fake_db()
    result = MagicMock()
    result.first.return_value = None
    db.execute.return_value = result
    assert user_profiles.get_profile(db, "ghost") is None


def test_require_profile_raises_when_missing():
    db = _fake_db()
    result = MagicMock()
    result.first.return_value = None
    db.execute.return_value = result
    with pytest.raises(UserProfileNotFoundError):
        user_profiles.require_profile(db, "ghost")


# ─────────────────────────────────────────────
#  IG cache upsert + refresh
# ─────────────────────────────────────────────

def _sample_ig_cache():
    return IgFeedCache(
        scope="full",
        profile_basics=IgFeedProfileBasics(username="yuni"),
        feed_highlights=["a"],
        fetched_at=datetime.now(timezone.utc),
    )


def test_upsert_ig_feed_cache_with_payload():
    db = _fake_db()
    cache = _sample_ig_cache()
    user_profiles.upsert_ig_feed_cache(
        db, user_id="u1", cache=cache, status="success",
    )
    assert db.execute.call_count == 1
    sql = _exec_calls_sql(db)[0]
    assert "ig_feed_cache = CAST(:cache AS jsonb)" in sql
    assert "ig_fetched_at = NOW()" in sql

    params = db.execute.call_args_list[0].args[1]
    assert params["status"] == "success"
    # JSON 직렬화된 문자열인지 확인
    loaded = json.loads(params["cache"])
    assert loaded["scope"] == "full"


def test_upsert_ig_feed_cache_with_null_cache():
    """failed/skipped 시 cache=None. fetched_at 은 NULL 로 세팅."""
    db = _fake_db()
    user_profiles.upsert_ig_feed_cache(
        db, user_id="u1", cache=None, status="failed",
    )
    sql = _exec_calls_sql(db)[0]
    assert "ig_fetched_at = NULL" in sql
    params = db.execute.call_args_list[0].args[1]
    assert params["cache"] is None


# ─────────────────────────────────────────────
#  structured_fields shallow merge
# ─────────────────────────────────────────────

def test_merge_structured_fields_shallow_merge_excludes_none():
    db = _fake_db()
    fields = StructuredFields(
        desired_image="정돈된 뮤트",
        height="165_170",
        reference_style=None,   # None 은 payload 에서 제외돼야
    )
    user_profiles.merge_structured_fields(db, user_id="u1", fields=fields)
    assert db.execute.call_count == 1
    sql = _exec_calls_sql(db)[0]
    assert "COALESCE(structured_fields, '{}'::jsonb) || CAST(:patch AS jsonb)" in sql
    params = db.execute.call_args_list[0].args[1]
    payload = json.loads(params["patch"])
    assert payload == {"desired_image": "정돈된 뮤트", "height": "165_170"}
    assert "reference_style" not in payload


def test_merge_structured_fields_noop_when_empty():
    db = _fake_db()
    user_profiles.merge_structured_fields(db, user_id="u1", fields=StructuredFields())
    assert db.execute.call_count == 0   # noop


# ─────────────────────────────────────────────
#  restart_conversation + mark_onboarding_completed
# ─────────────────────────────────────────────

def test_restart_conversation_clears_structured_fields():
    db = _fake_db()
    user_profiles.restart_conversation(db, "u1")
    sql = _exec_calls_sql(db)[0]
    assert "structured_fields = '{}'::jsonb" in sql
    assert "onboarding_completed = FALSE" in sql


def test_mark_onboarding_completed_flips_flag():
    db = _fake_db()
    user_profiles.mark_onboarding_completed(db, "u1")
    sql = _exec_calls_sql(db)[0]
    assert "onboarding_completed = TRUE" in sql


# ─────────────────────────────────────────────
#  refresh_ig_feed
# ─────────────────────────────────────────────

def _mock_profile_row(ig_handle="@yuni", ig_fetched_at=None):
    row = MagicMock()
    row.user_id = "u1"
    row.gender = "female"
    row.birth_date = date(1999, 3, 15)
    row.ig_handle = ig_handle
    row.ig_feed_cache = None
    row.ig_fetch_status = None
    row.ig_fetched_at = ig_fetched_at
    row.structured_fields = {}
    row.onboarding_completed = False
    row.created_at = datetime(2026, 4, 20, tzinfo=timezone.utc)
    row.updated_at = datetime(2026, 4, 20, tzinfo=timezone.utc)
    result = MagicMock()
    result.first.return_value = row
    return result


def test_refresh_ig_feed_not_stale_skipped(monkeypatch):
    """STEP 2 이후: should_refresh_ig_snapshot False → fetch skip.

    기존 14-day is_stale 대신 24h ig_last_snapshot_at 기준으로 전환됨.
    """
    db = _fake_db()
    recent = datetime.now(timezone.utc) - timedelta(days=3)
    db.execute.return_value = _mock_profile_row(ig_fetched_at=recent)

    # STEP 2 새 캐시 판정 — 24h 내 이므로 skip
    monkeypatch.setattr(user_profiles, "should_refresh_ig_snapshot",
                        lambda db, uid: False)

    called = []
    monkeypatch.setattr(
        user_profiles, "fetch_ig_profile",
        lambda *a, **kw: called.append(1) or ("success", None),
    )

    status = user_profiles.refresh_ig_feed(db, "u1", force=False)
    assert status == "skipped"
    assert called == []   # fetch_ig_profile 호출 X


def test_refresh_ig_feed_stale_triggers_fetch(monkeypatch):
    db = _fake_db()
    old = datetime.now(timezone.utc) - timedelta(days=30)
    # 1st call: SELECT profile, 2nd call: UPDATE ig_feed_cache, 3rd: mark_snapshot_taken
    db.execute.side_effect = [
        _mock_profile_row(ig_fetched_at=old),
        MagicMock(),
        MagicMock(),
    ]
    # STEP 2 — 24h 초과 → refresh
    monkeypatch.setattr(user_profiles, "should_refresh_ig_snapshot",
                        lambda db, uid: True)
    cache = _sample_ig_cache()
    monkeypatch.setattr(
        user_profiles, "fetch_ig_profile",
        lambda h: ("success", cache),
    )
    # R2 materialization 우회 — dev 환경에서 R2 local fallback 이면 OK 이지만 단순화
    monkeypatch.setattr(user_profiles, "materialize_snapshot_to_r2",
                        lambda cache, *, user_id: cache)
    status = user_profiles.refresh_ig_feed(db, "u1", force=False)
    assert status == "success"


def test_refresh_ig_feed_force_triggers_fetch_even_if_fresh(monkeypatch):
    db = _fake_db()
    recent = datetime.now(timezone.utc) - timedelta(hours=1)
    db.execute.side_effect = [
        _mock_profile_row(ig_fetched_at=recent),
        MagicMock(),
    ]
    cache = _sample_ig_cache()
    monkeypatch.setattr(
        user_profiles, "fetch_ig_profile",
        lambda h: ("success", cache),
    )
    status = user_profiles.refresh_ig_feed(db, "u1", force=True)
    assert status == "success"
