"""Vault completion 검증 — CLAUDE.md §4.2 spec 이행.

목표:
  1. basic_info.name 이 users 테이블에서 join 됨
  2. user_history JSONB 가 UserHistory 로 파싱되어 vault 에 노출
  3. feed_snapshots / aspiration_history / best_shot_history / verdict_history
     properties 가 올바르게 derived
  4. UserTasteProfile.aspiration_vector 가 최신 aspiration_analyses 에서 산출
  5. preference_evidence 에 IG feed + Best Shot selected 모두 포함
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from schemas.user_history import (
    AspirationHistoryEntry,
    BestShotHistoryEntry,
    ConversationHistoryEntry,
    HistoryIgSnapshot,
    HistoryPhotoPair,
    HistorySelectedPhoto,
    UserHistory,
    VerdictHistoryEntry,
)
from services import user_data_vault as vault_mod


# ─────────────────────────────────────────────
#  Fake DB — SELECT 분기별 응답
# ─────────────────────────────────────────────

class _Row:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _FakeDb:
    """쿼리 문자열 분기로 응답 선택."""

    def __init__(
        self,
        *,
        name: str | None = None,
        user_history: dict | None = None,
        aspiration_result: dict | None = None,
    ):
        self._name = name
        self._user_history = user_history
        self._aspiration_result = aspiration_result
        self._last_query = None

    def execute(self, stmt, params=None):
        self._last_query = str(stmt)
        return self

    def first(self):
        q = (self._last_query or "").lower()
        if "select name from users" in q:
            if self._name is None:
                return None
            return _Row(name=self._name)
        if "select user_history from users" in q:
            return _Row(user_history=self._user_history)
        if "select result_data from aspiration_analyses" in q:
            if self._aspiration_result is None:
                return None
            return _Row(result_data=self._aspiration_result)
        return None

    def scalar(self):
        return 0


# ─────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────

def _profile(
    *,
    gender: str = "female",
    structured_fields: dict | None = None,
    ig_feed_cache: dict | None = None,
) -> dict:
    return {
        "gender": gender,
        "birth_date": None,
        "ig_handle": "me_handle",
        "ig_feed_cache": ig_feed_cache,
        "structured_fields": structured_fields or {},
    }


def _sample_user_history_dict() -> dict:
    """JSONB 에 저장된 모습의 user_history — 4 카테고리 각 1건."""
    return {
        "conversations": [
            {
                "session_id": "sia_s1",
                "started_at": "2026-04-24T10:00:00+00:00",
                "ended_at": "2026-04-24T10:05:00+00:00",
                "messages": [
                    {"role": "assistant", "content": "안녕하세요", "msg_type": "opening"},
                    {"role": "user", "content": "네"},
                ],
                "ig_snapshot": {
                    "r2_dir": "user_media/u1/ig_snapshots/20260424/",
                    "photo_r2_urls": [
                        "https://cdn.sigak.kr/.../photo_01.jpg",
                    ],
                    "analysis": {"tone_category": "쿨뮤트"},
                },
            }
        ],
        "best_shot_sessions": [
            {
                "session_id": "bs_s1",
                "created_at": "2026-04-23T12:00:00+00:00",
                "uploaded_count": 150,
                "uploaded_r2_dir": "users/u1/best_shot/uploads/bs_s1/",
                "selected": [
                    {
                        "r2_url": "https://cdn.sigak.kr/.../bs/photo_01.jpg",
                        "sonnet_rationale": "구도 안정",
                        "sia_comment": "눈빛이 살아있어요",
                    },
                    {
                        "r2_url": "https://cdn.sigak.kr/.../bs/photo_02.jpg",
                        "sonnet_rationale": None,
                        "sia_comment": None,
                    },
                ],
                "overall_message": "차분한 톤",
            }
        ],
        "aspiration_analyses": [
            {
                "analysis_id": "asp_1",
                "created_at": "2026-04-22T15:00:00+00:00",
                "source": "instagram",
                "target_handle": "@yuni",
                "photo_pairs": [
                    {
                        "user_photo_r2_url": "https://.../u.jpg",
                        "target_photo_r2_url": "https://.../t.jpg",
                        "pair_comment": "실루엣 차이",
                    }
                ],
                "gap_narrative": "샤프한 방향",
                "sia_overall_message": "정돈 방향",
                "target_analysis_snapshot": None,
            }
        ],
        "verdict_sessions": [
            {
                "session_id": "vd_1",
                "created_at": "2026-04-21T09:00:00+00:00",
                "photos_r2_urls": [
                    "https://.../v1.jpg",
                    "https://.../v2.jpg",
                ],
                "photo_insights": [{"photo_index": 0, "insight": "좋음"}],
                "recommendation": {"overall": "keep"},
            }
        ],
    }


def _sample_gap_vector_dict() -> dict:
    return {
        "primary_axis": "shape",
        "primary_delta": 0.25,
        "secondary_axis": "volume",
        "secondary_delta": 0.10,
        "tertiary_axis": "age",
        "tertiary_delta": -0.05,
    }


# ─────────────────────────────────────────────
#  users.name join
# ─────────────────────────────────────────────

def test_basic_info_name_populated_from_users_table(monkeypatch):
    profile = _profile()
    db = _FakeDb(name="정세현")
    monkeypatch.setattr(vault_mod, "get_profile", lambda d, u: profile)
    monkeypatch.setattr(vault_mod, "_fetch_product_counts", lambda d, u: {})

    vault = vault_mod.load_vault(db, "u1")
    assert vault is not None
    assert vault.basic_info.name == "정세현"


def test_basic_info_name_none_when_users_row_missing(monkeypatch):
    profile = _profile()
    db = _FakeDb(name=None)   # fake returns None
    monkeypatch.setattr(vault_mod, "get_profile", lambda d, u: profile)
    monkeypatch.setattr(vault_mod, "_fetch_product_counts", lambda d, u: {})

    vault = vault_mod.load_vault(db, "u1")
    assert vault is not None
    assert vault.basic_info.name is None


def test_basic_info_name_none_when_whitespace(monkeypatch):
    profile = _profile()
    db = _FakeDb(name="   ")
    monkeypatch.setattr(vault_mod, "get_profile", lambda d, u: profile)
    monkeypatch.setattr(vault_mod, "_fetch_product_counts", lambda d, u: {})

    vault = vault_mod.load_vault(db, "u1")
    assert vault.basic_info.name is None


# ─────────────────────────────────────────────
#  user_history hydration
# ─────────────────────────────────────────────

def test_user_history_hydrated_from_jsonb(monkeypatch):
    profile = _profile()
    db = _FakeDb(user_history=_sample_user_history_dict())
    monkeypatch.setattr(vault_mod, "get_profile", lambda d, u: profile)
    monkeypatch.setattr(vault_mod, "_fetch_product_counts", lambda d, u: {})

    vault = vault_mod.load_vault(db, "u1")
    assert vault is not None

    uh = vault.user_history
    assert isinstance(uh, UserHistory)
    assert len(uh.conversations) == 1
    assert uh.conversations[0].session_id == "sia_s1"
    assert len(uh.best_shot_sessions) == 1
    assert len(uh.aspiration_analyses) == 1
    assert len(uh.verdict_sessions) == 1


def test_user_history_empty_when_column_missing(monkeypatch):
    """마이그레이션 미적용 환경 — user_history 컬럼 자체가 없음."""
    class _DbColumnMissing:
        def execute(self, stmt, params=None):
            raise Exception("column 'user_history' does not exist")

    profile = _profile()
    monkeypatch.setattr(vault_mod, "get_profile", lambda d, u: profile)
    monkeypatch.setattr(vault_mod, "_fetch_product_counts", lambda d, u: {})

    vault = vault_mod.load_vault(_DbColumnMissing(), "u1")
    assert vault is not None
    assert isinstance(vault.user_history, UserHistory)
    assert vault.user_history.conversations == []
    assert vault.basic_info.name is None   # name 조회도 실패 흡수


def test_user_history_empty_when_jsonb_is_malformed(monkeypatch):
    """JSONB 가 list 로 저장되는 등 파싱 실패 시 빈 UserHistory 반환."""
    class _DbWithBadHistory:
        def __init__(self):
            self._last = None

        def execute(self, stmt, params=None):
            self._last = str(stmt).lower()
            return self

        def first(self):
            if "user_history" in self._last:
                return _Row(user_history=[1, 2, 3])   # list 타입 — 예상 dict
            return None

        def scalar(self):
            return 0

    profile = _profile()
    monkeypatch.setattr(vault_mod, "get_profile", lambda d, u: profile)
    monkeypatch.setattr(vault_mod, "_fetch_product_counts", lambda d, u: {})

    vault = vault_mod.load_vault(_DbWithBadHistory(), "u1")
    assert vault is not None
    assert vault.user_history.conversations == []


# ─────────────────────────────────────────────
#  Derived list properties
# ─────────────────────────────────────────────

def test_derived_history_properties(monkeypatch):
    profile = _profile()
    db = _FakeDb(user_history=_sample_user_history_dict())
    monkeypatch.setattr(vault_mod, "get_profile", lambda d, u: profile)
    monkeypatch.setattr(vault_mod, "_fetch_product_counts", lambda d, u: {})

    vault = vault_mod.load_vault(db, "u1")
    assert vault is not None

    # 4 properties
    assert len(vault.feed_snapshots) == 1
    assert vault.feed_snapshots[0].r2_dir.startswith("user_media/u1/")

    assert len(vault.aspiration_history) == 1
    assert vault.aspiration_history[0].target_handle == "@yuni"

    assert len(vault.best_shot_history) == 1
    assert vault.best_shot_history[0].uploaded_count == 150

    assert len(vault.verdict_history) == 1
    assert vault.verdict_history[0].session_id == "vd_1"

    assert len(vault.conversation_history) == 1


def test_feed_snapshots_skips_conversations_without_ig_snapshot(monkeypatch):
    uh = {
        "conversations": [
            {"session_id": "s1", "messages": [], "ig_snapshot": None},
            {
                "session_id": "s2",
                "messages": [],
                "ig_snapshot": {
                    "r2_dir": "user_media/u1/ig_snapshots/t/",
                    "photo_r2_urls": [],
                    "analysis": None,
                },
            },
        ],
    }
    profile = _profile()
    db = _FakeDb(user_history=uh)
    monkeypatch.setattr(vault_mod, "get_profile", lambda d, u: profile)
    monkeypatch.setattr(vault_mod, "_fetch_product_counts", lambda d, u: {})

    vault = vault_mod.load_vault(db, "u1")
    # 2 conversations 중 1 만 ig_snapshot 있음
    assert len(vault.feed_snapshots) == 1


# ─────────────────────────────────────────────
#  aspiration_vector population
# ─────────────────────────────────────────────

def test_aspiration_vector_populated_from_latest_analysis(monkeypatch):
    profile = _profile()
    db = _FakeDb(
        user_history=_sample_user_history_dict(),
        aspiration_result={
            "analysis_id": "asp_1",
            "gap_vector": _sample_gap_vector_dict(),
        },
    )
    monkeypatch.setattr(vault_mod, "get_profile", lambda d, u: profile)
    monkeypatch.setattr(vault_mod, "_fetch_product_counts", lambda d, u: {})

    vault = vault_mod.load_vault(db, "u1")
    assert vault is not None
    assert vault.latest_aspiration_gap is not None
    assert vault.latest_aspiration_gap.primary_axis == "shape"
    assert vault.latest_aspiration_gap.primary_delta == pytest.approx(0.25)

    # UserTasteProfile 에 propagate
    tp = vault.get_user_taste_profile()
    assert tp.aspiration_vector is not None
    assert tp.aspiration_vector.primary_axis == "shape"


def test_aspiration_vector_none_when_no_analysis_row(monkeypatch):
    profile = _profile()
    db = _FakeDb(aspiration_result=None)
    monkeypatch.setattr(vault_mod, "get_profile", lambda d, u: profile)
    monkeypatch.setattr(vault_mod, "_fetch_product_counts", lambda d, u: {})

    vault = vault_mod.load_vault(db, "u1")
    assert vault.latest_aspiration_gap is None
    tp = vault.get_user_taste_profile()
    assert tp.aspiration_vector is None


def test_aspiration_vector_none_when_gap_missing_from_result(monkeypatch):
    """result_data 는 있지만 gap_vector 키 없음 — 예외 없이 None."""
    profile = _profile()
    db = _FakeDb(aspiration_result={"analysis_id": "asp_1"})   # no gap_vector
    monkeypatch.setattr(vault_mod, "get_profile", lambda d, u: profile)
    monkeypatch.setattr(vault_mod, "_fetch_product_counts", lambda d, u: {})

    vault = vault_mod.load_vault(db, "u1")
    assert vault.latest_aspiration_gap is None


# ─────────────────────────────────────────────
#  preference_evidence 확장 (Best Shot 포함)
# ─────────────────────────────────────────────

def test_preference_evidence_includes_best_shot_selected(monkeypatch):
    ig_cache = {
        "latest_posts": [
            {
                "display_url": "https://cdn/.../feed_01.jpg",
                "timestamp": "2026-04-20T00:00:00Z",
                "caption": "a",
            },
            {
                "display_url": "https://cdn/.../feed_02.jpg",
                "timestamp": "2026-04-19T00:00:00Z",
                "caption": "b",
            },
        ],
    }
    profile = _profile(ig_feed_cache=ig_cache)
    db = _FakeDb(user_history=_sample_user_history_dict())
    monkeypatch.setattr(vault_mod, "get_profile", lambda d, u: profile)
    monkeypatch.setattr(vault_mod, "_fetch_product_counts", lambda d, u: {})

    vault = vault_mod.load_vault(db, "u1")
    tp = vault.get_user_taste_profile()

    # IG feed 2 + Best Shot 2
    sources = [r.source for r in tp.preference_evidence]
    assert sources.count("ig_feed") == 2
    assert sources.count("best_shot_upload") == 2

    bs_refs = [r for r in tp.preference_evidence if r.source == "best_shot_upload"]
    assert bs_refs[0].sia_comment == "눈빛이 살아있어요"
    assert bs_refs[0].stored_url.endswith("photo_01.jpg")


def test_preference_evidence_ig_only_when_no_best_shot(monkeypatch):
    ig_cache = {
        "latest_posts": [
            {"display_url": "https://cdn/feed.jpg", "timestamp": None, "caption": ""},
        ],
    }
    profile = _profile(ig_feed_cache=ig_cache)
    db = _FakeDb(user_history={"best_shot_sessions": []})
    monkeypatch.setattr(vault_mod, "get_profile", lambda d, u: profile)
    monkeypatch.setattr(vault_mod, "_fetch_product_counts", lambda d, u: {})

    vault = vault_mod.load_vault(db, "u1")
    tp = vault.get_user_taste_profile()
    sources = [r.source for r in tp.preference_evidence]
    assert sources == ["ig_feed"]


# ─────────────────────────────────────────────
#  기존 동작 regression
# ─────────────────────────────────────────────

def test_empty_vault_still_builds(monkeypatch):
    """user_history / ig_feed_cache / aspiration 전부 없음 → vault 조립 여전히 성공."""
    profile = _profile()
    db = _FakeDb()
    monkeypatch.setattr(vault_mod, "get_profile", lambda d, u: profile)
    monkeypatch.setattr(vault_mod, "_fetch_product_counts", lambda d, u: {})

    vault = vault_mod.load_vault(db, "u1")
    assert vault is not None
    tp = vault.get_user_taste_profile()
    assert tp.current_position is None
    assert tp.aspiration_vector is None
    assert tp.preference_evidence == []
    assert tp.strength_score == 0.0
