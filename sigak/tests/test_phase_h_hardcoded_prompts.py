"""Phase H4 — 하드코딩 4 타입 + Haiku 프롬프트 로더 테스트.

Scope:
  A) sia_hardcoded.render_hardcoded
     - 4 타입 × 5 변형 = 20 템플릿
     - 결정성 (같은 시드 → 같은 index)
     - user_name 치환
     - 모든 변형이 find_violations_v4 pass
  B) sia_prompts_v4.load_haiku_prompt
     - HAIKU_TYPES 7 개 모두 로드 가능
     - HARDCODED_TYPES 는 ValueError
     - base.md + type.md + ctx 3 섹션 조립
"""
from __future__ import annotations

import pytest

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
    TEMPLATES,
    pick_variant_index,
    render_hardcoded,
)
from services.sia_prompts_v4 import available_types, load_haiku_prompt
from services.sia_validators_v4 import find_violations_v4


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
    def test_four_types_registered(self):
        assert set(TEMPLATES.keys()) == set(HARDCODED_TYPES)

    def test_each_type_has_five_variants(self):
        for mt, variants in TEMPLATES.items():
            assert len(variants) == 5, f"{mt.value} has {len(variants)} variants"

    def test_total_twenty_variants(self):
        total = sum(len(v) for v in TEMPLATES.values())
        assert total == 20


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


# ─────────────────────────────────────────────
#  (A) 모든 변형이 validator v4 pass
# ─────────────────────────────────────────────

class TestAllVariantsPassValidator:
    """20 변형 × 각 타입 규칙 → find_violations_v4 위반 없음 확인.

    state 없이 호출 (A-2/A-3 창 체크는 현재 턴만, A-4 스킵).
    """

    @pytest.mark.parametrize("mt", list(HARDCODED_TYPES))
    def test_type_variants_clean(self, mt: MsgType):
        for raw in TEMPLATES[mt]:
            text = raw.format(user_name="만재")
            v = find_violations_v4(text, mt)
            assert v == {}, f"{mt.value} variant violated: {v}\n  text={text}"


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
