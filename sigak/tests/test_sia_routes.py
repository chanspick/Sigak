"""Sia routes integration tests (v2 Priority 1 D5 Tasks 1 & 3 & 4).

`/api/v1/sia/chat/{start,message,end}` FastAPI TestClient 통합 테스트.
LLM, Redis, DB 모두 mock — live API 호출 없음.

커버리지:
  Task 1 — MessageResponse 확장 + Sia parser:
    - /chat/start 가 choices mode 4지선다 반환
    - /chat/start 가 name_fallback mode 반환 (비한글 name)
    - /chat/start 가 name_fallback mode 반환 (null name, 애플 로그인)
    - /chat/message freetext mode (주관식 턴)
    - /chat/message choices mode (4지선다 턴)

  Task 3 — Redis TTL expiry probe → DB flush:
    - /chat/message 410 + backup 없음 → recovery copy 응답
    - /chat/message 410 + backup 존재 → DB flush (status="ended_by_timeout")
    - /chat/message 410 + flush 후 두 번째 probe idempotent (중복 insert 없음)
    - /chat/message backup 이 다른 user 의 conversation → flush 안 함

  Task 4 — Recovery copy 품질 게이트:
    - 410 응답에 영어 기술 용어 없음 (session/expired/TTL/timeout/redis)
    - 410 응답이 Korean 서술형 정중체
"""
from __future__ import annotations

import json
import os
import sys
from typing import Optional
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from fastapi.testclient import TestClient


# ─────────────────────────────────────────────
#  Fake user / DB / Redis
# ─────────────────────────────────────────────

def _user_korean() -> dict:
    return {
        "id": "u1",
        "kakao_id": "k1",
        "email": "",
        "name": "정세현",   # 한글 name
        "gender": "female",
        "tier": "standard",
    }


def _user_english() -> dict:
    return {
        "id": "u1",
        "kakao_id": "k1",
        "email": "",
        "name": "chanspick",   # 비한글 name
        "gender": "female",
        "tier": "standard",
    }


def _user_null_name() -> dict:
    return {
        "id": "u1",
        "kakao_id": "k1",
        "email": "",
        "name": "",   # 애플 로그인, 빈 name
        "gender": "female",
        "tier": "standard",
    }


class _FakeDB:
    def __init__(self):
        self.executes: list[tuple[str, dict]] = []
        self.committed = 0

    def execute(self, stmt, params: Optional[dict] = None):
        self.executes.append((str(stmt), params or {}))
        result = MagicMock()
        result.first.return_value = None
        result.rowcount = 0
        return result

    def commit(self):
        self.committed += 1

    def rollback(self):
        pass


# ─────────────────────────────────────────────
#  Fake Redis (test_sia_session.py 와 동일 구조 — 간결 재구현)
# ─────────────────────────────────────────────

class _FakePipeline:
    def __init__(self, r):
        self._r = r
        self._ops: list[tuple[str, tuple, dict]] = []

    def set(self, k, v, ex=None):
        self._ops.append(("set", (k, v), {"ex": ex}))
        return self

    def delete(self, *keys):
        self._ops.append(("delete", keys, {}))
        return self

    def execute(self):
        results = []
        for op, args, kwargs in self._ops:
            fn = getattr(self._r, op)
            results.append(fn(*args, **kwargs))
        self._ops.clear()
        return results


class _FakeRedis:
    def __init__(self):
        self._store: dict[str, str] = {}
        self._ttls: dict[str, int] = {}

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

    def pipeline(self, transaction=True):   # noqa: ARG002
        return _FakePipeline(self)

    def ping(self):
        return True

    def close(self):
        pass

    def _force_expire(self, key):
        self._store.pop(key, None)
        self._ttls.pop(key, None)


# ─────────────────────────────────────────────
#  LLM stub — parse_sia_output 에 맞는 고정 응답
# ─────────────────────────────────────────────

OPENING_WITH_CHOICES = (
    "정세현님, 시각의 AI 미감 분석가 Sia입니다.\n"
    "피드 38장 분석 완료했습니다 — 쿨뮤트 68%, 채도 낮습니다.\n"
    "\n"
    "주말 저녁, 어떤 인상으로 기억되고 싶으신가요?\n"
    "- 편안하고 기대고 싶은 인상\n"
    "- 세련되고 거리감 있는 인상\n"
    "- 특별한 날처럼 공들인 인상\n"
    "- 무심한데 센스 있는 인상"
)


