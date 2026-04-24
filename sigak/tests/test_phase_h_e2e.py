"""Phase H E2E 통합 시뮬레이션 — routes/sia.py v4 cutover 개통 검증 (STEP 2-H).

범위:
  (A) chat/start → chat/message → chat/end 풀 경로 smoke
  (B) 만재 15턴 시뮬레이션 — decide() 트리거 트레이싱 (msg_type 시퀀스 = fixture 예상)
  (C) 준호 A-9 → CHECK_IN → RE_ENTRY 관리 버킷 시나리오
  (D) 도윤 C6 / C7 자동 감지 경로
  (E) TTL 만료 복구 (410 + backup flush)

Mock 전략:
  - FakeRedis: sia_session_v4.get_redis 교체 (ConversationState JSON 저장)
  - call_sia_turn_with_retry: 'HAIKU:{msg_type.value}' 반환 (msg_type 트레이싱)
  - render_hardcoded: 실 호출 (deterministic variant index)
  - get_profile: fixture profile 반환
  - services.conversations: 캡처 버전으로 교체 (실 SQL 우회)
  - services.extraction.extract_structured_fields: stub ExtractionResult 반환
"""
from __future__ import annotations

import os
import sys
from typing import Any

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import BackgroundTasks, HTTPException

from schemas.sia_state import MsgType
from schemas.user_profile import ExtractionResult, StructuredFields


# ─────────────────────────────────────────────
#  Fake infrastructure
# ─────────────────────────────────────────────

class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ex=None):
        self.store[key] = value

    def delete(self, *keys):
        n = 0
        for k in keys:
            if k in self.store:
                del self.store[k]
                n += 1
        return n

    def exists(self, key):
        return 1 if key in self.store else 0

    def pipeline(self, transaction=True):
        return _FakePipeline(self)


class _FakePipeline:
    def __init__(self, parent):
        self.parent = parent
        self.ops: list[tuple[str, str]] = []

    def set(self, key, value, ex=None):
        self.ops.append((key, value))
        return self

    def execute(self):
        for k, v in self.ops:
            self.parent.store[k] = v
        self.ops = []


class _FakeDB:
    """최소 mock — commit / rollback / close / execute no-op."""
    def __init__(self) -> None:
        self.committed = 0
        self.rolled_back = 0
        self.closed = False

    def commit(self):
        self.committed += 1

    def rollback(self):
        self.rolled_back += 1

    def close(self):
        self.closed = True

    def execute(self, *args, **kwargs):
        # routes/sia 는 conv_service 통해만 DB 접근. execute 는 mock 불필요지만
        # _run_extraction_job 경로에서 conv_svc.mark_* 내부가 DB 접근할 수 있으니 noop.
        class _Row:
            def scalar(self):
                return 0
            def first(self):
                return None
        return _Row()


class _ConvStore:
    """services.conversations 함수 대체용 in-memory dict."""
    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []
        self.extracted: list[dict[str, Any]] = []
        self.failed: list[dict[str, Any]] = []

    def create_ended_conversation(
        self, db, *, user_id, conversation_id, messages, turn_count,
        started_at_iso, status="ended",
    ):
        self.created.append({
            "conversation_id": conversation_id,
            "user_id": user_id,
            "messages": [m.model_dump(mode="json") for m in messages],
            "turn_count": turn_count,
            "started_at_iso": started_at_iso,
            "status": status,
        })

    def get_conversation(self, db, conversation_id):
        for c in self.created:
            if c["conversation_id"] == conversation_id:
                return c
        return None

    def mark_extracted(self, db, *, conversation_id, user_id, result):
        self.extracted.append({
            "conversation_id": conversation_id,
            "user_id": user_id,
            "result": result,
        })

    def mark_failed(self, db, *, conversation_id, reason=None):
        self.failed.append({
            "conversation_id": conversation_id,
            "reason": reason,
        })


# ─────────────────────────────────────────────
#  Fixtures (pytest)
# ─────────────────────────────────────────────

@pytest.fixture
def fake_redis(monkeypatch):
    import config as config_module
    config_module._settings = None
    config_module._settings = config_module.Settings()

    fake = _FakeRedis()
    from services import sia_session_v4 as sv4
    monkeypatch.setattr(sv4, "get_redis", lambda: fake)
    yield fake
    config_module._settings = None


