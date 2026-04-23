"""Sia session v3 extensions 테스트 — Phase B2.

parse_spectrum_choice / record_spectrum_choice / decide_next_turn.
fakeredis 없이 Redis 호출 부분은 monkey-patch 로 격리.
"""
from __future__ import annotations

import sys
import os
import json
from datetime import datetime, timezone
from typing import Optional

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services import sia_session


# ─────────────────────────────────────────────
#  parse_spectrum_choice — canonical
# ─────────────────────────────────────────────

def test_parse_spectrum_canonical_exact_match():
    assert sia_session.parse_spectrum_choice("네, 비슷하다") == 1
    assert sia_session.parse_spectrum_choice("절반 정도 맞다") == 2
    assert sia_session.parse_spectrum_choice("다르다") == 3
    assert sia_session.parse_spectrum_choice("전혀 다르다") == 4


def test_parse_spectrum_canonical_trims_whitespace():
    assert sia_session.parse_spectrum_choice("  다르다  ") == 3
    assert sia_session.parse_spectrum_choice("\n전혀 다르다\n") == 4


# ─────────────────────────────────────────────
#  parse_spectrum_choice — fuzzy
# ─────────────────────────────────────────────

def test_parse_spectrum_fuzzy_jeonhyeo_beats_dareu():
    """'전혀 다르다'는 '다르' 보다 '전혀' 우선순위가 높아 4 로 분류."""
    assert sia_session.parse_spectrum_choice("이건 전혀 다릅니다") == 4


def test_parse_spectrum_fuzzy_half_beats_dareu():
    """'반은 맞고 반은 다릅니다' — 복합문이지만 절반 우선 → 2."""
    assert sia_session.parse_spectrum_choice("반은 맞고 반은 다릅니다") == 2


def test_parse_spectrum_fuzzy_agree_variations():
    assert sia_session.parse_spectrum_choice("네 비슷한 것 같아요") == 1
    assert sia_session.parse_spectrum_choice("맞는 것 같습니다") == 1


def test_parse_spectrum_fuzzy_disagree_without_jeonhyeo():
    assert sia_session.parse_spectrum_choice("다른 편입니다") == 3


def test_parse_spectrum_fuzzy_anmat_not_agree():
    """'안 맞' 는 동의 아님 → 1 로 분류되지 않아야."""
    result = sia_session.parse_spectrum_choice("별로 안 맞습니다")
    assert result != 1


def test_parse_spectrum_returns_none_for_non_spectrum_text():
    assert sia_session.parse_spectrum_choice("세련되고 거리감 있는 인상") is None
    assert sia_session.parse_spectrum_choice("") is None
    assert sia_session.parse_spectrum_choice("   ") is None


# ─────────────────────────────────────────────
#  decide_next_turn — turn mapping
# ─────────────────────────────────────────────

def _state(turn_count: int, spectrum_log=None, misses: int = 0, hits: int = 0) -> dict:
    return {
        "turn_count": turn_count,
        "spectrum_log": spectrum_log or [],
        "precision_hits": hits,
        "precision_misses": misses,
    }


def test_decide_next_turn_zero_is_opening():
    assert sia_session.decide_next_turn(_state(0)) == "opening"


def test_decide_next_turn_internal_spectrum_1_to_4():
    assert sia_session.decide_next_turn(_state(1, [1])) == "branch_agree"
    assert sia_session.decide_next_turn(_state(1, [2])) == "branch_half"
    assert sia_session.decide_next_turn(_state(1, [3], misses=1)) == "branch_disagree"
    assert sia_session.decide_next_turn(_state(1, [4], misses=1)) == "branch_fail"


def test_decide_next_turn_precision_continue_when_no_spectrum():
    """내적 구간인데 spectrum 파싱 실패 — 안전 재시도."""
    assert sia_session.decide_next_turn(_state(2)) == "precision_continue"


def test_decide_next_turn_three_misses_forces_external():
    state = _state(3, [3, 4, 3], misses=3)
    assert sia_session.decide_next_turn(state) == "force_external_transition"


def test_decide_next_turn_two_misses_still_internal():
    """miss 2 회까지는 내적 계속."""
    state = _state(2, [3, 4], misses=2)
    assert sia_session.decide_next_turn(state) == "branch_fail"


