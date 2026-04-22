"""conversations CRUD + lifecycle tests (v2 Priority 1 D2).

D2 계약 #3 검증:
  - create_ended_conversation: Redis → DB INSERT (status="ended")
  - mark_extracted: UPDATE status="extracted" + user_profiles merge + completion
  - mark_failed: UPDATE status="failed"

DB 는 mock. 실제 lifecycle 은 D3 route + D6~7 통합 테스트에서.
"""
import sys
import os
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schemas.user_profile import (
    ConversationMessage,
    ExtractionResult,
    StructuredFields,
)
from services import conversations
from services.conversations import ConversationNotFoundError


def _fake_db():
    db = MagicMock()
    return db


def _sample_messages(n: int = 3) -> list[ConversationMessage]:
    base = datetime(2026, 4, 22, 10, 0, 0, tzinfo=timezone.utc)
    out = []
    for i in range(n):
        out.append(ConversationMessage(
            role="user" if i % 2 == 0 else "assistant",
            content=f"message {i}",
            ts=base,
        ))
    return out


# ─────────────────────────────────────────────
#  create_ended_conversation
# ─────────────────────────────────────────────

def test_create_ended_conversation_inserts_with_status_ended():
    db = _fake_db()
    msgs = _sample_messages(3)
    conversations.create_ended_conversation(
        db,
        user_id="u1",
        conversation_id="conv-abc",
        messages=msgs,
        turn_count=2,
    )
    assert db.execute.call_count == 1
    sql = str(db.execute.call_args.args[0]).replace("\n", " ")
    assert "INSERT INTO conversations" in sql
    # 2026-04-22: status 는 바인딩 파라미터로 변경. default="ended" 검증.
    assert ":status" in sql
    params = db.execute.call_args.args[1]
    assert params["status"] == "ended"
    assert params["cid"] == "conv-abc"
    assert params["uid"] == "u1"
    assert params["tc"] == 2
    # messages 는 JSON 직렬화
    loaded = json.loads(params["msgs"])
    assert len(loaded) == 3
    assert loaded[0]["role"] == "user"


def test_create_ended_conversation_with_started_at_iso():
    db = _fake_db()
    conversations.create_ended_conversation(
        db,
        user_id="u1",
        conversation_id="conv-xyz",
        messages=_sample_messages(1),
        turn_count=1,
        started_at_iso="2026-04-22T10:00:00+00:00",
    )
    sql = str(db.execute.call_args.args[0]).replace("\n", " ")
    assert ":sa" in sql   # started_at 바인딩 변수 포함 경로
    params = db.execute.call_args.args[1]
    assert params["sa"] == "2026-04-22T10:00:00+00:00"


def test_create_ended_conversation_empty_messages_allowed():
    """대화 0 턴 (즉시 abandon) 도 INSERT 가능 — 운영 로그 보존용."""
    db = _fake_db()
    conversations.create_ended_conversation(
        db,
        user_id="u1",
        conversation_id="conv-empty",
        messages=[],
        turn_count=0,
    )
    params = db.execute.call_args.args[1]
    assert json.loads(params["msgs"]) == []


# ─────────────────────────────────────────────
#  mark_extracted
# ─────────────────────────────────────────────

def _mock_rowcount_result(count: int):
    r = MagicMock()
    r.rowcount = count
    return r


def test_mark_extracted_updates_status_and_merges(monkeypatch):
    db = _fake_db()
    db.execute.return_value = _mock_rowcount_result(1)

    merge_calls = []
    complete_calls = []
    monkeypatch.setattr(
        conversations, "merge_structured_fields",
        lambda db, user_id, fields: merge_calls.append((user_id, fields)),
    )
    monkeypatch.setattr(
        conversations, "mark_onboarding_completed",
        lambda db, user_id: complete_calls.append(user_id),
    )

    result = ExtractionResult(
        fields=StructuredFields(desired_image="뮤트", height="165_170"),
        fallback_needed=[],
    )
    conversations.mark_extracted(
        db,
        conversation_id="conv-1",
        user_id="u1",
        result=result,
    )
    # conversations UPDATE
    sql = str(db.execute.call_args.args[0]).replace("\n", " ")
    assert "UPDATE conversations" in sql
    assert "'extracted'" in sql
    params = db.execute.call_args.args[1]
    assert params["cid"] == "conv-1"
    # payload 는 JSON 직렬화
    loaded = json.loads(params["payload"])
    assert loaded["fields"]["desired_image"] == "뮤트"

    # downstream 호출 검증 (contract #3: merge + completion 순서)
    assert merge_calls == [("u1", result.fields)]
    assert complete_calls == ["u1"]


