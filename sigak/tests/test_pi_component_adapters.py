"""Phase I PI-C — 9 컴포넌트 어댑터 단위 테스트.

검증 범위:
  - 정상 경로 (full input)
  - Day 1 fallback (None / 빈 input)
  - boundary (truncate, scale 변환, dedup)

PI-A/B/D/E 와의 회귀 통합 테스트는 본 파일에서 다루지 않음.
"""
from __future__ import annotations

import pytest

from schemas.knowledge import CoordinateRange, MatchedTrend, TrendItem
from schemas.pi_report import (
    ActionPlanContent,
    AxisCoord,
    CelebReferenceContent,
    CelebReferenceMatch,
    CoordinateMapContent,
    CoverContent,
    FaceStructureContent,
    FaceStructureMetric,
    GapAnalysisContent,
    HairRecommendationContent,
    PiContent,
    PiPreview,
    SkinAnalysisContent,
    TypeReferenceContent,
)
from services.coordinate_system import VisualCoordinate, neutral_coordinate
from services.pi_component_adapters import (
    build_action_plan,
    build_coordinate_map,
    build_gap_analysis,
    build_hair_recommendation,
    build_skin_analysis,
    to_preview,
)
from services.pi_methodology import (
    ActionMethodologyEntry,
    ColorMethodologyEntry,
    HairMethodologyEntry,
)


# ─────────────────────────────────────────────
#  helpers
# ─────────────────────────────────────────────

def _make_trend(
    trend_id: str,
    category: str,
    *,
    compatible: tuple[float, float] = (0.4, 0.6),
    title: str = "test trend",
    action_hints: list[str] | None = None,
) -> MatchedTrend:
    rng = CoordinateRange(
        shape=compatible,
        volume=compatible,
        age=compatible,
    )
    trend = TrendItem(
        trend_id=trend_id,
        season="2026_spring",
        gender="female",
        category=category,
        title=title,
        compatible_coordinates=rng,
        action_hints=action_hints or [],
    )
    return MatchedTrend(trend=trend, score=0.85, distance=0.15)


def _color_entry() -> ColorMethodologyEntry:
    return ColorMethodologyEntry(
        best=["#FFAABB", "#CCDDEE", "#112233"],
        ok=["#445566"],
        avoid=["#778899"],
        foundation="warm undertone",
        lip_cheek_eye={"lip": "rose", "cheek": "peach", "eye": "warm brown"},
        classification_reason="autumn warm light",
    )


def _full_pi_content() -> PiContent:
    return PiContent(
        coordinate_map=CoordinateMapContent(
            user_coord=AxisCoord(shape=0.5, volume=0.5, age=0.5),
            type_anchors={},
            trend_overlay=[],
        ),
        face_structure=FaceStructureContent(
            metrics=[
                FaceStructureMetric(
                    name="턱 각도",
                    value=120,
                    descriptor="부드러운 턱선",
                )
            ],
            harmony_note="전체 결이 모여 있어요.",
            distinctive_points=[],
        ),
        celeb_reference=CelebReferenceContent(
            top_celebs=[
                CelebReferenceMatch(
                    name="A",
                    photo_url="https://x/a.jpg",
                    similarity=0.9,
                    reason="r",
                )
            ],
        ),
        cover=CoverContent(
            narrative="첫인상 narrative.",
            key_phrases=["분위기"],
            headline="첫사랑의 첫인상",
        ),
        type_reference=TypeReferenceContent(
            matched_type_id="type_1",
            matched_type_name="따뜻한 첫사랑",
            reason="r",
            features_bullet=["둥근 얼굴"],
            cluster_label="소프트 프레시",
        ),
        gap_analysis=GapAnalysisContent(
            essence_coord=AxisCoord(shape=0.5, volume=0.5, age=0.5),
            aspiration_coord=None,
            gap_narrative="지금은 균형점에 가까워요.",
            vault_phrase_echo=[],
        ),
        skin_analysis=SkinAnalysisContent(
            best_colors=["#FF0000", "#00FF00", "#0000FF"],
            ok_colors=[],
            avoid_colors=[],
            foundation_guide="",
            lip_cheek_eye={},
            trend_palette_match=[],
        ),
        hair_recommendation=HairRecommendationContent(top_hairs=[]),
        action_plan=ActionPlanContent(actions=[]),
    )


