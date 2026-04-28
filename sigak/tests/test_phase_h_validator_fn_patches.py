"""Phase H3 §5.2 drop-in 검증 — FN 4건 해소 + A-1 확장 + 공개 API.

Source: SIA_SESSION4_V2 §5 Validator v4.

FN 회수 대상 (§5):
  FN-1 (#7)  "아 그렇게 느끼셨구나" — GUNNA_PATTERN 매치 + BANMAL 안전
  FN-2 (#8)  "봄웜이라고 하셨네"   — BANMAL_END_PATTERN (문장 끝 반말)
  FN-3 (#9)  잖아요 3창 2회 초과   — check_cross_turn_rules 합산
  FN-4 (#10) EMPATHY ~잖아요      — check_type_conditional
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
    ValidationResult,
    check_a17_commerce,
    check_a18_length,
    check_a18_length_warning,
    check_a20_abstract_praise,
    check_cross_turn_rules,
    check_global_forbidden,
    check_haiku_naturalness,
    check_markdown_markup,
    check_type_conditional,
    find_violations_v4,
    validate,
)


# ─────────────────────────────────────────────
#  fixtures
# ─────────────────────────────────────────────

def _state(
    *, user_name: str = "만재", user_id: str = "u-fn",
) -> ConversationState:
    return ConversationState(
        session_id="sess-fn",
        user_id=user_id,
        user_name=user_name,
    )


def _prior_drafts(state: ConversationState, drafts: list[str]) -> None:
    """state.turns 에 AssistantTurn 을 주입. 간단 tokenizer."""
    for i, text in enumerate(drafts):
        state.turns.append(AssistantTurn(
            text=text,
            msg_type=MsgType.OBSERVATION,
            turn_idx=i,
            jangayo_count=text.count("잖아요"),
        ))


# ─────────────────────────────────────────────
#  FN 4건 해소
# ─────────────────────────────────────────────

class TestFN1Gunna:
    """FN-1: "~구나" 단독 (~요 없이) 유저 공감 실패 유형."""

    def test_catches_geureoke_neukkyeo_sseonguna(self):
        errs = check_global_forbidden(
            "아 그렇게 느끼셨구나", MsgType.EMPATHY_MIRROR,
        )
        assert any("~구나" in e for e in errs)

    def test_catches_bwasseunguna(self):
        errs = check_global_forbidden(
            "아 봤구나", MsgType.EMPATHY_MIRROR,
        )
        assert any("~구나" in e for e in errs)

    def test_allows_shieosseoseo_gunayo(self):
        # 뒤에 요가 붙으면 통과 — `~구나요` 는 금지 아님
        errs = check_global_forbidden(
            "그러셨구나요", MsgType.EMPATHY_MIRROR,
        )
        assert not any("~구나" in e for e in errs)


class TestFN2Banmal:
    """FN-2: 문장 끝 반말 종결 — 네/나/야/지/군."""

    def test_catches_end_ne(self):
        errs = check_global_forbidden(
            "봄웜이라고 하셨네", MsgType.PROBE,
        )
        assert any("반말 종결" in e for e in errs)

    def test_catches_end_ji_with_qmark(self):
        errs = check_global_forbidden(
            "맞지?", MsgType.PROBE,
        )
        assert any("반말 종결" in e for e in errs)

    def test_allows_neyo(self):
        # "네요" 는 페르소나 B 해요체. BANMAL 안 걸려야 함.
        errs = check_global_forbidden(
            "좋네요", MsgType.OBSERVATION,
        )
        assert not any("반말 종결" in e for e in errs)

    def test_allows_indirect_question_neunji(self):
        # "~는지" 간접 의문 문장 중간 — false positive 회피 확인 (regex tighten)
        errs = check_global_forbidden(
            "어디서 오는지 살펴봐요", MsgType.OPENING_DECLARATION,
        )
        assert not any("반말 종결" in e for e in errs)

    def test_allows_gunyo(self):
        # "~군요?" 는 A-1 내 기존 forbidden 으로 따로 잡힘 (a1_forbidden_suffix).
        # 여기서는 BANMAL 이 아님 (군 뒤에 요 있음) 확인.
        errs = check_global_forbidden(
            "그러시는군요?", MsgType.PROBE,
        )
        assert not any("반말 종결" in e for e in errs)


class TestFN3JangayoCrossTurn:
    """FN-3: ~잖아요 3 메시지 창 누적 카운트."""

    def test_blocks_when_window_exceeds(self):
        s = _state()
        _prior_drafts(s, [
            "만재님이 고르신 거잖아요?",
            "맞잖아요?",
        ])
        errors, warnings = check_cross_turn_rules(
            "그거잖아요?", MsgType.PROBE, s,
        )
        assert any("~잖아요" in e and "초과" in e for e in errors)

    def test_allows_when_window_ok(self):
        s = _state()
        _prior_drafts(s, [
            "만재님이 고르신 거잖아요?",
        ])
        # current + prior = 2 total, not exceeding
        errors, _ = check_cross_turn_rules(
            "맞잖아요?", MsgType.PROBE, s,
        )
        assert not any("~잖아요" in e for e in errors)


class TestFN4EmpathyJangayo:
    """FN-4: EMPATHY_MIRROR 는 ~잖아요 금지 (공감 반사의 톤 깨짐)."""

    def test_blocks_empathy_with_jangayo(self):
        errs = check_type_conditional(
            "어색하셨잖아요", MsgType.EMPATHY_MIRROR,
        )
        assert any("EMPATHY_MIRROR" in e and "잖아요" in e for e in errs)

    def test_allows_probe_with_jangayo(self):
        errs = check_type_conditional(
            "이미 아시잖아요?", MsgType.PROBE,
        )
        assert not any("EMPATHY_MIRROR" in e for e in errs)


# ─────────────────────────────────────────────
#  A-1 확장 (§5.1 regex 목록)
# ─────────────────────────────────────────────

class TestA1Extension:
    def test_blocks_kiekie(self):
        errs = check_global_forbidden("ㅋㅋ 편하셨나봐요?", MsgType.PROBE)
        assert any("ㅋ 전역 금지" in e for e in errs)

    def test_blocks_axis_label_alone(self):
        # "색깔요" 축 라벨 단독 호명
        errs = check_global_forbidden("색깔요, 그 부분", MsgType.PROBE)
        assert any("축 라벨" in e for e in errs)

    def test_blocks_victory_expression_imi_ashineun(self):
        errs = check_global_forbidden(
            "만재님 이미 아시는 거잖아요?", MsgType.RECOGNITION,
        )
        assert any("승리 표현" in e for e in errs)

    def test_blocks_victory_expression_jabasseoyo(self):
        errs = check_global_forbidden("그거 잡았어요!", MsgType.DIAGNOSIS)
        assert any("승리 표현" in e for e in errs)

    def test_blocks_double_contrast(self):
        # 마케터 regex 는 `인 거예요[,\s.]*\S*\s*아니` — 사이 단어 1개만 허용.
        errs = check_global_forbidden(
            "본인 선택인 거예요. 감각 아니라고요.",
            MsgType.DIAGNOSIS,
        )
        assert any("이중 대비" in e for e in errs)

    def test_blocks_absolute_obs_in_observation(self):
        errs = check_global_forbidden(
            "피드에 본인 사진 하나도 없으시더라구요?",
            MsgType.OBSERVATION,
        )
        assert any("관찰 절대 표현" in e for e in errs)

    def test_allows_absolute_obs_in_recognition(self):
        # RECOGNITION 은 COLLECTION 타입 아님 → 절대 표현 제외.
        errs = check_global_forbidden(
            "하나도 없는 쪽이신가봐요?", MsgType.RECOGNITION,
        )
        assert not any("절대 표현" in e for e in errs)


# ─────────────────────────────────────────────
#  A-5 RECOGNITION 단정 ~예요
# ─────────────────────────────────────────────

class TestA5RecognitionYeyoDancheong:
    def test_blocks_recognition_declarative_yeyo(self):
        errs = check_type_conditional(
            "그게 만재님 쪽이예요.", MsgType.RECOGNITION,
        )
        assert any("RECOGNITION" in e and "~예요" in e for e in errs)

    def test_allows_recognition_yeyo_question(self):
        # ~예요? 질문 종결이면 허용
        errs = check_type_conditional(
            "그게 만재님 쪽이예요?", MsgType.RECOGNITION,
        )
        assert not any("단정 ~예요" in e for e in errs)

    def test_allows_diagnosis_yeyo(self):
        # DIAGNOSIS 는 단정 ~예요 허용 (진단 자체가 평서)
        errs = check_type_conditional(
            "만재님 피드는 배경이 먼저예요.", MsgType.DIAGNOSIS,
        )
        assert not any("RECOGNITION" in e for e in errs)


# ─────────────────────────────────────────────
#  Cross-turn ~예요 연타
# ─────────────────────────────────────────────

class TestYeyoRepeat:
    def test_yeyo_repeat_without_softener_blocks(self):
        s = _state()
        _prior_drafts(s, ["본인 쪽이예요."])
        errs, _ = check_cross_turn_rules(
            "그게 맞는 쪽이예요?", MsgType.PROBE, s,
        )
        assert any("~예요 연타" in e for e in errs)

    def test_yeyo_repeat_with_neyo_softener_ok(self):
        s = _state()
        _prior_drafts(s, ["본인 쪽이예요."])
        errs, _ = check_cross_turn_rules(
            "그게 맞는 쪽이네요.", MsgType.PROBE, s,
        )
        assert not any("~예요 연타" in e for e in errs)


# ─────────────────────────────────────────────
#  EMPATHY_MIRROR 비율 경고 (sub-rule, A-3 우선)
# ─────────────────────────────────────────────

class TestEmpathyRatioWarning:
    def test_warning_when_em_pct_exceeds_15(self):
        s = _state()
        # 현재 type_counts: EMPATHY 2, OBSERVATION 5, RECOGNITION 2 → total 9
        # + current EMPATHY 1 = total 10, em = 3/10 = 30% > 15%
        s.type_counts[MsgType.EMPATHY_MIRROR] = 2
        s.type_counts[MsgType.OBSERVATION] = 5
        s.type_counts[MsgType.RECOGNITION] = 2
        _, warnings = check_cross_turn_rules(
            "어색하셨구나.", MsgType.EMPATHY_MIRROR, s,
        )
        assert any("EMPATHY_MIRROR" in w for w in warnings)

    def test_no_warning_when_em_pct_ok(self):
        s = _state()
        s.type_counts[MsgType.EMPATHY_MIRROR] = 0
        s.type_counts[MsgType.OBSERVATION] = 9
        _, warnings = check_cross_turn_rules(
            "어색하셨구나.", MsgType.EMPATHY_MIRROR, s,
        )
        assert not any("EMPATHY_MIRROR" in w for w in warnings)


# ─────────────────────────────────────────────
#  Public API — validate() + ValidationResult
# ─────────────────────────────────────────────

class TestValidateAPI:
    def test_validation_result_default_ok(self):
        r = ValidationResult()
        assert r.ok
        assert r.errors == []
        assert r.warnings == []

    def test_validate_clean(self):
        r = validate("편하신 자리이신가봐요?", MsgType.OBSERVATION)
        # Note: 이 텍스트는 A-5 question 체크 OK (question mark 있음).
        # §5.2 로는 clean. 다만 base validator 의 tone 등은 별도 API.
        assert r.ok
        assert r.errors == []

    def test_validate_catches_jangayo_stack_in_empathy(self):
        r = validate("어색하셨잖아요", MsgType.EMPATHY_MIRROR)
        assert not r.ok
        joined = " | ".join(r.errors)
        assert "EMPATHY_MIRROR" in joined and "잖아요" in joined

    def test_validate_state_optional(self):
        # state=None 허용 — cross-turn 체크만 생략.
        # "느끼셨구나" — 마케터 GUNNA 그룹 중 `느끼셨` 포함.
        r = validate("아 느끼셨구나", MsgType.EMPATHY_MIRROR, state=None)
        assert not r.ok
        assert any("구나" in e for e in r.errors)


# ─────────────────────────────────────────────
#  find_violations_v4 merge 검증
# ─────────────────────────────────────────────

class TestFindViolationsV4Merge:
    def test_drop_in_errors_merged(self):
        v = find_violations_v4("ㅋㅋ 편하신가봐요?", MsgType.OBSERVATION)
        assert "marketer_errors" in v
        assert any("ㅋ" in e for e in v["marketer_errors"])

    def test_clean_no_marketer_key(self):
        v = find_violations_v4("편하신 자리이신가봐요?", MsgType.OBSERVATION)
        assert "marketer_errors" not in v

    def test_warning_key_emerges_with_state(self):
        s = _state()
        s.type_counts[MsgType.EMPATHY_MIRROR] = 3
        s.type_counts[MsgType.OBSERVATION] = 5
        v = find_violations_v4(
            "어색하셨구나.", MsgType.EMPATHY_MIRROR, state=s,
            emotion_word_raw="어색",
        )
        assert "marketer_warnings" in v


# ─────────────────────────────────────────────
#  기존 하드코딩 템플릿 §5.2 clean 유지 회귀
# ─────────────────────────────────────────────

class TestHardcodedStillClean:
    """기존 하드코딩 4 타입 변형이 §5.2 추가 후에도 clean.

    STEP 2-B 이후 META_REBUTTAL / EVIDENCE_DEFENSE / SOFT_WALKBACK 은 user_name 외에
    추가 슬롯 (user_meta_raw / observation_evidence / last_diagnosis) 도 포함.
    """

    _SLOTS = dict(
        user_name="만재",
        user_meta_raw="MBTI 같은 거 맞추는 거 아니에요",
        observation_evidence="최근 10장 중 7장이 같은 각도예요.",
        last_diagnosis="만재님 피드는 배경이 본인보다 먼저 자리잡고 있어요.",
        feed_count=15,
    )

    def test_opening_variants(self):
        from services.sia_hardcoded import TEMPLATES
        for raw in TEMPLATES[MsgType.OPENING_DECLARATION]:
            text = raw.format(**self._SLOTS)
            r = validate(text, MsgType.OPENING_DECLARATION)
            assert r.ok, f"opening §5.2 fail: {r.errors}\n  text={text}"

    def test_meta_rebuttal_variants(self):
        from services.sia_hardcoded import TEMPLATES
        for raw in TEMPLATES[MsgType.META_REBUTTAL]:
            text = raw.format(**self._SLOTS)
            r = validate(text, MsgType.META_REBUTTAL)
            assert r.ok, f"meta §5.2 fail: {r.errors}\n  text={text}"

    def test_evidence_defense_variants(self):
        from services.sia_hardcoded import TEMPLATES
        for raw in TEMPLATES[MsgType.EVIDENCE_DEFENSE]:
            text = raw.format(**self._SLOTS)
            r = validate(text, MsgType.EVIDENCE_DEFENSE)
            assert r.ok, f"evidence §5.2 fail: {r.errors}\n  text={text}"

    def test_soft_walkback_variants(self):
        from services.sia_hardcoded import TEMPLATES
        for raw in TEMPLATES[MsgType.SOFT_WALKBACK]:
            text = raw.format(**self._SLOTS)
            r = validate(text, MsgType.SOFT_WALKBACK)
            assert r.ok, f"soft_walkback §5.2 fail: {r.errors}\n  text={text}"


# ─────────────────────────────────────────────
#  세션 #4 v2 §9.5 — 구나 "단독 vs 연결" 정밀 검증
# ─────────────────────────────────────────────

class TestGunnaSoloVsConnected:
    """구나 solo-check 정확 해석: 뒤에 서술 연결 있으면 허용."""

    def test_standalone_geureosseonguna_fails(self):
        """단독 '그러셨구나' (뒤 내용 없음) → 위반."""
        errs = check_global_forbidden(
            "아 그러셨구나", MsgType.EMPATHY_MIRROR,
        )
        assert any("~구나" in e for e in errs)

    def test_geureosseonguna_with_period_only_fails(self):
        """구두점만 따라오면 단독으로 간주."""
        errs = check_global_forbidden(
            "아 그러셨구나.", MsgType.EMPATHY_MIRROR,
        )
        assert any("~구나" in e for e in errs)

    def test_geureosseonguna_with_continuation_passes(self):
        """RE_ENTRY V0 케이스 — 서술 연결 있으면 허용.

        세션 #6 v2 §10.2: '아 그러셨구나. 그럼 제가 본 걸 정리해서 말씀드릴게요.'
        """
        errs = check_global_forbidden(
            "아 그러셨구나. 그럼 제가 본 걸 정리해서 말씀드릴게요. 맞다 아니다만 반응 주셔도 괜찮아요",
            MsgType.RE_ENTRY,
        )
        assert not any("~구나" in e for e in errs)

    def test_geureongeoyeotguna_with_continuation_passes(self):
        """RE_ENTRY V3 '아 그런 거였구나. 그럼 남은 얘기는...' 케이스."""
        errs = check_global_forbidden(
            "아 그런 거였구나. 그럼 남은 얘기는 제가 마무리하는 쪽으로 갈게요. 맞다 아니다만 반응 주셔도 괜찮아요",
            MsgType.RE_ENTRY,
        )
        assert not any("~구나" in e for e in errs)

    def test_gunayo_still_allowed(self):
        """~구나요 는 기존처럼 금지 아님."""
        errs = check_global_forbidden(
            "그러셨구나요 좋아요", MsgType.EMPATHY_MIRROR,
        )
        assert not any("~구나" in e for e in errs)


# ─────────────────────────────────────────────
#  세션 #7 §1.3 — EMPATHY 결합 출력 시 ? 허용
# ─────────────────────────────────────────────

class TestEmpathyCombinedQuestionAllowance:
    """is_combined=True 이면 EMPATHY_MIRROR draft 에 `?` 허용."""

    def test_empathy_with_question_and_combined_passes(self):
        errs = check_type_conditional(
            "아 어색하셨구나. 빛삭하셨던 사진들은 어느 부분이 걸리셨어요?",
            MsgType.EMPATHY_MIRROR,
            is_combined=True,
        )
        assert not any("질문 부호 금지" in e for e in errs)

    def test_empathy_with_question_and_not_combined_fails(self):
        errs = check_type_conditional(
            "아 어색하셨네. 어떠세요?",
            MsgType.EMPATHY_MIRROR,
            is_combined=False,
        )
        assert any("질문 부호 금지" in e for e in errs)

    def test_empathy_jangayo_allowed_in_combined_output(self):
        """A-4: ~잖아요 는 is_combined=True 이면 허용 (secondary RECOGNITION 등에서 자연).

        세션 #7 §1.5 서연 M5 fixture: EMPATHY + RECOGNITION(=C6) 결합 시
        secondary 에 '...작동하고 있는 거잖아요' 패턴이 합법적으로 포함.
        단독 EMPATHY (is_combined=False) 에선 기존대로 A-4 엄격 적용.
        """
        errs_combined = check_type_conditional(
            "어색하셨구나. 이 두 기준이 한 사람 안에서 작동하고 있는 거잖아요?",
            MsgType.EMPATHY_MIRROR,
            is_combined=True,
        )
        errs_not = check_type_conditional(
            "어색하셨잖아요",
            MsgType.EMPATHY_MIRROR,
            is_combined=False,
        )
        assert not any("잖아요" in e for e in errs_combined), (
            f"combined 모드에선 허용되어야 함: {errs_combined}"
        )
        assert any("잖아요" in e for e in errs_not)


# ─────────────────────────────────────────────
#  세션 #6 v2 §9.1 — CHECK_IN 전용 체크
# ─────────────────────────────────────────────

class TestCheckInTypeCheck:
    """CHECK_IN 속도 옵션 + 이탈 옵션 필수 + 금지 표현 체크."""

    def test_clean_check_in_variant_passes(self):
        """하드코딩 V0 변형 = clean."""
        text = "만재님, 제 질문이 좀 많은 것 같아요. 편한 속도로 말씀해주시거나 여기서 그만하고 싶으시면 그것도 괜찮아요"
        r = validate(text, MsgType.CHECK_IN)
        assert r.ok, f"errors: {r.errors}"

    def test_missing_pace_option_fails(self):
        text = "만재님, 좀 쉬시면서 그만하고 싶으시면 괜찮아요"
        r = validate(text, MsgType.CHECK_IN)
        assert any("속도 옵션" in e for e in r.errors)

    def test_missing_exit_option_fails(self):
        text = "만재님, 편한 속도로 이야기하셔도 돼요"
        r = validate(text, MsgType.CHECK_IN)
        assert any("이탈 옵션" in e for e in r.errors)

    def test_forbidden_pressure_phrase_fails(self):
        text = "만재님, 편한 속도로 조금만 더 해보실래요 그만하고 싶으시면 괜찮아요"
        r = validate(text, MsgType.CHECK_IN)
        assert any("조금만 더" in e for e in r.errors)

    def test_forbidden_byeolsseoyo_fails(self):
        text = "만재님, 벌써요? 편한 속도로 그만하셔도 돼요"
        r = validate(text, MsgType.CHECK_IN)
        # 질문 금지 또는 "벌써요" 둘 중 하나 걸림
        assert any("벌써요" in e for e in r.errors)


# ─────────────────────────────────────────────
#  세션 #6 v2 §9.2 — RE_ENTRY 전용 체크
# ─────────────────────────────────────────────

class TestReEntryTypeCheck:
    """RE_ENTRY 직전 CHECK_IN + 완화 표현 필수."""

    def test_clean_re_entry_variant_passes(self):
        state = _state()
        state.turns.append(AssistantTurn(
            text="만재님, 편한 속도로 하셔도 되고 그만하셔도 괜찮아요",
            msg_type=MsgType.CHECK_IN,
            turn_idx=0,
        ))
        text = "아 그러셨구나. 그럼 제가 본 걸 정리해서 말씀드릴게요. 맞다 아니다만 반응 주셔도 괜찮아요"
        r = validate(text, MsgType.RE_ENTRY, state=state)
        assert r.ok, f"errors: {r.errors}"

    def test_missing_relaxed_marker_fails(self):
        state = _state()
        state.turns.append(AssistantTurn(
            text="만재님, 편한 속도로 그만하셔도 돼요",
            msg_type=MsgType.CHECK_IN, turn_idx=0,
        ))
        text = "아 그러셨구나. 제가 본 걸 정리해드릴게요. 계속 진행할게요"
        r = validate(text, MsgType.RE_ENTRY, state=state)
        assert any("완화 표현" in e for e in r.errors)

    def test_v5_exit_variant_passes_with_unjedeun(self):
        """V5 '언제든 돌아오시면' 은 완화 표현으로 간주."""
        state = _state()
        state.turns.append(AssistantTurn(
            text="편한 속도로 그만하셔도 돼요", msg_type=MsgType.CHECK_IN, turn_idx=0,
        ))
        text = "알겠어요. 만재님 언제든 돌아오시면 이어갈 수 있어요"
        r = validate(text, MsgType.RE_ENTRY, state=state, exit_confirmed=True)
        assert r.ok, f"errors: {r.errors}"

    def test_missing_prior_check_in_fails(self):
        """직전 assistant 가 CHECK_IN 아니면 RE_ENTRY 위반."""
        state = _state()
        state.turns.append(AssistantTurn(
            text="관찰 1", msg_type=MsgType.OBSERVATION, turn_idx=0,
        ))
        text = "아 그러셨구나. 제가 본 걸 정리해볼게요. 맞다 아니다만 반응 주셔도 괜찮아요"
        r = validate(text, MsgType.RE_ENTRY, state=state)
        assert any("직전 assistant" in e for e in r.errors)


# ─────────────────────────────────────────────
#  세션 #6 v2 §9.3 — RANGE_DISCLOSURE 전용 체크
# ─────────────────────────────────────────────

class TestRangeDisclosureTypeCheck:
    """RANGE_DISCLOSURE 범위 명시 (limit 만) + 자기부정 + 관계 형성 금지."""

    def test_clean_limit_mild_variant_passes(self):
        text = "제가 본 건 피드 15장이 전부라서, 만재님 전체를 아는 건 아니에요. 그치만 피드에서 드러난 부분은 이 정도 또렷했다는 거예요"
        r = validate(text, MsgType.RANGE_DISCLOSURE, range_mode="limit")
        assert r.ok, f"errors: {r.errors}"

    def test_limit_without_scope_fails(self):
        """limit 모드인데 피드 범위 명시 없으면 위반."""
        text = "만재님 전체를 아는 건 아니에요. 그치만 드러난 부분은 또렷했다는 거예요"
        r = validate(text, MsgType.RANGE_DISCLOSURE, range_mode="limit")
        assert any("범위 명시" in e for e in r.errors)

    # 베타 hotfix (2026-04-28) 폐기 — RANGE_REAFFIRM 동작 정리 (1-A 변형 / 1-B 분기 / 1-C 가이드).
    # test_reaffirm_without_scope_passes 폐기.

    def test_self_negation_fails(self):
        text = "제가 본 건 피드 15장이 전부라서 별 의미 없지만 괜찮아요"
        r = validate(text, MsgType.RANGE_DISCLOSURE, range_mode="limit")
        assert any("자기부정" in e for e in r.errors)

    def test_relational_fails(self):
        text = "제가 본 건 피드 15장이지만 만재님 저도 좋아요"
        r = validate(text, MsgType.RANGE_DISCLOSURE, range_mode="limit")
        assert any("관계 형성" in e for e in r.errors)


# ─────────────────────────────────────────────
#  세션 #7 §2.8 / §3.8 — C6 / C7 블록 체크
# ─────────────────────────────────────────────

class TestC6BlockCheck:
    """C6 평가 의존 돌파 — 평가 직접 답변 / 회피 금지."""

    def test_clean_c6_reframe_passes(self):
        """서연 M5 형 C6 응답 — 유저 발화 기반 재프레임."""
        text = (
            "근데 서연님, 방금 말씀해주신 거 보면 빛삭 기준이 "
            "기괴해진 순간이고, 살아남은 기준이 원래 선이 살아있는 순간이잖아요. "
            "서연님이 본인 얼굴의 원래 선이 뭔지에 대한 감각은 이미 갖고 계신 거 아닐까요?"
        )
        r = validate(
            text, MsgType.CONFRONTATION, confrontation_block="C6",
        )
        # C6 위반은 없어야 함 — 다른 A 규칙으로 안 걸리도록 설계됨 check
        c6_errors = [e for e in r.errors if "C6" in e]
        assert not c6_errors, f"C6 errors: {c6_errors}"

    def test_direct_pretty_answer_fails(self):
        text = "서연님 예뻐요. 본인 매력이 있잖아요?"
        r = validate(text, MsgType.CONFRONTATION, confrontation_block="C6")
        assert any("C6" in e for e in r.errors)

    def test_dodge_to_diagnosis_fails(self):
        text = "그건 진단 결과에서 보여드릴게요. 지금은 넘어가요"
        r = validate(text, MsgType.CONFRONTATION, confrontation_block="C6")
        assert any("C6" in e for e in r.errors)

    def test_ceremony_praise_fails(self):
        text = "서연님은 본인만의 매력이 있어요. 그러니까 괜찮아요"
        r = validate(text, MsgType.CONFRONTATION, confrontation_block="C6")
        assert any("C6" in e for e in r.errors)


class TestC7BlockCheck:
    """C7 일반화 회피 돌파 — 위로형/전면 부정 금지."""

    def test_clean_c7_partial_acceptance_passes(self):
        """도윤 M6 형 C7 응답 — 일반화 부분 인정 + specifics 재제시."""
        text = (
            "다들 모노톤 + 머슬핏 어울린다고 하긴 하죠. 근데 도윤님 피드 보면 "
            "무채색 안에서도 블랙 비중이 압도적이에요"
        )
        r = validate(
            text, MsgType.CONFRONTATION, confrontation_block="C7",
        )
        c7_errors = [e for e in r.errors if "C7" in e]
        assert not c7_errors, f"C7 errors: {c7_errors}"

    def test_placating_denial_special_fails(self):
        text = "도윤님은 특별해요. 일반화 하지 마세요"
        r = validate(text, MsgType.CONFRONTATION, confrontation_block="C7")
        assert any("C7" in e for e in r.errors)

    def test_full_denial_fails(self):
        text = "다들 그런 게 아니에요. 각자 달라요"
        r = validate(text, MsgType.CONFRONTATION, confrontation_block="C7")
        assert any("C7" in e for e in r.errors)


# ─────────────────────────────────────────────
#  세션 #7 §8.3 — check_haiku_naturalness
# ─────────────────────────────────────────────

class TestHaikuNaturalness:
    """분석 jargon + 어색 종결 검출."""

    def test_clean_friend_tone_passes(self):
        text = "지은님 피드 보다 보니 베이지랑 식물 초록만 거의 쭉이던데"
        r = validate(text, MsgType.OBSERVATION)
        # A-8 질문 종결 누락은 별개 — naturalness 는 clean
        nat_errors = [e for e in r.errors if "A-2:" in e and "jargon" in e]
        assert not nat_errors

    def test_jargon_mode_fails(self):
        text = "피드 톤이 다른 모드로 갈려 있더라구요"
        r = validate(text, MsgType.OBSERVATION)
        assert any("분석 jargon" in e for e in r.errors)

    def test_jargon_clustering_fails(self):
        text = "컬러 팔레트가 베이지/그린 톤으로 클러스터링되어 있어요"
        r = validate(text, MsgType.OBSERVATION)
        assert any("분석 jargon" in e for e in r.errors)

    def test_jargon_metaincognition_fails(self):
        text = "메타인지 작동이 드러나 있어요"
        r = validate(text, MsgType.DIAGNOSIS)
        assert any("분석 jargon" in e for e in r.errors)

    def test_awkward_end_myeonyo_fails(self):
        text = "만재님, 그럴 거면요"
        r = validate(text, MsgType.OBSERVATION)
        assert any("어색한 종결" in e for e in r.errors)

    def test_awkward_end_seomijyeo_fails(self):
        text = "그건 만재님 선택인 셈이죠"
        r = validate(text, MsgType.DIAGNOSIS)
        assert any("어색한 종결" in e for e in r.errors)

    def test_mode_in_compound_word_ignored(self):
        """'모드' 가 단독 단어일 때만 jargon — '모드' 는 lookahead 로 격리."""
        # "모두" 는 jargon 아님 — false positive 회피 확인
        text = "모두 함께 보실 수 있어요"
        errs = check_haiku_naturalness(text)
        assert not any("모드" in e for e in errs)


# ─────────────────────────────────────────────
#  44 하드코딩 전수 — 세션 #6/7 신규 타입 clean 검증
# ─────────────────────────────────────────────

class TestHardcodedSeventypesClean:
    """관리 3 타입 변형이 validator v4 pass.

    ※ 베타 hotfix (2026-04-28) — RANGE_REAFFIRM 변형 검증은 폐기 (1-A 변형 / 1-B 분기 / 1-C 가이드 / 1-D 테스트).
    """

    _SLOTS = dict(
        user_name="만재",
        user_meta_raw="MBTI 같은 거 맞추는 거 아니에요",
        observation_evidence="최근 10장 중 7장이 같은 각도예요.",
        last_diagnosis="만재님 피드는 배경이 본인보다 먼저 자리잡고 있어요.",
        feed_count=15,
    )

    def test_check_in_variants(self):
        from services.sia_hardcoded import TEMPLATES
        for raw in TEMPLATES[MsgType.CHECK_IN]:
            text = raw.format(**self._SLOTS)
            r = validate(text, MsgType.CHECK_IN)
            assert r.ok, f"CHECK_IN fail: {r.errors}\n  text={text}"

    def test_re_entry_default_variants(self):
        from services.sia_hardcoded import TEMPLATES
        state = _state()
        state.turns.append(AssistantTurn(
            text="편한 속도로 그만하셔도 돼요",
            msg_type=MsgType.CHECK_IN, turn_idx=0,
        ))
        for raw in TEMPLATES[MsgType.RE_ENTRY]:
            text = raw.format(**self._SLOTS)
            r = validate(text, MsgType.RE_ENTRY, state=state)
            assert r.ok, f"RE_ENTRY fail: {r.errors}\n  text={text}"

    def test_re_entry_exit_variant(self):
        from services.sia_hardcoded import ALL_VARIANT_POOLS
        state = _state()
        state.turns.append(AssistantTurn(
            text="편한 속도로 그만하셔도 돼요",
            msg_type=MsgType.CHECK_IN, turn_idx=0,
        ))
        for raw in ALL_VARIANT_POOLS["re_entry_exit"]:
            text = raw.format(**self._SLOTS)
            r = validate(text, MsgType.RE_ENTRY, state=state, exit_confirmed=True)
            assert r.ok, f"RE_ENTRY V5 fail: {r.errors}\n  text={text}"

    def test_range_limit_mild_variants(self):
        from services.sia_hardcoded import ALL_VARIANT_POOLS
        for raw in ALL_VARIANT_POOLS["range_limit_mild"]:
            text = raw.format(**self._SLOTS)
            r = validate(text, MsgType.RANGE_DISCLOSURE, range_mode="limit")
            assert r.ok, f"RANGE limit mild fail: {r.errors}\n  text={text}"

    def test_range_limit_severe_variants(self):
        """severity=severe 인 state 로 검증 — SV0 의 비-피드 범위 문구 허용."""
        from services.sia_hardcoded import ALL_VARIANT_POOLS
        severe_state = _state()
        severe_state.overattachment_severity = "severe"
        for raw in ALL_VARIANT_POOLS["range_limit_severe"]:
            text = raw.format(**self._SLOTS)
            r = validate(
                text, MsgType.RANGE_DISCLOSURE,
                state=severe_state, range_mode="limit",
            )
            block_errors = [
                e for e in r.errors
                if any(k in e for k in ("범위 명시", "자기부정", "관계 형성"))
            ]
            assert not block_errors, (
                f"RANGE severe fail (block checks): {block_errors}\n  text={text}"
            )

    # 베타 hotfix (2026-04-28) 폐기 — RANGE_REAFFIRM 동작 정리 (1-A 변형 / 1-B 분기 / 1-C 가이드).
    # test_range_reaffirm_variants 폐기.


# ─────────────────────────────────────────────
#  A-17 영업/상품 어휘 hard reject (유저 실측 피드백)
# ─────────────────────────────────────────────

class TestA17Commerce:
    """A-17 — 영업 / 상품 / 가격 어휘 hard reject.

    유저 실측 대화 2026-04-24: Sia 가 "피드 진단 리포트 (₩49,000)", "PI 컨설팅",
    "구독 상품", "다음 단계" 류 영업 톤 출력 → 페르소나 B 정면 위반. 전수 hard block.
    """

    def test_blocks_daum_dangye(self):
        errs = check_a17_commerce("다음 단계로 넘어갈게요")
        assert any("A-17" in e and "다음" in e for e in errs)

    def test_blocks_purodeuri(self):
        errs = check_a17_commerce("제가 풀어드릴 수 있어요")
        assert any("A-17" in e and "풀어드릴" in e for e in errs)

    def test_blocks_jungrihaedeuri(self):
        errs = check_a17_commerce("제가 정리해드릴게요")
        assert any("A-17" in e and "정리해드릴" in e for e in errs)

    def test_blocks_chucheonhaedeuri(self):
        errs = check_a17_commerce("이 각도 추천해드릴 수 있어요")
        assert any("A-17" in e and "추천해드릴" in e for e in errs)

    def test_blocks_haeksim_point(self):
        errs = check_a17_commerce("만재님의 핵심 포인트는")
        assert any("A-17" in e and "핵심" in e for e in errs)

    def test_blocks_report(self):
        errs = check_a17_commerce("자세한 건 리포트에서")
        assert any("A-17" in e and "리포트" in e for e in errs)

    def test_blocks_consulting(self):
        errs = check_a17_commerce("컨설팅 받아보시면")
        assert any("A-17" in e and "컨설팅" in e for e in errs)

    def test_blocks_subscription(self):
        errs = check_a17_commerce("구독 상품으로 이어집니다")
        assert any("A-17" in e and "구독" in e for e in errs)

    def test_blocks_tier(self):
        errs = check_a17_commerce("프리미엄 티어에서만")
        assert any("A-17" in e and "티어" in e for e in errs)

    def test_blocks_premium_korean(self):
        errs = check_a17_commerce("프리미엄 기능")
        assert any("A-17" in e and "프리미엄" in e for e in errs)

    def test_blocks_premium_english(self):
        errs = check_a17_commerce("Premium plan 으로")
        assert any("A-17" in e for e in errs)

    def test_blocks_jindanesseo(self):
        errs = check_a17_commerce("진단에서 자세히 보여드릴게요")
        assert any("A-17" in e and "진단에서" in e for e in errs)

    def test_blocks_jindaneul(self):
        errs = check_a17_commerce("진단을 받아보시면")
        assert any("A-17" in e and "진단을" in e for e in errs)

    def test_blocks_jindaneuro(self):
        errs = check_a17_commerce("진단으로 이어집니다")
        assert any("A-17" in e and "진단으로" in e for e in errs)

    def test_blocks_price_won_symbol(self):
        errs = check_a17_commerce("₩49,000 에 이용 가능")
        assert any("A-17" in e for e in errs)

    def test_blocks_price_won_korean(self):
        errs = check_a17_commerce("49,000원에 이용")
        assert any("A-17" in e for e in errs)

    def test_blocks_price_tokens(self):
        errs = check_a17_commerce("10 토큰 결제")
        assert any("A-17" in e for e in errs)

    def test_blocks_price_manwon(self):
        errs = check_a17_commerce("5만원 결제 후")
        assert any("A-17" in e for e in errs)

    def test_allows_diagnosis_word_standalone(self):
        """'진단' 단독 (뒤에 에서/을/으로 없음) 은 허용. DIAGNOSIS msg_type 과 충돌 회피."""
        errs = check_a17_commerce("그게 만재님 쪽이라고 보여요")
        assert not errs

    def test_allows_wonrae(self):
        """'원래' 는 가격 '원' 과 다름. lookahead 로 구분."""
        errs = check_a17_commerce("원래 좋아하시던 거잖아요")
        price_errs = [e for e in errs if "원" in e and "다음" not in e]
        assert not price_errs

    def test_integrated_in_validate(self):
        """validate() 파이프라인에서도 A-17 걸러짐."""
        r = validate("구독 상품으로 넘어가셔야 해요", MsgType.OBSERVATION)
        assert not r.ok
        assert any("A-17" in e for e in r.errors)


# ─────────────────────────────────────────────
#  A-20 추상 칭찬어 hard reject (유저 실측 피드백)
# ─────────────────────────────────────────────

class TestA20AbstractPraise:
    """A-20 — 추상 칭찬어 hard reject.

    "매력 / 독특 / 특별 / 흥미로운 / 인상적 / 센스 / 안목 / 감각이 있" AI 티 나는
    추상 찬사 전수 금지. 대체는 구체 관찰.
    """

    def test_blocks_maelyeok_jeok(self):
        errs = check_a20_abstract_praise("만재님 매력적이세요")
        assert any("A-20" in e and "매력적" in e for e in errs)

    def test_blocks_maelyeok_i(self):
        errs = check_a20_abstract_praise("매력이 있으세요")
        assert any("A-20" in e and "매력" in e for e in errs)

    def test_blocks_dokteughan(self):
        errs = check_a20_abstract_praise("독특한 느낌이에요")
        assert any("A-20" in e and "독특" in e for e in errs)

    def test_blocks_teukbyeolhan(self):
        errs = check_a20_abstract_praise("특별한 분이세요")
        assert any("A-20" in e and "특별" in e for e in errs)

    def test_blocks_heungmiroun(self):
        errs = check_a20_abstract_praise("흥미로운 조합이네요")
        assert any("A-20" in e and "흥미로" in e for e in errs)

    def test_blocks_insangjeok(self):
        errs = check_a20_abstract_praise("인상적인 피드")
        assert any("A-20" in e and "인상적" in e for e in errs)

    def test_blocks_sense(self):
        errs = check_a20_abstract_praise("센스 있으세요")
        assert any("A-20" in e and "센스" in e for e in errs)

    def test_blocks_anmok(self):
        errs = check_a20_abstract_praise("안목이 있으세요")
        assert any("A-20" in e and "안목" in e for e in errs)

    def test_blocks_gamgak_iisseu(self):
        errs = check_a20_abstract_praise("감각이 있으신 분")
        assert any("A-20" in e and "감각" in e for e in errs)

    def test_allows_concrete_observation(self):
        """구체 관찰은 허용."""
        errs = check_a20_abstract_praise("만재님 피드는 베이지랑 그린이 반복되더라구요")
        assert not errs

    def test_allows_gamgak_in_other_context(self):
        """'감각' 단독 (이 있 없음) 은 허용 — '미적 감각' 등 다른 용법."""
        errs = check_a20_abstract_praise("그 감각 어디서 오는 거예요?")
        # "감각\s*이\s*있" 패턴이라 단독 "감각" 은 안 걸림
        assert not errs

    def test_integrated_in_validate(self):
        r = validate("매력적이세요 정말", MsgType.OBSERVATION)
        assert not r.ok
        assert any("A-20" in e for e in r.errors)


# ─────────────────────────────────────────────
#  A-18 발화 길이 원칙 (유저 실측 피드백)
# ─────────────────────────────────────────────

class TestA18Length:
    """A-18 — 발화 길이 원칙. 300자 hard reject, 200자 / 4문장 warning."""

    def test_allows_short_utterance(self):
        errs = check_a18_length("간단히 짚고 갈게요")
        assert not errs

    def test_allows_200_chars(self):
        text = "가" * 200
        errs = check_a18_length(text)
        assert not errs

    def test_allows_exactly_300_chars(self):
        text = "가" * 300
        errs = check_a18_length(text)
        assert not errs

    def test_blocks_301_chars(self):
        text = "가" * 301
        errs = check_a18_length(text)
        assert any("A-18" in e and "hard reject" in e for e in errs)

    def test_blocks_500_chars(self):
        text = "가" * 500
        errs = check_a18_length(text)
        assert any("A-18" in e and "500자" in e for e in errs)


class TestA18LengthWarning:
    """A-18 warning — 200자 < x ≤ 300자 and 문장 수 > 3."""

    def test_no_warning_for_short(self):
        warns = check_a18_length_warning("짧은 문장이에요")
        assert not warns

    def test_no_warning_at_200(self):
        text = "가" * 200
        warns = check_a18_length_warning(text)
        assert not any("권장 초과" in w for w in warns)

    def test_warning_at_201_chars(self):
        text = "가" * 201
        warns = check_a18_length_warning(text)
        assert any("A-18" in w and "권장 초과" in w for w in warns)

    def test_warning_at_300_chars(self):
        text = "가" * 300
        warns = check_a18_length_warning(text)
        assert any("A-18" in w and "300자" in w for w in warns)

    def test_no_length_warning_beyond_hard_cap(self):
        """301자 이상은 hard reject 라서 length 경고 이중 발생 없음."""
        text = "가" * 350
        warns = check_a18_length_warning(text)
        length_warns = [w for w in warns if "권장 초과" in w]
        assert not length_warns

    def test_warning_for_4_sentences(self):
        text = "한 문장이에요. 두 문장이에요. 세 문장이에요. 네 문장이에요."
        warns = check_a18_length_warning(text)
        assert any("A-18" in w and "문장 수" in w for w in warns)

    def test_no_warning_for_3_sentences(self):
        text = "한 문장. 두 문장. 세 문장."
        warns = check_a18_length_warning(text)
        assert not any("문장 수" in w for w in warns)


# ─────────────────────────────────────────────
#  마크다운 강조 hard reject (유저 실측 피드백)
# ─────────────────────────────────────────────

class TestMarkdownMarkup:
    """마크다운 강조 전수 hard reject.

    유저 직접 피드백 2026-04-24: "프론트에 별 하나라도 나오면 ai티 확 나고 짜게 식어"
    """

    def test_blocks_double_star(self):
        errs = check_markdown_markup("**중요** 한 부분")
        assert any("마크다운" in e for e in errs)

    def test_blocks_single_star_emphasis(self):
        errs = check_markdown_markup("*강조* 하고 싶은데")
        assert any("마크다운" in e for e in errs)

    def test_blocks_heading(self):
        errs = check_markdown_markup("## 섹션 제목\n본문")
        assert any("마크다운" in e for e in errs)

    def test_blocks_blockquote(self):
        errs = check_markdown_markup("> 인용구\n본문")
        assert any("마크다운" in e for e in errs)

    def test_blocks_codeblock(self):
        errs = check_markdown_markup("```python\ncode\n```")
        assert any("마크다운" in e for e in errs)

    def test_allows_clean_text(self):
        errs = check_markdown_markup("만재님 피드 보다 보니 꽤 또렷하시더라구요")
        assert not errs

    def test_allows_parens(self):
        """괄호는 마크다운 아님."""
        errs = check_markdown_markup("(실루엣 관점에서)")
        assert not errs

    def test_allows_dash(self):
        """하이픈 — 은 마크다운 아님."""
        errs = check_markdown_markup("만재님 — 그런 느낌이에요")
        assert not errs

    def test_integrated_in_validate(self):
        r = validate("**중요** 한 부분이에요", MsgType.OBSERVATION)
        assert not r.ok
        assert any("마크다운" in e for e in r.errors)
