"""Sia fixture sanity suite — Phase D (Task 8).

tests/fixtures/sia_samples/{female,male}/*.json 30 개를 로드하여:
  - JSON 파싱 / 스키마 / 개수
  - validator v3 통과 (assertion ≤ 2, abstract noun 0, forbidden endings 0)
  - [NAME] 치환 상태
  - gender / turn_type 일관성
  - 성별 체형 범위 분기
  - branch_fail 고정 교정문 포함
  - 화이트리스트 정렬 태그 정합성

실 Haiku / Apify 호출 없음. 비용 0.
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from services.sia_validators import (
    count_assertions,
    has_abstract_noun,
    find_violations,
)
from tests.fixtures.sia_samples import (
    FIXTURE_ROOT,
    load_all_fixtures,
    iter_fixture_paths,
)


REQUIRED_KEYS = {
    "fixture_id", "gender", "turn_type",
    "context", "expected_response", "validator_expectations",
}

ASSERTION_TURNS = {
    "opening", "branch_agree", "branch_disagree", "precision_continue",
}


# ─────────────────────────────────────────────
#  1 — 로드 / 스키마 / 개수
# ─────────────────────────────────────────────

def test_all_fixtures_load_without_error():
    fixtures = load_all_fixtures()
    assert len(fixtures) >= 20, f"only loaded {len(fixtures)} fixtures"


def test_all_fixtures_have_required_keys():
    for fx_path in iter_fixture_paths():
        import json
        data = json.loads(fx_path.read_text(encoding="utf-8"))
        missing = REQUIRED_KEYS - set(data.keys())
        assert not missing, f"{fx_path.name} missing: {missing}"


def test_fixture_count_at_least_20():
    fixtures = load_all_fixtures()
    assert len(fixtures) >= 20


# ─────────────────────────────────────────────
#  4 — validator v3 통과
# ─────────────────────────────────────────────

def _fixture_id(fx):
    return fx.get("fixture_id", "unknown")


def test_fixture_pass_validator():
    """각 expected_response 가 Phase B validator 전수 통과."""
    for fx in load_all_fixtures():
        text = fx["expected_response"]
        fid = _fixture_id(fx)

        # Hard constraints — violator 로 검증
        violations = find_violations(text)
        assert "assertion_excess" not in violations, (
            f"{fid} — assertion_excess: {violations.get('assertion_excess')}"
        )
        assert "abstract_noun" not in violations, (
            f"{fid} — abstract_noun: {violations.get('abstract_noun')}"
        )
        # 금지 어미 / 평가 / 확인 요청 / 마크다운 등 기존 규칙도 전부 통과
        for rule in (
            "HR1_verdict", "HR2_judgment", "HR3_markdown",
            "HR4_bullet", "HR5_emoji",
            "tone_suffix", "tone_missing",
            "eval_language", "confirmation",
        ):
            assert rule not in violations, f"{fid} — {rule}: {violations[rule]}"

        # 직접 헬퍼 재확인
        assert count_assertions(text) <= 2, fid
        assert has_abstract_noun(text) is False, fid


# ─────────────────────────────────────────────
#  5 — [NAME] placeholder 치환 완료
# ─────────────────────────────────────────────

def test_fixture_name_placeholder_replaced():
    """fixture 안에 [NAME] 리터럴이 남아 있으면 치환 로직 문제."""
    for fx in load_all_fixtures():
        assert "[NAME]" not in fx["expected_response"], _fixture_id(fx)


# ─────────────────────────────────────────────
#  6 / 7 — gender 디렉터리 일관성
# ─────────────────────────────────────────────

def test_female_fixtures_gender_consistent():
    for fx_path in iter_fixture_paths():
        if fx_path.parent.name != "female":
            continue
        import json
        data = json.loads(fx_path.read_text(encoding="utf-8"))
        assert data["gender"] == "female", fx_path.name


def test_male_fixtures_gender_consistent():
    for fx_path in iter_fixture_paths():
        if fx_path.parent.name != "male":
            continue
        import json
        data = json.loads(fx_path.read_text(encoding="utf-8"))
        assert data["gender"] == "male", fx_path.name


# ─────────────────────────────────────────────
#  8 — 성별 체형 범위 분리
# ─────────────────────────────────────────────

def test_external_body_height_gender_ranges():
    from tests.fixtures.sia_samples import load_fixture

    female = load_fixture("female", "external_body_height")["expected_response"]
    male = load_fixture("male", "external_body_height")["expected_response"]

    # 여성 경계
    for r in ("150cm", "158cm", "163cm", "168cm"):
        assert r in female, f"female missing {r}"
    # 여성 fixture 에 남성 경계 교차 0
    for r in ("172-178cm", "178-183cm"):
        assert r not in female, f"female should not contain {r}"

    # 남성 경계
    for r in ("165cm", "172cm", "178cm", "183cm"):
        assert r in male, f"male missing {r}"
    # 남성 fixture 에 여성 경계 교차 0
    for r in ("150-158cm", "158-163cm"):
        assert r not in male, f"male should not contain {r}"


# ─────────────────────────────────────────────
#  9 — branch_fail 고정 교정문
# ─────────────────────────────────────────────

def test_branch_fail_fixed_copy():
    from tests.fixtures.sia_samples import load_fixture
    for gender in ("female", "male"):
        text = load_fixture(gender, "branch_fail")["expected_response"]
        assert "피드에서 읽히는" in text, gender
        assert "갭이 있으십니다" in text, gender
        # Blocker 1 재발 방지 — 추상명사 / 모호 어미
        assert "결" not in text, f"{gender} branch_fail contains abstract '결'"
        assert "같습니다" not in text, f"{gender} branch_fail ends with '같습니다'"
        # 이름 치환 완료
        assert "정세현님" in text
        assert "[NAME]" not in text


# ─────────────────────────────────────────────
#  10 — 화이트리스트 정렬 태그
# ─────────────────────────────────────────────

def test_whitelist_alignment_marked():
    for fx in load_all_fixtures():
        turn = fx["turn_type"]
        mark = fx["validator_expectations"]["whitelist_alignment"]
        if turn in ASSERTION_TURNS:
            assert mark is True, f"{_fixture_id(fx)} should have whitelist_alignment=true"
        else:
            assert mark is False, f"{_fixture_id(fx)} should have whitelist_alignment=false"


# ─────────────────────────────────────────────
#  추가 — 전수 30 파일 보장 (15 turn × 2 gender)
# ─────────────────────────────────────────────

_EXPECTED_TURN_TYPES = {
    "opening", "branch_agree", "branch_half", "branch_disagree", "branch_fail",
    "precision_continue", "force_external_transition",
    "external_desired_image", "external_reference",
    "external_body_height", "external_body_weight", "external_body_shoulder",
    "external_concerns", "external_lifestyle",
    "closing",
}


@pytest.mark.parametrize("gender", ["female", "male"])
def test_fixture_directory_covers_all_turn_types(gender):
    dir_path = FIXTURE_ROOT / gender
    present = {p.stem for p in dir_path.glob("*.json")}
    missing = _EXPECTED_TURN_TYPES - present
    assert not missing, f"{gender} missing turn types: {missing}"
