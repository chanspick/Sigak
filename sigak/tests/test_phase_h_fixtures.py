"""Phase H fixture 5종 검증 — 만재/지은/준호/서연/도윤.

SPEC 출처: .moai/specs/SPEC-SIA/ 세션 #4 v2 + #6 v2 + #7.

검증 범위:
  (A) 구조 검증 — 각 assistant 턴 text 가 validate() 통과 (cross-turn A-2 제외)
  (B) 분포 검증 — primary_type 카운트가 expected type_counts 와 일치
  (C) Composition 검증 — M1 결합 / EMPATHY 결합 / C6/C7 블록 / RANGE 모드 플래그 정합
  (D) 세션 길이 검증 — assistant 턴 수 = session_length

검증 제외:
  - A-2/A-3 cross-turn (rhythm) 규칙 — 스펙 fixture 는 자연스러운 대화 흐름을 의도 반영
    했으므로 상대적 엄격 적용 시 false positive 발생. pipeline 레벨 (routes) 에서 적용.
  - find_violations_v4 의 A-1 suffix pattern (네요/같아요 등) — §5.2 validate() 는 이
    체크를 하지 않음 (스펙 설계대로).
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schemas.sia_state import (
    COLLECTION,
    CONFRONT,
    HARDCODED_TYPES,
    MANAGEMENT,
    UNDERSTANDING,
    WHITESPACE,
    AssistantTurn,
    ConversationState,
    MsgType,
    UserTurn,
)
from services.sia_decision import update_state_from_user_turn
from services.sia_flag_extractor import extract_flags
from services.sia_validators_v4 import validate
from tests.fixtures.sia_phase_h import ALL_FIXTURES
from tests.fixtures.sia_phase_h.schema import AssistantSpec, Fixture, UserSpec


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

# 구조 오류로 취급하지 않는 rhythm 계열 에러 키워드 (cross-turn 영역).
# A-2 = 잖아요 3창 초과 / ~예요 연타. 스펙 fixture 는 이 rhythm 제한을 의도 반영 안 함
# (대화 흐름 우선). pipeline 레벨 (routes) 에서 살아있는 check 이므로 fixture 검증에선 pass.
_RHYTHM_ERROR_PREFIXES = ("A-2:", "A-3:")


def _is_rhythm_error(err: str) -> bool:
    return any(err.startswith(p) for p in _RHYTHM_ERROR_PREFIXES)


def _structural_errors(errors: list[str]) -> list[str]:
    """rhythm (A-2/A-3 cross-turn) 제외 구조 오류만 반환."""
    return [e for e in errors if not _is_rhythm_error(e)]


def _build_state(fixture: Fixture) -> ConversationState:
    return ConversationState(
        session_id=f"fixture-{fixture.id}",
        user_id=f"user-{fixture.id}",
        user_name=fixture.name,
    )


def _walk_fixture(fixture: Fixture) -> tuple[ConversationState, list[tuple[int, AssistantSpec, list[str]]]]:
    """fixture 턴을 순차 재생 — user update → validate assistant → append.

    Returns:
        (final_state, [(turn_idx, spec, structural_errors), ...])
    """
    state = _build_state(fixture)
    results: list[tuple[int, AssistantSpec, list[str]]] = []

    turn_idx = 0
    for item in fixture.turns:
        if isinstance(item, UserSpec):
            flags = extract_flags(item.text)
            state.turns.append(
                UserTurn(text=item.text, turn_idx=turn_idx, flags=flags)
            )
            update_state_from_user_turn(state, item.text)
            turn_idx += 1
            continue

        # AssistantSpec
        result = validate(
            item.text,
            item.msg_type,
            state=state,
            range_mode=item.range_mode,
            confrontation_block=item.confrontation_block,
            is_combined=item.is_combined,
            exit_confirmed=item.exit_confirmed,
        )
        structural = _structural_errors(result.errors)
        results.append((turn_idx, item, structural))

        # state 에 append (다음 validate 가 이 draft 를 참조)
        state.turns.append(
            AssistantTurn(
                text=item.text,
                msg_type=item.msg_type,
                turn_idx=turn_idx,
            )
        )
        # type_counts 집계
        state.type_counts[item.msg_type] = (
            state.type_counts.get(item.msg_type, 0) + 1
        )
        turn_idx += 1

    return state, results


# ─────────────────────────────────────────────
#  (A) 구조 검증 — rhythm 제외
# ─────────────────────────────────────────────

@pytest.mark.parametrize("fixture_id", list(ALL_FIXTURES.keys()))
def test_fixture_all_assistant_turns_structurally_valid(fixture_id):
    """각 assistant 턴의 text 가 validate() 통과 (cross-turn A-2 제외).

    HARDCODED_TYPES 도 포함 — 스펙 fixture 의 raw text 자체가 검증 대상.
    """
    fixture = ALL_FIXTURES[fixture_id]
    _, results = _walk_fixture(fixture)
    failures: list[str] = []
    for turn_idx, spec, structural in results:
        if structural:
            failures.append(
                f"[{fixture_id}] turn {turn_idx} ({spec.msg_type.value}): "
                f"{structural}\n  text={spec.text[:80]}..."
            )
    assert not failures, "\n".join(failures)


# ─────────────────────────────────────────────
#  (B) 분포 검증
# ─────────────────────────────────────────────

@pytest.mark.parametrize("fixture_id", list(ALL_FIXTURES.keys()))
def test_fixture_type_distribution_matches_expected(fixture_id):
    """primary_type 별 카운트가 expected.type_counts 와 동일."""
    fixture = ALL_FIXTURES[fixture_id]
    actual: dict[MsgType, int] = {}
    for spec in fixture.assistant_turns():
        actual[spec.msg_type] = actual.get(spec.msg_type, 0) + 1
    expected = fixture.expected.type_counts
    assert actual == expected, (
        f"[{fixture_id}] distribution mismatch\n"
        f"  expected={expected}\n  actual={actual}"
    )


@pytest.mark.parametrize("fixture_id", list(ALL_FIXTURES.keys()))
def test_fixture_session_length_matches(fixture_id):
    """assistant 턴 수 = session_length."""
    fixture = ALL_FIXTURES[fixture_id]
    actual_len = len(fixture.assistant_turns())
    assert actual_len == fixture.session_length, (
        f"[{fixture_id}] session_length mismatch: "
        f"expected={fixture.session_length}, actual={actual_len}"
    )


# ─────────────────────────────────────────────
#  (C) Composition meta 검증
# ─────────────────────────────────────────────

@pytest.mark.parametrize("fixture_id", list(ALL_FIXTURES.keys()))
def test_fixture_first_turn_is_m1_combined(fixture_id):
    """모든 fixture 의 첫 assistant 턴은 M1 결합 (OPENING + secondary=OBS)."""
    fixture = ALL_FIXTURES[fixture_id]
    first = fixture.assistant_turns()[0]
    assert first.msg_type == MsgType.OPENING_DECLARATION
    assert first.is_first_turn is True
    assert first.secondary_type == MsgType.OBSERVATION


def test_seoyeon_empathy_combined_outputs_present():
    """서연 M3/M4/M5 — 전부 EMPATHY 결합 출력."""
    fixture = ALL_FIXTURES["seoyeon"]
    empathy_turns = [
        s for s in fixture.assistant_turns()
        if s.msg_type == MsgType.EMPATHY_MIRROR
    ]
    assert len(empathy_turns) == 3
    for t in empathy_turns:
        assert t.is_combined is True
        assert t.secondary_type is not None


def test_seoyeon_m4_reaffirm_mode():
    """서연 M4 = EMPATHY + RANGE_REAFFIRM (막막함 우세)."""
    fixture = ALL_FIXTURES["seoyeon"]
    assistants = fixture.assistant_turns()
    # M1, M2, M3, M4 — 인덱스 3 (0-based)
    m4 = assistants[3]
    assert m4.msg_type == MsgType.EMPATHY_MIRROR
    assert m4.secondary_type == MsgType.RANGE_DISCLOSURE
    assert m4.range_mode == "reaffirm"


def test_seoyeon_m5_c6_combined():
    """서연 M5 = EMPATHY + CONFRONTATION(C6) — 평가 의존 돌파."""
    fixture = ALL_FIXTURES["seoyeon"]
    m5 = fixture.assistant_turns()[4]
    assert m5.msg_type == MsgType.EMPATHY_MIRROR
    assert m5.secondary_type == MsgType.CONFRONTATION
    assert m5.confrontation_block == "C6"


def test_doyoon_c6_and_c7_blocks_present():
    """도윤 M5 = CONFRONTATION C6, M6 = CONFRONTATION C7."""
    fixture = ALL_FIXTURES["doyoon"]
    assistants = fixture.assistant_turns()
    m5 = assistants[4]
    m6 = assistants[5]
    assert m5.msg_type == MsgType.CONFRONTATION
    assert m5.confrontation_block == "C6"
    assert m6.msg_type == MsgType.CONFRONTATION
    assert m6.confrontation_block == "C7"


def test_doyoon_self_pr_prefix_marked_on_three_turns():
    """도윤 M2, M3, M5 — A-13 자기 PR prefix 적용."""
    fixture = ALL_FIXTURES["doyoon"]
    assistants = fixture.assistant_turns()
    prefix_turns = [s for s in assistants if s.apply_self_pr_prefix]
    assert len(prefix_turns) == 3
    assert {s.msg_type for s in prefix_turns} == {
        MsgType.EVIDENCE_DEFENSE,   # M2
        MsgType.PROBE,               # M3
        MsgType.CONFRONTATION,       # M5
    }


def test_junho_check_in_and_re_entry_present():
    """준호 M7 CHECK_IN, M8 RE_ENTRY — 관리 3 타입 중 2개 활용."""
    fixture = ALL_FIXTURES["junho"]
    assistants = fixture.assistant_turns()
    m7 = assistants[6]
    m8 = assistants[7]
    assert m7.msg_type == MsgType.CHECK_IN
    assert m8.msg_type == MsgType.RE_ENTRY


def test_manjae_confrontation_c1():
    """만재 M7 = CONFRONTATION C1 (외부 권위 회귀 돌파)."""
    fixture = ALL_FIXTURES["manjae"]
    m7 = fixture.assistant_turns()[6]
    assert m7.msg_type == MsgType.CONFRONTATION
    assert m7.confrontation_block == "C1"


def test_jieun_confrontation_c2_twice():
    """지은 M7 + M12 = CONFRONTATION C2 (자기 축소 돌파 + 재투입)."""
    fixture = ALL_FIXTURES["jieun"]
    assistants = fixture.assistant_turns()
    c2_turns = [
        s for s in assistants
        if s.msg_type == MsgType.CONFRONTATION and s.confrontation_block == "C2"
    ]
    assert len(c2_turns) == 2


# ─────────────────────────────────────────────
#  (D) sub-rule 비율 검증
# ─────────────────────────────────────────────

@pytest.mark.parametrize("fixture_id", ["manjae", "jieun", "junho"])
def test_diagnosis_min_ratio_for_full_sessions(fixture_id):
    """세션 15턴 fixture 는 DIAGNOSIS ≥ 12% (2회 이상) 충족."""
    fixture = ALL_FIXTURES[fixture_id]
    if not fixture.expected.diagnosis_min_satisfied:
        pytest.skip("diagnosis_min 미충족으로 명시 — 검증 skip")
    diag_count = fixture.expected.type_counts.get(MsgType.DIAGNOSIS, 0)
    total = fixture.session_length
    ratio = diag_count / total
    assert diag_count >= 2, f"{fixture_id}: DIAGNOSIS {diag_count}회 < 2회 하한"
    assert ratio >= 0.12, (
        f"{fixture_id}: DIAGNOSIS 비율 {ratio:.1%} < 12% 하한"
    )


@pytest.mark.parametrize("fixture_id", ["manjae", "jieun", "junho"])
def test_recognition_two_floor_for_full_sessions(fixture_id):
    """세션 15턴 fixture 는 RECOGNITION ≥ 2회 하한 충족 (세션 #5 v2 §7.2)."""
    fixture = ALL_FIXTURES[fixture_id]
    if not fixture.expected.recognition_min_satisfied:
        pytest.skip("recognition_min 미충족으로 명시 — 검증 skip")
    recog_count = fixture.expected.type_counts.get(MsgType.RECOGNITION, 0)
    assert recog_count >= 2, (
        f"{fixture_id}: RECOGNITION {recog_count}회 < 2회 하한"
    )


@pytest.mark.parametrize("fixture_id", ["jieun"])
def test_empathy_within_15_percent_for_normal_sessions(fixture_id):
    """EMPATHY 15% 이하 가이드 (sub-rule 허용 제외 fixture 만 검증)."""
    fixture = ALL_FIXTURES[fixture_id]
    if fixture.expected.empathy_over_15_percent_allowed:
        pytest.skip("EMPATHY 초과 허용 fixture — 검증 skip")
    em_count = fixture.expected.type_counts.get(MsgType.EMPATHY_MIRROR, 0)
    ratio = em_count / fixture.session_length
    assert ratio <= 0.15, (
        f"{fixture_id}: EMPATHY {ratio:.1%} > 15% 가이드"
    )


@pytest.mark.parametrize("fixture_id", ["jieun"])
def test_soft_walkback_within_8_percent(fixture_id):
    """SOFT_WALKBACK 8% 이하 sub-rule."""
    fixture = ALL_FIXTURES[fixture_id]
    soft_count = fixture.expected.type_counts.get(MsgType.SOFT_WALKBACK, 0)
    ratio = soft_count / fixture.session_length
    assert ratio <= 0.08, (
        f"{fixture_id}: SOFT_WALKBACK {ratio:.1%} > 8% 상한"
    )


# ─────────────────────────────────────────────
#  (E) 버킷 합계 검증
# ─────────────────────────────────────────────

@pytest.mark.parametrize("fixture_id", list(ALL_FIXTURES.keys()))
def test_fixture_bucket_total_equals_session_length(fixture_id):
    """5 버킷 (수집/이해/여백/대결/관리) 합 = session_length."""
    fixture = ALL_FIXTURES[fixture_id]
    bucket_total = 0
    for mt, count in fixture.expected.type_counts.items():
        if mt in COLLECTION or mt in UNDERSTANDING or mt in WHITESPACE \
                or mt in CONFRONT or mt in MANAGEMENT:
            bucket_total += count
    assert bucket_total == fixture.session_length, (
        f"[{fixture_id}] bucket total {bucket_total} != session {fixture.session_length}"
    )


# ─────────────────────────────────────────────
#  (F) Hardcoded 타입 비중 (준호 관리 2개, 나머지 0)
# ─────────────────────────────────────────────

def test_only_junho_has_management_types():
    """CHECK_IN / RE_ENTRY / RANGE_DISCLOSURE 는 준호에만 나타남 (실패 모드 대응 fixture)."""
    for fid, fixture in ALL_FIXTURES.items():
        management_count = sum(
            fixture.expected.type_counts.get(mt, 0) for mt in MANAGEMENT
        )
        if fid == "junho":
            assert management_count == 2, (
                f"junho: 관리 타입 2회 (CHECK_IN + RE_ENTRY) — actual {management_count}"
            )
        else:
            assert management_count == 0, (
                f"{fid}: 관리 타입 기대값 0 — actual {management_count}"
            )


# ─────────────────────────────────────────────
#  (G) 필수 fixture 수량
# ─────────────────────────────────────────────

def test_five_fixtures_registered():
    """만재 / 지은 / 준호 / 서연 / 도윤 5종 정확 등록."""
    assert set(ALL_FIXTURES.keys()) == {
        "manjae", "jieun", "junho", "seoyeon", "doyoon",
    }


def test_fixture_archetypes_cover_key_defense_modes():
    """각 fixture 의 archetype 가 중복 없이 주요 방어 모드 커버."""
    archetypes = {f.archetype for f in ALL_FIXTURES.values()}
    assert len(archetypes) == 5
    # 필수 archetype 명 검증 (세션 #4 v2 + #6 v2 + #7 커버)
    assert "외부 권위 회귀형" in archetypes
    assert "자기 축소형" in archetypes
    assert "방관 단답형" in archetypes
    assert "자기평가 변동형" in archetypes
    assert "자기 PR 과잉형" in archetypes
