"""STEP 4 검증 — user_history append helper + 4 기능 훅 호출 가능성.

범위:
  1. append_history — prepend + trim
  2. append_history — 실패 경로 (column 없음, user 없음, 직렬화 실패)
  3. 각 entry 스키마 round-trip

실제 route hook 전체 호출은 통합 테스트 대상 — 여기서는 헬퍼 + 스키마만.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schemas.user_history import (
    AspirationHistoryEntry,
    BestShotHistoryEntry,
    ConversationHistoryEntry,
    HistoryIgSnapshot,
    HistoryMessage,
    HistoryPhotoPair,
    HistorySelectedPhoto,
    UserHistory,
    VerdictHistoryEntry,
)
from services.user_history import append_history


@pytest.fixture(autouse=True)
def _reset_settings():
    import config as config_module
    config_module._settings = None
    yield
    config_module._settings = None


# ─────────────────────────────────────────────
#  DB stub — SELECT FOR UPDATE + UPDATE 만 처리
# ─────────────────────────────────────────────

class _StubExecResult:
    def __init__(self, row):
        self._row = row
    def first(self):
        return self._row


class _StubRow:
    def __init__(self, user_history):
        self.user_history = user_history


class _StubDB:
    def __init__(self, initial_history=None, raise_on_select=False, raise_on_update=False):
        self.history = initial_history if initial_history is not None else {}
        self.raise_on_select = raise_on_select
        self.raise_on_update = raise_on_update
        self.updates: list[tuple[str, dict]] = []

    def execute(self, stmt, params=None):
        sql = str(stmt)
        if "SELECT user_history" in sql:
            if self.raise_on_select:
                raise RuntimeError("column does not exist")
            return _StubExecResult(_StubRow(self.history))
        if "UPDATE users" in sql:
            if self.raise_on_update:
                raise RuntimeError("write failed")
            self.updates.append((sql, params))
            new_h = json.loads(params["h"])
            self.history = new_h
            return _StubExecResult(None)
        return _StubExecResult(None)


# ─────────────────────────────────────────────
#  append_history — happy path
# ─────────────────────────────────────────────

def test_append_history_prepend_to_empty():
    db = _StubDB(initial_history={})
    entry = AspirationHistoryEntry(
        analysis_id="asp_1",
        created_at=datetime.now(timezone.utc),
        source="instagram",
        target_handle="yuni",
        gap_narrative="테스트 갭",
    )
    ok = append_history(db, user_id="u1", category="aspiration_analyses", entry=entry)
    assert ok is True
    assert db.history["aspiration_analyses"][0]["analysis_id"] == "asp_1"
    assert len(db.history["aspiration_analyses"]) == 1


def test_append_history_prepend_to_existing():
    existing = [{"analysis_id": "asp_OLD", "source": "instagram"}]
    db = _StubDB(initial_history={"aspiration_analyses": existing})
    entry = AspirationHistoryEntry(
        analysis_id="asp_NEW",
        created_at=datetime.now(timezone.utc),
        source="instagram",
    )
    append_history(db, user_id="u1", category="aspiration_analyses", entry=entry)
    assert db.history["aspiration_analyses"][0]["analysis_id"] == "asp_NEW"
    assert db.history["aspiration_analyses"][1]["analysis_id"] == "asp_OLD"


def test_append_history_truncates_to_max(monkeypatch):
    """max=10 초과 시 tail pop."""
    import config as config_module
    config_module._settings = config_module.Settings(user_history_max_per_type=3)

    existing = [{"session_id": f"old_{i}"} for i in range(5)]
    db = _StubDB(initial_history={"conversations": existing})
    entry = ConversationHistoryEntry(session_id="new_1")
    append_history(db, user_id="u1", category="conversations", entry=entry)

    convs = db.history["conversations"]
    assert len(convs) == 3
    assert convs[0]["session_id"] == "new_1"
    assert convs[1]["session_id"] == "old_0"
    assert convs[2]["session_id"] == "old_1"


def test_append_history_preserves_other_categories():
    """다른 category 는 건드리지 않음."""
    existing = {
        "conversations": [{"session_id": "conv_1"}],
        "best_shot_sessions": [{"session_id": "bs_1"}],
    }
    db = _StubDB(initial_history=existing)
    entry = AspirationHistoryEntry(analysis_id="asp_X", source="instagram")
    append_history(db, user_id="u1", category="aspiration_analyses", entry=entry)
    assert db.history["conversations"] == [{"session_id": "conv_1"}]
    assert db.history["best_shot_sessions"] == [{"session_id": "bs_1"}]
    assert len(db.history["aspiration_analyses"]) == 1


# ─────────────────────────────────────────────
#  append_history — 실패 경로
# ─────────────────────────────────────────────

def test_append_history_column_missing_returns_false():
    db = _StubDB(raise_on_select=True)
    entry = AspirationHistoryEntry(analysis_id="x", source="instagram")
    ok = append_history(db, user_id="u1", category="aspiration_analyses", entry=entry)
    assert ok is False


def test_append_history_user_not_found_returns_false():
    class _NullDB:
        def execute(self, stmt, params=None):
            return _StubExecResult(None)
    db = _NullDB()
    entry = AspirationHistoryEntry(analysis_id="x", source="instagram")
    ok = append_history(db, user_id="ghost", category="aspiration_analyses", entry=entry)
    assert ok is False


def test_append_history_update_failure_returns_false():
    db = _StubDB(initial_history={}, raise_on_update=True)
    entry = AspirationHistoryEntry(analysis_id="x", source="instagram")
    ok = append_history(db, user_id="u1", category="aspiration_analyses", entry=entry)
    assert ok is False


# ─────────────────────────────────────────────
#  Entry 스키마 round-trip (4 카테고리)
# ─────────────────────────────────────────────

def test_conversation_entry_with_ig_snapshot_roundtrip():
    entry = ConversationHistoryEntry(
        session_id="sia_123",
        started_at=datetime.now(timezone.utc),
        ended_at=datetime.now(timezone.utc),
        messages=[
            HistoryMessage(role="user", content="안녕"),
            HistoryMessage(role="assistant", content="결이 차분하신가봐요"),
        ],
        ig_snapshot=HistoryIgSnapshot(
            r2_dir="user_media/u1/ig_snapshots/20260424T000000Z/",
            photo_r2_urls=["https://r2/1.jpg", "https://r2/2.jpg"],
            analysis={"tone_category": "쿨뮤트"},
        ),
    )
    d = entry.model_dump(mode="json")
    assert d["session_id"] == "sia_123"
    assert len(d["messages"]) == 2
    assert d["ig_snapshot"]["r2_dir"].startswith("user_media/")


def test_best_shot_entry_roundtrip():
    entry = BestShotHistoryEntry(
        session_id="bs_x",
        created_at=datetime.now(timezone.utc),
        uploaded_count=100,
        uploaded_r2_dir="users/u1/best_shot/uploads/bs_x/",
        selected=[
            HistorySelectedPhoto(r2_url="https://r2/a.jpg", sia_comment="또렷하네요"),
            HistorySelectedPhoto(r2_url="https://r2/b.jpg"),
        ],
        overall_message="정리 완료했어요",
    )
    d = entry.model_dump(mode="json")
    assert d["uploaded_count"] == 100
    assert len(d["selected"]) == 2


def test_aspiration_entry_roundtrip():
    entry = AspirationHistoryEntry(
        analysis_id="asp_z",
        created_at=datetime.now(timezone.utc),
        source="instagram",
        target_handle="yuni",
        photo_pairs=[
            HistoryPhotoPair(
                user_photo_r2_url="https://r2/u.jpg",
                target_photo_r2_url="https://r2/t.jpg",
                pair_comment="결 다른 쪽이시잖아요",
            ),
        ],
        gap_narrative="형태 쪽 이동",
        sia_overall_message="종합",
        target_analysis_snapshot={"tone_category": "쿨뮤트"},
    )
    d = entry.model_dump(mode="json")
    assert d["source"] == "instagram"
    assert d["photo_pairs"][0]["user_photo_r2_url"].endswith("u.jpg")


def test_verdict_entry_roundtrip():
    entry = VerdictHistoryEntry(
        session_id="verdict_v",
        created_at=datetime.now(timezone.utc),
        photos_r2_urls=["https://r2/v1.jpg", "https://r2/v2.jpg"],
        photo_insights=[{"photo_id": "p1", "rank": 1}],
        recommendation={"top_action": "자연스럽게 유지"},
    )
    d = entry.model_dump(mode="json")
    assert len(d["photos_r2_urls"]) == 2
    assert d["recommendation"]["top_action"] == "자연스럽게 유지"
