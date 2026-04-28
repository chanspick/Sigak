"""Phase H2 — flag_extractor + decide_next_message 테스트.

범위:
  flag_extractor:
    - 9 플래그 각각 양성 1 케이스
    - emotion_word_raw 첫 히트 저장
    - 독립성 (다중 true)
    - 빈 문자열

  decide_next_message:
    - 오프닝 2
    - A-3 트리거 6 (explain / meta / evidence / emotion / tt / self_disclosure)
    - A-2 비율 3 (수집 3연속 / RECOGNITION 하한 / DIAGNOSIS 하한)
    - phase 기본 4 (concede / defensive / 수집 부족 / DIAGNOSIS 후)
    - 우선순위 충돌 3
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
    UserMessageFlags,
    UserTurn,
)
from services.sia_decision import (
    DISCLAIMER_MEMORY_TURNS,
    SELF_PR_PREFIX_MAX,
    decide,
    decide_next_message,
    detect_eval_request,
    detect_exit_signal,
    detect_generalization,
    detect_overattachment,
    detect_self_pr,
    detect_user_disclaimer,
    is_trivial,
    update_state_from_user_turn,
)
from services.sia_flag_extractor import extract_flags


# ─────────────────────────────────────────────
#  extract_flags — 9 플래그
# ─────────────────────────────────────────────

def test_flag_concede_variants():
    """맞아요 / 사실 / 맞긴 해요 / 그렇지 — concede."""
    for text in (
        "네 맞아요",
        "사실 그래요",
        "아 맞긴 해요",
        "그렇긴 해요 좀",
        "맞죠",
    ):
        f = extract_flags(text)
        assert f.has_concede, f"failed: {text!r}"


def test_flag_emotion_word_raw_saves_first_hit():
    """emotion_word_raw 는 첫 히트 어휘 그대로."""
    f = extract_flags("좀 부담스러워서 어색해요")
    assert f.has_emotion_word is True
    assert f.emotion_word_raw == "부담"   # 어휘 목록 순서 첫 hit


def test_flag_tt_detects_double():
    """ㅜㅜ / ㅠㅠ 2자 이상 연속."""
    assert extract_flags("모르겠어요ㅜㅜ").has_tt
    assert extract_flags("음ㅠㅠ").has_tt
    assert extract_flags("ㅜ").has_tt is False       # 1자 단독 false


def test_flag_explain_req():
    for text in ("무슨 얘기에요", "뭔 소리에요", "이해가 안 가서요", "설명 좀"):
        assert extract_flags(text).has_explain_req, text


def test_flag_meta_challenge():
    for text in ("MBTI 같은 거 아녜요", "AI 가 뭘 알아요", "너 뭔데", "이런 거 다 비슷하지"):
        assert extract_flags(text).has_meta_challenge, text


def test_flag_evidence_doubt():
    for text in ("어떻게 알아요", "근거 없잖아요", "뭘 보고 그래요", "억지 아닌가요"):
        assert extract_flags(text).has_evidence_doubt, text


def test_flag_self_disclosure():
    for text in ("사실 저는 예전에", "실은 그런 이유가", "원래 이래요", "제가 요즘 좀"):
        assert extract_flags(text).has_self_disclosure, text


def test_flag_defensive():
    for text in ("편해서요", "그냥 올리는 거예요", "취향이에요", "잘 안 찍어요", "입어보면 어색해요"):
        assert extract_flags(text).is_defensive, text


def test_flag_multiple_flags_independent():
    """감정 + ㅜㅜ + 자기개시 동시 true."""
    f = extract_flags("사실 저는 좀 부담스러워요ㅠㅠ")
    assert f.has_self_disclosure
    assert f.has_emotion_word
    assert f.has_tt


def test_flag_empty_text_all_false():
    f = extract_flags("")
    for attr in (
        "has_concede", "has_emotion_word", "has_tt",
        "has_explain_req", "has_meta_challenge",
        "has_evidence_doubt", "has_self_disclosure", "is_defensive",
    ):
        assert not getattr(f, attr)
    assert f.emotion_word_raw is None


def test_flag_non_matching_text():
    """랜덤 중립 텍스트 — 전부 false."""
    f = extract_flags("그래요 오늘 날씨 좋네요")
    # "맞네요" 없어서 concede 없음. "그래요" 는 CONCEDE 패턴 "그렇(긴 해요|지|네요)" 밖.
    assert not f.has_concede
    assert not f.has_emotion_word
    assert not f.has_tt
    assert not f.is_defensive


def test_flag_안_맞_not_concede():
    """부정형 '안 맞' 는 concede 로 오인하지 않아야.

    현 구현은 정규식 base. '안 맞' 가 포함돼도 패턴 '맞(아요|긴 해요|...)'
    는 어절 시작에서 매칭 안 됨. 확인 겸 추가.
    """
    f = extract_flags("그거 안 맞는 거 같아요")
    # "맞는" 는 패턴 어미 리스트에 없음 (아요/긴 해요/네요/았어요/죠)
    assert f.has_concede is False


# ─────────────────────────────────────────────
#  decide_next_message — helpers
# ─────────────────────────────────────────────

def _new_state() -> ConversationState:
    return ConversationState(session_id="s", user_id="u", user_name="세현")


def _add_assistant(state: ConversationState, msg_type: MsgType, text: str = "x"):
    state.turns.append(AssistantTurn(
        text=text, msg_type=msg_type, turn_idx=len(state.turns),
    ))


def _add_user(state: ConversationState, text: str = "", flags: UserMessageFlags | None = None):
    state.turns.append(UserTurn(
        text=text, turn_idx=len(state.turns),
        flags=flags or UserMessageFlags(),
    ))


# ─────────────────────────────────────────────
#  오프닝 2
# ─────────────────────────────────────────────

def test_decide_empty_state_returns_opening():
    assert decide_next_message(_new_state()) == MsgType.OPENING_DECLARATION


def test_decide_after_opening_returns_observation():
    s = _new_state()
    _add_assistant(s, MsgType.OPENING_DECLARATION)
    _add_user(s, "넹")
    assert decide_next_message(s) == MsgType.OBSERVATION


# ─────────────────────────────────────────────
#  A-3 트리거 6
# ─────────────────────────────────────────────

def test_decide_explain_req_with_few_obs_returns_observation():
    """obs<2 면 OBSERVATION 로 재수집."""
    s = _new_state()
    _add_assistant(s, MsgType.OPENING_DECLARATION)
    _add_user(s, "넹")
    _add_assistant(s, MsgType.OBSERVATION)   # obs_count 수동 업데이트 필요
    s.observation_count = 1
    f = UserMessageFlags(has_explain_req=True)
    _add_user(s, "무슨 얘기에요", flags=f)
    assert decide_next_message(s) == MsgType.OBSERVATION


def test_decide_explain_req_with_enough_obs_returns_diagnosis():
    s = _new_state()
    _add_assistant(s, MsgType.OPENING_DECLARATION)
    _add_assistant(s, MsgType.OBSERVATION)
    _add_assistant(s, MsgType.OBSERVATION)
    s.observation_count = 2
    _add_user(s, "무슨 얘기에요", flags=UserMessageFlags(has_explain_req=True))
    assert decide_next_message(s) == MsgType.DIAGNOSIS


def test_decide_meta_challenge_first_use_returns_meta_rebuttal():
    s = _new_state()
    _add_assistant(s, MsgType.OPENING_DECLARATION)
    _add_assistant(s, MsgType.OBSERVATION)
    _add_user(s, "MBTI 같은 거 아녜요", flags=UserMessageFlags(has_meta_challenge=True))
    assert decide_next_message(s) == MsgType.META_REBUTTAL


def test_decide_meta_challenge_after_used_falls_through():
    """meta_rebuttal_used=True 면 META_REBUTTAL 스킵."""
    s = _new_state()
    _add_assistant(s, MsgType.OPENING_DECLARATION)
    _add_assistant(s, MsgType.OBSERVATION)
    s.meta_rebuttal_used = True
    s.observation_count = 1
    _add_user(s, "MBTI 같은 거 아녜요", flags=UserMessageFlags(has_meta_challenge=True))
    # explain_req 가 false, 다음 트리거 없음. phase 3.3: obs<3 + last=OBSERVATION → PROBE
    assert decide_next_message(s) == MsgType.PROBE


def test_decide_evidence_doubt_returns_evidence_defense():
    s = _new_state()
    _add_assistant(s, MsgType.OPENING_DECLARATION)
    _add_assistant(s, MsgType.OBSERVATION)
    _add_user(s, "어떻게 알아요", flags=UserMessageFlags(has_evidence_doubt=True))
    assert decide_next_message(s) == MsgType.EVIDENCE_DEFENSE


def test_decide_emotion_word_returns_empathy_mirror():
    s = _new_state()
    _add_assistant(s, MsgType.OPENING_DECLARATION)
    _add_assistant(s, MsgType.OBSERVATION)
    _add_user(s, "좀 부담스러워서요", flags=UserMessageFlags(
        has_emotion_word=True, emotion_word_raw="부담",
    ))
    assert decide_next_message(s) == MsgType.EMPATHY_MIRROR


def test_decide_tt_returns_empathy_mirror():
    s = _new_state()
    _add_assistant(s, MsgType.OPENING_DECLARATION)
    _add_assistant(s, MsgType.OBSERVATION)
    _add_user(s, "몰라요ㅠㅠ", flags=UserMessageFlags(has_tt=True))
    assert decide_next_message(s) == MsgType.EMPATHY_MIRROR


def test_decide_consecutive_self_disclosure_returns_empathy_mirror():
    s = _new_state()
    _add_assistant(s, MsgType.OPENING_DECLARATION)
    _add_assistant(s, MsgType.OBSERVATION)
    _add_user(s, "실은 원래", flags=UserMessageFlags(has_self_disclosure=True))
    _add_assistant(s, MsgType.OBSERVATION)
    _add_user(s, "사실 저는", flags=UserMessageFlags(has_self_disclosure=True))
    assert decide_next_message(s) == MsgType.EMPATHY_MIRROR


# ─────────────────────────────────────────────
#  A-2 비율 강제 3
# ─────────────────────────────────────────────

def test_decide_collection_streak_3_forces_recognition():
    s = _new_state()
    _add_assistant(s, MsgType.OPENING_DECLARATION)
    _add_assistant(s, MsgType.OBSERVATION)
    _add_assistant(s, MsgType.PROBE)
    _add_assistant(s, MsgType.EXTRACTION)
    s.collection_streak = 3
    s.observation_count = 1
    _add_user(s, "네")
    assert decide_next_message(s) == MsgType.RECOGNITION


def test_decide_recognition_min_ratio_triggers_when_obs_3():
    """obs>=3 + recog_done=0 + observations_since_recognition>=2 → RECOGNITION 강제."""
    s = _new_state()
    _add_assistant(s, MsgType.OPENING_DECLARATION)
    _add_assistant(s, MsgType.OBSERVATION)
    _add_assistant(s, MsgType.OBSERVATION)
    _add_assistant(s, MsgType.OBSERVATION)
    s.observation_count = 3
    s.observations_since_recognition = 3
    s.type_counts = {MsgType.RECOGNITION: 0}
    _add_user(s, "네")     # no flags
    assert decide_next_message(s) == MsgType.RECOGNITION


def test_decide_diagnosis_min_ratio_at_8_turns_with_concede():
    """총 8턴 이상 + diag_done<1 + obs>=3 + concede → DIAGNOSIS 강제."""
    s = _new_state()
    # assistant 8 turns (OPENING + OBSERVATION*7)
    _add_assistant(s, MsgType.OPENING_DECLARATION)
    for _ in range(7):
        _add_assistant(s, MsgType.OBSERVATION)
    s.observation_count = 7
    s.observations_since_recognition = 0   # 비율 강제 2.2 발동 방지
    s.type_counts = {MsgType.DIAGNOSIS: 0, MsgType.RECOGNITION: 2}
    _add_user(s, "아 맞아요", flags=UserMessageFlags(has_concede=True))
    assert decide_next_message(s) == MsgType.DIAGNOSIS


# ─────────────────────────────────────────────
#  Phase 기본 4
# ─────────────────────────────────────────────

def test_decide_concede_with_many_obs_returns_recognition_then_diagnosis():
    """RECOGNITION 먼저, 다음 concede 에서 DIAGNOSIS."""
    s = _new_state()
    _add_assistant(s, MsgType.OPENING_DECLARATION)
    for _ in range(3):
        _add_assistant(s, MsgType.OBSERVATION)
    s.observation_count = 3
    s.type_counts = {MsgType.RECOGNITION: 2}   # 2.2 강제 skip
    s.observations_since_recognition = 0
    _add_user(s, "맞아요", flags=UserMessageFlags(has_concede=True))
    # 마지막 assistant == OBSERVATION → RECOGNITION
    assert decide_next_message(s) == MsgType.RECOGNITION

    # 이번엔 마지막이 RECOGNITION 인 상태
    _add_assistant(s, MsgType.RECOGNITION)
    _add_user(s, "맞아요 2", flags=UserMessageFlags(has_concede=True))
    assert decide_next_message(s) == MsgType.DIAGNOSIS


def test_decide_defensive_with_obs_returns_confrontation():
    s = _new_state()
    _add_assistant(s, MsgType.OPENING_DECLARATION)
    _add_assistant(s, MsgType.OBSERVATION)
    _add_assistant(s, MsgType.OBSERVATION)
    s.observation_count = 2
    _add_user(s, "편해서요", flags=UserMessageFlags(is_defensive=True))
    assert decide_next_message(s) == MsgType.CONFRONTATION


def test_decide_obs_shortage_cycles_observation_probe_extraction():
    """obs<3 + 마지막 타입에 따라 OBSERVATION → PROBE → EXTRACTION 순환."""
    s = _new_state()
    _add_assistant(s, MsgType.OPENING_DECLARATION)
    _add_assistant(s, MsgType.OBSERVATION)
    s.observation_count = 1
    _add_user(s, "네")
    assert decide_next_message(s) == MsgType.PROBE

    _add_assistant(s, MsgType.PROBE)
    _add_user(s, "네")
    assert decide_next_message(s) == MsgType.EXTRACTION

    _add_assistant(s, MsgType.EXTRACTION)
    _add_user(s, "네")
    # 마지막 != OBSERVATION / PROBE → OBSERVATION
    assert decide_next_message(s) == MsgType.OBSERVATION


def test_decide_after_diagnosis_returns_soft_walkback():
    s = _new_state()
    _add_assistant(s, MsgType.OPENING_DECLARATION)
    for _ in range(3):
        _add_assistant(s, MsgType.OBSERVATION)
    _add_assistant(s, MsgType.RECOGNITION)
    _add_assistant(s, MsgType.DIAGNOSIS)
    s.observation_count = 3
    s.type_counts = {MsgType.RECOGNITION: 1, MsgType.DIAGNOSIS: 1}
    s.observations_since_recognition = 0
    _add_user(s, "음", flags=UserMessageFlags())   # no trigger
    assert decide_next_message(s) == MsgType.SOFT_WALKBACK


# ─────────────────────────────────────────────
#  우선순위 충돌 3
# ─────────────────────────────────────────────

def test_priority_trigger_beats_collection_streak():
    """collection_streak=3 인데 meta_challenge 오면 META_REBUTTAL 우선."""
    s = _new_state()
    _add_assistant(s, MsgType.OPENING_DECLARATION)
    _add_assistant(s, MsgType.OBSERVATION)
    _add_assistant(s, MsgType.PROBE)
    _add_assistant(s, MsgType.EXTRACTION)
    s.collection_streak = 3
    _add_user(s, "MBTI 뭐", flags=UserMessageFlags(has_meta_challenge=True))
    assert decide_next_message(s) == MsgType.META_REBUTTAL


def test_priority_ratio_beats_phase_concede():
    """concede + obs>=3 — 원래 phase 3.1 RECOGNITION. 하지만 diag_needed 충족 안 됐으면 동일 경로."""
    # 여기는 오히려 2.3 (DIAGNOSIS 하한) > 3.1 경로 검증
    s = _new_state()
    _add_assistant(s, MsgType.OPENING_DECLARATION)
    for _ in range(7):
        _add_assistant(s, MsgType.OBSERVATION)  # 총 8 assistant turns
    s.observation_count = 7
    s.observations_since_recognition = 0
    s.type_counts = {MsgType.RECOGNITION: 2, MsgType.DIAGNOSIS: 0}
    _add_user(s, "맞아요", flags=UserMessageFlags(has_concede=True))
    # 2.3 가 DIAGNOSIS 강제 (diag_done=0 < max(1, 8*0.12)=1)
    assert decide_next_message(s) == MsgType.DIAGNOSIS


def test_priority_no_consecutive_same_type():
    """obs<3 구간에서 마지막 OBSERVATION 이면 PROBE 로 분산."""
    s = _new_state()
    _add_assistant(s, MsgType.OPENING_DECLARATION)
    _add_assistant(s, MsgType.OBSERVATION)
    s.observation_count = 1
    _add_user(s, "응")
    result = decide_next_message(s)
    # 직전 OBSERVATION → PROBE 로 분산 (2 연속 회피)
    assert result == MsgType.PROBE
    assert result != MsgType.OBSERVATION


# ─────────────────────────────────────────────
#  세션 #6 v2 신규 — 관리 3 타입 트리거
# ─────────────────────────────────────────────

class TestM1CombinedOutput:
    """세션 #4 v2 §6: 첫 턴 = OPENING_DECLARATION + OBSERVATION 결합."""

    def test_empty_state_returns_combined_composition(self):
        comp = decide(_new_state())
        assert comp.primary_type == MsgType.OPENING_DECLARATION
        assert comp.secondary_type == MsgType.OBSERVATION
        assert comp.is_combined is True

    def test_decide_next_message_returns_primary_only(self):
        """기존 호출부 호환: primary_type 만 반환."""
        assert decide_next_message(_new_state()) == MsgType.OPENING_DECLARATION