FALLBACK_NAME_QUESTION = (
    "시각의 AI 미감 분석가 Sia입니다.\n"
    "어떻게 불러드리면 됩니까?"
)


MID_TURN_SUBJECTIVE = (
    "지금 추구하는 인상을 한 문장으로 표현한다면 어떻습니까?\n"
    "자유롭게 답변해 주십시오."
)


MID_TURN_CHOICES = (
    "흥미로운 선택입니다. 다음 질문으로 넘어갑니다.\n"
    "\n"
    "지금 가장 공들이는 영역은 어디입니까?\n"
    "- 헤어 관리\n"
    "- 스킨케어\n"
    "- 의류 스타일\n"
    "- 특별히 없음"
)


# ─────────────────────────────────────────────
#  App fixture — isolated FastAPI with only sia router + mocked deps
# ─────────────────────────────────────────────

@pytest.fixture
def app_ctx(monkeypatch):
    """Sia router 만 올린 FastAPI app + mock 된 deps.

    반환: (TestClient, FakeDB, FakeRedis, monkeypatch_proxy)
    """
    from routes import sia as sia_route
    import deps
    from services import sia_session, sia_llm

    # ── Redis 교체 ──
    fake_redis = _FakeRedis()
    sia_session._redis_client = fake_redis
    monkeypatch.setattr(sia_session, "get_redis", lambda: fake_redis)

    # ── LLM call stub — caller 가 monkeypatch.setattr 로 override 가능 ──
    monkeypatch.setattr(
        sia_llm, "call_sia_turn_with_retry",
        lambda *, system_prompt, messages_history, **_: OPENING_WITH_CHOICES,
    )

    # ── profile stub — chat_start 에서 사용 ──
    def _fake_profile(db, uid):
        return {
            "user_id": uid,
            "gender": "female",
            "birth_date": "1999-03-15",
            "ig_handle": None,
            "ig_feed_cache": None,
            "ig_fetch_status": "skipped",
            "structured_fields": {},
        }
    monkeypatch.setattr(sia_route, "get_profile", _fake_profile)

    # ── FastAPI app 구성 ──
    app = FastAPI()
    app.include_router(sia_route.router)

    fake_db = _FakeDB()
    app.dependency_overrides[deps.db_session] = lambda: fake_db
    # user 는 테스트마다 override 가능 — 기본 한글 user
    user_holder = {"current": _user_korean()}
    app.dependency_overrides[deps.get_current_user] = lambda: user_holder["current"]

    yield app, fake_db, fake_redis, monkeypatch, user_holder

    sia_session.reset_redis_client()


@pytest.fixture
def client(app_ctx):
    app, fake_db, fake_redis, mp, user_holder = app_ctx
    with TestClient(app) as c:
        yield c, fake_db, fake_redis, mp, user_holder


# ─────────────────────────────────────────────
#  Task 1 — MessageResponse 확장 검증
# ─────────────────────────────────────────────

def test_chat_start_returns_choices_mode_with_four_options(client):
    """한글 name + LLM 이 4지선다 응답 → mode=choices, choices 길이 4."""
    c, *_ = client
    r = c.post("/api/v1/sia/chat/start")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["response_mode"] == "choices"
    assert len(body["choices"]) == 4
    assert "편안하고 기대고 싶은 인상" in body["choices"]
    # body 에는 trailing bullet 블록 제거
    assert "- 편안하고" not in body["opening_message"]


def test_chat_start_name_fallback_for_non_korean_user(client):
    """비한글 name 유저 → LLM 이 어떤 응답을 내든 route 가 name_fallback 오버라이드."""
    c, fake_db, fake_redis, mp, user_holder = client
    user_holder["current"] = _user_english()
    # LLM 이 choices 를 주더라도 route 가 name_fallback 으로 override
    r = c.post("/api/v1/sia/chat/start")
    assert r.status_code == 200
    body = r.json()
    assert body["response_mode"] == "name_fallback"
    assert body["choices"] == []


def test_chat_start_name_fallback_for_null_name(client):
    """애플 로그인 등 name="" 유저 → name_fallback."""
    c, fake_db, fake_redis, mp, user_holder = client
    user_holder["current"] = _user_null_name()
    r = c.post("/api/v1/sia/chat/start")
    assert r.status_code == 200
    body = r.json()
    assert body["response_mode"] == "name_fallback"
    assert body["choices"] == []