# ─────────────────────────────────────────────
#  build_gap_analysis
# ─────────────────────────────────────────────

class TestGapAnalysis:
    def test_with_aspiration_and_phrases(self):
        essence = VisualCoordinate(shape=0.3, volume=0.4, age=0.5)
        aspiration = VisualCoordinate(shape=0.7, volume=0.6, age=0.5)
        result = build_gap_analysis(
            essence,
            aspiration_coord=aspiration,
            vault_phrases=["분위기", "또렷한 인상"],
        )
        assert isinstance(result, GapAnalysisContent)
        assert result.essence_coord.shape == pytest.approx(0.3)
        assert result.aspiration_coord is not None
        assert result.aspiration_coord.shape == pytest.approx(0.7)
        assert result.vault_phrase_echo == ["분위기", "또렷한 인상"]
        assert len(result.gap_narrative) <= 150

    def test_without_aspiration_with_pull(self):
        coord = VisualCoordinate(shape=0.2, volume=0.5, age=0.7)
        result = build_gap_analysis(coord, aspiration_coord=None, vault_phrases=None)
        assert result.aspiration_coord is None
        # 0.2 → 소프트, 0.7 → 성숙 추출 기대
        assert "소프트" in result.gap_narrative or "성숙" in result.gap_narrative

    def test_day1_neutral(self):
        coord = neutral_coordinate()
        result = build_gap_analysis(coord)
        assert result.aspiration_coord is None
        assert "균형" in result.gap_narrative
        assert result.vault_phrase_echo == []

    def test_phrase_echo_truncated_to_3(self):
        coord = neutral_coordinate()
        result = build_gap_analysis(
            coord,
            vault_phrases=["a", "b", "c", "d", "e"],
        )
        assert result.vault_phrase_echo == ["a", "b", "c"]


# ─────────────────────────────────────────────
#  build_skin_analysis
# ─────────────────────────────────────────────

class TestSkinAnalysis:
    def test_full(self):
        color = _color_entry()
        trends = [
            _make_trend("trend_a", "color_palette"),
            _make_trend("trend_b", "color_palette"),
        ]
        result = build_skin_analysis(color, color_palette_trends=trends)
        assert result.best_colors == ["#FFAABB", "#CCDDEE", "#112233"]
        assert result.foundation_guide == "warm undertone"
        assert result.lip_cheek_eye["lip"] == "rose"
        assert result.trend_palette_match == ["trend_a", "trend_b"]

    def test_no_trends(self):
        color = _color_entry()
        result = build_skin_analysis(color, color_palette_trends=None)
        assert result.trend_palette_match == []

    def test_dedup_trend_ids(self):
        color = _color_entry()
        trends = [
            _make_trend("trend_a", "color_palette"),
            _make_trend("trend_a", "color_palette"),
            _make_trend("trend_b", "color_palette"),
        ]
        result = build_skin_analysis(color, color_palette_trends=trends)
        assert result.trend_palette_match == ["trend_a", "trend_b"]


# ─────────────────────────────────────────────
#  build_coordinate_map
# ─────────────────────────────────────────────

class TestCoordinateMap:
    def test_internal_to_external_conversion(self):
        coord = VisualCoordinate(shape=0.5, volume=0.5, age=0.5)
        type_data = {
            "anchors": {
                "type_1": {
                    "coords": {"shape": -0.8, "volume": -0.7, "age": -0.8},
                },
                "type_5": {
                    "coords": {"shape": 0.8, "volume": 0.7, "age": 0.8},
                },
            }
        }
        result = build_coordinate_map(coord, type_anchors_data=type_data)
        assert result.user_coord.shape == pytest.approx(0.5)
        assert "type_1" in result.type_anchors
        assert result.type_anchors["type_1"].shape == pytest.approx(0.1)
        assert result.type_anchors["type_5"].shape == pytest.approx(0.9)

    def test_trend_overlay(self):
        coord = neutral_coordinate()
        trends = [
            _make_trend("sil_1", "silhouette", compatible=(0.2, 0.4)),
        ]
        result = build_coordinate_map(
            coord,
            type_anchors_data=None,
            silhouette_trends=trends,
        )
        assert len(result.trend_overlay) == 1
        assert result.trend_overlay[0]["trend_id"] == "sil_1"
        assert result.trend_overlay[0]["coord_center"]["shape"] == pytest.approx(0.3)

    def test_day1_empty(self):
        coord = neutral_coordinate()
        result = build_coordinate_map(
            coord,
            type_anchors_data=None,
            silhouette_trends=None,
        )
        assert result.user_coord.shape == pytest.approx(0.5)
        assert result.type_anchors == {}
        assert result.trend_overlay == []

    def test_corrupt_anchor_skipped(self):
        coord = neutral_coordinate()
        type_data = {
            "anchors": {
                "type_bad": {"coords": "invalid"},
                "type_partial": {"coords": {"shape": "x", "volume": 0, "age": 0}},
                "type_good": {"coords": {"shape": 0.0, "volume": 0.0, "age": 0.0}},
            }
        }
        result = build_coordinate_map(coord, type_anchors_data=type_data)
        assert "type_bad" not in result.type_anchors
        assert "type_partial" not in result.type_anchors
        assert result.type_anchors["type_good"].shape == pytest.approx(0.5)