class TestA11Overattachment:
    """세션 #6 v2 §4 A-11 과몰입 → RANGE_DISCLOSURE."""

    def test_mild_overattachment_returns_range_disclosure(self):
        s = _new_state()
        _add_assistant(s, MsgType.OPENING_DECLARATION)
        _add_assistant(s, MsgType.OBSERVATION)
        _add_user(s, "너 진짜 나 잘 아네")
        comp = decide(s)
        assert comp.primary_type == MsgType.RANGE_DISCLOSURE
        assert comp.range_mode == "limit"
        assert s.overattachment_severity == "mild"

    def test_severe_overattachment_sets_severity(self):
        s = _new_state()
        _add_assistant(s, MsgType.OPENING_DECLARATION)
        _add_assistant(s, MsgType.OBSERVATION)
        _add_user(s, "들어줄 사람 없었는데 네가 낫네")
        comp = decide(s)
        assert comp.primary_type == MsgType.RANGE_DISCLOSURE
        assert s.overattachment_severity == "severe"

    def test_overattachment_beats_other_triggers(self):
        """과몰입은 최우선 — concede / defensive 보다 먼저."""
        s = _new_state()
        _add_assistant(s, MsgType.OPENING_DECLARATION)
        for _ in range(3):
            _add_assistant(s, MsgType.OBSERVATION)
        s.observation_count = 3
        _add_user(s, "너 진짜 나 잘 아네 맞아요",
                  flags=UserMessageFlags(has_concede=True))
        assert decide(s).primary_type == MsgType.RANGE_DISCLOSURE


