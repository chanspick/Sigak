"""Phase H3 — validator v4 (A-1 ~ A-8) 테스트.

각 규칙 positive/negative + 어미 카운트 helper.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schemas.sia_state import (
    AssistantTurn,
    ConversationState,
    MsgType,
)
from services.sia_validators_v4 import (
    A2_JANGAYO_WINDOW_MAX,
    A3_DEORAGUYO_WINDOW_MAX,
    count_deoraguyo,
    count_jangayo,
    count_neyo,
    count_yeyo,
    find_violations_v4,
    populate_turn_counts,
)


# ─────────────────────────────────────────────
#  fixtures
# ─────────────────────────────────────────────

def _state_with_assistant_turns(turns: list[AssistantTurn]) -> ConversationState:
    s = ConversationState(
        session_id="sess-h3",
        user_id="user-h3",
        user_name="만재",
    )
    s.turns = list(turns)
    return s


def _atn(
    msg_type: MsgType,
    text: str = "관찰 본문입니다",
    idx: int = 0,
    jangayo: int = 0,
    deoraguyo: int = 0,
    neyo: int = 0,
) -> AssistantTurn:
    return AssistantTurn(
        text=text,
        msg_type=msg_type,
        turn_idx=idx,
        jangayo_count=jangayo,
        deoraguyo_count=deoraguyo,
        neyo_count=neyo,
    )


# ─────────────────────────────────────────────
#  어미 카운트 helpers
# ─────────────────────────────────────────────

class TestSuffixCounters:
    def test_count_jangayo(self):
        assert count_jangayo("이미 아시잖아요") == 1
        assert count_jangayo("그렇잖아요 그치 잖아요") == 2
        assert count_jangayo("평범한 문장") == 0

    def test_count_deoraguyo(self):
        assert count_deoraguyo("자주 그러시더라구요") == 1
        assert count_deoraguyo("없음") == 0

    def test_count_neyo(self):
        assert count_neyo("좋네요") == 1
        assert count_neyo("네요 네요 네요") == 3
        assert count_neyo("없음") == 0

    def test_count_yeyo(self):
        # 참고용 — 예요/에요 단순 카운트
        assert count_yeyo("커피예요") == 1
        assert count_yeyo("학생이에요") == 1
        assert count_yeyo("없음") == 0


# ─────────────────────────────────────────────
#  A-1 금지 어미
# ─────────────────────────────────────────────

class TestA1ForbiddenSuffix:
    def test_catches_neyo(self):
        v = find_violations_v4("방해가 있으신가 보네요?", MsgType.OBSERVATION)
        assert "a1_forbidden_suffix" in v

    def test_catches_gunyo(self):
        v = find_violations_v4("그러시는군요?", MsgType.RECOGNITION)
        assert "a1_forbidden_suffix" in v

    def test_catches_gatayo(self):
        v = find_violations_v4("그런 것 같아요?", MsgType.PROBE)
        assert "a1_forbidden_suffix" in v

    def test_catches_gatseumnida(self):
        v = find_violations_v4("그런 것 같습니다.", MsgType.DIAGNOSIS)
        assert "a1_forbidden_suffix" in v

    def test_catches_su_itseumnida(self):
        v = find_violations_v4("그러실 수 있습니다.", MsgType.DIAGNOSIS)
        assert "a1_forbidden_suffix" in v

    def test_allows_geos_gateunde(self):
        # "것 같은데" 는 허용 표현 — false positive 금지
        v = find_violations_v4(
            "편안한 자리이신 것 같은데 맞으실까요?", MsgType.PROBE,
        )
        assert "a1_forbidden_suffix" not in v

    def test_allows_jangayo(self):
        v = find_violations_v4("아시잖아요?", MsgType.PROBE)
        assert "a1_forbidden_suffix" not in v

    def test_allows_deoraguyo(self):
        v = find_violations_v4("편하시더라구요?", MsgType.OBSERVATION)
        assert "a1_forbidden_suffix" not in v


# ─────────────────────────────────────────────
#  A-2 잖아요 창
# ─────────────────────────────────────────────

class TestA2JangayoWindow:
    def test_allow_within_limit(self):
        prev = [
            _atn(MsgType.OBSERVATION, jangayo=1, idx=0),
            _atn(MsgType.PROBE, jangayo=0, idx=1),
        ]
        state = _state_with_assistant_turns(prev)
        # current = 1 → window sum = 2 (한계 포함 OK)
        v = find_violations_v4(
            "아시잖아요?", MsgType.PROBE, state=state,
        )
        assert "a2_jangayo_window" not in v

    def test_block_over_limit(self):
        prev = [
            _atn(MsgType.OBSERVATION, jangayo=1, idx=0),
            _atn(MsgType.PROBE, jangayo=1, idx=1),
        ]
        state = _state_with_assistant_turns(prev)
        # current = 1 → window sum = 3 > 2
        v = find_violations_v4(
            "이미 그렇잖아요?", MsgType.PROBE, state=state,
        )
        assert "a2_jangayo_window" in v

    def test_no_state_skips_window(self):
        v = find_violations_v4(
            "잖아요 잖아요 잖아요?", MsgType.PROBE, state=None,
        )
        # 현재 턴만: current=3 > 2 → 차단
        assert "a2_jangayo_window" in v

    def test_limit_constant(self):
        assert A2_JANGAYO_WINDOW_MAX == 2


# ─────────────────────────────────────────────
#  A-3 더라구요 창
# ─────────────────────────────────────────────

class TestA3DeoraguyoWindow:
    def test_allow_single(self):
        prev = [
            _atn(MsgType.OBSERVATION, deoraguyo=0, idx=0),
            _atn(MsgType.PROBE, deoraguyo=0, idx=1),
        ]
        state = _state_with_assistant_turns(prev)
        v = find_violations_v4(
            "편하시더라구요?", MsgType.OBSERVATION, state=state,
        )
        assert "a3_deoraguyo_window" not in v

    def test_block_double(self):
        prev = [
            _atn(MsgType.OBSERVATION, deoraguyo=1, idx=0),
            _atn(MsgType.PROBE, deoraguyo=0, idx=1),
        ]
        state = _state_with_assistant_turns(prev)
        v = find_violations_v4(
            "평소에 그러시더라구요?", MsgType.OBSERVATION, state=state,
        )
        assert "a3_deoraguyo_window" in v

    def test_limit_constant(self):
        assert A3_DEORAGUYO_WINDOW_MAX == 1


# ─────────────────────────────────────────────
#  A-4 같은 타입 3연속
# ─────────────────────────────────────────────

class TestA4SameTypeStreak:
    def test_allow_two_streak(self):
        prev = [
            _atn(MsgType.PROBE, idx=0),
        ]
        state = _state_with_assistant_turns(prev)
        v = find_violations_v4(
            "편하신 자리이신가봐요?", MsgType.PROBE, state=state,
        )
        assert "a4_same_type_streak" not in v

    def test_block_three_streak(self):
        prev = [
            _atn(MsgType.OBSERVATION, idx=0),
            _atn(MsgType.OBSERVATION, idx=1),
        ]
        state = _state_with_assistant_turns(prev)
        v = find_violations_v4(
            "편해 보이시는가봐요?", MsgType.OBSERVATION, state=state,
        )
        assert "a4_same_type_streak" in v

    def test_different_types_pass(self):
        prev = [
            _atn(MsgType.OBSERVATION, idx=0),
            _atn(MsgType.PROBE, idx=1),
        ]
        state = _state_with_assistant_turns(prev)
        v = find_violations_v4(
            "편해 보이시는가봐요?", MsgType.OBSERVATION, state=state,
        )
        assert "a4_same_type_streak" not in v

    def test_no_state_skips(self):
        v = find_violations_v4(
            "편해 보이시는가봐요?", MsgType.OBSERVATION, state=None,
        )
        assert "a4_same_type_streak" not in v


# ─────────────────────────────────────────────
#  A-5 질문 누락 / A-6 질문 금지
# ─────────────────────────────────────────────

class TestA5QuestionMissing:
    def test_observation_requires_question(self):
        v = find_violations_v4(
            "편해 보이시는가봐요.", MsgType.OBSERVATION,
        )
        assert "a5_question_missing" in v

    def test_observation_with_question_ok(self):
        v = find_violations_v4(
            "편해 보이시는가봐요?", MsgType.OBSERVATION,
        )
        assert "a5_question_missing" not in v

    def test_diagnosis_no_requirement(self):
        v = find_violations_v4(
            "자리의 편안함을 우선하시는 쪽입니다.", MsgType.DIAGNOSIS,
        )
        assert "a5_question_missing" not in v

    def test_recognition_requires_question(self):
        v = find_violations_v4(
            "그 결이 계속 읽히세요.", MsgType.RECOGNITION,
        )
        assert "a5_question_missing" in v


class TestA6QuestionForbidden:
    def test_diagnosis_forbids_question(self):
        v = find_violations_v4(
            "자리 우선형이신 것이 맞을까요?", MsgType.DIAGNOSIS,
        )
        assert "a6_question_forbidden" in v

    def test_empathy_mirror_forbids_question(self):
        v = find_violations_v4(
            "부담이 크셨겠어요?", MsgType.EMPATHY_MIRROR,
        )
        assert "a6_question_forbidden" in v

    def test_soft_walkback_forbids_question(self):
        v = find_violations_v4(
            "방금은 제가 과했어요?", MsgType.SOFT_WALKBACK,
        )
        assert "a6_question_forbidden" in v


# ─────────────────────────────────────────────
#  A-7 EMPATHY_MIRROR 원어 반사
# ─────────────────────────────────────────────

class TestA7EmotionMirror:
    def test_echoes_word_ok(self):
        v = find_violations_v4(
            "부담이 많이 쌓이셨어요.", MsgType.EMPATHY_MIRROR,
            emotion_word_raw="부담",
        )
        assert "a7_emotion_mirror_miss" not in v

    def test_missing_echo_blocks(self):
        v = find_violations_v4(
            "힘드셨겠어요.", MsgType.EMPATHY_MIRROR,
            emotion_word_raw="부담",
        )
        assert "a7_emotion_mirror_miss" in v

    def test_non_empathy_ignored(self):
        # OBSERVATION 은 emotion_word_raw 있어도 A-7 비적용
        v = find_violations_v4(
            "편해 보이시는가봐요?", MsgType.OBSERVATION,
            emotion_word_raw="부담",
        )
        assert "a7_emotion_mirror_miss" not in v

    def test_no_emotion_word_skips(self):
        v = find_violations_v4(
            "그랬군...", MsgType.EMPATHY_MIRROR,
            emotion_word_raw=None,
        )
        assert "a7_emotion_mirror_miss" not in v


# ─────────────────────────────────────────────
#  A-8 문장 길이
# ─────────────────────────────────────────────

class TestA8TooLong:
    def test_short_ok(self):
        v = find_violations_v4("편한 자리이신가봐요?", MsgType.OBSERVATION)
        assert "a8_too_long" not in v

    def test_long_blocks(self):
        # 60자 초과 단일 절 (종결부호 없이 한 절 유지)
        long_text = (
            "편하신 자리와 편안한 분위기 그리고 익숙한 사람과의 관계가 모두 "
            "겹쳐지는 그 순간에 은근하게 읽히는 자연스러운 표정이신가봐요?"
        )
        v = find_violations_v4(long_text, MsgType.OBSERVATION)
        assert "a8_too_long" in v


# ─────────────────────────────────────────────
#  base 병합 / populate_turn_counts
# ─────────────────────────────────────────────

class TestBaseMerge:
    def test_base_verdict_kept(self):
        v = find_violations_v4("verdict 테스트", MsgType.DIAGNOSIS)
        assert "HR1_verdict" in v

    def test_base_tone_missing_dropped(self):
        # 해요체 단독 메시지 — 페르소나 A 의 tone_missing 은 v4 에서 제외돼야
        v = find_violations_v4("편하신가봐요?", MsgType.OBSERVATION)
        assert "tone_missing" not in v

    def test_base_tone_suffix_dropped(self):
        # 페르소나 A tone_suffix 는 A-1 대체 — v4 dict 에는 노출되지 않아야
        v = find_violations_v4("좋네요?", MsgType.OBSERVATION)
        assert "tone_suffix" not in v
        # 대신 A-1 에는 잡혀야
        assert "a1_forbidden_suffix" in v


class TestPopulateTurnCounts:
    def test_populate(self):
        t = AssistantTurn(
            text="편하시잖아요? 편하시더라구요 네요 커피예요",
            msg_type=MsgType.PROBE,
            turn_idx=5,
        )
        populate_turn_counts(t)
        assert t.jangayo_count == 1
        assert t.deoraguyo_count == 1
        assert t.neyo_count == 1
        assert t.yeyo_count == 1

    def test_populate_empty(self):
        t = AssistantTurn(text="평범한 문장.", msg_type=MsgType.OBSERVATION, turn_idx=0)
        populate_turn_counts(t)
        assert t.jangayo_count == 0
        assert t.deoraguyo_count == 0
        assert t.neyo_count == 0
        assert t.yeyo_count == 0
