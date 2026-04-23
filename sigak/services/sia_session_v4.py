"""Sia session v4 — ConversationState ↔ Redis 변환 레이어 (Phase H1b).

설계 원칙 (PHASE_H_DIRECTIVE §2.2):
- 기존 sia_session.py 의 Redis dual-write 인프라 그대로 재사용
  (get_redis / session_key / _backup_key / primary TTL / backup 24h).
- Phase H 는 ConversationState dataclass 에서 Redis dict 로 변환만 책임.
- Phase A-F 의 spectrum 기반 함수 (decide_next_turn / record_spectrum_choice)
  는 유지되지만 이 모듈은 사용하지 않는다. Phase H7 에서 폐기 예정.

핵심 API:
  load_conversation_state(session_id) -> Optional[ConversationState]
  save_conversation_state(state) -> None (primary + backup dual-write)
  create_conversation_state(session_id, user_id, user_name) -> ConversationState
  delete_conversation_state(session_id) -> bool
  get_backup_state(session_id) -> Optional[ConversationState]
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from config import get_settings
from schemas.sia_state import ConversationState
from services.sia_session import (
    BACKUP_TTL_SECONDS,
    _backup_key,
    get_redis,
    session_key,
)


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Core CRUD
# ─────────────────────────────────────────────

def create_conversation_state(
    *,
    session_id: str,
    user_id: str,
    user_name: str,
) -> ConversationState:
    """신규 세션 state 생성 + Redis dual-write.

    기존 키 존재 시 idempotent — 기존 상태 리턴 (페이즈 A-F 패턴 준수).
    """
    existing = load_conversation_state(session_id)
    if existing is not None:
        logger.info(
            "create_conversation_state idempotent hit: session=%s", session_id,
        )
        return existing

    now_iso = _now_iso()
    state = ConversationState(
        session_id=session_id,
        user_id=user_id,
        user_name=user_name,
        turns=[],
        status="active",
        created_at=now_iso,
        updated_at=now_iso,
    )
    save_conversation_state(state)
    return state


def load_conversation_state(session_id: str) -> Optional[ConversationState]:
    """Redis primary (5m TTL) 에서 state 로드. 없으면 None.

    backup 24h 는 get_backup_state() 로 별도 조회 (timeout 복구 흐름).
    """
    try:
        r = get_redis()
    except Exception:
        logger.debug("Redis unavailable — load_conversation_state skipped")
        return None

    raw = r.get(session_key(session_id))
    if raw is None:
        return None
    try:
        data = json.loads(raw)
        return ConversationState.from_dict(data)
    except Exception:
        logger.exception(
            "ConversationState deserialize failed: session=%s", session_id,
        )
        return None


def save_conversation_state(state: ConversationState) -> None:
    """ConversationState → Redis primary + backup 원자적 dual-write.

    primary TTL sliding (매 저장마다 5m reset).
    backup TTL 24h (sia_session 기존 상수 재사용).
    """
    state.updated_at = _now_iso()
    payload = json.dumps(state.to_dict(), ensure_ascii=False)

    try:
        r = get_redis()
    except Exception:
        logger.warning(
            "Redis unavailable — save_conversation_state skipped session=%s",
            state.session_id,
        )
        return

    settings = get_settings()
    primary_ttl = int(getattr(settings, "sia_session_ttl_seconds", 300))

    pipe = r.pipeline(transaction=True)
    pipe.set(session_key(state.session_id), payload, ex=primary_ttl)
    pipe.set(_backup_key(state.session_id), payload, ex=BACKUP_TTL_SECONDS)
    pipe.execute()


def get_backup_state(session_id: str) -> Optional[ConversationState]:
    """Backup 스냅샷 조회 — primary TTL 만료 후 복구 흐름."""
    try:
        r = get_redis()
    except Exception:
        return None
    raw = r.get(_backup_key(session_id))
    if raw is None:
        return None
    try:
        return ConversationState.from_dict(json.loads(raw))
    except Exception:
        logger.exception(
            "backup ConversationState deserialize failed: session=%s", session_id,
        )
        return None


def delete_conversation_state(session_id: str) -> bool:
    """명시 종료 — primary + backup 전부 삭제. 반환: primary 존재 여부."""
    try:
        r = get_redis()
    except Exception:
        return False
    existed = bool(r.exists(session_key(session_id)))
    r.delete(session_key(session_id), _backup_key(session_id))
    return existed


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