class TestA10ExitSignal:
    """세션 #6 v2 §3 A-10 직접 이탈 → CHECK_IN."""

    def test_exit_signal_returns_check_in(self):
        s = _new_state()
        _add_assistant(s, MsgType.OPENING_DECLARATION)
        _add_assistant(s, MsgType.OBSERVATION)
        _add_user(s, "나중에 할게요")
        assert decide(s).primary_type == MsgType.CHECK_IN

    def test_geuman_triggers_check_in(self):
        s = _new_state()
        _add_assistant(s, MsgType.OPENING_DECLARATION)
        _add_user(s, "그만 할래요")
        assert decide(s).primary_type == MsgType.CHECK_IN


class TestA9TrivialStreak:
    """세션 #6 v2 §2 A-9 단답 스트릭 분기."""

    def test_streak_3_returns_check_in(self):
        s = _new_state()
        _add_assistant(s, MsgType.OPENING_DECLARATION)
        _add_assistant(s, MsgType.OBSERVATION)
        s.trivial_streak = 3
        _add_user(s, "네")
        assert decide(s).primary_type == MsgType.CHECK_IN

    def test_streak_1_after_observation_returns_extraction(self):
        """B 경로 — 같은 축 좁힘. last=OBSERVATION → EXTRACTION."""
        s = _new_state()
        _add_assistant(s, MsgType.OPENING_DECLARATION)
        _add_assistant(s, MsgType.OBSERVATION)
        s.trivial_streak = 1
        _add_user(s, "네")
        assert decide(s).primary_type == MsgType.EXTRACTION

    def test_streak_1_after_probe_returns_probe(self):
        """B 경로 — last != OBSERVATION → PROBE."""
        s = _new_state()
        _add_assistant(s, MsgType.OPENING_DECLARATION)
        _add_assistant(s, MsgType.PROBE)
        s.trivial_streak = 1
        _add_user(s, "네")
        assert decide(s).primary_type == MsgType.PROBE

    def test_streak_2_returns_observation_and_sets_axis_switch(self):
        """D 경로 — 수용부 + 축 전환 복귀."""
        s = _new_state()
        _add_assistant(s, MsgType.OPENING_DECLARATION)
        _add_assistant(s, MsgType.OBSERVATION)
        s.trivial_streak = 2
        _add_user(s, "네")
        comp = decide(s)
        assert comp.primary_type == MsgType.OBSERVATION
        assert s.axis_switch_required is True


