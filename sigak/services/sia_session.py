"""Sia conversation session store — Redis sliding TTL (v2 Priority 1 D3).

Contract #3 (SPEC-ONBOARDING-V2 REQ-SIA-006/007/008):
  - 대화 active 기간에는 Redis 만 사용. DB write 없음.
  - 유저 메시지마다 TTL 5분 reset (sliding).
  - Idle >5분 OR 명시 종료 시 세션 DELETE + DB INSERT via services.conversations.
  - Redis 손실 시 해당 대화 데이터 소실 (onboarding snapshot 특성상 감수).

Redis key 설계:
  sia:session:{conversation_id}  → full session_state JSON

Session state shape (Pydantic-less, 직접 JSON):
  {
    "conversation_id": str,
    "user_id": str,
    "turn_count": int,
    "messages": [{"role", "content", "ts"}],
    "collected_fields": dict,        # light tracking (extraction 은 종료 후)
    "missing_fields": [str],
    "resolved_name": Optional[str],  # 호칭 폴백 2순위 fallback 응답
    "ig_feed_cache": Optional[dict], # Step 1 결과 복사 (읽기 전용)
    "status": "active",
    "created_at": iso,
    "updated_at": iso,
  }

Redis client: singleton `redis.Redis` sync. 타 모듈에서 얕게 import 해서 사용.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import redis

from config import get_settings


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Redis Client Singleton
# ─────────────────────────────────────────────

_redis_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    """Redis 클라이언트 싱글톤. 최초 호출 시 초기화."""
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,     # str 반환 (bytes 디코딩 자동)
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    return _redis_client


def reset_redis_client() -> None:
    """테스트 격리 용 — 싱글톤 해제."""
    global _redis_client
    if _redis_client is not None:
        try:
            _redis_client.close()
        except Exception:
            pass
        _redis_client = None


# ─────────────────────────────────────────────
#  Key helpers
# ─────────────────────────────────────────────

def session_key(conversation_id: str) -> str:
    return f"sia:session:{conversation_id}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────────────────────────
#  Session CRUD
# ─────────────────────────────────────────────

def create_session(
    *,
    conversation_id: str,
    user_id: str,
    resolved_name: Optional[str],
    ig_feed_cache: Optional[dict],
    missing_fields: list[str],
) -> dict:
    """새 세션 생성. 이미 존재하면 덮어쓰지 않고 기존 반환 (idempotent safety).

    Returns: 생성된 (또는 기존) session_state dict.
    """
    r = get_redis()
    key = session_key(conversation_id)

    # idempotent: 이미 있으면 기존 리턴 (재시도/duplicate start 방어)
    existing_raw = r.get(key)
    if existing_raw is not None:
        logger.info("create_session idempotent hit: cid=%s", conversation_id)
        return json.loads(existing_raw)

    now = _now_iso()
    state = {
        "conversation_id": conversation_id,
        "user_id": user_id,
        "turn_count": 0,
        "messages": [],
        "collected_fields": {},
        "missing_fields": missing_fields,
        "resolved_name": resolved_name,
        "ig_feed_cache": ig_feed_cache,
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    settings = get_settings()
    r.set(key, json.dumps(state, ensure_ascii=False), ex=settings.sia_session_ttl_seconds)
    return state


def get_session(conversation_id: str) -> Optional[dict]:
    """세션 조회. 없으면 None (TTL 만료 포함)."""
    r = get_redis()
    raw = r.get(session_key(conversation_id))
    if raw is None:
        return None
    return json.loads(raw)


def append_message(
    *,
    conversation_id: str,
    role: str,
    content: str,
) -> Optional[dict]:
    """세션에 메시지 1건 추가 + TTL 리셋 (sliding).

    role: "user" | "assistant"
    turn_count 는 role="user" 일 때만 증가 (Sia 응답은 카운트 안 함 — 유저 발화 기준).

    Returns: 업데이트된 session_state. 세션이 없으면 None (TTL 만료 등).
    """
    if role not in ("user", "assistant"):
        raise ValueError(f"invalid role: {role!r}")

    r = get_redis()
    key = session_key(conversation_id)
    raw = r.get(key)
    if raw is None:
        return None

    state = json.loads(raw)
    state["messages"].append({
        "role": role,
        "content": content,
        "ts": _now_iso(),
    })
    if role == "user":
        state["turn_count"] = int(state.get("turn_count", 0)) + 1
    state["updated_at"] = _now_iso()

    settings = get_settings()
    r.set(key, json.dumps(state, ensure_ascii=False), ex=settings.sia_session_ttl_seconds)
    return state


def update_collected_fields(
    *,
    conversation_id: str,
    field_updates: dict,
    missing_fields: Optional[list[str]] = None,
    resolved_name: Optional[str] = None,
) -> Optional[dict]:
    """경량 필드 추적 — 각 턴에서 식별된 필드 값 즉시 반영.

    Extraction (Sonnet) 은 대화 종료 후 일괄이지만, 대화 중에도 어느 필드가
    수집됐는지 추적해야 다음 질문 결정 가능.
    """
    r = get_redis()
    key = session_key(conversation_id)
    raw = r.get(key)
    if raw is None:
        return None

    state = json.loads(raw)
    state["collected_fields"].update(field_updates or {})
    if missing_fields is not None:
        state["missing_fields"] = missing_fields
    if resolved_name is not None:
        state["resolved_name"] = resolved_name
    state["updated_at"] = _now_iso()

    settings = get_settings()
    r.set(key, json.dumps(state, ensure_ascii=False), ex=settings.sia_session_ttl_seconds)
    return state


def delete_session(conversation_id: str) -> bool:
    """세션 명시 삭제. 반환: 삭제됐으면 True, 이미 없었으면 False."""
    r = get_redis()
    return bool(r.delete(session_key(conversation_id)))


def touch_session(conversation_id: str) -> bool:
    """TTL 만 리셋 (메시지 추가 없이). client 연결 확인 등 keepalive 용.

    Returns: 세션 존재해서 TTL 갱신됐으면 True.
    """
    r = get_redis()
    settings = get_settings()
    key = session_key(conversation_id)
    # Redis EXPIRE 는 키가 존재해야만 성공
    return bool(r.expire(key, settings.sia_session_ttl_seconds))


# ─────────────────────────────────────────────
#  Health
# ─────────────────────────────────────────────

def ping() -> bool:
    """Redis 연결 헬스체크. 라우트 /health 에서 사용 가능."""
    try:
        return bool(get_redis().ping())
    except Exception:
        logger.exception("Redis ping failed")
        return False