@pytest.fixture
def conv_store(monkeypatch):
    store = _ConvStore()
    from routes import sia as sia_routes
    from services import conversations as conv_svc
    # routes/sia 에서 from services import conversations as conv_service 로 bind
    monkeypatch.setattr(
        sia_routes.conv_service, "create_ended_conversation",
        store.create_ended_conversation,
    )
    # _run_extraction_job 내부에서 서비스 호출 — 실 모듈 교체
    monkeypatch.setattr(
        conv_svc, "get_conversation", store.get_conversation,
    )
    monkeypatch.setattr(
        conv_svc, "mark_extracted", store.mark_extracted,
    )
    monkeypatch.setattr(
        conv_svc, "mark_failed", store.mark_failed,
    )
    yield store


@pytest.fixture
def mock_haiku(monkeypatch):
    """call_sia_turn_with_retry 를 system_prompt 내용 기반 결정적 응답으로 교체.

    prompt 에 포함된 msg_type 섹션 힌트를 기반으로 "HAIKU:{type}: {last_user}" 형태
    응답 반환. 실제 Anthropic 호출 없음.
    """
    calls: list[dict[str, Any]] = []

    def fake_call(*, system_prompt: str, messages_history: list[dict]) -> str:
        # msg_type 추정: type.md 이름이 prompt 내 헤더에 들어감
        # 예: "# OBSERVATION — Vision 관찰 선언"
        type_hint = "unknown"
        for line in system_prompt.split("\n"):
            if line.startswith("# ") and " — " in line:
                type_hint = line.split("—")[0].lstrip("# ").strip().lower()
                break
        last_user = messages_history[-1]["content"] if messages_history else ""
        reply = f"HAIKU[{type_hint}]: seen '{last_user[:30]}'"
        calls.append({
            "type_hint": type_hint,
            "last_user": last_user,
            "prompt_len": len(system_prompt),
        })
        return reply

    from services import sia_llm
    monkeypatch.setattr(sia_llm, "call_sia_turn_with_retry", fake_call)
    # routes/sia 가 재 import 없이 bound — 모듈 레벨 setattr 로 덮어야 함
    from routes import sia as sia_routes
    monkeypatch.setattr(sia_routes.sia_llm, "call_sia_turn_with_retry", fake_call)
    yield calls


@pytest.fixture
def mock_extraction(monkeypatch):
    """extraction.extract_structured_fields 를 stub 으로 교체."""
    def fake_extract(messages):
        return ExtractionResult(
            fields=StructuredFields(desired_image="E2E test 추출값"),
            fallback_needed=[],
        )
    from services import extraction
    monkeypatch.setattr(
        extraction, "extract_structured_fields", fake_extract,
    )
    yield


@pytest.fixture
def mock_profile(monkeypatch):
    """get_profile 을 fixture profile 반환으로 교체 (user_id 별 프로필)."""
    store: dict[str, dict] = {}

    def set_profile(user_id: str, profile: dict) -> None:
        store[user_id] = profile

    def fake_get_profile(db, user_id):
        return store.get(user_id)

    from services import user_profiles
    monkeypatch.setattr(user_profiles, "get_profile", fake_get_profile)
    from routes import sia as sia_routes
    monkeypatch.setattr(sia_routes, "get_profile", fake_get_profile)
    yield set_profile


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

_DEFAULT_PROFILE = {
    "gender": "female",
    "ig_feed_cache": None,
    "birth_date": "2000-01-01",
    "ig_handle": None,
    "structured_fields": {},
    "onboarding_completed": False,
}


def _user(user_id: str = "u-e2e", name: str = "만재") -> dict:
    return {"id": user_id, "name": name}


_CURRENT_DB: _FakeDB | None = None


@pytest.fixture(autouse=True)
def fake_db(monkeypatch):
    """Autouse — 모든 테스트에 FakeDB 주입 + db.get_db() 교체."""
    global _CURRENT_DB
    _CURRENT_DB = _FakeDB()
    import db as db_mod
    monkeypatch.setattr(db_mod, "get_db", lambda: _CURRENT_DB)
    yield _CURRENT_DB
    _CURRENT_DB = None


