"""Aspiration narrative — Phase J5 검증.

사용자 명령서 7-A 5 시나리오 + 추가 회귀 가드:
  1. profile 5 필드 채워진 케이스 → Stub deterministic narrative
  2. profile 빈 케이스 (Day 1) → fallback 정상 동작
  3. A-17 영업 어휘 hard reject 검증
  4. A-20 추상 칭찬어 hard reject 검증
  5. A-18 길이 300자 초과 hard reject (overall_message 만 적용)
  6. _parse_aspiration_response — JSON wrapper 제거
  7. _parse_aspiration_response — 잘못된 JSON fallback
  8. _build_aspiration_fallback — 자체 위반 0 (페르소나 B 통과)
  9. compose_overall_message 어댑터 — Stub 환경 dict 반환
 10. AspirationHistoryEntry 격리 — aspiration_vector_snapshot 추가, raw 필드 부재
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from schemas.user_taste import (
    ConversationSignals,
    UserTasteProfile,
)
from services.coordinate_system import GapVector, VisualCoordinate
from services.sia_writer import (
    StubSiaWriter,
    _build_aspiration_fallback,
    _collect_violations_aspiration,
    _load_aspiration_system_prompt,
    _parse_aspiration_response,
    _render_taste_profile_slim,
)


# ─────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────

def _gap_shape_primary() -> GapVector:
    return GapVector(
        primary_axis="shape", primary_delta=0.30,
        secondary_axis="age", secondary_delta=-0.10,
        tertiary_axis="volume", tertiary_delta=0.02,
    )


def _profile_full() -> UserTasteProfile:
    """5 필드 모두 채워진 풀 데이터 케이스 — strength_score 0.85."""
    return UserTasteProfile(
        user_id="u_full",
        snapshot_at=datetime.now(timezone.utc),
        current_position=VisualCoordinate(shape=0.40, volume=0.55, age=0.45),
        aspiration_vector=_gap_shape_primary(),
        conversation_signals=ConversationSignals(
            current_concerns="얼굴이 넓어 보여서 고민",
            specific_context="요즘 셀프 사진 많이 찍는데 답답함",
            desired_image_keywords=["차분한", "정돈된"],
        ),
        user_original_phrases=["차분한 결", "정돈된 분위기"],
        strength_score=0.85,
    )


def _profile_day1() -> UserTasteProfile:
    """Day 1 유저 — 모든 필드 default."""
    return UserTasteProfile(
        user_id="u_day1",
        snapshot_at=datetime.now(timezone.utc),
    )


# ─────────────────────────────────────────────
#  1. profile 5 필드 풀 케이스
# ─────────────────────────────────────────────

class TestProfileFullCase:
    def test_stub_returns_dict_with_required_keys(self):
        stub = StubSiaWriter()
        result = stub.generate_aspiration_overall(
            profile=_profile_full(),
            gap_vector=_gap_shape_primary(),
            target_display_name="@yuni",
            user_name="정세현",
        )
        assert isinstance(result, dict)
        for key in (
            "overall_message",
            "gap_summary",
            "action_hints",
            "raw_haiku_response",
            "matched_trends_used",
        ):
            assert key in result, f"missing key: {key}"

    def test_overall_uses_dynamic_user_name(self):
        stub = StubSiaWriter()
        result = stub.generate_aspiration_overall(
            profile=_profile_full(),
            gap_vector=_gap_shape_primary(),
            target_display_name="@yuni",
            user_name="정세현",
        )
        assert "정세현" in result["overall_message"]
        # Stub: Haiku 미호출이라 raw_haiku_response 빈 문자열
        assert result["raw_haiku_response"] == ""

    def test_taste_profile_slim_5_fields(self):
        slim = _render_taste_profile_slim(_profile_full())
        # Phase I — Backward echo: latest_pi 키 추가 (5 → 6 fields)
        assert set(slim.keys()) == {
            "current_position",
            "aspiration_vector",
            "conversation_signals",
            "user_original_phrases",
            "latest_pi",
            "strength_score",
        }
        # 풀 데이터 — 5 필드 비어있지 않음 + latest_pi 는 fixture 기본 None
        assert slim["current_position"] is not None
        assert slim["aspiration_vector"] is not None
        assert slim["conversation_signals"] is not None
        assert slim["user_original_phrases"]
        assert slim["latest_pi"] is None    # _profile_full fixture 기본 latest_pi 미설정
        assert slim["strength_score"] == 0.85


# ─────────────────────────────────────────────
#  2. Day 1 유저 fallback
# ─────────────────────────────────────────────

class TestDay1Fallback:
    def test_stub_day1_returns_valid_narrative(self):
        stub = StubSiaWriter()
        result = stub.generate_aspiration_overall(
            profile=_profile_day1(),
            gap_vector=_gap_shape_primary(),
            target_display_name="@yuni",
            user_name=None,
        )
        # 빈 user_name → "이분" fallback
        assert "이분" in result["overall_message"]
        assert isinstance(result["action_hints"], list)
        assert len(result["action_hints"]) >= 1

    def test_taste_profile_slim_day1(self):
        slim = _render_taste_profile_slim(_profile_day1())
        # current_position None / aspiration_vector None
        assert slim["current_position"] is None
        assert slim["aspiration_vector"] is None
        # conversation_signals default factory → dict (empty fields)
        assert slim["conversation_signals"] is not None
        assert slim["user_original_phrases"] == []
        # Phase I — Day 1 = PI 미체험 → latest_pi None
        assert slim["latest_pi"] is None
        assert slim["strength_score"] == 0.0


# ─────────────────────────────────────────────
#  3. A-17 영업 어휘 hard reject
# ─────────────────────────────────────────────

class TestA17CommerceReject:
    def test_a17_consulting_word_in_overall_message(self):
        commerce_text = json.dumps({
            "overall_message": "본인 결을 살펴봤어요. 컨설팅을 추천해드릴 수 있어요.",
            "gap_summary": "shape 갭",
            "action_hints": ["다음 단계로 넘어가세요"],
        }, ensure_ascii=False)
        violations = _collect_violations_aspiration(commerce_text)
        assert violations, "영업 어휘가 reject 안 됨"

    def test_a17_clean_text_passes(self):
        clean_text = json.dumps({
            "overall_message": "본인 결을 같이 봤어요 더라구요. 차분하시잖아요.",
            "gap_summary": "shape 축 갭",
            "action_hints": ["한 컷 시도해보세요"],
        }, ensure_ascii=False)
        violations = _collect_violations_aspiration(clean_text)
        # 페르소나 B clean text — A-17/A-18/A-20/markdown 0건 기대
        assert violations == [], f"clean text 에 violation 발생: {violations}"


# ─────────────────────────────────────────────
#  4. A-20 추상 칭찬어 hard reject
# ─────────────────────────────────────────────

class TestA20AbstractPraiseReject:
    def test_a20_maeryeok_word(self):
        text = json.dumps({
            "overall_message": "정말 매력적인 분이시잖아요. 독특한 결이에요.",
            "gap_summary": "shape 갭",
            "action_hints": ["흥미로운 시도"],
        }, ensure_ascii=False)
        violations = _collect_violations_aspiration(text)
        assert violations, "추상 칭찬어 reject 안 됨"


# ─────────────────────────────────────────────
#  5. A-18 길이 hard reject (overall_message 만)
# ─────────────────────────────────────────────

class TestA18LengthReject:
    def test_a18_overall_over_300_chars(self):
        long_overall = "본인 결을 같이 봤어요 더라구요. " * 30  # ~390+ chars
        text = json.dumps({
            "overall_message": long_overall,
            "gap_summary": "shape 갭",
            "action_hints": [],
        }, ensure_ascii=False)
        violations = _collect_violations_aspiration(text)
        assert violations, f"300자 초과 reject 안 됨, len={len(long_overall)}"

    def test_a18_overall_within_limit_passes(self):
        # 200자 내외 narrative
        normal = (
            "본인 결을 살피고 추구미 결도 같이 봤어요 더라구요. "
            "shape 축에서 갭이 보이시잖아요. 한 컷 시도 권해드려요."
        )
        text = json.dumps({
            "overall_message": normal,
            "gap_summary": "shape 갭이에요",
            "action_hints": ["시도 권유"],
        }, ensure_ascii=False)
        violations = _collect_violations_aspiration(text)
        assert violations == [], f"normal length 에 violation 발생: {violations}"


# ─────────────────────────────────────────────
#  6. JSON parser — wrapper 제거
# ─────────────────────────────────────────────

class TestParserWrapperStrip:
    def test_json_code_fence_stripped(self):
        fallback = {
            "overall_message": "fb_overall",
            "gap_summary": "fb_gap",
            "action_hints": ["fb1"],
        }
        wrapped = (
            "```json\n"
            '{"overall_message": "x", "gap_summary": "y", "action_hints": ["z"]}\n'
            "```"
        )
        parsed = _parse_aspiration_response(wrapped, fallback)
        assert parsed["overall_message"] == "x"
        assert parsed["gap_summary"] == "y"
        assert parsed["action_hints"] == ["z"]


# ─────────────────────────────────────────────
#  7. Parser fallback on invalid JSON
# ─────────────────────────────────────────────

class TestParserFallback:
    def test_invalid_json_returns_fallback(self):
        fallback = {
            "overall_message": "fb_overall",
            "gap_summary": "fb_gap",
            "action_hints": ["fb1"],
        }
        parsed = _parse_aspiration_response("not a json", fallback)
        assert parsed["overall_message"] == "fb_overall"
        assert parsed["gap_summary"] == "fb_gap"
        assert parsed["action_hints"] == ["fb1"]

    def test_empty_raw_returns_fallback(self):
        fallback = {
            "overall_message": "fb_overall",
            "gap_summary": "fb_gap",
            "action_hints": ["fb1"],
        }
        parsed = _parse_aspiration_response("", fallback)
        assert parsed["overall_message"] == "fb_overall"


# ─────────────────────────────────────────────
#  8. fallback 자체 위반 0 (페르소나 B 통과)
# ─────────────────────────────────────────────

class TestFallbackCleanByDesign:
    def test_fallback_violation_free(self):
        fb = _build_aspiration_fallback(
            honor="정세현님",
            target_display_name="@yuni",
            gap_vector=_gap_shape_primary(),
            profile=_profile_full(),
        )
        full_text = json.dumps(fb, ensure_ascii=False)
        violations = _collect_violations_aspiration(full_text)
        assert violations == [], f"fallback 자체 위반: {violations}"

    def test_fallback_persona_b_endings(self):
        fb = _build_aspiration_fallback(
            honor="정세현님",
            target_display_name="@yuni",
            gap_vector=_gap_shape_primary(),
            profile=_profile_full(),
        )
        # 페르소나 B 어미 1개 이상 포함
        assert any(
            ending in fb["overall_message"]
            for ending in ("더라구요", "잖아요", "이세요", "이시잖아요", "어요")
        )


# ─────────────────────────────────────────────
#  9. compose_overall_message 어댑터 (Stub 환경)
# ─────────────────────────────────────────────

class TestComposeAdapter:
    def test_compose_returns_dict_via_writer(self):
        from services.aspiration_common import compose_overall_message
        result = compose_overall_message(
            target_display_name="@yuni",
            gap_vector=_gap_shape_primary(),
            profile=_profile_full(),
            user_name="정세현",
        )
        assert isinstance(result, dict)
        assert "overall_message" in result
        assert "gap_summary" in result
        assert "action_hints" in result


# ─────────────────────────────────────────────
#  10. AspirationHistoryEntry 격리 (aspiration_vector_snapshot 추가 후)
# ─────────────────────────────────────────────

class TestHistoryEntryIsolation:
    def test_aspiration_vector_snapshot_added(self):
        from schemas.user_history import AspirationHistoryEntry
        fields = AspirationHistoryEntry.model_fields
        assert "aspiration_vector_snapshot" in fields, (
            "Phase J5 신규 필드 누락"
        )

    def test_raw_fields_still_isolated(self):
        from schemas.user_history import AspirationHistoryEntry
        fields = AspirationHistoryEntry.model_fields
        # raw 격리 — Phase J5 추가 후에도 유지
        assert "raw_haiku_response" not in fields
        assert "r2_apify_raw_key" not in fields
        assert "r2_vision_raw_key" not in fields
        assert "raw_items" not in fields


# ─────────────────────────────────────────────
#  11. system prompt 로딩
# ─────────────────────────────────────────────

class TestSystemPromptLoad:
    def test_system_prompt_loaded(self):
        sp = _load_aspiration_system_prompt()
        assert len(sp) > 1000, "base.md 로딩 실패"
        # 핵심 키워드 존재
        assert "페르소나 B" in sp
        assert "Verdict" in sp  # 금지어로 명시되어 있음
        assert "overall_message" in sp
        assert "action_hints" in sp
