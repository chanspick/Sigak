"""Sia v3 prompt assembly 테스트 — Phase C (Task 1 + 7).

render_gender_block / render_turn_block / build_system_prompt 연동.
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from services import sia_llm
from services.sia_prompts import (
    WHITELIST_PATTERNS_FEMALE,
    WHITELIST_PATTERNS_MALE,
    FEMALE_HEIGHT_RANGES,
    MALE_HEIGHT_RANGES,
    FEMALE_WEIGHT_RANGES,
    MALE_WEIGHT_RANGES,
    render_gender_block,
    render_turn_block,
    SELF_CHECK_BLOCK,
)


# ─────────────────────────────────────────────
#  render_gender_block — 화이트리스트 + 범위
# ─────────────────────────────────────────────

def test_gender_block_female_has_whitelist_8():
    block = render_gender_block("female")
    for pattern in WHITELIST_PATTERNS_FEMALE:
        assert pattern in block, f"missing: {pattern}"
    assert "여성" in block


def test_gender_block_male_has_whitelist_8():
    block = render_gender_block("male")
    for pattern in WHITELIST_PATTERNS_MALE:
        assert pattern in block, f"missing: {pattern}"
    assert "남성" in block


def test_gender_block_female_body_ranges():
    block = render_gender_block("female")
    for r in FEMALE_HEIGHT_RANGES:
        assert r in block
    for r in FEMALE_WEIGHT_RANGES:
        assert r in block


def test_gender_block_male_body_ranges():
    block = render_gender_block("male")
    for r in MALE_HEIGHT_RANGES:
        assert r in block
    for r in MALE_WEIGHT_RANGES:
        assert r in block


def test_gender_block_female_concern_hints():
    block = render_gender_block("female")
    assert "메이크업 방향" in block


def test_gender_block_male_concern_hints():
    block = render_gender_block("male")
    assert "그루밍 방향" in block


def test_gender_block_rejects_invalid():
    with pytest.raises(ValueError):
        render_gender_block("other")  # type: ignore


# ─────────────────────────────────────────────
#  render_turn_block — 15 turn types 전수
# ─────────────────────────────────────────────

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


@pytest.mark.parametrize("turn_type", _ALL_TURN_TYPES)
def test_turn_block_all_types_non_empty(turn_type):
    out = render_turn_block(turn_type, "female", "정세현님")
    assert out.strip(), f"{turn_type} empty"
    assert f"[현재 턴" in out


def test_turn_block_unknown_falls_back_to_opening():
    out = render_turn_block("mystery_type", "female", "정세현님")
    assert "opening 폴백" in out or "Unknown" in out


# ─────────────────────────────────────────────
#  render_turn_block — 고정 문구 검증
# ─────────────────────────────────────────────

def test_turn_block_branch_half_fixed_copy():
    out = render_turn_block("branch_half", "female", "정세현님")
    assert "절반 정도 맞다고 하신 건" in out
    assert "여쭙겠습니다" in out
    assert "단정 전반은 맞는데 뉘앙스가 조금 다르다" in out
    assert "반은 맞고 반은 틀리다" in out
    assert "표면은 맞는데 속은 다르다" in out
    assert "구체 방향이 다르다" in out


def test_turn_block_branch_fail_fixed_copy():
    out = render_turn_block("branch_fail", "female", "정세현님")
    # Blocker 1 교정문 검증 — "결" 추상명사 / "~같습니다" 모호 어미 0 건
    assert "피드에서 읽히는" in out
    assert "실제" in out
    assert "갭이 있으십니다" in out
    # 추상명사/모호 어미 재발 방지
    assert "결" not in out
    assert "같습니다" not in out


def test_turn_block_name_substitution():
    """[NAME] placeholder 가 resolved_name_display 로 치환되는지."""
    out = render_turn_block("branch_fail", "female", "민지님")
    assert "민지님" in out
    assert "[NAME]" not in out


def test_turn_block_empty_name_uses_fallback():
    """빈 display → '당신' 폴백."""
    out = render_turn_block("branch_fail", "female", "")
    assert "[NAME]" not in out
    assert "당신" in out


def test_turn_block_body_height_gender_split():
    female = render_turn_block("external_body_height", "female", "민지님")
    male = render_turn_block("external_body_height", "male", "준호님")
    assert "158-163cm" in female
    assert "158-163cm" not in male
    assert "172-178cm" in male
    assert "172-178cm" not in female


def test_turn_block_body_weight_gender_split():
    female = render_turn_block("external_body_weight", "female", "민지님")
    male = render_turn_block("external_body_weight", "male", "준호님")
    assert "50-55kg" in female
    assert "50-55kg" not in male
    assert "68-75kg" in male
    assert "68-75kg" not in female


def test_turn_block_opening_contains_spectrum():
    out = render_turn_block("opening", "female", "민지님")
    assert "네, 비슷하다" in out
    assert "절반 정도 맞다" in out
    assert "다르다" in out
    assert "전혀 다르다" in out


def test_turn_block_force_external_includes_transition_phrase():
    out = render_turn_block("force_external_transition", "female", "민지님")
    assert "충분히 감을 잡았습니다" in out
    assert "구체적으로 여쭙겠습니다" in out


# ─────────────────────────────────────────────
#  SELF_CHECK_BLOCK
# ─────────────────────────────────────────────

def test_self_check_block_lists_six_items():
    assert "1." in SELF_CHECK_BLOCK
    assert "2." in SELF_CHECK_BLOCK
    assert "3." in SELF_CHECK_BLOCK
    assert "4." in SELF_CHECK_BLOCK
    assert "5." in SELF_CHECK_BLOCK
    assert "6." in SELF_CHECK_BLOCK
    assert "추상명사" in SELF_CHECK_BLOCK
    assert "직전 답 사후 참조" in SELF_CHECK_BLOCK


# ─────────────────────────────────────────────
#  build_system_prompt — e2e 통합
# ─────────────────────────────────────────────

def test_build_system_prompt_e2e_female_opening():
    prompt = sia_llm.build_system_prompt(
        user_name="민지",
        resolved_name=None,
        collected_fields={},
        missing_fields=["desired_image"],
        ig_feed_cache=None,
        turn_type="opening",
        gender="female",
    )
    # 여성 화이트리스트 8 패턴 전부 포함
    for pattern in WHITELIST_PATTERNS_FEMALE:
        assert pattern in prompt
    # SELF_CHECK 포함
    assert "[응답 생성 전 자체 검증" in prompt
    # Turn 블록 포함
    assert "[현재 턴: Opening" in prompt
    # Spectrum 문구 포함
    assert "네, 비슷하다" in prompt


def test_build_system_prompt_e2e_male_branch_half():
    prompt = sia_llm.build_system_prompt(
        user_name="준호",
        resolved_name=None,
        collected_fields={},
        missing_fields=[],
        ig_feed_cache=None,
        turn_type="branch_half",
        gender="male",
    )
    # 남성 화이트리스트 등장
    assert "자기 기준이 명확하신 분" in prompt
    # Half follow-up 고정 문구
    assert "절반 정도 맞다고 하신 건" in prompt
    # 남성 수치 범위 포함 (gender_block 에서)
    assert "172-178cm" in prompt
    # 여성 범위는 없어야
    assert "158-163cm" not in prompt


def test_build_system_prompt_invalid_gender_falls_back_to_female(caplog):
    prompt = sia_llm.build_system_prompt(
        user_name="민지",
        resolved_name=None,
        collected_fields={},
        missing_fields=[],
        ig_feed_cache=None,
        turn_type="opening",
        gender=None,
    )
    # 여성 기본값 적용 — female 화이트리스트 등장
    assert "무게 있게 받아들여지는 분" in prompt
    # 경고 로그 발생
    assert any("gender" in r.message for r in caplog.records)


def test_build_system_prompt_unknown_turn_type_falls_back(caplog):
    prompt = sia_llm.build_system_prompt(
        user_name="민지",
        resolved_name=None,
        collected_fields={},
        missing_fields=[],
        ig_feed_cache=None,
        turn_type="never_heard_of_this",
        gender="female",
    )
    # Unknown turn → fallback 표식
    assert "opening 폴백" in prompt or "Unknown" in prompt
