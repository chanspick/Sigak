"""Phase H1 — sia_state / sia_session_v4 테스트.

범위:
  - MsgType 그룹핑 (COLLECTION / UNDERSTANDING / WHITESPACE / CONFRONT)
  - UserMessageFlags / UserTurn / AssistantTurn 기본
  - ConversationState 쿼리 메서드 (last_user / assistant_turns / last_k_assistant)
  - 창 카운터 (jangayo_window_count / has_neyo_or_deoraguyo_in_window)
  - Redis round-trip (to_dict / from_dict)
  - sia_session_v4 create/load/save/delete with FakeRedis
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schemas.sia_state import (
    COLLECTION,
    CONFRONT,
    HAIKU_TYPES,
    HARDCODED_TYPES,
    QUESTION_FORBIDDEN,
    QUESTION_REQUIRED,
    UNDERSTANDING,
    WHITESPACE,
    AssistantTurn,
    ConversationState,
    MsgType,
    UserMessageFlags,
    UserTurn,
)


# ─────────────────────────────────────────────
#  MsgType 그룹핑
# ─────────────────────────────────────────────

def test_msg_type_count_is_eleven():
    """HOOK 삭제 후 11개 타입 유지."""
    assert len(list(MsgType)) == 11


def test_group_coverage_is_full_and_disjoint():
    """그룹 4개가 11개 전부를 덮고 교집합 없음."""
    all_grouped = COLLECTION | UNDERSTANDING | WHITESPACE | CONFRONT
    assert all_grouped == set(MsgType)

    pairs = [
        (COLLECTION, UNDERSTANDING),
        (COLLECTION, WHITESPACE),
        (COLLECTION, CONFRONT),
        (UNDERSTANDING, WHITESPACE),
        (UNDERSTANDING, CONFRONT),
        (WHITESPACE, CONFRONT),
    ]
    for a, b in pairs:
        assert not (a & b), f"group intersection: {a & b}"


def test_hardcoded_vs_haiku_partition():
    """하드코딩 4 + Haiku 7 = 11, 교집합 0."""
    assert len(HARDCODED_TYPES) == 4
    assert len(HAIKU_TYPES) == 7
    assert not (HARDCODED_TYPES & HAIKU_TYPES)
    assert (HARDCODED_TYPES | HAIKU_TYPES) == set(MsgType)


def test_question_required_forbidden_partition():
    """질문 required / forbidden 이 11개 전부 커버 + 교집합 0."""
    assert not (QUESTION_REQUIRED & QUESTION_FORBIDDEN)
    assert (QUESTION_REQUIRED | QUESTION_FORBIDDEN) == set(MsgType)


# ─────────────────────────────────────────────
#  UserMessageFlags / UserTurn / AssistantTurn
# ─────────────────────────────────────────────

def test_flags_default_all_false():
    f = UserMessageFlags()
    for attr in (
        "has_concede", "has_emotion_word", "has_tt",
        "has_explain_req", "has_meta_challenge",
        "has_evidence_doubt", "has_self_disclosure", "is_defensive",
    ):
        assert getattr(f, attr) is False
    assert f.emotion_word_raw is None


def test_user_turn_default_flags_independent():
    """각 UserTurn 의 flags 가 서로 다른 인스턴스."""
    a = UserTurn(text="a", turn_idx=0)
    b = UserTurn(text="b", turn_idx=1)
    a.flags.has_tt = True
    assert b.flags.has_tt is False


def test_assistant_turn_counts_default_zero():
    t = AssistantTurn(text="정세현님 피드 봤어요", msg_type=MsgType.OPENING_DECLARATION, turn_idx=0)
    assert t.jangayo_count == 0
    assert t.yeyo_count == 0
    assert t.neyo_count == 0
    assert t.deoraguyo_count == 0
    assert t.observed_axes == []


# ─────────────────────────────────────────────
#  ConversationState queries
# ─────────────────────────────────────────────

def _state_with_pattern() -> ConversationState:
    """assistant-user-assistant-user-assistant 패턴."""
    s = ConversationState(
        session_id="s1", user_id="u1", user_name="정세현",
    )
    s.turns.append(AssistantTurn(
        text="정세현님 피드 돌아봤어요",
        msg_type=MsgType.OPENING_DECLARATION, turn_idx=0,
    ))
    s.turns.append(UserTurn(text="네", turn_idx=1))
    s.turns.append(AssistantTurn(
        text="정물 위주더라구요, 원래 그런 편이에요?",
        msg_type=MsgType.OBSERVATION, turn_idx=2, deoraguyo_count=1,
    ))
    s.turns.append(UserTurn(text="아 맞아요", turn_idx=3))
    s.turns.append(AssistantTurn(
        text="색도 베이지만 쓰시는 편이잖아요?",
        msg_type=MsgType.OBSERVATION, turn_idx=4, jangayo_count=1,
    ))
    return s


def test_state_query_helpers():
    s = _state_with_pattern()
    assert len(s.assistant_turns()) == 3
    assert len(s.user_turns()) == 2
    assert s.last_user().text == "아 맞아요"
    assert s.last_assistant().text.startswith("색도 베이지")


def test_last_k_assistant_clipping():
    s = _state_with_pattern()
    assert len(s.last_k_assistant(2)) == 2
    assert len(s.last_k_assistant(10)) == 3


def test_jangayo_window_counts_last_three():
    s = ConversationState(session_id="s", user_id="u", user_name="n")
    s.turns.extend([
        AssistantTurn("a1", MsgType.OBSERVATION, 0, jangayo_count=1),
        AssistantTurn("a2", MsgType.OBSERVATION, 1, jangayo_count=0),
        AssistantTurn("a3", MsgType.OBSERVATION, 2, jangayo_count=2),
        AssistantTurn("a4", MsgType.OBSERVATION, 3, jangayo_count=0),   # window 에서 탈락
    ])
    # window 는 [a2, a3, a4] — 합 2
    assert s.jangayo_window_count == 2


def test_has_neyo_or_deoraguyo_in_window():
    s = ConversationState(session_id="s", user_id="u", user_name="n")
    s.turns.extend([
        AssistantTurn("a1", MsgType.OBSERVATION, 0, neyo_count=0, deoraguyo_count=0),
        AssistantTurn("a2", MsgType.OBSERVATION, 1, deoraguyo_count=1),
        AssistantTurn("a3", MsgType.OBSERVATION, 2, neyo_count=0),
    ])
    assert s.has_neyo_or_deoraguyo_in_window is True

    s2 = ConversationState(session_id="s", user_id="u", user_name="n")
    s2.turns.extend([
        AssistantTurn("a1", MsgType.OBSERVATION, 0),
        AssistantTurn("a2", MsgType.OBSERVATION, 1),
    ])
    assert s2.has_neyo_or_deoraguyo_in_window is False


# ─────────────────────────────────────────────
#  Round-trip (Redis JSON)
# ─────────────────────────────────────────────

def test_round_trip_preserves_turns_and_counters():
    s = _state_with_pattern()
    s.observation_count = 2
    s.meta_rebuttal_used = True
    s.collected_fields = {"body_shape": "상체", "desired_image_keywords": ["차분함"]}
    s.type_counts = {
        MsgType.OBSERVATION: 2,
        MsgType.OPENING_DECLARATION: 1,
    }

    d = s.to_dict()
    # type_counts key 는 str 로 내려가야 함
    assert "observation" in d["type_counts"]
    restored = ConversationState.from_dict(d)

    assert restored.session_id == s.session_id
    assert len(restored.turns) == len(s.turns)
    # UserTurn vs AssistantTurn 타입 보존
    assert isinstance(restored.turns[0], AssistantTurn)
    assert isinstance(restored.turns[1], UserTurn)
    # MsgType enum 역매핑
    assert restored.turns[0].msg_type == MsgType.OPENING_DECLARATION
    # 어미 카운트 보존
    assert restored.turns[2].deoraguyo_count == 1
    # flags 보존
    assert restored.last_user().text == "아 맞아요"
    # counter/fields
    assert restored.observation_count == 2
    assert restored.meta_rebuttal_used is True
    assert restored.collected_fields["body_shape"] == "상체"
    assert restored.type_counts[MsgType.OBSERVATION] == 2


def test_round_trip_unknown_type_count_key_skipped():
    """type_counts 에 unknown MsgType 값이 들어와도 파싱 실패 없음."""
    d = {
        "session_id": "s", "user_id": "u", "user_name": "n",
        "turns": [],
        "type_counts": {"observation": 1, "__future_type__": 9},
    }
    state = ConversationState.from_dict(d)
    assert state.type_counts.get(MsgType.OBSERVATION) == 1
    # unknown 은 누락
    assert len(state.type_counts) == 1


def test_round_trip_user_flags_preserved():
    s = ConversationState(session_id="s", user_id="u", user_name="n")
    u = UserTurn(text="어떻게 알아요ㅠㅠ", turn_idx=0)
    u.flags.has_tt = True
    u.flags.has_evidence_doubt = True
    u.flags.has_emotion_word = True
    u.flags.emotion_word_raw = "부담"
    s.turns.append(u)

    restored = ConversationState.from_dict(s.to_dict())
    lu = restored.last_user()
    assert lu.flags.has_tt
    assert lu.flags.has_evidence_doubt
    assert lu.flags.has_emotion_word
    assert lu.flags.emotion_word_raw == "부담"


# ─────────────────────────────────────────────
#  sia_session_v4 — FakeRedis E2E
# ─────────────────────────────────────────────

class _FakeRedis:
    def __init__(self):
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
        self.ops = []

    def set(self, key, value, ex=None):
        self.ops.append((key, value))
        return self

    def execute(self):
        for k, v in self.ops:
            self.parent.store[k] = v
        self.ops = []


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


def test_create_conversation_state_seeds_redis(fake_redis):
    from services import sia_session_v4 as sv4
    state = sv4.create_conversation_state(
        session_id="c1", user_id="u1", user_name="정세현",
    )
    assert state.session_id == "c1"
    # primary + backup 모두 기록
    from services.sia_session import session_key, _backup_key
    assert session_key("c1") in fake_redis.store
    assert _backup_key("c1") in fake_redis.store


def test_create_idempotent_returns_existing(fake_redis):
    from services import sia_session_v4 as sv4
    first = sv4.create_conversation_state(
        session_id="c2", user_id="u1", user_name="정세현",
    )
    first.observation_count = 7
    sv4.save_conversation_state(first)
    second = sv4.create_conversation_state(
        session_id="c2", user_id="u1", user_name="정세현",
    )
    assert second.observation_count == 7


def test_save_and_load_round_trip(fake_redis):
    from services import sia_session_v4 as sv4
    state = sv4.create_conversation_state(
        session_id="c3", user_id="u1", user_name="만재",
    )
    state.turns.append(AssistantTurn(
        text="만재님 피드 돌아봤어요",
        msg_type=MsgType.OPENING_DECLARATION, turn_idx=0,
    ))
    state.observation_count = 1
    sv4.save_conversation_state(state)

    loaded = sv4.load_conversation_state("c3")
    assert loaded is not None
    assert loaded.user_name == "만재"
    assert loaded.observation_count == 1
    assert loaded.turns[0].text.startswith("만재님")


def test_delete_conversation_state_removes_both(fake_redis):
    from services import sia_session_v4 as sv4
    sv4.create_conversation_state(
        session_id="c4", user_id="u1", user_name="x",
    )
    from services.sia_session import session_key, _backup_key
    assert session_key("c4") in fake_redis.store
    assert _backup_key("c4") in fake_redis.store

    existed = sv4.delete_conversation_state("c4")
    assert existed is True
    assert session_key("c4") not in fake_redis.store
    assert _backup_key("c4") not in fake_redis.store


def test_get_backup_state_independent_of_primary(fake_redis):
    """primary 삭제 후에도 backup 만 살아있으면 복구 가능해야."""
    from services import sia_session_v4 as sv4
    from services.sia_session import session_key
    sv4.create_conversation_state(
        session_id="c5", user_id="u1", user_name="x",
    )
    # primary 만 지움 (backup 유지)
    del fake_redis.store[session_key("c5")]

    primary = sv4.load_conversation_state("c5")
    backup = sv4.get_backup_state("c5")
    assert primary is None
    assert backup is not None
    assert backup.session_id == "c5"


def test_load_missing_returns_none(fake_redis):
    from services import sia_session_v4 as sv4
    assert sv4.load_conversation_state("nonexistent") is None
    assert sv4.get_backup_state("nonexistent") is None
