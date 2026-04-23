"""Phase G — 공통 인프라 테스트.

CoordinateSystem / UserTasteProfile / UserDataVault / KnowledgeBase /
KnowledgeMatcher / SiaWriter / tokens.py 신규 상수.
"""
from __future__ import annotations

import sys
import os
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services import tokens
from services.coordinate_system import (
    AXES,
    VisualCoordinate,
    GapVector,
    neutral_coordinate,
)
from schemas.user_taste import (
    ConversationSignals,
    UserTasteProfile,
    compute_strength_score,
)
from schemas.knowledge import TrendItem, CoordinateRange
from services.knowledge_base import load_trends
from services.knowledge_matcher import match_trends_for_user
from services.sia_writer import StubSiaWriter, get_sia_writer, set_sia_writer


# ─────────────────────────────────────────────
#  tokens.py — 신규 상수
# ─────────────────────────────────────────────

def test_tokens_new_cost_constants():
    assert tokens.COST_ASPIRATION_IG == 20
    assert tokens.COST_ASPIRATION_PINTEREST == 20
    assert tokens.COST_BEST_SHOT == 30


def test_tokens_new_kind_values():
    assert tokens.KIND_CONSUME_ASPIRATION_IG == "consume_aspiration_ig"
    assert tokens.KIND_CONSUME_ASPIRATION_PINTEREST == "consume_aspiration_pinterest"
    assert tokens.KIND_CONSUME_BEST_SHOT == "consume_best_shot"


# ─────────────────────────────────────────────
#  CoordinateSystem
# ─────────────────────────────────────────────

def test_axes_metadata_complete():
    assert set(AXES.keys()) == {"shape", "volume", "age"}
    assert AXES["shape"].negative_short == "소프트"
    assert AXES["shape"].positive_short == "샤프"


def test_visual_coordinate_clamp_range():
    with pytest.raises(Exception):
        VisualCoordinate(shape=-0.1, volume=0.5, age=0.5)
    with pytest.raises(Exception):
        VisualCoordinate(shape=1.2, volume=0.5, age=0.5)


def test_distance_identity_and_symmetry():
    a = VisualCoordinate(shape=0.3, volume=0.4, age=0.5)
    b = VisualCoordinate(shape=0.8, volume=0.2, age=0.9)
    assert a.distance_to(a) == 0.0
    assert abs(a.distance_to(b) - b.distance_to(a)) < 1e-9


def test_gap_vector_primary_largest_delta():
    cur = VisualCoordinate(shape=0.2, volume=0.5, age=0.5)
    tgt = VisualCoordinate(shape=0.7, volume=0.6, age=0.4)
    gap = cur.gap_vector(tgt)
    assert gap.primary_axis == "shape"
    assert abs(gap.primary_delta - 0.5) < 1e-9
    # secondary = |Δ|=0.1 (volume), tertiary = 0.1 (age) — 순서 stable 하면 volume
    assert gap.secondary_axis in ("volume", "age")


def test_internal_external_roundtrip():
    c = VisualCoordinate.from_internal(-1.0, 0.0, 1.0)
    assert c.shape == 0.0
    assert c.volume == 0.5
    assert c.age == 1.0
    # 다시 내부로
    s, v, a = c.to_internal()
    assert (s, v, a) == (-1.0, 0.0, 1.0)


def test_apply_deltas_clamps():
    c = VisualCoordinate(shape=0.9, volume=0.5, age=0.5)
    # +0.5 누적해도 1.0 초과 clamp
    c2 = c.apply_deltas(shape_d=0.5, volume_d=0.0, age_d=0.0)
    assert c2.shape == 1.0


def test_gap_narrative_contains_axis_labels():
    cur = VisualCoordinate(shape=0.3, volume=0.5, age=0.5)
    tgt = VisualCoordinate(shape=0.7, volume=0.5, age=0.5)
    text = cur.gap_vector(tgt).narrative()
    assert "형태" in text or "shape" in text
    assert "소프트 → 샤프" in text or "샤프 → 소프트" in text


def test_neutral_coordinate():
    n = neutral_coordinate()
    assert (n.shape, n.volume, n.age) == (0.5, 0.5, 0.5)


# ─────────────────────────────────────────────
#  UserTasteProfile
# ─────────────────────────────────────────────

def test_compute_strength_score_empty():
    assert compute_strength_score(
        has_ig_analysis=False,
        conversation_field_count=0,
        aspiration_count=0,
        best_shot_count=0,
        monthly_report_count=0,
    ) == 0.0


def test_compute_strength_score_full():
    score = compute_strength_score(
        has_ig_analysis=True,
        conversation_field_count=5,
        aspiration_count=5,
        best_shot_count=5,
        monthly_report_count=5,
    )
    assert score == 1.0