# ─────────────────────────────────────────────
#  build_hair_recommendation
# ─────────────────────────────────────────────

class TestHairRecommendation:
    def test_full(self):
        hair_entries = [
            HairMethodologyEntry(
                hair_id="h1",
                hair_name="long_layered",
                score=0.83,
                reason="둥근 얼굴 보정. 광대 가림.",
                matched_features=["face_wide_short"],
            ),
            HairMethodologyEntry(
                hair_id="h2",
                hair_name="short_bob",
                score=0.71,
                reason="턱선 강조.",
                matched_features=["square_jaw"],
            ),
        ]
        styling = [_make_trend("style_a", "styling_method")]
        result = build_hair_recommendation(
            hair_entries,
            styling_trends=styling,
            limit=5,
        )
        assert len(result.top_hairs) == 2
        assert result.top_hairs[0].hair_id == "h1"
        assert result.top_hairs[0].score == pytest.approx(0.83)
        assert result.top_hairs[0].trend_match == ["style_a"]

    def test_limit(self):
        hair_entries = [
            HairMethodologyEntry(
                hair_id=f"h{i}",
                hair_name=f"name{i}",
                score=1.0 - i * 0.1,
                reason="r",
                matched_features=[],
            )
            for i in range(7)
        ]
        result = build_hair_recommendation(hair_entries, limit=3)
        assert len(result.top_hairs) == 3

    def test_day1_empty(self):
        result = build_hair_recommendation(hair_methodology=None)
        assert result.top_hairs == []

    def test_reason_truncated(self):
        long_reason = "a" * 200
        entry = HairMethodologyEntry(
            hair_id="h1",
            hair_name="n",
            score=0.5,
            reason=long_reason,
            matched_features=[],
        )
        result = build_hair_recommendation([entry])
        assert len(result.top_hairs[0].reason) <= 120
        assert result.top_hairs[0].reason.endswith("…")


# ─────────────────────────────────────────────
#  build_action_plan
# ─────────────────────────────────────────────

