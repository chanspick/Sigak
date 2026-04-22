"""conversations CRUD + lifecycle (v2 Priority 1 D2).

Contract #3 (SPEC-ONBOARDING-V2 REQ-SIA-006/007/008 + REQ-EXT-005):
  - Redis active 기간에는 DB row 없음
  - 세션 종료 시 INSERT (status="ended")
  - extraction 성공 시 UPDATE status="extracted"
  - extraction 최종 실패 시 UPDATE status="failed"

Route layer 책임:
  - sia/chat/start → Redis 세션만 생성, 여기 건드리지 않음
  - sia/chat/end / idle timeout → create_ended_conversation 호출
  - Sonnet extraction worker → mark_extracted / mark_failed 호출
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from sqlalchemy import text

from schemas.user_profile import ConversationMessage, ExtractionResult
from services.user_profiles import (
    mark_onboarding_completed,
    merge_structured_fields,
)


logger = logging.getLogger(__name__)


class ConversationNotFoundError(Exception):
    """conversations 에 conversation_id 존재 안 함."""


# ─────────────────────────────────────────────
#  세션 종료 시 DB insert (contract #3)
# ─────────────────────────────────────────────

def create_ended_conversation(
    db,
    *,
    user_id: str,
    conversation_id: str,
    messages: list[ConversationMessage],
    turn_count: int,
    started_at_iso: Optional[str] = None,
    status: str = "ended",
) -> None:
    """Redis 세션 종료 atomic sequence 의 1단계: conversations INSERT.

    extraction 은 이후 worker 가 수행.

    Args:
        messages: Redis session_state.messages 스냅샷 (Pydantic validated)
        turn_count: 유저 발화 턴 수 (Sia 턴 제외, 프로덕트 분석용)
        started_at_iso: 원 대화 시작 시각 ISO string (None 이면 서버 NOW() 사용)
        status: "ended" (명시 종료 /chat/end) | "ended_by_timeout" (primary TTL 만료
            후 backup probe flush). conversations.status 는 VARCHAR(20) 이므로
            추가 migration 불필요.
    """
    payload = [m.model_dump(mode="json") for m in messages]
    if started_at_iso:
        db.execute(
            text(
                "INSERT INTO conversations "
                "  (conversation_id, user_id, messages, status, turn_count, started_at, ended_at) "
                "VALUES "
                "  (:cid, :uid, CAST(:msgs AS jsonb), :status, :tc, :sa, NOW())"
            ),
            {
                "cid": conversation_id,
                "uid": user_id,
                "msgs": json.dumps(payload),
                "status": status,
                "tc": turn_count,
                "sa": started_at_iso,
            },
        )
    else:
        db.execute(
            text(
                "INSERT INTO conversations "
                "  (conversation_id, user_id, messages, status, turn_count, started_at, ended_at) "
                "VALUES "
                "  (:cid, :uid, CAST(:msgs AS jsonb), :status, :tc, NOW(), NOW())"
            ),
            {
                "cid": conversation_id,
                "uid": user_id,
                "msgs": json.dumps(payload),
                "status": status,
                "tc": turn_count,
            },
        )


# ─────────────────────────────────────────────
#  Extraction 결과 반영 (contract #3)
# ─────────────────────────────────────────────

def mark_extracted(
    db,
    *,
    conversation_id: str,
    user_id: str,
    result: ExtractionResult,
) -> None:
    """Sonnet extraction 성공 시 호출.

    1) conversations UPDATE status="extracted", extraction_result, extracted_at
    2) user_profiles.structured_fields shallow merge
    3) user_profiles.onboarding_completed=TRUE
    """
    payload = json.dumps(result.model_dump(mode="json"))
    affected = db.execute(
        text(
            "UPDATE conversations SET "
            "  status = 'extracted', "
            "  extraction_result = CAST(:payload AS jsonb), "
            "  extracted_at = NOW() "
            "WHERE conversation_id = :cid"
        ),
        {"cid": conversation_id, "payload": payload},
    ).rowcount

    if affected == 0:
        raise ConversationNotFoundError(
            f"conversation_id={conversation_id} not found for mark_extracted"
        )

    merge_structured_fields(db, user_id=user_id, fields=result.fields)
    mark_onboarding_completed(db, user_id=user_id)


def mark_failed(db, *, conversation_id: str, reason: Optional[str] = None) -> None:
    """Extraction 재시도 최종 실패 시 호출.

    status="failed" 로 남겨 둠. user_profiles 는 건드리지 않음 (onboarding 미완료
    상태 유지). 운영자 수동 개입 대상.
    """
    affected = db.execute(
        text(
            "UPDATE conversations SET status = 'failed' WHERE conversation_id = :cid"
        ),
        {"cid": conversation_id},
    ).rowcount
    if affected == 0:
        raise ConversationNotFoundError(
            f"conversation_id={conversation_id} not found for mark_failed"
        )
    if reason:
        logger.error("Conversation failed: cid=%s reason=%s", conversation_id, reason)


# ─────────────────────────────────────────────
#  Read
# ─────────────────────────────────────────────

def get_conversation(db, conversation_id: str) -> Optional[dict]:
    """단일 conversation row 조회. 없으면 None."""
    row = db.execute(
        text(
            "SELECT conversation_id, user_id, messages, status, turn_count, "
            "       started_at, ended_at, extracted_at, extraction_result "
            "FROM conversations WHERE conversation_id = :cid"
        ),
        {"cid": conversation_id},
    ).first()
    if row is None:
        return None
    return {
        "conversation_id": row.conversation_id,
        "user_id": row.user_id,
        "messages": row.messages or [],
        "status": row.status,
        "turn_count": row.turn_count,
        "started_at": row.started_at,
        "ended_at": row.ended_at,
        "extracted_at": row.extracted_at,
        "extraction_result": row.extraction_result,
    }


def list_user_conversations(db, user_id: str, limit: int = 10) -> list[dict]:
    """유저의 대화 이력 (최신순). 설정 페이지 archive 용."""
    rows = db.execute(
        text(
            "SELECT conversation_id, status, turn_count, started_at, ended_at, extracted_at "
            "FROM conversations "
            "WHERE user_id = :uid "
            "ORDER BY COALESCE(ended_at, started_at) DESC "
            "LIMIT :lim"
        ),
        {"uid": user_id, "lim": limit},
    ).all()
    return [
        {
            "conversation_id": r.conversation_id,
            "status": r.status,
            "turn_count": r.turn_count,
            "started_at": r.started_at,
            "ended_at": r.ended_at,
            "extracted_at": r.extracted_at,
        }
        for r in rows
    ]
