"""Phase H4 — 하드코딩 7 타입 (44 문구) + Haiku 프롬프트 로더 테스트.

Scope:
  A) sia_hardcoded.render_hardcoded
     - 7 타입 디폴트 pool (각 5 변형) + 3 특수 pool = 총 44 문구
     - 결정성 (같은 시드 → 같은 index)
     - user_name / user_meta_raw / observation_evidence / last_diagnosis / feed_count 슬롯
     - RE_ENTRY exit_confirmed 분기 → V5 종결
     - RANGE_DISCLOSURE range_mode="reaffirm" 분기 → RANGE_REAFFIRM
     - RANGE_DISCLOSURE limit + state.overattachment_severity="severe" → severe pool
     - 질문 종결 규칙 준수 (A-5 / A-6) — 스펙 구조 불변
  B) sia_prompts_v4.load_haiku_prompt
     - HAIKU_TYPES 7 개 모두 로드 가능
     - HARDCODED_TYPES 7 개는 ValueError
     - base.md + type.md + ctx 3 섹션 조립
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schemas.sia_state import (
    HAIKU_TYPES,
    HARDCODED_TYPES,
    AssistantTurn,
    ConversationState,
    MsgType,
    UserMessageFlags,
    UserTurn,
)
from services.sia_hardcoded import (
    ALL_VARIANT_POOLS,
    TEMPLATES,
    pick_variant_index,
    render_hardcoded,
    total_variant_count,
)
from services.sia_prompts_v4 import available_types, load_haiku_prompt


# ─────────────────────────────────────────────
#  fixtures
# ─────────────────────────────────────────────

def _blank_state(
    *, user_id: str = "user-x", user_name: str = "만재",
) -> ConversationState:
    return ConversationState(
        session_id="sess-x",
        user_id=user_id,
        user_name=user_name,
    )


# ─────────────────────────────────────────────
#  (A) Templates 전수
# ─────────────────────────────────────────────

class TestTemplateInventory:
    def test_seven_types_registered(self):
        """HARDCODED_TYPES 7 종 전부 디폴트 pool 보유."""
        assert set(TEMPLATES.keys()) == set(HARDCODED_TYPES)

    def test_each_type_default_pool_has_five_variants(self):
        """디폴트 pool 은 모든 타입에서 5 변형 (스펙 일관성)."""
        for mt, variants in TEMPLATES.items():
            assert len(variants) == 5, f"{mt.value} has {len(variants)} variants"

    def test_default_pool_total_thirtyfive_variants(self):
        """디폴트 pool 합: 7 × 5 = 35."""
        total = sum(len(v) for v in TEMPLATES.values())
        assert total == 35

    def test_all_pools_total_fortyfour_variants(self):
        """디폴트 + 특수 pool 합: 35 + 1 (RE_ENTRY exit V5) + 3 (RANGE severe) + 5 (RANGE reaffirm) = 44.

        스펙 확정값 (세션 #7 §9.3).
        """
        assert total_variant_count() == 44

    def test_all_pools_registry_has_ten_pools(self):
        """디폴트 7 + 특수 3 = 10 pool."""
        assert len(ALL_VARIANT_POOLS) == 10

    def test_special_pool_sizes(self):
        """특수 pool 개별 크기 검증 (스펙 상 고정)."""
        assert len(ALL_VARIANT_POOLS["re_entry_exit"]) == 1
        assert len(ALL_VARIANT_POOLS["range_limit_severe"]) == 3
        assert len(ALL_VARIANT_POOLS["range_reaffirm"]) == 5


# ─────────────────────────────────────────────
#  (A) pick_variant_index 결정성
# ─────────────────────────────────────────────

class TestPickVariantIndex:
    def test_deterministic_same_inputs(self):
        a = pick_variant_index("u1", MsgType.OPENING_DECLARATION, 0, 5)
        b = pick_variant_index("u1", MsgType.OPENING_DECLARATION, 0, 5)
        assert a == b

    def test_different_user_likely_different(self):
        # 20 유저 중 최소 2개 이상 다른 index 가 나와야
        results = {
            pick_variant_index(f"u{i}", MsgType.OPENING_DECLARATION, 0, 5)
            for i in range(20)
        }
        assert len(results) >= 2

    def test_different_turn_idx(self):
        a = pick_variant_index("u1", MsgType.META_REBUTTAL, 0, 5)
        b = pick_variant_index("u1", MsgType.META_REBUTTAL, 5, 5)
        # 해시 시드 다름 — 동등 확률은 1/5 이므로 세션 여러 개로 체크
        distinct = {
            pick_variant_index("u1", MsgType.META_REBUTTAL, t, 5)
            for t in range(20)
        }
        assert len(distinct) >= 2

    def test_index_in_range(self):
        for i in range(100):
            idx = pick_variant_index(f"u{i}", MsgType.SOFT_WALKBACK, i, 5)
            assert 0 <= idx < 5

    def test_zero_n_raises(self):
        with pytest.raises(ValueError):
            pick_variant_index("u1", MsgType.OPENING_DECLARATION, 0, 0)


# ─────────────────────────────────────────────
#  (A) render_hardcoded
# ─────────────────────────────────────────────

class TestRenderHardcoded:
    def test_opening_renders_with_user_name(self):
        s = _blank_state(user_name="만재")
        text = render_hardcoded(MsgType.OPENING_DECLARATION, s)
        assert "만재" in text
        assert "{user_name}" not in text

    def test_meta_rebuttal_has_question(self):
        s = _blank_state()
        text = render_hardcoded(MsgType.META_REBUTTAL, s)
        assert text.rstrip().endswith("?")

    def test_evidence_defense_has_question(self):
        s = _blank_state()
        text = render_hardcoded(MsgType.EVIDENCE_DEFENSE, s)
        assert text.rstrip().endswith("?")

    def test_soft_walkback_no_question(self):
        s = _blank_state()
        text = render_hardcoded(MsgType.SOFT_WALKBACK, s)
        assert "?" not in text

    def test_opening_no_question(self):
        s = _blank_state()
        text = render_hardcoded(MsgType.OPENING_DECLARATION, s)
        assert "?" not in text

    def test_haiku_type_raises(self):
        s = _blank_state()
        with pytest.raises(ValueError):
            render_hardcoded(MsgType.OBSERVATION, s)

    def test_deterministic_same_state(self):
        s = _blank_state()
        a = render_hardcoded(MsgType.OPENING_DECLARATION, s)
        b = render_hardcoded(MsgType.OPENING_DECLARATION, s)
        assert a == b

    def test_varies_across_turn_idx(self):
        outputs = []
        for i in range(12):
            s = _blank_state(user_id=f"u{i}")
            outputs.append(render_hardcoded(MsgType.EVIDENCE_DEFENSE, s))
        assert len({o for o in outputs}) >= 2

    # ── 슬롯 주입 ──

    def test_meta_rebuttal_injects_user_meta_raw(self):
        s = _blank_state()
        text = render_hardcoded(
            MsgType.META_REBUTTAL, s,
            user_meta_raw="MBTI 같은 거 맞추는 거 아니에요",
        )
        assert "MBTI 같은 거 맞추는 거 아니에요" in text

    def test_evidence_defense_injects_observation_evidence(self):
        s = _blank_state()
        text = render_hardcoded(
            MsgType.EVIDENCE_DEFENSE, s,
            observation_evidence="최근 10장 중 7장이 같은 각도예요.",
        )
        assert "7장이 같은 각도" in text

    def test_soft_walkback_injects_last_diagnosis(self):
        s = _blank_state()
        text = render_hardcoded(
            MsgType.SOFT_WALKBACK, s,
            last_diagnosis="만재님 피드는 배경이 본인보다 먼저 자리잡고 있어요.",
        )
        assert "배경이 본인보다 먼저" in text

    # ── 신규 3 타입 (CHECK_IN / RE_ENTRY / RANGE_DISCLOSURE) ──

    def test_check_in_contains_pace_and_exit_markers(self):
        """세션 #6 v2 §10.1: CHECK_IN 구조 = 상태 명시 + 속도 옵션 + 이탈 옵션."""
        s = _blank_state(user_name="준호")
        text = render_hardcoded(MsgType.CHECK_IN, s)
        pace_markers = ["편한 속도", "편하신 만큼", "천천히"]
        exit_markers = ["그만", "여기까지", "나중에", "멈추"]
        assert any(m in text for m in pace_markers), f"속도 옵션 누락: {text}"
        assert any(m in text for m in exit_markers), f"이탈 옵션 누락: {text}"

    def test_re_entry_default_contains_relaxed_reaction(self):
        """세션 #6 v2 §10.2: RE_ENTRY 반응 기준 완화 표현 필수."""
        s = _blank_state(user_name="준호")
        text = render_hardcoded(MsgType.RE_ENTRY, s)
        relaxed_markers = ["맞다 아니다만", "편하신 만큼", "반응 주셔도", "반응해주셔도", "들으셔도", "들으셔도 되고"]
        assert any(m in text for m in relaxed_markers), f"완화 표현 누락: {text}"

    def test_re_entry_exit_confirmed_returns_v5_farewell(self):
        """세션 #6 v2 §10.2 V5: 이탈 선택 시 종결 문구 "언제든 돌아오시면" 포함."""
        s = _blank_state(user_name="도윤")
        text = render_hardcoded(MsgType.RE_ENTRY, s, exit_confirmed=True)
        assert "언제든 돌아오시면" in text
        assert "도윤" in text

    def test_range_limit_mild_injects_feed_count(self):
        """RANGE_DISCLOSURE limit mild 는 {feed_count} 포함."""
        s = _blank_state(user_name="서연")
        text = render_hardcoded(MsgType.RANGE_DISCLOSURE, s, feed_count=24)
        assert "24" in text
        assert "서연" in text

    def test_range_limit_severe_uses_severe_pool(self):
        """세션 #6 v2 §10.4: overattachment_severity=severe → 심각 pool (외부 자원 권유)."""
        s = _blank_state(user_name="서연")
        s.overattachment_severity = "severe"
        text = render_hardcoded(MsgType.RANGE_DISCLOSURE, s, feed_count=24)
        external_resource_markers = ["사람한테", "가까운 사람", "친구"]
        assert any(m in text for m in external_resource_markers), (
            f"심각 pool 외부 자원 권유 누락: {text}"
        )

    def test_range_reaffirm_mode_uses_reaffirm_pool(self):
        """세션 #7 §9: range_mode="reaffirm" → 사업 존재 재선언 pool."""
        s = _blank_state(user_name="서연")
        text = render_hardcoded(
            MsgType.RANGE_DISCLOSURE, s, range_mode="reaffirm",
        )
        reaffirm_markers = ["막막", "풀어", "도와드리", "정리해보려고", "제가 온 거", "제가 들어온 거"]
        assert any(m in text for m in reaffirm_markers), (
            f"reaffirm pool 특유 표현 누락: {text}"
        )
        # reaffirm 은 feed_count 무관 — 숫자 놓고 안 들어가도 OK
        assert "서연" in text

    def test_range_mode_reaffirm_overrides_severe(self):
        """reaffirm 모드는 severity 와 무관하게 항상 reaffirm pool.

        평가 요청 + 막막함 우세 (세션 #7 §2.4) 케이스 커버.
        """
        s = _blank_state(user_name="서연")
        s.overattachment_severity = "severe"
        text = render_hardcoded(
            MsgType.RANGE_DISCLOSURE, s, range_mode="reaffirm", feed_count=24,
        )
        # severe pool 특유 표현은 안 나와야 함
        assert "상담 대체" not in text
        assert "가까운 사람한테" not in text

    def test_exit_confirmed_ignored_for_non_re_entry(self):
        """exit_confirmed 는 RE_ENTRY 전용. 다른 타입에선 무시."""
        s = _blank_state(user_name="만재")
        text = render_hardcoded(
            MsgType.OPENING_DECLARATION, s, exit_confirmed=True,
        )
        assert "언제든 돌아오시면" not in text


# ─────────────────────────────────────────────
#  (A) 구조 불변 — 질문 종결 규칙 (A-5 / A-6) + 금지 문자
# ─────────────────────────────────────────────

# 슬롯 기본 테스트 값. validator 의 의미적 체크 (A-2 등) 는 STEP 2-D 에서 스펙 정합.
_TEST_SLOTS = dict(
    user_name="만재",
    user_meta_raw="MBTI 같은 거 맞추는 거 아니에요",
    observation_evidence="최근 10장 중 7장이 같은 각도예요.",
    last_diagnosis="만재님 피드는 배경이 본인보다 먼저 자리잡고 있어요.",
    feed_count=15,
)


def _render_all_variants_for(pool_name: str) -> list[str]:
    """특정 pool 의 모든 변형을 테스트 슬롯으로 렌더."""
    return [t.format(**_TEST_SLOTS) for t in ALL_VARIANT_POOLS[pool_name]]


class TestQuestionTerminationRule:
    """QUESTION_REQUIRED / QUESTION_FORBIDDEN 규칙 준수.

    세션 #6 v2 §6.2: 관리 3 타입 (CHECK_IN/RE_ENTRY/RANGE_DISCLOSURE) + OPENING/EMPATHY/
    DIAGNOSIS/SOFT_WALKBACK 은 질문 부호 금지. META_REBUTTAL/EVIDENCE_DEFENSE 는 필수.
    """

    @pytest.mark.parametrize("pool_name", [
        "opening_declaration",
        "soft_walkback",
        "check_in",
        "re_entry",
        "re_entry_exit",
        "range_limit_mild",
        "range_limit_severe",
        "range_reaffirm",
    ])
    def test_no_question_mark_in_forbidden_pools(self, pool_name):
        for text in _render_all_variants_for(pool_name):
            assert "?" not in text, f"{pool_name}: 질문 부호 금지 위반\n  text={text}"

    @pytest.mark.parametrize("pool_name", [
        "meta_rebuttal",
        "evidence_defense",
    ])
    def test_question_mark_present_in_required_pools(self, pool_name):
        for text in _render_all_variants_for(pool_name):
            assert text.rstrip().endswith("?"), (
                f"{pool_name}: 질문 종결 필수 위반\n  text={text}"
            )


class TestGlobalForbiddenCharacters:
    """A-1 전역 금지: ㅋ 변형 (세션 #4 v2 §9.1)."""

    def test_no_giggle_character_anywhere(self):
        for pool_name in ALL_VARIANT_POOLS:
            for text in _render_all_variants_for(pool_name):
                assert "ㅋ" not in text, (
                    f"{pool_name}: ㅋ 전역 금지 위반\n  text={text}"
                )


class TestUserNameSubstitution:
    """템플릿의 {user_name} 플레이스홀더가 누출되지 않음."""

    def test_no_unsubstituted_slots_in_any_pool(self):
        for pool_name in ALL_VARIANT_POOLS:
            for text in _render_all_variants_for(pool_name):
                # 슬롯 placeholder 가 그대로 남아있으면 실패
                for slot in ("{user_name}", "{user_meta_raw}",
                             "{observation_evidence}", "{last_diagnosis}",
                             "{feed_count}"):
                    assert slot not in text, (
                        f"{pool_name}: unsubstituted {slot}\n  text={text}"
                    )


# ─────────────────────────────────────────────
#  (B) load_haiku_prompt
# ─────────────────────────────────────────────

class TestLoadHaikuPrompt:
    def test_available_types_is_haiku_types(self):
        assert available_types() == set(HAIKU_TYPES)

    @pytest.mark.parametrize("mt", list(HAIKU_TYPES))
    def test_loads_every_haiku_type(self, mt: MsgType):
        s = _blank_state()
        prompt = load_haiku_prompt(mt, s)
        assert prompt
        assert "Sia 페르소나 B" in prompt     # base.md 포함
        assert "현재 대화 컨텍스트" in prompt  # ctx 포함

    @pytest.mark.parametrize("mt", list(HARDCODED_TYPES))
    def test_hardcoded_raises(self, mt: MsgType):
        s = _blank_state()
        with pytest.raises(ValueError):
            load_haiku_prompt(mt, s)

    def test_injects_user_name(self):
        s = _blank_state(user_name="정세현")
        prompt = load_haiku_prompt(MsgType.OBSERVATION, s)
        assert "정세현" in prompt

    def test_injects_obs_count(self):
        s = _blank_state()
        s.observation_count = 3
        prompt = load_haiku_prompt(MsgType.RECOGNITION, s)
        assert "OBSERVATION 누적: 3" in prompt

    def test_injects_last_user_message(self):
        s = _blank_state()
        s.turns.append(UserTurn(text="그냥 편해서요", turn_idx=1))
        prompt = load_haiku_prompt(MsgType.CONFRONTATION, s)
        assert "그냥 편해서요" in prompt

    def test_injects_flags(self):
        s = _blank_state()
        flags = UserMessageFlags(
            is_defensive=True,
            has_emotion_word=True,
            emotion_word_raw="부담",
        )
        prompt = load_haiku_prompt(MsgType.EMPATHY_MIRROR, s, user_flags=flags)
        assert "is_defensive" in prompt
        assert "부담" in prompt

    def test_injects_vision_summary(self):
        s = _blank_state()
        prompt = load_haiku_prompt(
            MsgType.OBSERVATION, s,
            vision_summary="색온도 쿨 / 구도 광각 반복 / 배경 흰벽 다수",
        )
        assert "색온도 쿨" in prompt

    def test_recent_assistant_drafts_included(self):
        s = _blank_state()
        s.turns.append(AssistantTurn(
            text="이전 OBSERVATION 본문 예시",
            msg_type=MsgType.OBSERVATION,
            turn_idx=0,
        ))
        prompt = load_haiku_prompt(MsgType.PROBE, s)
        assert "이전 OBSERVATION 본문 예시" in prompt


# ─────────────────────────────────────────────
#  (B+) Composition 플래그 주입 (세션 #7)
# ─────────────────────────────────────────────

class TestCompositionInjection:
    """Composition 플래그별 조건부 모드 지시 블록 주입 검증."""

    def test_default_flags_no_composition_block(self):
        """모든 플래그 기본값이면 '조건부 모드 지시' 섹션 생략."""
        s = _blank_state()
        prompt = load_haiku_prompt(MsgType.OBSERVATION, s)
        assert "조건부 모드 지시" not in prompt

    def test_is_first_turn_activates_m1_combined(self):
        s = _blank_state()
        prompt = load_haiku_prompt(
            MsgType.OBSERVATION, s, is_first_turn=True,
        )
        assert "M1 결합 출력 모드" in prompt
        assert "OPENING_DECLARATION" in prompt

    def test_is_first_turn_not_activated_for_non_observation(self):
        """M1 결합은 OBSERVATION 에만 적용."""
        s = _blank_state()
        prompt = load_haiku_prompt(
            MsgType.PROBE, s, is_first_turn=True,
        )
        assert "M1 결합 출력 모드" not in prompt

    def test_empathy_combined_injects_secondary_guide_probe(self):
        s = _blank_state()
        prompt = load_haiku_prompt(
            MsgType.EMPATHY_MIRROR, s,
            is_combined=True,
            secondary_type=MsgType.PROBE,
        )
        assert "EMPATHY 결합 출력 모드" in prompt
        assert "secondary = probe" in prompt
        assert "탐색 질문" in prompt

    def test_empathy_combined_c6_secondary(self):
        s = _blank_state()
        prompt = load_haiku_prompt(
            MsgType.EMPATHY_MIRROR, s,
            is_combined=True,
            secondary_type=MsgType.CONFRONTATION,
            confrontation_block="C6",
        )
        assert "EMPATHY 결합 출력 모드" in prompt
        assert "secondary = confrontation" in prompt
        assert "C6" in prompt
        assert "재프레임" in prompt

    def test_empathy_combined_reaffirm_secondary(self):
        s = _blank_state()
        prompt = load_haiku_prompt(
            MsgType.EMPATHY_MIRROR, s,
            is_combined=True,
            secondary_type=MsgType.RANGE_DISCLOSURE,
            range_mode="reaffirm",
        )
        assert "RANGE_REAFFIRM" in prompt
        assert "사업 존재 재선언" in prompt

    def test_apply_self_pr_prefix_activates(self):
        s = _blank_state()
        prompt = load_haiku_prompt(
            MsgType.OBSERVATION, s,
            apply_self_pr_prefix=True,
        )
        assert "A-13 Prefix 모드" in prompt

    def test_confrontation_c6_block_hint(self):
        s = _blank_state()
        prompt = load_haiku_prompt(
            MsgType.CONFRONTATION, s,
            confrontation_block="C6",
        )
        assert "CONFRONTATION 블록: C6" in prompt
        assert "평가 의존 돌파" in prompt

    def test_confrontation_c7_block_hint(self):
        s = _blank_state()
        prompt = load_haiku_prompt(
            MsgType.CONFRONTATION, s,
            confrontation_block="C7",
        )
        assert "CONFRONTATION 블록: C7" in prompt
        assert "일반화 회피 돌파" in prompt

    def test_disclaimer_memory_active_injected(self):
        s = _blank_state()
        s.user_disclaimer_memory = {"recent": 2}
        prompt = load_haiku_prompt(MsgType.OBSERVATION, s)
        assert "A-16 유저 무지 영역" in prompt
        assert "남은 2턴" in prompt

    def test_disclaimer_memory_empty_not_injected(self):
        s = _blank_state()
        prompt = load_haiku_prompt(MsgType.OBSERVATION, s)
        assert "A-16 유저 무지 영역" not in prompt


class TestBaseMdExpansion:
    """base.md 세션 #7 보강 섹션 검증."""

    def test_jargon_list_present(self):
        s = _blank_state()
        prompt = load_haiku_prompt(MsgType.OBSERVATION, s)
        assert "분석 jargon 금지" in prompt
        assert "포지셔닝" in prompt
        assert "클러스터링" in prompt

    def test_sasok_section_present(self):
        s = _blank_state()
        prompt = load_haiku_prompt(MsgType.OBSERVATION, s)
        assert "사족 금지" in prompt

    def test_three_gates_section_present(self):
        s = _blank_state()
        prompt = load_haiku_prompt(MsgType.PROBE, s)
        assert "A-12" in prompt
        assert "A-15" in prompt
        assert "A-16" in prompt

    def test_friend_tone_positive_example_present(self):
        s = _blank_state()
        prompt = load_haiku_prompt(MsgType.OBSERVATION, s)
        assert "자연스러운 친구 톤" in prompt
