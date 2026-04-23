"""Sia v3 integration suite — Phase E (Task 9).

decide_next_turn → build_system_prompt → validator 파이프라인 검증.
실 Haiku 호출 없음. Phase F 에서 live probe 담당.

Groups:
  A — state 기반 turn transition + prompt 내용 검증 (6)
  B — external turn 진행 시퀀스 + gender 분기 (3)
  C — validator 경계 (4)
  D — prompt 구조 일관성 (3)

Total: 16 tests.
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from services import sia_llm
from services.sia_session import decide_next_turn
from services.sia_validators import (
    count_assertions,
    has_abstract_noun,
    find_violations,
    validate_sia_output,
    SiaValidationError,
)
from services.sia_prompts import (
    WHITELIST_PATTERNS_FEMALE,
    WHITELIST_PATTERNS_MALE,
)


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _state(
    *,
    turn_count: int = 0,
    spectrum_log=None,
    precision_hits: int = 0,
    precision_misses: int = 0,
) -> dict:
    return {
        "turn_count": turn_count,
        "spectrum_log": spectrum_log or [],
        "precision_hits": precision_hits,
        "precision_misses": precision_misses,
    }


def _build_prompt(
    turn_type: str,
    gender: str = "female",
    user_name: str = "정세현",
    ig_feed_cache=None,
    collected_fields=None,
    missing_fields=None,
) -> str:
    return sia_llm.build_system_prompt(
        user_name=user_name,
        resolved_name=None,
        collected_fields=collected_fields or {},
        missing_fields=missing_fields or [],
        ig_feed_cache=ig_feed_cache,
        turn_type=turn_type,
        gender=gender,
    )


_ALL_TURN_TYPES = [
    "opening",
    "precision_continue",
    "branch_agree",
    "branch_half",
    "branch_disagree",
    "branch_fail",
    "force_external_transition",
    "external_desired_image",
    "external_reference",
    "external_body_height",
    "external_body_weight",
    "external_body_shoulder",
    "external_concerns",
    "external_lifestyle",
    "closing",
]


# ─────────────────────────────────────────────
#  Group A — decide_next_turn → build_system_prompt (6)
# ─────────────────────────────────────────────

def test_opening_state_produces_opening_prompt():
    state = _state(turn_count=0)
    assert decide_next_turn(state) == "opening"

    prompt = _build_prompt("opening", gender="female")

    # 화이트리스트 8 패턴 중 최소 3 개 포함 (실제로는 전부)
    hits = sum(1 for p in WHITELIST_PATTERNS_FEMALE if p in prompt)
    assert hits >= 3, f"only {hits} whitelist patterns in opening prompt"

    # Opening turn header
    assert "[현재 턴: Opening" in prompt


def test_spectrum_1_transitions_to_branch_agree():
    state = _state(turn_count=1, spectrum_log=[1], precision_hits=1)
    assert decide_next_turn(state) == "branch_agree"

    prompt = _build_prompt("branch_agree", gender="female")
    # branch_agree header + "심화" 지시
    assert "[현재 턴: 심화" in prompt
    # 직전 단정 사실 가정 지시
    assert "직전 단정을 사실로 가정" in prompt


def test_spectrum_2_transitions_to_branch_half():
    state = _state(turn_count=1, spectrum_log=[2], precision_hits=1)
    assert decide_next_turn(state) == "branch_half"

    prompt = _build_prompt("branch_half", gender="female")
    # fixed follow-up copy (여쭙겠습니다 형으로 유지 — Phase F validator 호환)
    assert "절반 정도 맞다고 하신 건" in prompt
    assert "어느 쪽이 더 가까우신지" in prompt


def test_spectrum_3_transitions_to_branch_disagree():
    state = _state(turn_count=1, spectrum_log=[3], precision_misses=1)
    assert decide_next_turn(state) == "branch_disagree"

    prompt = _build_prompt("branch_disagree", gender="female")
    # 전환 어구 3 중 최소 1
    markers = ("그러면", "오히려", "달리 보면")
    assert any(m in prompt for m in markers), f"no transition marker in {markers}"


def test_spectrum_4_transitions_to_branch_fail():
    state = _state(turn_count=1, spectrum_log=[4], precision_misses=1)
    assert decide_next_turn(state) == "branch_fail"

    prompt = _build_prompt("branch_fail", gender="female")
    assert "피드에서 읽히는" in prompt
    assert "갭이 있으십니다" in prompt
    # Blocker 1 재발 방지
    assert "같습니다" not in prompt or prompt.count("같습니다") < 2


def test_three_misses_force_external_transition():
    state = _state(turn_count=3, spectrum_log=[3, 4, 3], precision_misses=3)
    assert decide_next_turn(state) == "force_external_transition"

    prompt = _build_prompt("force_external_transition", gender="female")
    assert "충분히 감을 잡았습니다" in prompt
    assert "구체적으로 여쭙겠습니다" in prompt


# ─────────────────────────────────────────────
#  Group B — External turn sequence + gender branch (3)
# ─────────────────────────────────────────────

def test_turn_4_external_desired_image():
    state = _state(turn_count=4, spectrum_log=[1, 1], precision_hits=2)
    assert decide_next_turn(state) == "external_desired_image"

    prompt = _build_prompt("external_desired_image", gender="female")
    for option in (
        "편안하고 기대고 싶은 인상",
        "세련되고 거리감 있는 인상",
        "특별한 날처럼 공들인 인상",
        "무심한데 센스 있는 인상",
    ):
        assert option in prompt, f"missing desired_image option: {option}"


def test_turn_6_body_sequence_gender_branch():
    """body height + weight 에서 gender 별 수치 범위가 교차 없이 분기되는지."""
    # Turn 6 = body_height
    state6 = _state(turn_count=6, spectrum_log=[1, 1], precision_hits=2)
    assert decide_next_turn(state6) == "external_body_height"

    female_h = _build_prompt("external_body_height", gender="female")
    male_h = _build_prompt("external_body_height", gender="male")
    # female 경계
    assert "150-158cm" in female_h
    assert "158-163cm" in female_h
    # male cross 0
    assert "172-178cm" not in female_h
    # male 경계
    assert "172-178cm" in male_h
    assert "178-183cm" in male_h
    # female cross 0
    assert "150-158cm" not in male_h

    # Turn 7 = body_weight
    state7 = _state(turn_count=7, spectrum_log=[1, 1], precision_hits=2)
    assert decide_next_turn(state7) == "external_body_weight"

    female_w = _build_prompt("external_body_weight", gender="female")
    male_w = _build_prompt("external_body_weight", gender="male")
    assert "45-50kg" in female_w
    assert "50-55kg" in female_w
    assert "68-75kg" not in female_w
    assert "68-75kg" in male_w
    assert "75-82kg" in male_w
    assert "45-50kg" not in male_w


def test_turn_11_closing_includes_summary_and_cta():
    """turn_count 11 이상이면 closing. 6 필드 요약 + CTA 지시."""
    state = _state(turn_count=11, spectrum_log=[1, 1], precision_hits=2)
    assert decide_next_turn(state) == "closing"

    prompt = _build_prompt("closing", gender="female")
    # 6 필드 요약 지시
    for field_hint in (
        "desired_image", "reference_style", "height", "weight",
        "shoulder", "current_concerns", "lifestyle_context",
    ):
        assert field_hint in prompt, f"closing prompt missing field hint: {field_hint}"

    # CTA
    assert "시각이 본 나" in prompt
    assert "5,000" in prompt or "5000" in prompt


# ─────────────────────────────────────────────
#  Group C — Validator 경계 (4)
# ─────────────────────────────────────────────

def test_validator_catches_abstract_noun_in_mock_response():
    text = "정세현님은 결이 차분하신 분입니다."
    assert has_abstract_noun(text) is True
    violations = find_violations(text)
    assert "abstract_noun" in violations
    assert any("결이" in v for v in violations["abstract_noun"])


def test_validator_catches_excess_assertions():
    text = (
        "정세현님은 단정한 분입니다.\n"
        "정세현님은 조용한 편이십니다.\n"
        "정세현님은 신중한 쪽이십니다."
    )
    assert count_assertions(text) == 3
    violations = find_violations(text)
    assert "assertion_excess" in violations
    # excess 메타에 count 정보 포함
    assert any("count=3" in s for s in violations["assertion_excess"])


def test_validator_catches_banned_ending():
    """'~네요' 같은 구어체 어미를 tone_suffix 로 잡음."""
    text = "정세현님은 차분한 편이네요. 분석을 진행하겠습니다."
    violations = find_violations(text)
    assert "tone_suffix" in violations
    # 동시에 required suffix 는 충족 (진행하겠습니다)
    assert "tone_missing" not in violations


def test_validator_passes_fixture_responses():
    """Phase D fixture 의 expected_response 전수가 validator 통과."""
    from tests.fixtures.sia_samples import load_all_fixtures

    for fx in load_all_fixtures():
        text = fx["expected_response"]
        # validate_sia_output 가 raise 하지 않아야 함
        try:
            validate_sia_output(text)
        except SiaValidationError as e:
            pytest.fail(
                f"fixture {fx['fixture_id']} failed validation: {e.violations}"
            )


# ─────────────────────────────────────────────
#  Group D — Prompt 구조 일관성 (3 × 15 turn_types)
# ─────────────────────────────────────────────

@pytest.mark.parametrize("turn_type", _ALL_TURN_TYPES)
def test_gender_context_appears_in_all_turn_types(turn_type):
    """모든 turn_type 에서 gender block 이 삽입되는지. 여성 시."""
    prompt = _build_prompt(turn_type, gender="female")
    # 최소 1 개 여성 화이트리스트 패턴 등장 (gender_block 에서)
    hits = sum(1 for p in WHITELIST_PATTERNS_FEMALE if p in prompt)
    assert hits >= 1, f"{turn_type}: no female whitelist pattern in prompt"
    # 남성 패턴 교차 0 — "먼저 다가가기보다 기다리시는 분" 등은 없어야
    male_specific = "자기 기준이 명확하신 분"
    assert male_specific not in prompt, f"{turn_type}: male pattern leaked"


@pytest.mark.parametrize("turn_type", _ALL_TURN_TYPES)
def test_self_check_block_appears_in_all_prompts(turn_type):
    prompt = _build_prompt(turn_type, gender="female")
    assert "[응답 생성 전 자체 검증" in prompt, turn_type
    # 6 체크 항목 전수 번호 매칭
    for i in range(1, 7):
        assert f"{i}." in prompt, f"{turn_type}: self-check item {i} missing"


@pytest.mark.parametrize("turn_type", _ALL_TURN_TYPES)
def test_name_placeholder_replaced_in_all_prompts(turn_type):
    """모든 prompt 에 [NAME] 리터럴이 남아있지 않아야."""
    prompt = _build_prompt(turn_type, gender="female", user_name="정세현")
    assert "[NAME]" not in prompt, f"{turn_type}: [NAME] placeholder leaked"