class TestActionPlan:
    def test_axis_rules_priority(self):
        actions = [
            ActionMethodologyEntry(
                title="볼륨 다운",
                description="shape 축 increase 방향. 볼륨 다운.",
                zone="hair",
                method="layer cut",
                goal="볼륨 다운",
                source="axis:shape/increase",
            ),
        ]
        result = build_action_plan(action_methodology=actions, limit=5)
        assert len(result.actions) == 1
        assert result.actions[0].title == "볼륨 다운"
        assert result.actions[0].source == "axis:shape/increase"

    def test_kb_hints_supplement(self):
        mood = [
            _make_trend(
                "mood_1",
                "mood",
                action_hints=["부드러운 톤", "매트 마감"],
            )
        ]
        result = build_action_plan(
            action_methodology=[],
            mood_trends=mood,
            limit=5,
        )
        assert len(result.actions) == 2
        for action in result.actions:
            assert action.source.startswith("kb:")

    def test_vault_echo_match(self):
        actions = [
            ActionMethodologyEntry(
                title="턱선 정리",
                description="contour 가이드.",
                zone="jaw",
                method="contour",
                goal="턱선 정리",
                source="axis:shape/increase",
            ),
        ]
        result = build_action_plan(
            action_methodology=actions,
            vault_phrases=["턱선 강조"],
        )
        assert result.actions[0].vault_echo == "턱선 강조"

    def test_vault_echo_no_match(self):
        actions = [
            ActionMethodologyEntry(
                title="볼륨 다운",
                description="shape 축.",
                zone="hair",
                method="cut",
                goal="볼륨 다운",
                source="axis:shape/increase",
            ),
        ]
        result = build_action_plan(
            action_methodology=actions,
            vault_phrases=["완전히 다른 단어들"],
        )
        assert result.actions[0].vault_echo is None

    def test_day1_empty(self):
        result = build_action_plan()
        assert result.actions == []

    def test_dedup_axis_and_kb(self):
        actions = [
            ActionMethodologyEntry(
                title="볼륨 다운",
                description="d1",
                zone="hair",
                method="m",
                goal="g",
                source="axis:shape/increase",
            ),
        ]
        mood = [_make_trend("m1", "mood", action_hints=["볼륨 다운", "추가 액션"])]
        result = build_action_plan(action_methodology=actions, mood_trends=mood)
        titles = [a.title for a in result.actions]
        assert titles.count("볼륨 다운") == 1
        assert "추가 액션" in titles

    def test_description_truncated(self):
        long_desc = "a" * 200
        entry = ActionMethodologyEntry(
            title="t",
            description=long_desc,
            zone="z",
            method="m",
            goal="g",
            source="axis:shape/increase",
        )
        result = build_action_plan(action_methodology=[entry])
        assert len(result.actions[0].description) <= 120
        assert result.actions[0].description.endswith("…")


# ─────────────────────────────────────────────
#  to_preview
# ─────────────────────────────────────────────

class TestPreviewDispatcher:
    def test_full_content(self):
        content = _full_pi_content()
        preview = to_preview(content)
        assert isinstance(preview, PiPreview)
        assert preview.cover.narrative == "첫인상 narrative."
        assert preview.celeb_reference_top1 is not None
        assert preview.celeb_reference_top1.name == "A"
        assert "전체 결" in preview.face_structure_teaser
        assert "따뜻한 첫사랑" in preview.type_reference_teaser
        assert "균형점" in preview.gap_analysis_teaser
        assert "BEST" in preview.skin_analysis_teaser
        assert preview.locked_components == [
            "coordinate_map",
            "hair_recommendation",
            "action_plan",
        ]

    def test_no_celeb(self):
        content = _full_pi_content()
        content.celeb_reference = CelebReferenceContent(top_celebs=[])
        preview = to_preview(content)
        assert preview.celeb_reference_top1 is None

    def test_face_fallback_to_metric(self):
        content = _full_pi_content()
        content.face_structure = FaceStructureContent(
            metrics=[
                FaceStructureMetric(
                    name="턱 각도",
                    value=120,
                    descriptor="부드러운 턱선",
                )
            ],
            harmony_note="",
            distinctive_points=[],
        )
        preview = to_preview(content)
        assert "턱 각도" in preview.face_structure_teaser

    def test_face_dash_when_empty(self):
        content = _full_pi_content()
        content.face_structure = FaceStructureContent(
            metrics=[],
            harmony_note="",
            distinctive_points=[],
        )
        preview = to_preview(content)
        assert preview.face_structure_teaser == "—"

    def test_teaser_truncate(self):
        content = _full_pi_content()
        long_text = "a" * 200
        content.gap_analysis = GapAnalysisContent(
            essence_coord=AxisCoord(shape=0.5, volume=0.5, age=0.5),
            aspiration_coord=None,
            gap_narrative=long_text,
            vault_phrase_echo=[],
        )
        preview = to_preview(content)
        assert len(preview.gap_analysis_teaser) <= 80
        assert preview.gap_analysis_teaser.endswith("…")

    def test_type_with_cluster(self):
        content = _full_pi_content()
        preview = to_preview(content)
        assert "소프트 프레시" in preview.type_reference_teaser

    def test_skin_dash_when_no_colors(self):
        content = _full_pi_content()
        content.skin_analysis = SkinAnalysisContent(
            best_colors=[],
            ok_colors=[],
            avoid_colors=[],
            foundation_guide="",
            lip_cheek_eye={},
            trend_palette_match=[],
        )
        preview = to_preview(content)
        assert preview.skin_analysis_teaser == "—"
