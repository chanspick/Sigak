"""Sia session store tests (v2 Priority 1 D5 Task 3).

`services.sia_session` 의 primary(5m) + backup(24h) 이중 저장 검증.

Redis 는 경량 fake 로 대체 (fakeredis 미설치 환경에서도 동작). pipeline
transaction=True 는 단순히 큐잉 후 execute 시점에 순차 적용.

테스트 범위:
  - append_message 가 primary 와 backup 을 동시에 쓴다
  - primary TTL 만료(삭제) 후에도 backup 은 24h 로 살아있다
  - delete_session 은 primary + backup 을 모두 제거한다
  - get_backup 은 없으면 None 반환
  - create_session / update_collected_fields 도 이중 저장한다
"""
from __future__ import annotations

import json
import os
import sys
from typing import Optional

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ─────────────────────────────────────────────
#  Fake Redis — sia_session 사용 API 만 구현
# ─────────────────────────────────────────────
#  sia_session 이 redis.Redis 로부터 호출하는 메서드:
#    get(key) → str | None
#    set(key, value, ex=int)
#    delete(*keys) → int
#    exists(key) → int
#    expire(key, seconds) → int
#    pipeline(transaction=True) → Pipeline  (get_redis 의 fromurl 결과를 교체)
#  Pipeline: set/delete 등을 큐잉 후 execute() 로 실제 반영.

class _FakePipeline:
    def __init__(self, redis_ref: "_FakeRedis"):
        self._redis = redis_ref
        self._ops: list[tuple[str, tuple, dict]] = []

    def set(self, key, value, ex=None):
        self._ops.append(("set", (key, value), {"ex": ex}))
        return self

    def delete(self, *keys):
        self._ops.append(("delete", keys, {}))
        return self

    def execute(self):
        results = []
        for op, args, kwargs in self._ops:
            fn = getattr(self._redis, op)
            results.append(fn(*args, **kwargs))
        self._ops.clear()
        return results


class _FakeRedis:
    """In-memory Redis stub.

    TTL 은 `expiries` dict 로 추적하되, 테스트가 명시적으로 `_expire_primary`
    같은 helper 로 만료를 시뮬레이트한다. 자동 wall-clock expiration 은 생략
    (간결성 + 결정적 테스트).
    """

    def __init__(self):
        self._store: dict[str, str] = {}
        self._ttls: dict[str, int] = {}

    # ── 기본 op ──
    def get(self, key):
        return self._store.get(key)

    def set(self, key, value, ex=None):
        self._store[key] = value
        if ex is not None:
            self._ttls[key] = ex
        return True

    def delete(self, *keys):
        removed = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                removed += 1
            self._ttls.pop(k, None)
        return removed

    def exists(self, key):
        return 1 if key in self._store else 0

    def expire(self, key, seconds):
        if key not in self._store:
            return 0
        self._ttls[key] = seconds
        return 1

    def pipeline(self, transaction=True):   # noqa: ARG002 — signature 일치용
        return _FakePipeline(self)

    def ping(self):
        return True

    def close(self):
        pass

    # ── 테스트 helpers ──
    def _force_expire(self, key: str):
        """임의 키를 즉시 만료 시뮬레이트 (wall-clock 기다리지 않고)."""
        self._store.pop(key, None)
        self._ttls.pop(key, None)

    def _ttl_of(self, key: str) -> Optional[int]:
        return self._ttls.get(key)


@pytest.fixture
def fake_redis(monkeypatch):
    """sia_session 의 get_redis() 가 FakeRedis 싱글톤을 돌려주도록 교체."""
    # import 는 fixture 안에서 — 모듈 top-level import 는 실 redis 패키지 필요
    from services import sia_session

    fake = _FakeRedis()

    # 원본 모듈 global 교체. reset_redis_client 로 다음 테스트 간 격리.
    sia_session._redis_client = fake
    monkeypatch.setattr(sia_session, "get_redis", lambda: fake)

    yield fake

    # teardown
    sia_session.reset_redis_client()


# ─────────────────────────────────────────────
#  Tests
# ─────────────────────────────────────────────

def test_create_session_writes_both_primary_and_backup(fake_redis):
    """create_session 한 번으로 primary + backup 두 키 모두 저장."""
    from services import sia_session

    state = sia_session.create_session(
        conversation_id="cid-1",
        user_id="u1",
        resolved_name=None,
        ig_feed_cache=None,
        missing_fields=["height"],
    )

    assert state["conversation_id"] == "cid-1"
    assert fake_redis.exists(sia_session.session_key("cid-1"))
    assert fake_redis.exists(sia_session._backup_key("cid-1"))

    # TTL 구분 — primary 는 5m, backup 은 24h
    primary_ttl = fake_redis._ttl_of(sia_session.session_key("cid-1"))
    backup_ttl = fake_redis._ttl_of(sia_session._backup_key("cid-1"))
    assert primary_ttl == 300   # sia_session_ttl_seconds default
    assert backup_ttl == sia_session.BACKUP_TTL_SECONDS == 86400


