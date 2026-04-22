"""Sia conversation session store — Redis sliding TTL (v2 Priority 1 D3).

Contract #3 (SPEC-ONBOARDING-V2 REQ-SIA-006/007/008):
  - 대화 active 기간에는 Redis 만 사용. DB write 없음.
  - 유저 메시지마다 primary TTL 5분 reset (sliding).
  - Idle >5분 OR 명시 종료 시 세션 DELETE + DB INSERT via services.conversations.

2026-04-22 D5 Task 3 보강 — backup snapshot dual-write:
  - primary (sia:session:{cid}, TTL 5m) + backup (sia:backup:{cid}, TTL 24h) 이중 저장.
  - primary 만료 후에도 backup 은 24h 유지 → 유저 다음 방문 시 /chat/message 가
    첫 probe 로 backup 을 DB(status="ended_by_timeout") 로 flush + extraction 큐잉.
  - 원자적 이중 저장을 위해 Redis MULTI/EXEC (pipeline transaction=True) 사용.
  - 명시 종료(/chat/end) 는 primary+backup 둘 다 DELETE.

Redis key 설계:
  sia:session:{conversation_id}  → full session_state JSON (primary, TTL 5m)
  sia:backup:{conversation_id}   → full session_state JSON (backup, TTL 24h)

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

SESSION_KEY_PREFIX = "sia:session:"
BACKUP_KEY_PREFIX = "sia:backup:"
BACKUP_TTL_SECONDS = 24 * 3600   # 24 시간 — primary 5m 만료 후 유저 재방문 여유


def session_key(conversation_id: str) -> str:
    return f"{SESSION_KEY_PREFIX}{conversation_id}"


def _backup_key(conversation_id: str) -> str:
    return f"{BACKUP_KEY_PREFIX}{conversation_id}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_state(r: "redis.Redis", state: dict, primary_ttl: int) -> None:
    """Primary (sliding TTL) + backup (24h TTL) 원자적 이중 저장.

    Redis MULTI/EXEC 로 묶어 primary/backup 간 drift 방지. 파이프라인 실패 시
    둘 다 쓰이지 않거나 둘 다 쓰인다.
    """
    state_json = json.dumps(state, ensure_ascii=False)
    cid = state["conversation_id"]
    pipe = r.pipeline(transaction=True)
    pipe.set(session_key(cid), state_json, ex=primary_ttl)
    pipe.set(_backup_key(cid), state_json, ex=BACKUP_TTL_SECONDS)
    pipe.execute()


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
    # primary (5m) + backup (24h) 이중 저장
    _write_state(r, state, primary_ttl=settings.sia_session_ttl_seconds)
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
    # primary (sliding 5m reset) + backup (24h reset) 이중 저장
    _write_state(r, state, primary_ttl=settings.sia_session_ttl_seconds)
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
    # primary + backup 이중 저장 (경량 필드 추적도 backup 에 반영)
    _write_state(r, state, primary_ttl=settings.sia_session_ttl_seconds)
    return state


def delete_session(conversation_id: str) -> bool:
    """세션 명시 삭제 — primary + backup 둘 다 제거.

    명시 종료(/chat/end) 는 DB flush 가 이미 완료된 상태이므로 backup 도 불필요.
    반환: primary 가 존재해서 삭제됐으면 True, 이미 없었으면 False.
    """
    r = get_redis()
    # 두 키를 한 번에 삭제 — DEL 은 존재하는 키 수를 반환하므로 primary 삭제 여부만
    # 별도 확인 후 한 번에 delete 한다. (분할 delete 는 동시성 이슈 발생 가능.)
    existed = bool(r.exists(session_key(conversation_id)))
    r.delete(session_key(conversation_id), _backup_key(conversation_id))
    return existed


def get_backup(conversation_id: str) -> Optional[dict]:
    """Backup snapshot 조회 (TTL 24h). primary 만료 후 TTL expiry probe 용.

    Returns: 있으면 session_state dict, 없으면 None.
    """
    r = get_redis()
    raw = r.get(_backup_key(conversation_id))
    if raw is None:
        return None
    return json.loads(raw)


def delete_backup(conversation_id: str) -> bool:
    """Backup snapshot 만 삭제. flush 후 호출하여 중복 insert 방지."""
    r = get_redis()
    return bool(r.delete(_backup_key(conversation_id)))


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
