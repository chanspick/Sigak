"""Phase H3 §5.2 drop-in 검증 — FN 4건 해소 + A-1 확장 + 공개 API.

Source: SIA_SESSION4_V2 §5 Validator v4.

FN 회수 대상 (§5):
  FN-1 (#7)  "아 그렇게 느끼셨구나" — GUNNA_PATTERN 매치 + BANMAL 안전
  FN-2 (#8)  "봄웜이라고 하셨네"   — BANMAL_END_PATTERN (문장 끝 반말)
  FN-3 (#9)  잖아요 3창 2회 초과   — check_cross_turn_rules 합산
  FN-4 (#10) EMPATHY ~잖아요      — check_type_conditional
"""
from __future__ import annotations

import pytest

from schemas.sia_state import (
    AssistantTurn,
    ConversationState,
    MsgType,
)
from services.sia_validators_v4 import (
    ValidationResult,
    check_cross_turn_rules,
    check_global_forbidden,
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
    """기존 20 하드코딩 변형이 §5.2 추가 후에도 clean."""

    def test_opening_variants(self):
        from services.sia_hardcoded import TEMPLATES
        for raw in TEMPLATES[MsgType.OPENING_DECLARATION]:
            text = raw.format(user_name="만재")
            r = validate(text, MsgType.OPENING_DECLARATION)
            assert r.ok, f"opening §5.2 fail: {r.errors}\n  text={text}"

    def test_meta_rebuttal_variants(self):
        from services.sia_hardcoded import TEMPLATES
        for raw in TEMPLATES[MsgType.META_REBUTTAL]:
            text = raw.format(user_name="만재")
            r = validate(text, MsgType.META_REBUTTAL)
            assert r.ok, f"meta §5.2 fail: {r.errors}\n  text={text}"

    def test_evidence_defense_variants(self):
        from services.sia_hardcoded import TEMPLATES
        for raw in TEMPLATES[MsgType.EVIDENCE_DEFENSE]:
            text = raw.format(user_name="만재")
            r = validate(text, MsgType.EVIDENCE_DEFENSE)
            assert r.ok, f"evidence §5.2 fail: {r.errors}\n  text={text}"

    def test_soft_walkback_variants(self):
        from services.sia_hardcoded import TEMPLATES
        for raw in TEMPLATES[MsgType.SOFT_WALKBACK]:
            text = raw.format(user_name="만재")
            r = validate(text, MsgType.SOFT_WALKBACK)
            assert r.ok, f"soft_walkback §5.2 fail: {r.errors}\n  text={text}"