def test_append_message_writes_both_primary_and_backup(fake_redis):
    """append_message 도 dual-write — primary sliding + backup 24h."""
    from services import sia_session

    sia_session.create_session(
        conversation_id="cid-2", user_id="u1",
        resolved_name=None, ig_feed_cache=None, missing_fields=[],
    )
    updated = sia_session.append_message(
        conversation_id="cid-2", role="user", content="hi",
    )
    assert updated is not None
    assert updated["turn_count"] == 1

    # 두 키 모두 갱신됐는지 — payload JSON 파싱해서 메시지 반영 확인
    pri_raw = fake_redis.get(sia_session.session_key("cid-2"))
    bkp_raw = fake_redis.get(sia_session._backup_key("cid-2"))
    assert pri_raw is not None and bkp_raw is not None
    pri = json.loads(pri_raw)
    bkp = json.loads(bkp_raw)
    assert len(pri["messages"]) == 1
    assert len(bkp["messages"]) == 1
    assert pri["messages"][0]["content"] == "hi"
    assert bkp["messages"][0]["content"] == "hi"


def test_backup_survives_primary_expiry(fake_redis):
    """primary 키를 강제 만료시켜도 backup 은 살아있다. get_backup 조회 가능."""
    from services import sia_session

    sia_session.create_session(
        conversation_id="cid-3", user_id="u1",
        resolved_name=None, ig_feed_cache=None, missing_fields=[],
    )
    sia_session.append_message(
        conversation_id="cid-3", role="user", content="hello",
    )

    # primary 강제 만료 (wall-clock 기다리지 않고 즉시)
    fake_redis._force_expire(sia_session.session_key("cid-3"))

    # primary 조회는 None
    assert sia_session.get_session("cid-3") is None

    # backup 은 살아있고 내용 복구 가능
    backup = sia_session.get_backup("cid-3")
    assert backup is not None
    assert backup["conversation_id"] == "cid-3"
    assert backup["user_id"] == "u1"
    assert len(backup["messages"]) == 1


def test_delete_session_removes_backup_too(fake_redis):
    """delete_session 은 primary + backup 둘 다 삭제 (명시 종료 후 cleanup)."""
    from services import sia_session

    sia_session.create_session(
        conversation_id="cid-4", user_id="u1",
        resolved_name=None, ig_feed_cache=None, missing_fields=[],
    )
    assert fake_redis.exists(sia_session.session_key("cid-4"))
    assert fake_redis.exists(sia_session._backup_key("cid-4"))

    result = sia_session.delete_session("cid-4")
    assert result is True

    # 둘 다 없어야 함
    assert not fake_redis.exists(sia_session.session_key("cid-4"))
    assert not fake_redis.exists(sia_session._backup_key("cid-4"))


def test_get_backup_returns_none_when_absent(fake_redis):
    """존재하지 않는 conversation_id 의 backup 조회 → None."""
    from services import sia_session

    assert sia_session.get_backup("never-existed") is None


def test_delete_backup_removes_only_backup(fake_redis):
    """delete_backup 은 primary 를 건드리지 않는다."""
    from services import sia_session

    sia_session.create_session(
        conversation_id="cid-5", user_id="u1",
        resolved_name=None, ig_feed_cache=None, missing_fields=[],
    )
    assert fake_redis.exists(sia_session.session_key("cid-5"))
    assert fake_redis.exists(sia_session._backup_key("cid-5"))

    removed = sia_session.delete_backup("cid-5")
    assert removed is True

    # primary 는 유지
    assert fake_redis.exists(sia_session.session_key("cid-5"))
    # backup 은 삭제
    assert not fake_redis.exists(sia_session._backup_key("cid-5"))


def test_update_collected_fields_dual_writes(fake_redis):
    """update_collected_fields 도 primary + backup 모두 갱신."""
    from services import sia_session

    sia_session.create_session(
        conversation_id="cid-6", user_id="u1",
        resolved_name=None, ig_feed_cache=None, missing_fields=["height"],
    )
    updated = sia_session.update_collected_fields(
        conversation_id="cid-6",
        field_updates={"height": "165_170"},
        resolved_name="민지",
    )
    assert updated is not None
    assert updated["collected_fields"] == {"height": "165_170"}
    assert updated["resolved_name"] == "민지"

    bkp = json.loads(fake_redis.get(sia_session._backup_key("cid-6")))
    assert bkp["collected_fields"] == {"height": "165_170"}
    assert bkp["resolved_name"] == "민지"


def test_create_session_idempotent_does_not_overwrite(fake_redis):
    """같은 conversation_id 로 create 두 번 호출 → 기존 반환, backup 도 유지."""
    from services import sia_session

    sia_session.create_session(
        conversation_id="cid-7", user_id="u1",
        resolved_name=None, ig_feed_cache=None, missing_fields=[],
    )
    sia_session.append_message(
        conversation_id="cid-7", role="user", content="hi",
    )
    # 두 번째 create — append 결과 덮어쓰면 안 됨
    second = sia_session.create_session(
        conversation_id="cid-7", user_id="u1",
        resolved_name=None, ig_feed_cache=None, missing_fields=[],
    )
    # 두 번째 호출은 idempotent — 그대로 반환. messages 유지.
    assert len(second["messages"]) == 1
