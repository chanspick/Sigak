"""STEP 1 검증 — user_history 스키마 / R2 key helper 소형 테스트.

마이그레이션 자체는 alembic upgrade 가 Railway 에서 실행하므로
여기서는 스키마 직렬화 + key 생성 로직만 검증.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from schemas.user_history import (
    HISTORY_MAX_ENTRIES,
    INJECT_HISTORY_TOKEN_LIMIT,
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
from services.r2_client import (
    aspiration_target_dir,
    aspiration_target_photo_key,
    ig_snapshot_dir,
    ig_snapshot_photo_key,
    user_media_key,
)


# ─────────────────────────────────────────────
#  Schema round-trip
# ─────────────────────────────────────────────

def test_user_history_default_empty_lists():
    uh = UserHistory()
    assert uh.conversations == []
    assert uh.best_shot_sessions == []
    assert uh.aspiration_analyses == []
    assert uh.verdict_sessions == []


def test_conversation_history_entry_roundtrip():
    entry = ConversationHistoryEntry(
        session_id="sia_abc",
        started_at=datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 4, 24, 12, 5, tzinfo=timezone.utc),
        messages=[
            HistoryMessage(role="assistant", content="안녕하세요", msg_type="opening"),
            HistoryMessage(role="user", content="네"),
        ],
        ig_snapshot=HistoryIgSnapshot(
            r2_dir="user_media/u1/ig_snapshots/20260424T120000/",
            photo_r2_urls=["https://cdn.sigak.kr/user_media/u1/ig_snapshots/20260424T120000/photo_01.jpg"],
            analysis={"tone_category": "soft"},
        ),
    )
    payload = entry.model_dump(mode="json")
    restored = ConversationHistoryEntry.model_validate(payload)
    assert restored.session_id == "sia_abc"
    assert restored.messages[0].msg_type == "opening"
    assert restored.ig_snapshot is not None
    assert len(restored.ig_snapshot.photo_r2_urls) == 1


def test_best_shot_history_entry_roundtrip():
    entry = BestShotHistoryEntry(
        session_id="bs_xyz",
        uploaded_count=150,
        uploaded_r2_dir="users/u1/best_shot/uploads/bs_xyz/",
        selected=[
            HistorySelectedPhoto(
                r2_url="https://cdn.sigak.kr/users/u1/best_shot/selected/bs_xyz/photo_01.jpg",
                sonnet_rationale="구도 안정",
                sia_comment="눈빛이 살아있어요",
            )
        ],
        overall_message="전반적으로 차분한 톤",
    )
    payload = entry.model_dump(mode="json")
    restored = BestShotHistoryEntry.model_validate(payload)
    assert restored.uploaded_count == 150
    assert restored.selected[0].sonnet_rationale == "구도 안정"


def test_aspiration_history_entry_pairs():
    entry = AspirationHistoryEntry(
        analysis_id="asp_1",
        target_handle="@yuni",
        photo_pairs=[
            HistoryPhotoPair(
                user_photo_r2_url="https://.../user.jpg",
                target_photo_r2_url="https://.../target.jpg",
                pair_comment="실루엣 차이",
            ),
        ],
        gap_narrative="샤프한 방향",
        source="instagram",
    )
    assert entry.source == "instagram"
    assert len(entry.photo_pairs) == 1


def test_verdict_history_entry():
    entry = VerdictHistoryEntry(
        session_id="vd_1",
        photos_r2_urls=["https://.../1.jpg", "https://.../2.jpg"],
        photo_insights=[{"photo_index": 0, "comment": "좋음"}],
        recommendation={"overall": "keep"},
    )
    assert len(entry.photos_r2_urls) == 2


def test_history_max_entries_constant():
    assert HISTORY_MAX_ENTRIES == 10
    assert INJECT_HISTORY_TOKEN_LIMIT == 80_000


# ─────────────────────────────────────────────
#  R2 key helpers
# ─────────────────────────────────────────────

def test_user_media_key_prefix():
    assert user_media_key("u1", "foo/bar.jpg") == "user_media/u1/foo/bar.jpg"
    # leading slash 제거 확인
    assert user_media_key("u1", "/foo/bar.jpg") == "user_media/u1/foo/bar.jpg"


def test_ig_snapshot_keys():
    ts = "20260424T120000"
    assert ig_snapshot_dir("u1", ts) == "user_media/u1/ig_snapshots/20260424T120000/"
    assert (
        ig_snapshot_photo_key("u1", ts, 1)
        == "user_media/u1/ig_snapshots/20260424T120000/photo_01.jpg"
    )
    # zero-pad 2자리
    assert ig_snapshot_photo_key("u1", ts, 10).endswith("photo_10.jpg")


def test_aspiration_target_keys():
    assert (
        aspiration_target_dir("u1", "asp_1")
        == "user_media/u1/aspiration_targets/asp_1/"
    )
    assert (
        aspiration_target_photo_key("u1", "asp_1", 5)
        == "user_media/u1/aspiration_targets/asp_1/photo_05.jpg"
    )