class TestCheckInToReEntry:
    """세션 #6 v2 §8.1 step 6: CHECK_IN 직후 → RE_ENTRY."""

    def test_after_check_in_returns_re_entry_normal(self):
        s = _new_state()
        _add_assistant(s, MsgType.OPENING_DECLARATION)
        _add_assistant(s, MsgType.CHECK_IN)
        _add_user(s, "그냥 할 말이 없어서요")
        comp = decide(s)
        assert comp.primary_type == MsgType.RE_ENTRY
        assert comp.exit_confirmed is False

    def test_after_check_in_with_exit_signal_sets_exit_confirmed(self):
        """세션 #6 v2 §3.3: 이탈 선택 시 RE_ENTRY V5 종결 버전."""
        s = _new_state()
        _add_assistant(s, MsgType.OPENING_DECLARATION)
        _add_assistant(s, MsgType.CHECK_IN)
        _add_user(s, "네 나중에 할게요")
        comp = decide(s)
        assert comp.primary_type == MsgType.RE_ENTRY
        assert comp.exit_confirmed is True


# ─────────────────────────────────────────────
#  세션 #7 신규 — C6 / C7 / EMPATHY 결합 / A-13 prefix
# ─────────────────────────────────────────────

class TestC6EvalRequest:
    """세션 #7 §2: C6 평가 의존 돌파 분기."""

    def test_eval_request_with_rich_self_disclosure_returns_c6(self):
        """자기개시 풍부 → CONFRONTATION C6."""
        s = _new_state()
        _add_assistant(s, MsgType.OPENING_DECLARATION)
        _add_assistant(s, MsgType.OBSERVATION)
        # 50자+ 발화 2건으로 rich self-disclosure 조건 충족
        _add_user(s, "실은 제가 평소에 자신감이 없어서 그런지 사진 찍을 때마다 뭔가 어색하고 억지로 웃는 느낌이 들어요")
        _add_assistant(s, MsgType.RECOGNITION)
        _add_user(s, "본연의 매력이 있긴 한가요?")
        comp = decide(s)
        assert comp.primary_type == MsgType.CONFRONTATION
        assert comp.confrontation_block == "C6"

    # 베타 hotfix (2026-04-28) 폐기 + 신규 — RANGE_REAFFIRM 동작 정리 (1-A 변형 / 1-B 분기 / 1-C 가이드).
    # 폐기: test_eval_request_with_sparse_self_disclosure_returns_range_reaffirm.
    # 신규: test_eval_request_with_sparse_self_disclosure_returns_probe (PROBE 재라우팅 검증).
    def test_eval_request_with_sparse_self_disclosure_returns_probe(self):
        """베타 hotfix (2026-04-28): 막막함 우세 → PROBE 재라우팅 (RANGE_REAFFIRM 폐기 후)."""
        s = _new_state()
        _add_assistant(s, MsgType.OPENING_DECLARATION)
        _add_user(s, "네")
        _add_assistant(s, MsgType.OBSERVATION)
        _add_user(s, "제가 어때 보여요?")
        comp = decide(s)
        assert comp.primary_type == MsgType.PROBE


