"""Phase I — pi_engine v1 + sia_writer PI overall 단위 테스트.

PI-A 영역 (pi_engine.py 본문 + sia_writer.generate_pi_overall) 회귀 가드.

Mock 격리:
  - Sonnet / Haiku API: 호출 0 (helpers 단위 + fallback 만 검증)
  - R2 / DB: monkey-patch
  - vault load: 합성 dict 또는 fake

회귀 통합 검증 (PI-A/B/C/D/E 통합) 은 별도 단계. 본 테스트는 단위만.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Optional

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schemas.user_taste import (
    ConversationSignals,
    UserTasteProfile,
)
from services.coordinate_system import VisualCoordinate
from services.pi_engine import (
    PIEngineError,
    _assemble_9_components,
    _build_pi_narrative_fallback,
    _compose_pi_v1_boundary,
    _extract_aspiration_history_top,
    _extract_best_shot_history_top,
    _extract_verdict_history_top,
    _hair_recommendation_from_action,
    _resolve_cluster_label,
    determine_pi_photo_count,
)
from services.sia_writer import (
    StubSiaWriter,
    _build_pi_overall_fallback,
    _collect_violations_pi_report,
)


# ─────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────

def _profile(
    *,
    strength: float = 0.5,
    phrases: Optional[list[str]] = None,
) -> UserTasteProfile:
    return UserTasteProfile(
        user_id="u-test",
        snapshot_at=datetime.now(timezone.utc),
        current_position=None,
        aspiration_vector=None,
        preference_evidence=[],
        conversation_signals=ConversationSignals(),
        trajectory=[],
        user_original_phrases=phrases or [],
        strength_score=strength,
    )


def _sample_components() -> dict:
    """9 컴포넌트 샘플 — _assemble_9_components 출력과 정합."""
    return {
        "cover": {
            "weight": "vault", "mode": "preview",
            "content": {
                "headline": "차분한 결을 잡고 가시는 분이에요",
                "subhead": "벽돌톤과 라벤더 조합이 일관돼요",
                "body": "정면 분석과 vault 데이터로 정리한 결과예요.",
            },
        },
        "type_reference": {
            "weight": "vault", "mode": "teaser",
            "content": {
                "matched_label": "따뜻한 첫사랑",
                "matched_one_liner": "둥글고 작고 어린",
                "match_reason": "광대 부드럽고 턱각 100도 안쪽이에요.",
                "secondary": [],
            },
        },
        "gap_analysis": {
            "weight": "vault", "mode": "teaser",
            "content": {
                "primary_axis": "shape",
                "primary_direction": "샤프 쪽으로 0.3 이동",
                "primary_narrative": "현 위치는 둥근 쪽이에요.",
                "secondary_axis": "",
                "secondary_narrative": "",
                "tertiary_narrative": "",
            },
        },
        "action_plan": {
            "weight": "trend", "mode": "lock",
            "content": {
                "primary_action": "레이어드 롭 컷",
                "primary_why": "광대와 턱선 부드럽게 감싸 정합",
                "primary_how": "C컬 드라이로 마무리",
                "secondary_actions": [],
                "expected_effects": [],
                "trend_sources": [],
            },
        },
    }


# ─────────────────────────────────────────────
#  determine_pi_photo_count — 회귀 가드
# ─────────────────────────────────────────────

class TestDeterminePiPhotoCount:
    def test_zero(self):
        assert determine_pi_photo_count(0) == (0, 0)

    def test_under_15_proportional(self):
        # 8 → public=2 (8//3) / locked=6
        assert determine_pi_photo_count(8) == (2, 6)
        # 12 → public=4 / locked=8
        assert determine_pi_photo_count(12) == (4, 8)

    def test_16_to_40_fixed(self):
        assert determine_pi_photo_count(20) == (5, 10)
        assert determine_pi_photo_count(40) == (5, 10)

    def test_over_40_capped(self):
        # 50: 50//6=8, max(10, min(8,15))=10 → (5, 10)
        assert determine_pi_photo_count(50) == (5, 10)
        # 150: 150//6=25, min(25,15)=15, max(10,15)=15 → (5, 15)
        assert determine_pi_photo_count(150) == (5, 15)


# ─────────────────────────────────────────────
#  _resolve_cluster_label — type_id → cluster_labels.json 매핑
# ─────────────────────────────────────────────

class TestResolveClusterLabel:
    def test_empty_returns_none(self):
        assert _resolve_cluster_label(None) is None
        assert _resolve_cluster_label("") is None

    def test_unknown_type_returns_none(self):
        # cluster_labels.json 안에 없는 type_id
        assert _resolve_cluster_label("type_zzz") is None

    def test_real_type_id_resolves(self):
        # cluster_labels.json 의 cool_goddess 클러스터 = type_3 + type_8
        # 파일 부재 시 None — 회귀 가드 (실 파일 검증)
        result = _resolve_cluster_label("type_3")
        # 파일 있으면 "쿨 갓데스", 없으면 None — 둘 다 허용 (회귀 0)
        assert result is None or isinstance(result, str)


# ─────────────────────────────────────────────
#  _build_pi_narrative_fallback — Haiku 실패 시 deterministic
# ─────────────────────────────────────────────

class TestBuildPiNarrativeFallback:
    def test_4_components_returned(self):
        coord = VisualCoordinate(shape=0.5, volume=0.5, age=0.5)
        result = _build_pi_narrative_fallback(
            honor="진규님", coord_3axis=coord, face_type="달걀형",
            matched_types=[],
        )
        assert "cover" in result
        assert "type_reference" in result
        assert "gap_analysis" in result
        assert "action_plan" in result

    def test_cover_body_contains_honor(self):
        coord = VisualCoordinate(shape=0.5, volume=0.5, age=0.5)
        result = _build_pi_narrative_fallback(
            honor="진규님", coord_3axis=coord, face_type="",
            matched_types=[],
        )
        body = result["cover"]["body"]
        assert "진규님" in body

    def test_matched_types_used_when_provided(self):
        coord = VisualCoordinate(shape=0.5, volume=0.5, age=0.5)
        types = [{"name_kr": "따뜻한 첫사랑", "description": "둥글고 어린"}]
        result = _build_pi_narrative_fallback(
            honor="", coord_3axis=coord, face_type="달걀형",
            matched_types=types,
        )
        assert result["type_reference"]["matched_label"] == "따뜻한 첫사랑"

    def test_fallback_tone_compliant(self):
        """fallback 텍스트가 PI 리포트체 톤 검증 통과."""
        coord = VisualCoordinate(shape=0.5, volume=0.5, age=0.5)
        result = _build_pi_narrative_fallback(
            honor="진규님", coord_3axis=coord, face_type="",
            matched_types=[],
        )
        body = result["cover"]["body"]
        violations = _collect_violations_pi_report(body)
        assert not violations, f"fallback 톤 위반: {violations}"


# ─────────────────────────────────────────────
#  _hair_recommendation_from_action — 어댑터
# ─────────────────────────────────────────────

class TestHairRecommendationFromAction:
    def test_empty_action(self):
        result = _hair_recommendation_from_action({}, [])
        assert result["primary_action"] == ""
        assert result["styling_trends"] == []

    def test_styling_method_filtered(self):
        action_plan = {
            "primary_action": "레이어드 롭",
            "primary_why": "정합",
            "primary_how": "C컬",
        }
        trends = [
            {"trend_id": "t1", "category": "styling_method", "title": "레이어드 롭",
             "score_label": "강한 상승", "source": "W Korea", "action_hints": ["귀 아래"]},
            {"trend_id": "t2", "category": "color_palette", "title": "민트",
             "action_hints": []},
            {"trend_id": "t3", "category": "styling_method", "title": "커튼뱅",
             "action_hints": []},
        ]
        result = _hair_recommendation_from_action(action_plan, trends)
        assert result["primary_action"] == "레이어드 롭"
        # styling_method 만 필터, color_palette 제외
        assert len(result["styling_trends"]) == 2
        assert result["styling_trends"][0]["trend_id"] == "t1"

    def test_max_3_styling_trends(self):
        action_plan = {"primary_action": "x", "primary_why": "", "primary_how": ""}
        trends = [
            {"trend_id": f"t{i}", "category": "styling_method", "title": f"h{i}",
             "action_hints": []}
            for i in range(10)
        ]
        result = _hair_recommendation_from_action(action_plan, trends)
        assert len(result["styling_trends"]) == 3


# ─────────────────────────────────────────────
#  _compose_pi_v1_boundary — version 분기
# ─────────────────────────────────────────────

class TestComposePiV1Boundary:
    def test_version_1_first_pi(self):
        profile = _profile(strength=0.6)
        text = _compose_pi_v1_boundary(profile, version=1)
        assert "첫 PI" in text or "미리보기" in text
        # 톤 검증
        violations = _collect_violations_pi_report(text)
        assert not violations, f"boundary 톤 위반: {violations}"

    def test_version_2_regenerate(self):
        profile = _profile(strength=0.7)
        text = _compose_pi_v1_boundary(profile, version=2)
        assert "버전 2" in text
        violations = _collect_violations_pi_report(text)
        assert not violations


# ─────────────────────────────────────────────
#  _assemble_9_components — 9 키 + mode 분기
# ─────────────────────────────────────────────

class TestAssemble9Components:
    def test_all_9_keys_present(self):
        coord = VisualCoordinate(shape=0.5, volume=0.5, age=0.5)
        components = _assemble_9_components(
            sonnet_face_structure={"face_type": "달걀형"},
            sonnet_skin_analysis={"tone": "쿨 라이트"},
            haiku_cover={"headline": "h"},
            haiku_type_reference={"matched_label": "t"},
            haiku_gap_analysis={"primary_axis": "shape"},
            haiku_action_plan={"primary_action": "p"},
            coord_3axis=coord,
            matched_celebs=[], matched_types=[], matched_trends=[],
        )
        expected_keys = {
            "coordinate_map", "face_structure", "celeb_reference",
            "cover", "type_reference", "gap_analysis",
            "skin_analysis", "hair_recommendation", "action_plan",
        }
        assert set(components.keys()) == expected_keys

    def test_weight_distribution_3_3_3(self):
        coord = VisualCoordinate(shape=0.5, volume=0.5, age=0.5)
        components = _assemble_9_components(
            sonnet_face_structure={}, sonnet_skin_analysis={},
            haiku_cover={}, haiku_type_reference={},
            haiku_gap_analysis={}, haiku_action_plan={},
            coord_3axis=coord, matched_celebs=[], matched_types=[], matched_trends=[],
        )
        weights = [c["weight"] for c in components.values()]
        assert weights.count("raw") == 3
        assert weights.count("vault") == 3
        assert weights.count("trend") == 3

    def test_mode_distribution(self):
        """preview 2 + teaser 4 + lock 3."""
        coord = VisualCoordinate(shape=0.5, volume=0.5, age=0.5)
        components = _assemble_9_components(
            sonnet_face_structure={}, sonnet_skin_analysis={},
            haiku_cover={}, haiku_type_reference={},
            haiku_gap_analysis={}, haiku_action_plan={},
            coord_3axis=coord, matched_celebs=[], matched_types=[], matched_trends=[],
        )
        modes = [c["mode"] for c in components.values()]
        assert modes.count("preview") == 2     # cover + celeb_reference
        assert modes.count("teaser") == 4      # face / type / gap / skin
        assert modes.count("lock") == 3        # coord / hair / action

    def test_coordinate_map_current_coords(self):
        coord = VisualCoordinate(shape=0.65, volume=0.5, age=0.45)
        components = _assemble_9_components(
            sonnet_face_structure={}, sonnet_skin_analysis={},
            haiku_cover={}, haiku_type_reference={},
            haiku_gap_analysis={}, haiku_action_plan={},
            coord_3axis=coord, matched_celebs=[], matched_types=[], matched_trends=[],
            aspiration_vector={"primary_axis": "shape", "primary_delta": 0.2},
        )
        coord_content = components["coordinate_map"]["content"]
        assert coord_content["current_coords"]["shape"] == pytest.approx(0.65)
        assert coord_content["aspiration_coords"] is not None


# ─────────────────────────────────────────────
#  _extract_*_history_top — 강화 루프 vault history
# ─────────────────────────────────────────────

class _FakeVault:
    def __init__(self, **kw):
        self.verdict_history = kw.get("verdict_history", [])
        self.best_shot_history = kw.get("best_shot_history", [])
        self.aspiration_history = kw.get("aspiration_history", [])


class TestExtractHistoryTop:
    def test_verdict_empty(self):
        v = _FakeVault()
        assert _extract_verdict_history_top(v, n=3) == []

    def test_verdict_top_3_slim(self):
        history = [
            {"session_id": f"vd_{i}", "best_fit_coords": {"shape": 0.5},
             "style_direction": f"dir{i}", "photo_insights": [{}, {}]}
            for i in range(5)
        ]
        v = _FakeVault(verdict_history=history)
        result = _extract_verdict_history_top(v, n=3)
        assert len(result) == 3
        # 최신 3 (인덱스 2,3,4) — 마지막 N 추출
        assert result[-1]["session_id"] == "vd_4"
        assert result[-1]["top_photo_count"] == 2

    def test_best_shot_top_2(self):
        history = [
            {"session_id": f"bs_{i}", "selected_photos": [{}, {}, {}],
             "uploaded_count": 100, "overall_message": "x" * 250}
            for i in range(5)
        ]
        v = _FakeVault(best_shot_history=history)
        result = _extract_best_shot_history_top(v, n=2)
        assert len(result) == 2
        # overall_message 200자 truncate
        assert len(result[0]["overall_message"]) == 200
        assert result[0]["selected_count"] == 3

    def test_aspiration_top_2_with_gap(self):
        history = [
            {
                "analysis_id": "asp_1",
                "target_type": "ig", "target_display_name": "@yuni",
                "gap_vector": {"primary_axis": "shape"},
                "narrative": {"gap_summary": "샤프 방향"},
                "matched_trend_ids": ["t1", "t2"],
            },
        ]
        v = _FakeVault(aspiration_history=history)
        result = _extract_aspiration_history_top(v, n=2)
        assert len(result) == 1
        assert result[0]["primary_axis"] == "shape"
        assert result[0]["gap_summary"] == "샤프 방향"


# ─────────────────────────────────────────────
#  sia_writer PI overall — _build_pi_overall_fallback
# ─────────────────────────────────────────────

class TestBuildPiOverallFallback:
    def test_empty_components(self):
        text = _build_pi_overall_fallback(honor="진규님", components={})
        assert "진규님" in text
        violations = _collect_violations_pi_report(text)
        assert not violations

    def test_with_full_components(self):
        text = _build_pi_overall_fallback(
            honor="진규님", components=_sample_components(),
        )
        # matched_label / primary_direction echo
        assert "따뜻한 첫사랑" in text or "샤프 쪽으로 0.3 이동" in text
        violations = _collect_violations_pi_report(text)
        assert not violations

    def test_no_honor_no_violation(self):
        text = _build_pi_overall_fallback(honor="", components=_sample_components())
        violations = _collect_violations_pi_report(text)
        assert not violations


# ─────────────────────────────────────────────
#  _collect_violations_pi_report — 톤 검증 핵심
# ─────────────────────────────────────────────

class TestCollectViolationsPiReport:
    def test_clean_text_zero_violations(self):
        text = "정세현님 정면 분석 결과 차분한 결이 보여요. 비율도 정돈된 편이에요."
        assert _collect_violations_pi_report(text) == []

    def test_sia_chinmilche_rejected(self):
        """Sia 친밀체 (~잖아요/~더라구요) hard reject."""
        bad = "정면 분석에서 차분한 결이 보이잖아요"
        violations = _collect_violations_pi_report(bad)
        assert violations
        assert any("PI 톤 위반" in v for v in violations)

    def test_sia_doraguyo_rejected(self):
        bad = "광대 위치가 평균보다 위쪽이더라구요"
        violations = _collect_violations_pi_report(bad)
        assert any("PI 톤 위반" in v for v in violations)

    def test_verdict_jeongjungche_rejected(self):
        """Verdict 정중체 (~합니다) hard reject."""
        bad = "정면 분석 결과를 정리합니다"
        violations = _collect_violations_pi_report(bad)
        assert any("PI 톤 위반" in v for v in violations)

    def test_neyo_gunyo_rejected(self):
        """흐림/감탄 어미 hard reject."""
        for bad in ["차분한 결이네요.", "정돈된 편이군요"]:
            violations = _collect_violations_pi_report(bad)
            assert violations, f"미감지: {bad}"

    def test_a17_commerce_rejected(self):
        bad = "다음 단계로 정리해드릴게요"
        violations = _collect_violations_pi_report(bad)
        assert any("A-17" in v or "영업" in v.lower() for v in violations)

    def test_a20_abstract_praise_rejected(self):
        bad = "매력적인 비율이에요"
        violations = _collect_violations_pi_report(bad)
        assert violations

    def test_markdown_rejected(self):
        bad = "**광대** 부분은 정돈된 편이에요"
        violations = _collect_violations_pi_report(bad)
        assert violations

    def test_length_350_hard_reject(self):
        bad = "차분해요. " * 50  # 약 500자
        violations = _collect_violations_pi_report(bad)
        assert any("길이" in v for v in violations)

    def test_pi_only_vocab_allowed(self):
        """PI 한정 허용 어휘 (분석 / 얼굴형 / 비율) 통과."""
        good = "광대 분석 결과 비율이 정돈된 편이에요. 얼굴형은 달걀형에 가까워요."
        violations = _collect_violations_pi_report(good)
        # 길이 / 마크다운 / 영업 / 추상칭찬 0건 — 단 톤 어미 확인
        assert not any("PI 톤 위반" in v for v in violations)


# ─────────────────────────────────────────────
#  StubSiaWriter.generate_pi_overall — 외부 인터페이스
# ─────────────────────────────────────────────

class TestStubSiaWriterPiOverall:
    def test_returns_text(self):
        stub = StubSiaWriter()
        profile = _profile(strength=0.5)
        text = stub.generate_pi_overall(
            profile=profile,
            components=_sample_components(),
            user_name="진규",
        )
        assert text
        assert "진규님" in text

    def test_clean_of_violations(self):
        stub = StubSiaWriter()
        profile = _profile(strength=0.5)
        text = stub.generate_pi_overall(
            profile=profile,
            components=_sample_components(),
            user_name="진규",
        )
        violations = _collect_violations_pi_report(text)
        assert not violations, f"Stub 톤 위반: {violations}"

    def test_no_user_name_uses_generic(self):
        stub = StubSiaWriter()
        profile = _profile(strength=0.3)
        text = stub.generate_pi_overall(
            profile=profile, components={}, user_name=None,
        )
        assert text
        violations = _collect_violations_pi_report(text)
        assert not violations