def test_chat_message_freetext_mode_on_subjective_question(client):
    """중간 턴에서 LLM 이 하이픈 없는 주관식 질문을 내면 mode=freetext."""
    c, fake_db, fake_redis, mp, user_holder = client
    # 1. start — choices mode LLM 응답으로 세션 생성
    from services import sia_llm
    mp.setattr(sia_llm, "call_sia_turn_with_retry",
               lambda **kw: OPENING_WITH_CHOICES)
    r = c.post("/api/v1/sia/chat/start")
    assert r.status_code == 200
    cid = r.json()["conversation_id"]

    # 2. message — LLM 이 freetext 응답 전환
    mp.setattr(sia_llm, "call_sia_turn_with_retry",
               lambda **kw: MID_TURN_SUBJECTIVE)
    r = c.post("/api/v1/sia/chat/message",
               json={"conversation_id": cid, "user_message": "1번"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["response_mode"] == "freetext"
    assert body["choices"] == []


def test_chat_message_choices_mode_with_four_bullets(client):
    """중간 턴에서 LLM 이 4지선다 → mode=choices, choices 4."""
    c, fake_db, fake_redis, mp, user_holder = client
    from services import sia_llm
    mp.setattr(sia_llm, "call_sia_turn_with_retry",
               lambda **kw: OPENING_WITH_CHOICES)
    r = c.post("/api/v1/sia/chat/start")
    cid = r.json()["conversation_id"]

    mp.setattr(sia_llm, "call_sia_turn_with_retry",
               lambda **kw: MID_TURN_CHOICES)
    r = c.post("/api/v1/sia/chat/message",
               json={"conversation_id": cid, "user_message": "1번"})
    assert r.status_code == 200
    body = r.json()
    assert body["response_mode"] == "choices"
    assert len(body["choices"]) == 4
    assert "헤어 관리" in body["choices"]


# ─────────────────────────────────────────────
#  Task 3 — Redis TTL expiry probe → DB flush
# ─────────────────────────────────────────────

def test_chat_message_410_with_no_backup_returns_recovery_copy(client):
    """session primary 없음 + backup 없음 → 410 recovery copy."""
    c, *_ = client
    # 세션 생성 안 함 → primary/backup 둘 다 없음
    r = c.post("/api/v1/sia/chat/message",
               json={"conversation_id": "ghost-cid", "user_message": "hi"})
    assert r.status_code == 410
    detail = r.json()["detail"]
    assert detail["message"] == "지금까지 나눈 대화를 정리했습니다."
    assert detail["next"] == "extracting"
    assert detail["redirect"] == "/extracting"


def test_chat_message_410_flushes_backup_to_db_on_first_probe(client):
    """primary 만료 + backup 존재 → 첫 probe 가 DB flush (status=ended_by_timeout).

    flush 는 conversations INSERT + commit + extraction BackgroundTask 큐잉.
    """
    c, fake_db, fake_redis, mp, user_holder = client
    from services import sia_session, sia_llm

    # 1. 세션 생성 + message 한 번 → backup 에 실제 데이터
    mp.setattr(sia_llm, "call_sia_turn_with_retry",
               lambda **kw: OPENING_WITH_CHOICES)
    r = c.post("/api/v1/sia/chat/start")
    cid = r.json()["conversation_id"]
    c.post("/api/v1/sia/chat/message",
           json={"conversation_id": cid, "user_message": "hi"})

    # 2. primary 강제 만료 (backup 은 남아있음)
    fake_redis._force_expire(sia_session.session_key(cid))
    assert sia_session.get_backup(cid) is not None

    # 3. probe 로 /chat/message 호출
    before_inserts = len([
        e for e in fake_db.executes if "INSERT INTO conversations" in e[0]
    ])
    r = c.post("/api/v1/sia/chat/message",
               json={"conversation_id": cid, "user_message": "tick"})
    assert r.status_code == 410

    # INSERT 가 1회 발생 + status 파라미터는 ended_by_timeout
    after_inserts = [
        e for e in fake_db.executes if "INSERT INTO conversations" in e[0]
    ]
    assert len(after_inserts) == before_inserts + 1
    params = after_inserts[-1][1]
    assert params["status"] == "ended_by_timeout"
    assert params["uid"] == "u1"
    assert params["cid"] == cid
    assert fake_db.committed >= 1

    # backup 은 flush 후 삭제됨
    assert sia_session.get_backup(cid) is None


def test_chat_message_410_idempotent_second_probe_no_double_insert(client):
    """첫 probe 가 backup flush 하면, 두 번째 probe 는 추가 INSERT 없음."""
    c, fake_db, fake_redis, mp, user_holder = client
    from services import sia_session, sia_llm

    mp.setattr(sia_llm, "call_sia_turn_with_retry",
               lambda **kw: OPENING_WITH_CHOICES)
    r = c.post("/api/v1/sia/chat/start")
    cid = r.json()["conversation_id"]
    c.post("/api/v1/sia/chat/message",
           json={"conversation_id": cid, "user_message": "hi"})

    # primary 만료
    fake_redis._force_expire(sia_session.session_key(cid))

    # 첫 probe — flush
    r1 = c.post("/api/v1/sia/chat/message",
                json={"conversation_id": cid, "user_message": "1"})
    assert r1.status_code == 410
    inserts_after_first = len([
        e for e in fake_db.executes if "INSERT INTO conversations" in e[0]
    ])

    # 두 번째 probe — backup 없음 → 단순 410, INSERT 없음
    r2 = c.post("/api/v1/sia/chat/message",
                json={"conversation_id": cid, "user_message": "2"})
    assert r2.status_code == 410
    inserts_after_second = len([
        e for e in fake_db.executes if "INSERT INTO conversations" in e[0]
    ])
    assert inserts_after_second == inserts_after_first


def test_chat_message_410_rejects_backup_for_other_user(client):
    """backup 은 존재하지만 user_id 불일치 → flush 안 함 (유출 방지)."""
    c, fake_db, fake_redis, mp, user_holder = client
    from services import sia_session, sia_llm

    # A user 로 세션 생성
    mp.setattr(sia_llm, "call_sia_turn_with_retry",
               lambda **kw: OPENING_WITH_CHOICES)
    r = c.post("/api/v1/sia/chat/start")
    cid = r.json()["conversation_id"]
    c.post("/api/v1/sia/chat/message",
           json={"conversation_id": cid, "user_message": "hi"})

    # primary 만료 (backup 은 여전히 user_id=u1)
    fake_redis._force_expire(sia_session.session_key(cid))

    # B user 로 전환 (같은 conversation_id 사용)
    user_holder["current"] = {
        "id": "u_attacker",
        "kakao_id": "k2",
        "email": "", "name": "남의", "gender": "female", "tier": "standard",
    }

    before = len([
        e for e in fake_db.executes if "INSERT INTO conversations" in e[0]
    ])
    r = c.post("/api/v1/sia/chat/message",
               json={"conversation_id": cid, "user_message": "tick"})
    assert r.status_code == 410
    after = len([
        e for e in fake_db.executes if "INSERT INTO conversations" in e[0]
    ])
    # INSERT 추가 없음 — 다른 유저 대화 flush 거부
    assert after == before

    # backup 은 보존 (실제 owner 가 다시 오면 여전히 복구 가능)
    assert sia_session.get_backup(cid) is not None


# ─────────────────────────────────────────────
#  Task 4 — Recovery copy 품질 게이트
# ─────────────────────────────────────────────

_BANNED_TECH_TERMS = [
    "session", "Session", "SESSION",
    "expired", "Expired", "EXPIRED",
    "TTL", "ttl",
    "timeout", "Timeout", "TIMEOUT",
    "redis", "Redis", "REDIS",
    "재연결", "다시 시도",   # 유저가 resume 할 수 있다는 오해 유발
]


def test_recovery_copy_contains_no_english_tech_terms(client):
    """410 응답 body 전체에 infra/english 기술 용어 없음."""
    c, *_ = client
    r = c.post("/api/v1/sia/chat/message",
               json={"conversation_id": "ghost", "user_message": "hi"})
    assert r.status_code == 410
    body_str = json.dumps(r.json(), ensure_ascii=False)
    for term in _BANNED_TECH_TERMS:
        assert term not in body_str, (
            f"recovery copy 에 금지 용어 '{term}' 포함: {body_str}"
        )


def test_recovery_copy_uses_formal_korean_tone(client):
    """410 응답 message 가 서술형 정중체 어미 포함 (~습니다/~합니다/~있습니다)."""
    c, *_ = client
    r = c.post("/api/v1/sia/chat/message",
               json={"conversation_id": "ghost", "user_message": "hi"})
    assert r.status_code == 410
    message = r.json()["detail"]["message"]
    formal_endings = ("습니다", "합니다", "있습니다", "입니다")
    assert any(e in message for e in formal_endings), (
        f"recovery copy 가 서술형 정중체 어미 누락: {message!r}"
    )