class TestC7Generalization:
    """세션 #7 §3: C7 일반화 회피 돌파."""

    def test_generalization_returns_c7_confrontation(self):
        s = _new_state()
        _add_assistant(s, MsgType.OPENING_DECLARATION)
        _add_assistant(s, MsgType.OBSERVATION)
        _add_user(s, "뭐 다들 그렇지 않나요")
        comp = decide(s)
        assert comp.primary_type == MsgType.CONFRONTATION
        assert comp.confrontation_block == "C7"

    def test_pyeongbeom_triggers_c7(self):
        s = _new_state()
        _add_assistant(s, MsgType.OPENING_DECLARATION)
        _add_assistant(s, MsgType.OBSERVATION)
        _add_user(s, "저는 평범해요")
        assert decide(s).confrontation_block == "C7"


class TestEmpathyCombinedOutput:
    """세션 #7 §1: 감정 트리거 시 EMPATHY 결합 출력."""

    def test_emotion_word_returns_combined_empathy_probe_default(self):
        """obs_count < 3 + no eval → EMPATHY + PROBE."""
        s = _new_state()
        _add_assistant(s, MsgType.OPENING_DECLARATION)
        _add_assistant(s, MsgType.OBSERVATION)
        _add_user(s, "좀 부담스러워서요", flags=UserMessageFlags(
            has_emotion_word=True, emotion_word_raw="부담",
        ))
        comp = decide(s)
        assert comp.primary_type == MsgType.EMPATHY_MIRROR
        assert comp.secondary_type == MsgType.PROBE
        assert comp.is_combined is True

    def test_emotion_with_enough_obs_returns_combined_empathy_recognition(self):
        """obs_count >= 3 + no eval → EMPATHY + RECOGNITION."""
        s = _new_state()
        _add_assistant(s, MsgType.OPENING_DECLARATION)
        for _ in range(3):
            _add_assistant(s, MsgType.OBSERVATION)
        s.observation_count = 3
        _add_user(s, "좀 부담스러워서요", flags=UserMessageFlags(
            has_emotion_word=True, emotion_word_raw="부담",
        ))
        comp = decide(s)
        assert comp.primary_type == MsgType.EMPATHY_MIRROR
        assert comp.secondary_type == MsgType.RECOGNITION

    def test_emotion_with_eval_and_rich_disclosure_returns_empathy_c6(self):
        """서연 fixture M5 경로 재현: EMPATHY + CONFRONTATION(C6)."""
        s = _new_state()
        _add_assistant(s, MsgType.OPENING_DECLARATION)
        _add_assistant(s, MsgType.OBSERVATION)
        _add_user(s, "실은 제가 평소에 자신감이 없어서 그런지 사진 찍을 때마다 뭔가 어색하고 억지로 웃는 느낌이 들어요")
        _add_assistant(s, MsgType.EMPATHY_MIRROR)
        _add_user(
            s,
            "본연의 매력이 있긴 한가요? 저는 부담스러워서 사진이 꺼려져요",
            flags=UserMessageFlags(has_emotion_word=True, emotion_word_raw="부담"),
        )
        comp = decide(s)
        assert comp.primary_type == MsgType.EMPATHY_MIRROR
        assert comp.secondary_type == MsgType.CONFRONTATION
        assert comp.confrontation_block == "C6"

    # 베타 hotfix (2026-04-28) 폐기 + 신규 — RANGE_REAFFIRM 동작 정리 (1-A 변형 / 1-B 분기 / 1-C 가이드).
    # 폐기: test_emotion_with_eval_and_sparse_disclosure_returns_empathy_reaffirm.
    # 신규: test_emotion_with_eval_and_sparse_disclosure_returns_empathy_probe (PROBE 재라우팅 검증).
    def test_emotion_with_eval_and_sparse_disclosure_returns_empathy_probe(self):
        """베타 hotfix (2026-04-28): 막막함 우세 → EMPATHY + PROBE (RANGE_REAFFIRM 폐기 후)."""
        s = _new_state()
        _add_assistant(s, MsgType.OPENING_DECLARATION)
        _add_user(s, "네")
        _add_assistant(s, MsgType.OBSERVATION)
        _add_user(
            s,
            "제가 어때 보여요 부담스러워요",
            flags=UserMessageFlags(has_emotion_word=True, emotion_word_raw="부담"),
        )
        comp = decide(s)
        assert comp.primary_type == MsgType.EMPATHY_MIRROR
        assert comp.secondary_type == MsgType.PROBE