def _db():
    """Current test 의 shared FakeDB."""
    assert _CURRENT_DB is not None, "fake_db fixture not active"
    return _CURRENT_DB


def _call_start(user):
    from routes.sia import chat_start
    return chat_start(user=user, db=_db())


def _call_message(conv_id: str, text: str, user):
    from routes.sia import MessageRequest, chat_message
    body = MessageRequest(conversation_id=conv_id, user_message=text)
    bg = BackgroundTasks()
    resp = chat_message(body=body, background_tasks=bg, user=user, db=_db())
    return resp, bg


def _call_end(conv_id: str, user):
    from routes.sia import EndRequest, chat_end
    body = EndRequest(conversation_id=conv_id)
    bg = BackgroundTasks()
    resp = chat_end(body=body, background_tasks=bg, user=user, db=_db())
    # BackgroundTasks 수동 실행 — extraction 트리거
    for task in bg.tasks:
        task.func(**task.kwargs)
    return resp, bg


def _load_state(session_id: str):
    from services import sia_session_v4 as sv4
    return sv4.load_conversation_state(session_id)


# ─────────────────────────────────────────────
#  (A) Basic pipeline smoke
# ─────────────────────────────────────────────

class TestBasicPipelineSmoke:
    def test_chat_start_requires_user_profile(
        self, fake_redis, mock_haiku, mock_profile,
    ):
        """user_profile 없으면 409."""
        u = _user()
        # profile 미등록
        with pytest.raises(HTTPException) as exc:
            _call_start(u)
        assert exc.value.status_code == 409

    def test_chat_start_creates_session_and_opening(
        self, fake_redis, mock_haiku, mock_profile,
    ):
        u = _user()
        mock_profile(u["id"], _DEFAULT_PROFILE)
        resp = _call_start(u)

        assert resp.conversation_id
        assert resp.opening_message  # M1 결합 문자열
        assert resp.turn_count == 0
        # Redis primary + backup 기록
        state = _load_state(resp.conversation_id)
        assert state is not None
        assert state.user_id == u["id"]
        assert len(state.turns) == 1  # M1 combined = 1 assistant turn
        # Haiku 1회 호출 (OBSERVATION secondary)
        assert len(mock_haiku) == 1

    def test_chat_message_advances_turn(
        self, fake_redis, mock_haiku, mock_profile,
    ):
        u = _user()
        mock_profile(u["id"], _DEFAULT_PROFILE)
        start = _call_start(u)

        resp, _ = _call_message(start.conversation_id, "아 네네!", u)
        assert resp.assistant_message
        # turn_count 계산 (user+assistant 왕복 단위): M1(1) + user + assistant = 3 turns, 1 왕복
        assert resp.turn_count >= 1
        state = _load_state(start.conversation_id)
        # M1 + U1 + A2 = 3 turns
        assert len(state.turns) == 3

    def test_chat_end_persists_and_triggers_extraction(
        self, fake_redis, mock_haiku, mock_profile, conv_store, mock_extraction,
    ):
        u = _user()
        mock_profile(u["id"], _DEFAULT_PROFILE)
        start = _call_start(u)
        _call_message(start.conversation_id, "예전에 퍼스널컬러 컨설팅 받았어요", u)

        resp, bg = _call_end(start.conversation_id, u)

        assert resp.status == "ended"
        assert resp.extraction_queued is True
        assert resp.messages_persisted > 0
        # conversations INSERT 호출
        assert len(conv_store.created) == 1
        assert conv_store.created[0]["conversation_id"] == start.conversation_id
        # extraction BackgroundTask 실행 결과 (_call_end 가 수동 실행함)
        assert len(conv_store.extracted) == 1
        # Redis primary + backup 삭제됨
        state = _load_state(start.conversation_id)
        assert state is None

    def test_chat_message_on_expired_session_returns_410(
        self, fake_redis, mock_haiku, mock_profile, conv_store, mock_extraction,
    ):
        u = _user()
        mock_profile(u["id"], _DEFAULT_PROFILE)
        start = _call_start(u)

        # Primary 만 삭제 (backup 유지) — TTL 만료 시뮬
        from services.sia_session import session_key
        del fake_redis.store[session_key(start.conversation_id)]

        # 메시지 전송 → 410 + backup 자동 flush
        with pytest.raises(HTTPException) as exc:
            _call_message(start.conversation_id, "응", u)
        assert exc.value.status_code == 410
        # Backup 이 DB 로 flush 됨
        assert len(conv_store.created) == 1
        assert conv_store.created[0]["status"] == "ended_by_timeout"

    def test_chat_start_with_ig_feed_cache_injects_to_state(
        self, fake_redis, mock_haiku, mock_profile,
    ):
        u = _user()
        ig_cache = {
            "scope": "full",
            "profile_basics": {"username": "e2e"},
            "analysis": {"tone_category": "쿨뮤트", "tone_percentage": 68},
        }
        profile = dict(_DEFAULT_PROFILE, ig_feed_cache=ig_cache)
        mock_profile(u["id"], profile)

        start = _call_start(u)
        state = _load_state(start.conversation_id)
        assert state.ig_feed_cache is not None
        assert state.ig_feed_cache["scope"] == "full"
        assert state.gender == "female"


