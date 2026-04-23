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
        # v3 Phase B — 정조준 spectrum 추적
        "spectrum_log": [],
        "precision_hits": 0,       # spectrum 1/2 누적
        "precision_misses": 0,     # spectrum 3/4 누적
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
#  v3 — Spectrum 응답 추적 + 다음 턴 결정 (Phase B)
# ─────────────────────────────────────────────

# 유저 canonical 4지선다 문구 (UI 버튼에서 그대로 전송될 때 빠른 경로)
_CANONICAL_SPECTRUM: dict[str, int] = {
    "네, 비슷하다": 1,
    "절반 정도 맞다": 2,
    "다르다": 3,
    "전혀 다르다": 4,
}


def parse_spectrum_choice(user_message: str) -> Optional[int]:
    """유저 메시지 → spectrum 1/2/3/4. 매치 실패 시 None.

    우선순위:
      1) canonical 4 문구 정확 일치
      2) fuzzy 순서: 전혀 → 절반 → 비슷/맞 → 다르
         ("반은 맞고 반은 다릅니다" 같은 복합문이 2 로 분류되도록 절반 우선)
    """
    if not user_message:
        return None
    normalized = user_message.strip()
    if normalized in _CANONICAL_SPECTRUM:
        return _CANONICAL_SPECTRUM[normalized]

    # fuzzy — 특정 키워드 우선순위
    # 4 (전혀 다르다) 먼저: "전혀" 키워드가 있으면 무조건 강한 반대
    if "전혀" in normalized:
        return 4
    # 2 (절반) 우선: 복합문 "반은 맞고 반은 다르다" 등에서 절반 의도 포착
    half_markers = ("절반", "반만", "반반", "반은")
    if any(m in normalized for m in half_markers):
        return 2
    # 1 (비슷/맞) — "안 맞" 부정형은 제외
    if "비슷" in normalized or ("맞" in normalized and "안 맞" not in normalized):
        return 1
    # 3 (다르) — 한국어 활용형 "다르/다른/다릅/달라" 전부 커버
    disagree_markers = ("다르", "다른", "다릅", "달라")
    if any(m in normalized for m in disagree_markers):
        return 3
    return None


def record_spectrum_choice(
    *,
    conversation_id: str,
    user_message: str,
) -> Optional[dict]:
    """유저 메시지에서 spectrum 파싱 → 세션에 로그 + 히트/미스 누적.

    반환:
      - 매치됐고 세션 존재: 업데이트된 state dict
      - 매치 실패 OR 세션 없음: None (caller 는 분기 없이 일반 대화 흐름)
    """
    choice = parse_spectrum_choice(user_message)
    if choice is None:
        return None

    r = get_redis()
    key = session_key(conversation_id)
    raw = r.get(key)
    if raw is None:
        return None

    state = json.loads(raw)
    log = state.get("spectrum_log") or []
    log.append(choice)
    state["spectrum_log"] = log

    if choice in (1, 2):
        state["precision_hits"] = int(state.get("precision_hits", 0)) + 1
    else:
        state["precision_misses"] = int(state.get("precision_misses", 0)) + 1

    state["updated_at"] = _now_iso()
    settings = get_settings()
    _write_state(r, state, primary_ttl=settings.sia_session_ttl_seconds)
    return state


def decide_next_turn(state: dict) -> str:
    """다음 Sia 응답 유형 결정. v3 14턴 구조.

    Input: state (유저 직전 메시지가 append_message + record_spectrum_choice 를
           통해 이미 반영된 상태).

    Returns (turn_type string):
      "opening"                      — turn_count == 0, Sia 첫 응답
      "precision_continue"           — 내적 구간인데 spectrum 미파싱, 안전 재시도
      "branch_agree"                 — 직전 유저 spectrum=1
      "branch_half"                  — 직전 유저 spectrum=2
      "branch_disagree"              — 직전 유저 spectrum=3
      "branch_fail"                  — 직전 유저 spectrum=4
      "force_external_transition"    — 3회 miss 누적 → 즉시 외적 전환
      "external_desired_image"       — turn_count=4
      "external_reference"           — turn_count=5
      "external_body_height"         — turn_count=6
      "external_body_weight"         — turn_count=7
      "external_body_shoulder"       — turn_count=8
      "external_concerns"            — turn_count=9
      "external_lifestyle"           — turn_count=10
      "closing"                      — turn_count>=11

    Caller (routes/sia.py) 는 이 키를 system prompt 의 TURN_CONTEXT 에 주입.
    """
    turn_count = int(state.get("turn_count", 0))
    spectrum_log = state.get("spectrum_log") or []
    precision_misses = int(state.get("precision_misses", 0))

    # 0: Sia 첫 응답 — 유저가 아직 말 안 함
    if turn_count == 0:
        return "opening"

    # 내적 정조준 구간 (유저 1~3 응답 후)
    if turn_count <= 3:
        # 3회 연속 miss 누적 → 즉시 외적 전환 (복구)
        if precision_misses >= 3:
            return "force_external_transition"
        last = spectrum_log[-1] if spectrum_log else None
        if last == 1:
            return "branch_agree"
        if last == 2:
            return "branch_half"
        if last == 3:
            return "branch_disagree"
        if last == 4:
            return "branch_fail"
        # spectrum 파싱 실패 — 내적 계속 시도
        return "precision_continue"

    # 외적 수집 — turn_count 4~10
    external_map = {
        4: "external_desired_image",
        5: "external_reference",
        6: "external_body_height",
        7: "external_body_weight",
        8: "external_body_shoulder",
        9: "external_concerns",
        10: "external_lifestyle",
    }
    if turn_count in external_map:
        return external_map[turn_count]

    # 11 이상 — 클로징
    return "closing"


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
