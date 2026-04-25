"""PI 전용 validator 단위 테스트 (Phase I PI-D).

CLAUDE.md §3.2 / §6.3 / §7.1 PI 페르소나 톤 + 4종 hard reject.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.sia_validators_pi import (
    PI_LENGTH_BUDGETS,
    PI_USER_FACING_KEYS,
    PIValidationResult,
    check_pi_a17_commerce,
    check_pi_a18_length,
    check_pi_a20_abstract_praise,
    check_pi_markdown,
    check_pi_persona_formal,
    check_pi_persona_friendly,
    collect_pi_content_violations,
    collect_pi_violations,
    make_pi_validator,
    validate_pi_content,
    validate_pi_text,
)


# ─────────────────────────────────────────────
#  PI-A17 영업 차단 (PI 한정 어휘 허용)
# ─────────────────────────────────────────────

def test_pi_a17_blocks_subscription_terms():
    """구독/티어/프리미엄/매장 어휘는 차단."""
    bad_samples = [
        "프리미엄 구독으로 더 많은 정보를 받으세요",
        "헤어샵에서 구매하실 수 있어요",
        "₩2,000 추가 결제하면 받을 수 있어요",
        "20토큰만 충전하면 풀어드려요",
        "다음 단계로 컨설팅을 안내해드릴게요",
    ]
    for sample in bad_samples:
        errors = check_pi_a17_commerce(sample)
        assert errors, f"PI-A17 should reject: {sample!r}"


def test_pi_a17_allows_pi_native_terms():
    """리포트 / 진단 / 분석 어휘는 PI 영역에서 허용."""
    ok_samples = [
        "이번 리포트에서 핵심을 짚어드릴게요",
        "진단 결과 본인다움이 또렷해요",
        "객관적인 얼굴 분석이 가능해요",
        "추천 헤어 스타일은 레이어드 컷이에요",  # "추천" 단순 어휘는 허용
    ]
    for sample in ok_samples:
        errors = check_pi_a17_commerce(sample)
        assert not errors, f"PI-A17 false positive: {sample!r} → {errors}"


def test_pi_a17_blocks_recommendation_sales_phrase():
    """'추천해드릴' 영업 표현은 차단 (단순 '추천' 은 허용)."""
    errors = check_pi_a17_commerce("추천해드릴 다음 코스가 있어요")
    assert errors, "PI-A17 should block '추천해드릴' sales phrase"


# ─────────────────────────────────────────────
#  PI-A18 컴포넌트별 길이
# ─────────────────────────────────────────────

def test_pi_a18_length_within_budget():
    """cover budget (80-150) 안의 텍스트는 통과."""
    text = "본인다움이 또렷한 결을 보고 골랐어요. " * 4   # 약 80-100자
    errors = check_pi_a18_length(text, component="cover")
    assert not errors


def test_pi_a18_length_too_short():
    """cover 80자 미만은 too short 에러."""
    text = "짧아요"
    errors = check_pi_a18_length(text, component="cover")
    assert errors and "너무 짧음" in errors[0]


def test_pi_a18_length_too_long():
    """cover 150자 초과는 hard reject."""
    text = "긴 문장입니다 " * 30
    errors = check_pi_a18_length(text, component="cover")
    assert errors and ("hard reject" in errors[0] or "초과" in errors[0] or ">" in errors[0])


def test_pi_a18_action_item_short_budget():
    """action_item 은 30-80자 budget."""
    too_short = "짧아"
    errors_short = check_pi_a18_length(too_short, component="action_item")
    assert errors_short

    too_long = "긴 액션 아이템 " * 20
    errors_long = check_pi_a18_length(too_long, component="action_item")
    assert errors_long


def test_pi_a18_default_for_unknown_component():
    """알 수 없는 component 는 default budget (100-300)."""
    text = "어떤 컴포넌트인지 모르겠어요. " * 8   # ~100자
    errors = check_pi_a18_length(text, component="unknown_xyz")
    # default budget 안에 들어야 함 — 100-300 중간
    assert not errors


def test_pi_a18_empty_text_passes():
    """빈 문자열은 length 검증 우회 (LLM stub 통과 허용)."""
    assert check_pi_a18_length("", component="cover") == []
    assert check_pi_a18_length("   ", component="cover") == []


# ─────────────────────────────────────────────
#  PI-A20 추상 칭찬
# ─────────────────────────────────────────────

def test_pi_a20_blocks_abstract_praise():
    bad_samples = [
        "본인만의 매력이 또렷해요",
        "독특한 결이 인상적이에요",
        "특별한 분위기를 가지셨어요",
        "센스 있는 스타일이에요",
        "안목이 있으세요",
    ]
    for sample in bad_samples:
        errors = check_pi_a20_abstract_praise(sample)
        assert errors, f"PI-A20 should reject: {sample!r}"


def test_pi_a20_allows_objective_beauty_terms():
    """객관 뷰티 어휘 (얼굴형/비율/톤/무게감) 는 허용."""
    ok_samples = [
        "얼굴형이 또렷한 라인이에요",
        "비율이 균형 잡혀 있어요",
        "톤이 차분하게 모아져요",
        "무게감이 적절해요",
        "골격이 단단해요",
        "윤곽이 또렷해요",
    ]
    for sample in ok_samples:
        errors = check_pi_a20_abstract_praise(sample)
        assert not errors, f"PI-A20 false positive: {sample!r} → {errors}"


# ─────────────────────────────────────────────
#  PI-MD 마크다운
# ─────────────────────────────────────────────

def test_pi_md_blocks_markdown():
    bad_samples = [
        "**굵게** 표시",
        "*이탤릭* 표시",
        "## 헤더",
        "> 인용",
        "```\ncode\n```",
    ]
    for sample in bad_samples:
        errors = check_pi_markdown(sample)
        assert errors, f"PI-MD should reject: {sample!r}"


def test_pi_md_allows_normal_text():
    ok_samples = [
        "그냥 평범한 문장이에요",
        "본인다움이 또렷해요. 좋은 결이에요.",
        "라인이 곱고 톤이 차분해요",
    ]
    for sample in ok_samples:
        errors = check_pi_markdown(sample)
        assert not errors, f"PI-MD false positive: {sample!r}"


# ─────────────────────────────────────────────
#  페르소나 톤 — 친밀체 / 정중체 차단
# ─────────────────────────────────────────────

def test_pi_persona_blocks_friendly_suffixes():
    """Sia 친밀체 (~잖아요 / ~더라구요 / ~인가봐요) 차단."""
    bad_samples = [
        "본인이시잖아요",
        "톤이 또렷하더라구요",
        "이렇게 하시는 거인가봐요",
    ]
    for sample in bad_samples:
        errors = check_pi_persona_friendly(sample)
        assert errors, f"친밀체 should be blocked: {sample!r}"


def test_pi_persona_blocks_formal_endings():
    """Verdict 정중체 (~합니다 / ~입니다 / ~습니다) 문장 종결 차단."""
    bad_samples = [
        "본인다움이 또렷합니다.",
        "정세현님은 단정한 인상입니다.",
        "이 결을 따라가시면 됩니다.",
    ]
    for sample in bad_samples:
        errors = check_pi_persona_formal(sample)
        assert errors, f"정중체 should be blocked: {sample!r}"


def test_pi_persona_allows_report_tone():
    """리포트체 (~있어요 / ~세요 / ~해요 / ~이에요) 허용."""
    ok_samples = [
        "본인다움이 또렷하게 잡혀 있어요",
        "이런 결을 따라가보세요",
        "톤이 차분해요",
        "라인이 곱이에요",
    ]
    for sample in ok_samples:
        f_errors = check_pi_persona_friendly(sample)
        v_errors = check_pi_persona_formal(sample)
        assert not f_errors, f"친밀체 false positive: {sample!r} → {f_errors}"
        assert not v_errors, f"정중체 false positive: {sample!r} → {v_errors}"


# ─────────────────────────────────────────────
#  통합 entry — validate_pi_text
# ─────────────────────────────────────────────

def test_validate_pi_text_clean_passes():
    """4종 + 페르소나 모두 통과하는 정상 텍스트 (cover budget 80-150자)."""
    text = (
        "본인다움이 얼굴 라인에 또렷하게 잡혀 있어요. "
        "톤이 차분하게 모이고 윤곽이 곱이에요. "
        "이 결을 따라가시면 더 또렷해져요. "
        "지금 자리에서 한 발씩 자연스러운 흐름이 보여요."
    )
    result = validate_pi_text(text, component="cover")
    assert result.ok, f"clean text should pass: {result.errors}"


def test_validate_pi_text_collects_multiple_violations():
    """여러 위반이 한 번에 잡히는지."""
    bad = "**매력적인** 본인이세요. 49,000원에 컨설팅 가능해요."
    result = validate_pi_text(bad, component="cover")
    assert not result.ok
    # markdown + 추상칭찬 + 영업 모두 잡혀야 함
    error_text = " | ".join(result.errors)
    assert any("PI-A17" in e for e in result.errors)
    assert any("PI-A20" in e for e in result.errors)
    assert any("PI-MD" in e for e in result.errors)


def test_collect_pi_violations_returns_list():
    """sia_writer._call_with_retry validator 호환 list[str]."""
    bad = "프리미엄 구독을 추천해드릴게요"
    violations = collect_pi_violations(bad, component="cover")
    assert isinstance(violations, list)
    assert all(isinstance(v, str) for v in violations)
    assert len(violations) >= 1


def test_make_pi_validator_partial_binds_component():
    """make_pi_validator 가 component 를 partial-bind."""
    cover_validator = make_pi_validator("cover")
    bad = "짧아"   # cover budget 80-150 미만
    violations = cover_validator(bad)
    assert any("cover" in v for v in violations)


# ─────────────────────────────────────────────
#  PI-A 호환 진입점 — validate_pi_content
# ─────────────────────────────────────────────

def test_validate_pi_content_dict_clean():
    """cover content dict — 모든 필드 정상."""
    content = {
        "user_summary": (
            "본인다움이 얼굴 라인에 또렷하게 잡혀 있어요. "
            "톤이 차분하게 모이고 윤곽이 곱이에요."
        ),
        "needs_statement": (
            "이 결을 더 또렷하게 만들어가는 방향이 좋아요. "
            "지금 자리에서 한 발 더 나아가는 흐름이 자연스러워요."
        ),
        "sia_overall_message": (
            "정세현님 결을 따라 골랐어요. "
            "라인 / 톤 / 윤곽 세 축이 모두 한 방향으로 모이고 있어요."
        ),
    }
    result = validate_pi_content(section_id="cover", content=content)
    assert result.ok, f"clean dict should pass: {result.errors}"


def test_validate_pi_content_dict_catches_violation_with_key_prefix():
    """위반 발생 시 에러 메시지에 section.key prefix 포함."""
    content = {
        "user_summary": "**매력적인** 본인다움이에요",   # markdown + 추상칭찬
        "needs_statement": "그래도 좋은 방향이에요. 라인이 곱고 톤도 차분히 모여요.",
    }
    result = validate_pi_content(section_id="cover", content=content)
    assert not result.ok
    assert any("cover.user_summary" in e for e in result.errors)


def test_validate_pi_content_text_mode():
    """단일 text 모드 — section_id + text."""
    result = validate_pi_content(
        section_id="action_item",
        text="레이어드 컷을 한 번 시도해보세요",
    )
    assert result.ok, result.errors


def test_validate_pi_content_action_plan_items():
    """action_plan.items[].narrative 는 component='action_item' budget 으로 검증."""
    content = {
        "boundary_message": (
            "여기까지 펼쳐드렸어요. 나머지는 사용하실수록 정교해져요. "
            "다음 분석 때 다시 짚어드릴게요."
        ),
        "items": [
            {"narrative": "레이어드 컷 한 번 시도해보세요"},
            {"narrative": "짧"},  # too short for action_item (30-80)
        ],
    }
    result = validate_pi_content(section_id="action_plan", content=content)
    assert any("action_plan.items[1]" in e for e in result.errors)


def test_collect_pi_content_violations_returns_list():
    """sia_writer 호환 list[str]."""
    content = {"user_summary": "**bold**"}
    out = collect_pi_content_violations(section_id="cover", content=content)
    assert isinstance(out, list)
    assert any("PI-MD" in v for v in out)


# ─────────────────────────────────────────────
#  Schema 안정성 — PI_LENGTH_BUDGETS / PI_USER_FACING_KEYS
# ─────────────────────────────────────────────

def test_pi_length_budgets_covers_9_components():
    """9 컴포넌트 전수가 length budget 정의되어 있는지."""
    expected = {
        "cover", "celeb_reference", "face_structure",
        "type_reference", "gap_analysis", "skin_analysis",
        "coordinate_map", "hair_recommendation",
    }
    for c in expected:
        assert c in PI_LENGTH_BUDGETS, f"{c} budget missing"
    # action_plan 은 action_item 으로 항목 검증
    assert "action_item" in PI_LENGTH_BUDGETS
    assert "default" in PI_LENGTH_BUDGETS


def test_pi_user_facing_keys_covers_9_components():
    """9 컴포넌트 전수가 user-facing keys 정의되어 있는지."""
    expected_keys = {
        "cover", "celeb_reference", "face_structure",
        "type_reference", "gap_analysis", "skin_analysis",
        "coordinate_map", "hair_recommendation", "action_plan",
    }
    for c in expected_keys:
        assert c in PI_USER_FACING_KEYS, f"{c} user-facing keys missing"