# ─────────────────────────────────────────────
#  (B) 만재 시나리오 — A-3 트리거 시퀀스
# ─────────────────────────────────────────────

class TestManjaeFlow:
    """만재 fixture 의 유저 발화 시퀀스를 주입, decide() 결과 트레이싱."""

    def test_emotion_trigger_then_concede_produces_empathy_mirror(
        self, fake_redis, mock_haiku, mock_profile,
    ):
        u = _user(user_id="u-manjae", name="만재")
        mock_profile(u["id"], _DEFAULT_PROFILE)
        start = _call_start(u)
        cid = start.conversation_id

        # M2: "예전에 퍼스널컬러..." — 무 트리거 (obs_count=1 이므로 obs shortage cycle)
        _call_message(cid, "예전에 퍼스널컬러 컨설팅 받았는데 거기서 그런계열의 톤으로 맞추라고 했어요", u)
        # M3: "봄 웜톤이요" — short 이지만 content 있음
        _call_message(cid, "봄 웜톤이요", u)
        # M4: "코랄은 입어보면 좀 튀어서요. 어색하더라구요" — 감정 "어색"
        _call_message(cid, "코랄은 입어보면 좀 튀어서요. 어색하더라구요", u)

        state = _load_state(cid)
        # 마지막 assistant 턴은 EMPATHY_MIRROR (A-3 감정 트리거)
        last_a = state.last_assistant()
        assert last_a is not None
        assert last_a.msg_type == MsgType.EMPATHY_MIRROR

    def test_meta_rebuttal_fires_once_then_falls_through(
        self, fake_redis, mock_haiku, mock_profile,
    ):
        u = _user()
        mock_profile(u["id"], _DEFAULT_PROFILE)
        start = _call_start(u)
        cid = start.conversation_id

        # 메타 반박 발화
        _call_message(cid, "MBTI 같은 거 아녜요 그거", u)
        state = _load_state(cid)
        assert state.last_assistant().msg_type == MsgType.META_REBUTTAL
        assert state.meta_rebuttal_used is True

        # 두 번째 메타 반박 — 이미 사용했으므로 다른 타입으로 떨어짐
        _call_message(cid, "AI 가 뭘 알아요 MBTI 같은 거나 맞추는 거죠", u)
        state = _load_state(cid)
        last = state.last_assistant()
        assert last.msg_type != MsgType.META_REBUTTAL


# ─────────────────────────────────────────────
#  (C) 준호 시나리오 — A-9 → CHECK_IN → RE_ENTRY
# ─────────────────────────────────────────────

