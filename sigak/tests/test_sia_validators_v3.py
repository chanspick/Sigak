"""Sia validators v3 extensions 테스트 — Phase B1.

count_assertions / has_abstract_noun + find_violations 통합.
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.sia_validators import (
    count_assertions,
    has_abstract_noun,
    find_violations,
)


# ─────────────────────────────────────────────
#  count_assertions
# ─────────────────────────────────────────────

def test_count_assertions_single_assertion():
    text = "정세현님은 단정한 인상으로 기억되는 분입니다."
    assert count_assertions(text) == 1


def test_count_assertions_two_assertions_multi_line():
    text = (
        "정세현님은 단정한 분입니다.\n"
        "정세현님은 조용한 자신감을 드러내는 쪽이십니다."
    )
    assert count_assertions(text) == 2


def test_count_assertions_three_violation_candidate():
    text = (
        "정세현님은 A 분입니다.\n"
        "정세현님은 B 편이십니다.\n"
        "정세현님은 C 쪽이십니다."
    )
    assert count_assertions(text) == 3  # > 2 → find_violations 에서 위반


def test_count_assertions_excludes_function_line_sia_intro():
    text = (
        "정세현님, Sia 입니다.\n"
        "하나만 먼저 확인하겠습니다.\n"
        "정세현님은 단정한 분입니다."
    )
    # Sia 입니다 / 확인하겠습니다 는 기능문 → 제외. 단정은 1개.
    assert count_assertions(text) == 1


def test_count_assertions_excludes_numeric_range_line():
    text = (
        "정세현님은 신중하신 분입니다.\n"
        "- 165cm 이하\n"
        "- 165-172cm\n"
        "- 172-178cm"
    )
    # 수치 범위 라인은 기능문 → 제외
    assert count_assertions(text) == 1


def test_count_assertions_excludes_question_prompts():
    text = (
        "정세현님은 정돈된 인상의 분입니다.\n"
        "맞다고 느끼시나요?"
    )
    assert count_assertions(text) == 1


def test_count_assertions_danger_pattern():
    """이름 없는 서술문 — 단정 카운트에 들어가지 않음 (undercount OK)."""
    text = "그래서 차분한 경향이 있습니다."
    assert count_assertions(text) == 0


def test_count_assertions_당신_prefix_counted():
    text = "당신은 차분한 분입니다."
    assert count_assertions(text) == 1


def test_count_assertions_empty_text():
    assert count_assertions("") == 0
    assert count_assertions("\n\n\n") == 0


# ─────────────────────────────────────────────
#  has_abstract_noun
# ─────────────────────────────────────────────

def test_has_abstract_noun_detects_결_variants():
    assert has_abstract_noun("정세현님의 결이 다릅니다.") is True
    assert has_abstract_noun("피드의 결은 정돈되어 있습니다.") is True
    assert has_abstract_noun("결을 먼저 봅니다.") is True


def test_has_abstract_noun_detects_무드_variants():
    assert has_abstract_noun("무드가 느껴지는 분입니다.") is True
    assert has_abstract_noun("무드를 보여주십니다.") is True


def test_has_abstract_noun_detects_aura_and_ki():
    assert has_abstract_noun("고요한 아우라가 있습니다.") is True
    assert has_abstract_noun("묘한 기운이 있습니다.") is True


def test_has_abstract_noun_does_not_false_positive():
    """구체 단정 문장은 통과해야."""
    clean_lines = [
        "정세현님은 단정한 분입니다.",
        "피드에서 정돈된 인상이 드러납니다.",
        "조용한 자신감이 느껴지십니다.",
    ]
    for line in clean_lines:
        assert has_abstract_noun(line) is False, line


# ─────────────────────────────────────────────
#  find_violations 통합
# ─────────────────────────────────────────────

def test_find_violations_flags_assertion_excess():
    text = (
        "정세현님은 A 분입니다.\n"
        "정세현님은 B 편이십니다.\n"
        "정세현님은 C 쪽이십니다."
    )
    v = find_violations(text)
    assert "assertion_excess" in v
    assert "count=3" in v["assertion_excess"][0]


def test_find_violations_passes_two_assertions():
    text = (
        "정세현님은 A 분입니다.\n"
        "정세현님은 B 편이십니다."
    )
    v = find_violations(text)
    assert "assertion_excess" not in v


def test_find_violations_flags_abstract_noun():
    text = "정세현님의 결은 정돈되어 있습니다."
    v = find_violations(text)
    assert "abstract_noun" in v
    assert "결은" in v["abstract_noun"]


def test_find_violations_clean_passes_new_rules():
    text = (
        "정세현님, Sia 입니다.\n"
        "정세현님은 단정한 분입니다.\n"
        "하나만 먼저 확인하겠습니다.\n"
        "주말 저녁 어떤 인상으로 기억되고 싶으신가요?"
    )
    v = find_violations(text)
    assert "assertion_excess" not in v
    assert "abstract_noun" not in v