class TestA13SelfPrPrefix:
    """세션 #7 §5: A-13 자기 PR 라포 prefix."""

    def test_self_pr_sets_prefix_flag_on_observation_cycle(self):
        """자기 PR 감지 + obs<3 → apply_self_pr_prefix=True."""
        s = _new_state()
        _add_assistant(s, MsgType.OPENING_DECLARATION)
        _add_user(s, "딱히 신경안써요 누가봐도 제 몸은 좋아보이니까요")
        comp = decide(s)
        # Decide 결정이 obs<3 cycle → OBSERVATION with prefix
        assert comp.apply_self_pr_prefix is True

    def test_self_pr_prefix_capped_at_max_uses(self):
        """세션당 최대 SELF_PR_PREFIX_MAX (=2) 회 한정."""
        s = _new_state()
        s.self_pr_prefix_used = SELF_PR_PREFIX_MAX   # 상한 도달
        _add_assistant(s, MsgType.OPENING_DECLARATION)
        _add_user(s, "누가봐도 제 몸은 좋아보이니까요")
        comp = decide(s)
        assert comp.apply_self_pr_prefix is False

    def test_no_self_pr_marker_no_prefix(self):
        s = _new_state()
        _add_assistant(s, MsgType.OPENING_DECLARATION)
        _add_user(s, "그냥 편해서요")
        comp = decide(s)
        assert comp.apply_self_pr_prefix is False