class TestJunhoManagementBucket:
    def test_three_trivial_replies_trigger_check_in(
        self, fake_redis, mock_haiku, mock_profile,
    ):
        u = _user(user_id="u-junho", name="준호")
        mock_profile(u["id"], _DEFAULT_PROFILE)
        start = _call_start(u)
        cid = start.conversation_id

        # trivial 3연속 → streak 3 → CHECK_IN
        _call_message(cid, "네", u)
        _call_message(cid, "잘 모르겠어요", u)
        _call_message(cid, "네", u)

        state = _load_state(cid)
        assert state.trivial_streak == 3
        assert state.last_assistant().msg_type == MsgType.CHECK_IN

    def test_check_in_then_response_triggers_re_entry(
        self, fake_redis, mock_haiku, mock_profile,
    ):
        u = _user(user_id="u-junho2", name="준호")
        mock_profile(u["id"], _DEFAULT_PROFILE)
        start = _call_start(u)
        cid = start.conversation_id

        # 3연속 단답 → CHECK_IN
        _call_message(cid, "네", u)
        _call_message(cid, "응", u)
        _call_message(cid, "ㅎㅎ", u)

        # CHECK_IN 후 자기 설명 발화 → RE_ENTRY (exit_confirmed=False)
        _call_message(cid, "아뇨 그냥 할 말이 별로 없어서요", u)

        state = _load_state(cid)
        last = state.last_assistant()
        assert last.msg_type == MsgType.RE_ENTRY

    def test_check_in_then_exit_signal_sets_exit_confirmed(
        self, fake_redis, mock_haiku, mock_profile,
    ):
        u = _user(user_id="u-junho3", name="준호")
        mock_profile(u["id"], _DEFAULT_PROFILE)
        start = _call_start(u)
        cid = start.conversation_id

        # 3연속 trivial → CHECK_IN
        _call_message(cid, "네", u)
        _call_message(cid, "응", u)
        _call_message(cid, "ㅇㅇ", u)

        # CHECK_IN 직후 이탈 선언 → RE_ENTRY V5 종결 (exit_confirmed=True)
        _call_message(cid, "나중에 할게요", u)

        state = _load_state(cid)
        last = state.last_assistant()
        assert last.msg_type == MsgType.RE_ENTRY
        # V5 종결 텍스트 식별 — "언제든 돌아오시면" 포함
        assert "언제든 돌아오시면" in last.text


# ─────────────────────────────────────────────
#  (D) 도윤 시나리오 — C7 일반화 회피 자동 감지
# ─────────────────────────────────────────────

class TestDoyoonConfrontationBlocks:
    def test_generalization_trigger_produces_c7(
        self, fake_redis, mock_haiku, mock_profile,
    ):
        u = _user(user_id="u-doyoon", name="도윤")
        mock_profile(u["id"], _DEFAULT_PROFILE)
        start = _call_start(u)
        cid = start.conversation_id

        _call_message(cid, "뭐 다들 그런 거 아닌가요", u)
        state = _load_state(cid)
        last = state.last_assistant()
        assert last.msg_type == MsgType.CONFRONTATION
        # HAIKU mock 응답 안에 type_hint 로 "confrontation" 들어감
        assert "confrontation" in last.text.lower() or last.msg_type == MsgType.CONFRONTATION

    def test_overattachment_severe_triggers_range_disclosure(
        self, fake_redis, mock_haiku, mock_profile,
    ):
        u = _user(user_id="u-over", name="유저")
        mock_profile(u["id"], _DEFAULT_PROFILE)
        start = _call_start(u)
        cid = start.conversation_id

        _call_message(cid, "들어줄 사람 없었는데 네가 진짜 나 잘 아네", u)
        state = _load_state(cid)
        last = state.last_assistant()
        assert last.msg_type == MsgType.RANGE_DISCLOSURE
        assert state.overattachment_severity == "severe"


# ─────────────────────────────────────────────
#  (E) 한계: extraction failure 경로
# ─────────────────────────────────────────────

class TestExtractionFailure:
    def test_extraction_error_marks_failed(
        self, fake_redis, mock_haiku, mock_profile, conv_store, monkeypatch,
    ):
        """extract 중 ExtractionError → mark_failed 경로."""
        from services import extraction

        def raise_extraction(messages):
            raise extraction.ExtractionError("simulated failure")

        monkeypatch.setattr(
            extraction, "extract_structured_fields", raise_extraction,
        )

        u = _user()
        mock_profile(u["id"], _DEFAULT_PROFILE)
        start = _call_start(u)
        _call_message(start.conversation_id, "테스트 메시지", u)
        _call_end(start.conversation_id, u)

        assert len(conv_store.failed) == 1
        assert "simulated failure" in (conv_store.failed[0]["reason"] or "")
        assert len(conv_store.extracted) == 0