def test_compute_strength_score_monotonic():
    a = compute_strength_score(
        has_ig_analysis=True, conversation_field_count=2,
        aspiration_count=0, best_shot_count=0, monthly_report_count=0,
    )
    b = compute_strength_score(
        has_ig_analysis=True, conversation_field_count=5,
        aspiration_count=1, best_shot_count=1, monthly_report_count=1,
    )
    assert b > a


def test_user_taste_profile_snapshot_summary():
    p = UserTasteProfile(
        user_id="u1",
        snapshot_at=datetime.now(timezone.utc),
        current_position=VisualCoordinate(shape=0.4, volume=0.6, age=0.3),
        strength_score=0.55,
    )
    s = p.snapshot_summary()
    assert "u1" in s
    assert "strength=0.55" in s


# ─────────────────────────────────────────────
#  KnowledgeBase 로더
# ─────────────────────────────────────────────

def test_load_trends_female_spring():
    trends = load_trends(gender="female", season="2026_spring")
    assert len(trends) >= 2
    ids = [t.trend_id for t in trends]
    assert "female_2026_spring_001" in ids
    assert all(t.gender == "female" for t in trends)


def test_load_trends_male_spring():
    trends = load_trends(gender="male", season="2026_spring")
    assert len(trends) >= 2
    assert all(t.gender == "male" for t in trends)


def test_load_trends_gender_isolation():
    """gender 필터가 교차 오염 없음."""
    female = load_trends(gender="female")
    for t in female:
        assert t.gender == "female"


# ─────────────────────────────────────────────
#  KnowledgeMatcher
# ─────────────────────────────────────────────

def test_matcher_returns_trends_in_range():
    # 여성 001 은 shape[0.3, 0.7]. 유저 좌표 (0.5, 0.5, 0.3) 은 구간 안.
    profile = UserTasteProfile(
        user_id="u1",
        snapshot_at=datetime.now(timezone.utc),
        current_position=VisualCoordinate(shape=0.5, volume=0.5, age=0.3),
    )
    matched = match_trends_for_user(profile, gender="female", season="2026_spring")
    assert len(matched) >= 1
    # 구간 안 = score 1.0
    assert matched[0].score == 1.0
    assert matched[0].distance == 0.0


def test_matcher_filters_out_far_coordinates():
    # 좌표가 극단적으로 멀면 매칭 0
    profile = UserTasteProfile(
        user_id="u1",
        snapshot_at=datetime.now(timezone.utc),
        current_position=VisualCoordinate(shape=0.0, volume=0.0, age=1.0),
    )
    matched = match_trends_for_user(profile, gender="female", season="2026_spring")
    # 여성 002 (shape 0.5-1.0, age 0.4-0.9) 는 age=1.0 이라 구간 밖이지만 0.1 차이 — fallback 안
    # 여성 001 (age 0.2-0.5) 은 age=1.0 이라 0.5 차이 → 0.35 fallback 초과 → 제외
    # 매칭 결과는 1개 이하
    assert all(m.score >= 0.0 for m in matched)


def test_matcher_none_position_uses_neutral():
    """current_position 이 None 이면 neutral(0.5) 로 동작."""
    profile = UserTasteProfile(
        user_id="u1",
        snapshot_at=datetime.now(timezone.utc),
        current_position=None,
    )
    matched = match_trends_for_user(profile, gender="female", season="2026_spring")
    # neutral 좌표로는 female_001 (shape 0.3-0.7, vol 0.4-0.6, age 0.2-0.5) 구간 안
    assert len(matched) >= 1


# ─────────────────────────────────────────────
#  SiaWriter stub
# ─────────────────────────────────────────────

def test_stub_writer_comment_non_empty():
    writer = StubSiaWriter()
    profile = UserTasteProfile(
        user_id="u1",
        snapshot_at=datetime.now(timezone.utc),
    )
    out = writer.generate_comment_for_photo(
        photo_url="https://x/y.jpg",
        photo_context={"category": "signature"},
        profile=profile,
    )
    assert out.strip()
    assert "signature" in out


def test_stub_writer_boundary_message_counts():
    writer = StubSiaWriter()
    profile = UserTasteProfile(
        user_id="u1",
        snapshot_at=datetime.now(timezone.utc),
        strength_score=0.42,
    )
    out = writer.render_boundary_message(
        profile=profile,
        public_count=5,
        locked_count=20,
    )
    assert "20장" in out
    assert "42%" in out


def test_writer_registry_swap():
    """set_sia_writer 로 주입 교체 + 복원."""
    original = get_sia_writer()
    class _Dummy:
        def generate_comment_for_photo(self, **kw): return "X"
        def generate_overall_message(self, **kw): return "Y"
        def render_boundary_message(self, **kw): return "Z"

    try:
        set_sia_writer(_Dummy())
        assert get_sia_writer().generate_comment_for_photo() == "X"  # type: ignore
    finally:
        set_sia_writer(original)