# ─────────────────────────────────────────────
#  Detectors — 개별 함수 양성/음성
# ─────────────────────────────────────────────

class TestDetectors:
    def test_is_trivial_exact_set(self):
        for text in ("네", "넹", "ㅇㅇ", "응"):
            assert is_trivial(text)

    def test_is_trivial_ambiguous_includes_jalmoreugesseoyo(self):
        """세션 #6 v2 §2.1 §10.2 (a): '잘 모르겠어요' 포함 확정."""
        assert is_trivial("잘 모르겠어요")

    def test_is_trivial_rejects_content(self):
        assert is_trivial("좋아해요") is False
        assert is_trivial("그거 맞는 거 같아요") is False

    def test_detect_exit_signal_matches(self):
        for text in ("나중에 할게요", "이따가요", "그만할래요", "지금 바빠요"):
            assert detect_exit_signal(text)

    def test_detect_exit_signal_rejects(self):
        assert not detect_exit_signal("그래요 좋아요")

    def test_detect_overattachment_severe_wins(self):
        ok, sev = detect_overattachment("들어줄 사람 없었는데 진짜 나 잘 아네")
        assert ok
        assert sev == "severe"

    def test_detect_overattachment_mild(self):
        ok, sev = detect_overattachment("AI 인데 신기해요")
        assert ok
        assert sev == "mild"

    def test_detect_overattachment_negative(self):
        ok, sev = detect_overattachment("그냥 편해서요")
        assert not ok
        assert sev == ""

    def test_detect_eval_request(self):
        for text in ("제가 어때 보여요?", "솔직히 말해주세요", "매력 있긴 한가요"):
            assert detect_eval_request(text)

    def test_detect_generalization(self):
        for text in ("다들 그렇지 않나요", "보통 다 그래요", "저는 평범해요"):
            assert detect_generalization(text)

    def test_detect_user_disclaimer(self):
        for text in ("잘 모르겠어요", "딱히 신경 안 써요", "생각 안 해봤어요"):
            assert detect_user_disclaimer(text)

    def test_detect_self_pr(self):
        for text in ("누가봐도 좋아보이니까요", "딱 보면 모르나", "근육 좋잖아요"):
            assert detect_self_pr(text)