def test_mark_extracted_raises_when_conversation_missing():
    db = _fake_db()
    db.execute.return_value = _mock_rowcount_result(0)   # affected=0

    with pytest.raises(ConversationNotFoundError):
        conversations.mark_extracted(
            db,
            conversation_id="ghost",
            user_id="u1",
            result=ExtractionResult(fields=StructuredFields()),
        )


# ─────────────────────────────────────────────
#  mark_failed
# ─────────────────────────────────────────────

def test_mark_failed_updates_status():
    db = _fake_db()
    db.execute.return_value = _mock_rowcount_result(1)
    conversations.mark_failed(db, conversation_id="conv-1", reason="Sonnet timeout")
    sql = str(db.execute.call_args.args[0]).replace("\n", " ")
    assert "UPDATE conversations SET status = 'failed'" in sql


def test_mark_failed_raises_when_conversation_missing():
    db = _fake_db()
    db.execute.return_value = _mock_rowcount_result(0)
    with pytest.raises(ConversationNotFoundError):
        conversations.mark_failed(db, conversation_id="ghost")


# ─────────────────────────────────────────────
#  get_conversation / list_user_conversations
# ─────────────────────────────────────────────

def test_get_conversation_returns_dict():
    db = _fake_db()
    row = MagicMock()
    row.conversation_id = "conv-1"
    row.user_id = "u1"
    row.messages = [{"role": "user", "content": "hi"}]
    row.status = "extracted"
    row.turn_count = 5
    row.started_at = datetime(2026, 4, 22, tzinfo=timezone.utc)
    row.ended_at = datetime(2026, 4, 22, tzinfo=timezone.utc)
    row.extracted_at = datetime(2026, 4, 22, tzinfo=timezone.utc)
    row.extraction_result = {"fields": {"desired_image": "뮤트"}}
    result = MagicMock()
    result.first.return_value = row
    db.execute.return_value = result

    out = conversations.get_conversation(db, "conv-1")
    assert out is not None
    assert out["status"] == "extracted"
    assert out["turn_count"] == 5


def test_get_conversation_returns_none_when_missing():
    db = _fake_db()
    result = MagicMock()
    result.first.return_value = None
    db.execute.return_value = result
    assert conversations.get_conversation(db, "ghost") is None


def test_list_user_conversations_ordered():
    db = _fake_db()
    row1 = MagicMock()
    row1.conversation_id = "conv-new"
    row1.status = "extracted"
    row1.turn_count = 10
    row1.started_at = datetime(2026, 4, 22, tzinfo=timezone.utc)
    row1.ended_at = datetime(2026, 4, 22, 11, tzinfo=timezone.utc)
    row1.extracted_at = datetime(2026, 4, 22, 12, tzinfo=timezone.utc)
    row2 = MagicMock()
    row2.conversation_id = "conv-old"
    row2.status = "ended"
    row2.turn_count = 3
    row2.started_at = datetime(2026, 3, 1, tzinfo=timezone.utc)
    row2.ended_at = None
    row2.extracted_at = None
    result = MagicMock()
    result.all.return_value = [row1, row2]
    db.execute.return_value = result

    out = conversations.list_user_conversations(db, "u1", limit=10)
    assert [r["conversation_id"] for r in out] == ["conv-new", "conv-old"]
    assert out[1]["ended_at"] is None