def test_decide_next_turn_external_sequence():
    mapping = {
        4: "external_desired_image",
        5: "external_reference",
        6: "external_body_height",
        7: "external_body_weight",
        8: "external_body_shoulder",
        9: "external_concerns",
        10: "external_lifestyle",
    }
    for tc, expected in mapping.items():
        assert sia_session.decide_next_turn(_state(tc)) == expected, tc


def test_decide_next_turn_closing_at_11_plus():
    assert sia_session.decide_next_turn(_state(11)) == "closing"
    assert sia_session.decide_next_turn(_state(14)) == "closing"
    assert sia_session.decide_next_turn(_state(30)) == "closing"


def test_decide_next_turn_missing_spectrum_fields_defaults():
    """legacy state (spectrum_log / precision_* 없음) 도 깨지지 않음."""
    legacy = {"turn_count": 1}   # 신규 필드 전부 없음
    assert sia_session.decide_next_turn(legacy) == "precision_continue"


# ─────────────────────────────────────────────
#  record_spectrum_choice — Redis stub
# ─────────────────────────────────────────────

class _FakeRedis:
    """최소 Redis stub — get / pipeline (transaction) 만 구현."""

    def __init__(self):
        self.store: dict[str, str] = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ex=None):
        self.store[key] = value

    def pipeline(self, transaction=True):
        return _FakePipeline(self)


class _FakePipeline:
    def __init__(self, parent: _FakeRedis):
        self.parent = parent
        self.ops: list[tuple[str, str]] = []

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
    config_module._settings = None  # reset for deterministic TTL
    config_module._settings = config_module.Settings()

    fake = _FakeRedis()
    monkeypatch.setattr(sia_session, "get_redis", lambda: fake)
    yield fake
    config_module._settings = None


def _seed_session(fake: _FakeRedis, cid: str = "c1") -> dict:
    state = {
        "conversation_id": cid,
        "user_id": "u1",
        "turn_count": 1,
        "messages": [],
        "collected_fields": {},
        "missing_fields": [],
        "resolved_name": None,
        "ig_feed_cache": None,
        "status": "active",
        "spectrum_log": [],
        "precision_hits": 0,
        "precision_misses": 0,
        "created_at": "2026-04-22T00:00:00+00:00",
        "updated_at": "2026-04-22T00:00:00+00:00",
    }
    fake.store[sia_session.session_key(cid)] = json.dumps(state, ensure_ascii=False)
    return state


def test_record_spectrum_choice_agree_increments_hits(fake_redis):
    _seed_session(fake_redis)
    new_state = sia_session.record_spectrum_choice(
        conversation_id="c1",
        user_message="네, 비슷하다",
    )
    assert new_state is not None
    assert new_state["spectrum_log"] == [1]
    assert new_state["precision_hits"] == 1
    assert new_state["precision_misses"] == 0


def test_record_spectrum_choice_disagree_increments_misses(fake_redis):
    _seed_session(fake_redis)
    new_state = sia_session.record_spectrum_choice(
        conversation_id="c1",
        user_message="전혀 다르다",
    )
    assert new_state["spectrum_log"] == [4]
    assert new_state["precision_hits"] == 0
    assert new_state["precision_misses"] == 1


def test_record_spectrum_choice_appends_cumulatively(fake_redis):
    _seed_session(fake_redis)
    sia_session.record_spectrum_choice(conversation_id="c1", user_message="비슷하다")
    sia_session.record_spectrum_choice(conversation_id="c1", user_message="절반")
    final = sia_session.record_spectrum_choice(conversation_id="c1", user_message="전혀 다르다")
    assert final["spectrum_log"] == [1, 2, 4]
    assert final["precision_hits"] == 2
    assert final["precision_misses"] == 1


def test_record_spectrum_choice_returns_none_when_parse_fails(fake_redis):
    _seed_session(fake_redis)
    result = sia_session.record_spectrum_choice(
        conversation_id="c1",
        user_message="세련되고 거리감 있는 인상",
    )
    assert result is None


def test_record_spectrum_choice_returns_none_when_session_missing(fake_redis):
    # session 이 Redis 에 없음
    result = sia_session.record_spectrum_choice(
        conversation_id="does-not-exist",
        user_message="다르다",
    )
    assert result is None