# ─────────────────────────────────────────────
#  update_state_from_user_turn
# ─────────────────────────────────────────────

class TestPreDecideStateUpdater:
    def test_trivial_streak_increments(self):
        s = _new_state()
        update_state_from_user_turn(s, "네")
        assert s.trivial_streak == 1
        update_state_from_user_turn(s, "넹")
        assert s.trivial_streak == 2

    def test_trivial_streak_resets_on_content(self):
        s = _new_state()
        s.trivial_streak = 5
        update_state_from_user_turn(s, "사실 저는 요즘 피곤해서요")
        assert s.trivial_streak == 0

    def test_disclaimer_memory_set_on_detection(self):
        s = _new_state()
        update_state_from_user_turn(s, "잘 모르겠어요")
        assert s.user_disclaimer_memory.get("recent") == DISCLAIMER_MEMORY_TURNS

    def test_disclaimer_memory_decays_each_turn(self):
        s = _new_state()
        s.user_disclaimer_memory = {"recent": 2}
        update_state_from_user_turn(s, "그래요")   # 무 disclaimer
        assert s.user_disclaimer_memory.get("recent") == 1
        update_state_from_user_turn(s, "네")
        # 1 → 0 도달 시 삭제
        assert "recent" not in s.user_disclaimer_memory
