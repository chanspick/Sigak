"""Phase I — Backward echo 단위 테스트 (인스턴스 PI-E).

PI 결과 (pi_history) → 4 기능 prompt 흘림 검증:
  - append_history(category="pi_history") → user_history.pi_history + trajectory_events
  - history_injector._render_pi → 4 기능 prompt 마크다운 (상품명 직접 호명 금지)
  - sia_prompts_v4._format_vault_history_block PI echo (Sia 재대화)
  - vault.get_user_taste_profile().latest_pi (Aspiration / sia_writer carry)
  - sia_writer._render_taste_profile_slim 에 latest_pi 키 dump
  - 빈 PI 첫 진입 회귀 0

raw 격리: PiHistoryEntry 가 R2 raw 키 / sonnet_raw / haiku_raw / clip_embedding 미포함.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from schemas.user_history import (
    PiHistoryEntry,
    TrajectoryEvent,
    UserHistory,
)
from schemas.user_taste import UserTasteProfile
from services.history_injector import _render_pi, _compose_context
from services.sia_prompts_v4 import _format_vault_history_block
from services.sia_writer import _render_taste_profile_slim
from services.user_data_vault import UserDataVault, UserBasicInfo
from services.user_history import _build_trajectory_event


# ─────────────────────────────────────────────
#  Fixture helpers
# ─────────────────────────────────────────────

def _make_pi_entry(
    *,
    report_id: str = "pi_001",
    version: int = 1,
    matched_type: str = "Soft Fresh",
    cluster_label: str = "fresh-warm",
    coord_3axis: dict = None,
    top_celeb_name: str = "셀럽A",
    top_celeb_similarity: float = 0.78,
    top_hair_name: str = "C-curl 단발",
    top_action_text: str = "톤다운 + 컬러 스카프 추가",
) -> PiHistoryEntry:
    return PiHistoryEntry(
        report_id=report_id,
        version=version,
        created_at=datetime.now(timezone.utc),
        matched_type=matched_type,
        cluster_label=cluster_label,
        coord_3axis=coord_3axis or {"shape": 0.45, "volume": 0.55, "age": 0.30},
        top_celeb_name=top_celeb_name,
        top_celeb_similarity=top_celeb_similarity,
        top_hair_name=top_hair_name,
        top_action_text=top_action_text,
    )


# ─────────────────────────────────────────────
#  E1: schema
# ─────────────────────────────────────────────

def test_pi_history_entry_schema_minimal():
    """PiHistoryEntry 는 report_id 만 필수. 나머지는 Optional."""
    entry = PiHistoryEntry(report_id="pi_x")
    assert entry.report_id == "pi_x"
    assert entry.version == 1
    assert entry.matched_type is None
    assert entry.coord_3axis is None


def test_pi_history_entry_no_raw_fields():
    """raw 격리 — PiHistoryEntry 가 r2_/raw 키 미포함 검증."""
    entry = _make_pi_entry()
    dump = entry.model_dump(mode="json")
    forbidden_keys = {
        "r2_sonnet_raw_key", "r2_haiku_raw_key", "r2_clip_embedding_key",
        "sonnet_raw", "haiku_raw", "clip_embedding", "face_metrics",
        "matched_celebs", "matched_types", "vault_snapshot",
    }
    assert not (forbidden_keys & set(dump.keys())), (
        f"PiHistoryEntry 에 raw 영역 키가 노출됨: {forbidden_keys & set(dump.keys())}"
    )


def test_user_history_pi_history_default_empty():
    """첫 진입 유저 회귀 — UserHistory.pi_history default = []."""
    h = UserHistory()
    assert h.pi_history == []
    assert h.trajectory_events == []


# ─────────────────────────────────────────────
#  E2: _build_trajectory_event pi 매핑
# ─────────────────────────────────────────────

def test_trajectory_event_pi_extracts_coord():
    """PI append 시 trajectory event 에 coord_3axis 추출됨."""
    entry_dict = _make_pi_entry().model_dump(mode="json")
    ev = _build_trajectory_event("pi_history", entry_dict)
    assert ev is not None
    assert ev["event_type"] == "pi"
    assert ev["reference_id"] == "pi_001"
    snap = ev["coordinate_snapshot"]
    assert snap == {"shape": 0.45, "volume": 0.55, "age": 0.30}


def test_trajectory_event_pi_no_coord():
    """coord_3axis 없는 PI entry → coordinate_snapshot=None."""
    entry_dict = _make_pi_entry(coord_3axis=None).model_dump(mode="json")
    # coord_3axis 명시 None 으로 강제
    entry_dict["coord_3axis"] = None
    ev = _build_trajectory_event("pi_history", entry_dict)
    assert ev is not None
    assert ev["event_type"] == "pi"
    assert ev["coordinate_snapshot"] is None


def test_trajectory_event_pi_invalid_category():
    """잘못된 category 는 None."""
    ev = _build_trajectory_event("unknown_category", {"x": 1})
    assert ev is None


# ─────────────────────────────────────────────
#  E3: history_injector._render_pi
# ─────────────────────────────────────────────

def test_render_pi_basic_contents():
    """matched_type / cluster_label / 본질 좌표 / 셀럽 / 헤어 / 액션 모두 echo."""
    entry = _make_pi_entry().model_dump(mode="json")
    out = _render_pi([entry], mode="full")
    assert "본인 정밀 분석 이력" in out         # 헤더 우회 표현
    assert "Soft Fresh" in out
    assert "fresh-warm" in out
    assert "셀럽A" in out
    assert "C-curl 단발" in out
    assert "톤다운" in out


def test_render_pi_no_product_name_leak():
    """상품명 직접 호명 금지 — PI / 시각이 본 당신 / pi_reports 등 표기 X."""
    entry = _make_pi_entry().model_dump(mode="json")
    out = _render_pi([entry], mode="full")
    forbidden = ["PI", "시각이 본 당신", "pi_reports", "report_id"]
    for f in forbidden:
        assert f not in out, f"상품명 호명 발견: {f}"


def test_render_pi_summary_mode_minimal():
    """summary mode — matched_type + cluster_label 만 (좌표/셀럽 등 미노출)."""
    entry = _make_pi_entry().model_dump(mode="json")
    out = _render_pi([entry], mode="summary")
    assert "Soft Fresh" in out
    # summary 에서는 좌표 / 셀럽 / 헤어 / 액션 미노출
    assert "셀럽A" not in out
    assert "C-curl" not in out
    assert "톤다운" not in out


def test_compose_context_includes_pi_history():
    """_compose_context 가 pi_history 카테고리 분기 처리."""
    raw = {
        "pi_history": [_make_pi_entry().model_dump(mode="json")],
    }
    out = _compose_context(raw, ["pi_history"], max_per_type=1, mode="full")
    assert "본인 정밀 분석 이력" in out
    assert "Soft Fresh" in out


# ─────────────────────────────────────────────
#  E4: sia_prompts_v4 vault_history_block PI echo
# ─────────────────────────────────────────────

def test_sia_vault_block_includes_pi_count_and_type():
    """Sia vault block 에 pi_history N회 + matched_type 우회 echo."""
    history = UserHistory(pi_history=[_make_pi_entry()])
    block = _format_vault_history_block(history, None)
    assert "정밀 분석 1회" in block          # 우회 표현
    assert "Soft Fresh" in block             # matched_type
    assert "fresh-warm" in block             # cluster_label
    assert "셀럽A" in block                  # top_celeb_name
    # 상품명 직접 호명 금지
    assert "PI " not in block
    assert "시각이 본 당신" not in block


def test_sia_vault_block_empty_pi_returns_empty():
    """빈 history (PI 포함) — 첫 진입 유저 회귀 0."""
    history = UserHistory()  # 모든 list 빈
    block = _format_vault_history_block(history, None)
    assert block == ""


def test_sia_vault_block_only_pi_no_other_history():
    """PI 만 있고 다른 4 카테고리 빈 — block 정상 생성."""
    history = UserHistory(pi_history=[_make_pi_entry()])
    block = _format_vault_history_block(history, None)
    assert block != ""
    assert "정밀 분석 1회" in block


# ─────────────────────────────────────────────
#  E5/E10: sia_writer._render_taste_profile_slim latest_pi 키
# ─────────────────────────────────────────────

def test_sia_writer_slim_dumps_latest_pi():
    """sia_writer._render_taste_profile_slim 에 latest_pi 키가 존재 + dump 됨."""
    profile = UserTasteProfile(
        user_id="u1",
        snapshot_at=datetime.now(timezone.utc),
        latest_pi=_make_pi_entry(),
    )
    slim = _render_taste_profile_slim(profile)
    assert "latest_pi" in slim
    assert slim["latest_pi"] is not None
    assert slim["latest_pi"]["matched_type"] == "Soft Fresh"
    assert slim["latest_pi"]["top_action_text"] == "톤다운 + 컬러 스카프 추가"


def test_sia_writer_slim_latest_pi_none_safe():
    """latest_pi=None 시 dump 도 None — 첫 진입 회귀 0."""
    profile = UserTasteProfile(
        user_id="u1",
        snapshot_at=datetime.now(timezone.utc),
        latest_pi=None,
    )
    slim = _render_taste_profile_slim(profile)
    assert "latest_pi" in slim
    assert slim["latest_pi"] is None


# ─────────────────────────────────────────────
#  vault.get_user_taste_profile latest_pi 추출
# ─────────────────────────────────────────────

def test_vault_compose_latest_pi_from_history():
    """vault.get_user_taste_profile() 가 user_history.pi_history[0] → latest_pi."""
    vault = UserDataVault(
        basic_info=UserBasicInfo(user_id="u1"),
        user_history=UserHistory(pi_history=[_make_pi_entry()]),
    )
    profile = vault.get_user_taste_profile()
    assert profile.latest_pi is not None
    assert profile.latest_pi.matched_type == "Soft Fresh"
    assert profile.latest_pi.top_celeb_name == "셀럽A"


def test_vault_compose_latest_pi_none_when_empty():
    """pi_history=[] 시 latest_pi=None."""
    vault = UserDataVault(
        basic_info=UserBasicInfo(user_id="u1"),
        user_history=UserHistory(),
    )
    profile = vault.get_user_taste_profile()
    assert profile.latest_pi is None


def test_vault_pi_history_property():
    """vault.pi_history property — UserHistory.pi_history 노출."""
    e1 = _make_pi_entry(report_id="pi_a")
    e2 = _make_pi_entry(report_id="pi_b", version=2)
    vault = UserDataVault(
        basic_info=UserBasicInfo(user_id="u1"),
        user_history=UserHistory(pi_history=[e1, e2]),
    )
    assert len(vault.pi_history) == 2
    assert vault.pi_history[0].report_id == "pi_a"
    assert vault.pi_history[1].version == 2


# ─────────────────────────────────────────────
#  E11/E12/E13: 4 엔진 prompt 직접 inject
# ─────────────────────────────────────────────

_PIL_AVAILABLE = True
try:
    import PIL  # noqa: F401
except ImportError:
    _PIL_AVAILABLE = False


@pytest.mark.skipif(
    not _PIL_AVAILABLE,
    reason="services.verdict_v2 imports PIL — env dependency",
)
def test_verdict_v2_pi_block_renders_coord_and_celeb():
    """verdict_v2._render_latest_pi_for_verdict — coord + celeb echo."""
    from services.verdict_v2 import _render_latest_pi_for_verdict
    profile = UserTasteProfile(
        user_id="u1",
        snapshot_at=datetime.now(timezone.utc),
        latest_pi=_make_pi_entry(),
    )
    block = _render_latest_pi_for_verdict(profile)
    assert "지난번 정밀 분석" in block        # 우회 표현
    assert "본질 좌표" in block
    assert "shape" in block and "0.45" in block
    assert "닮은꼴 셀럽" in block
    assert "셀럽A" in block
    assert "0.78" in block                     # similarity
    # 상품명 직접 호명 금지
    assert "PI" not in block
    assert "시각이 본 당신" not in block


@pytest.mark.skipif(
    not _PIL_AVAILABLE,
    reason="services.verdict_v2 imports PIL — env dependency",
)
def test_verdict_v2_pi_block_empty_profile_returns_empty():
    """taste_profile=None / latest_pi=None — 빈 string (회귀 0)."""
    from services.verdict_v2 import _render_latest_pi_for_verdict
    assert _render_latest_pi_for_verdict(None) == ""

    profile = UserTasteProfile(
        user_id="u1",
        snapshot_at=datetime.now(timezone.utc),
        latest_pi=None,
    )
    assert _render_latest_pi_for_verdict(profile) == ""


@pytest.mark.skipif(
    not _PIL_AVAILABLE,
    reason="services.verdict_v2 imports PIL — env dependency",
)
def test_verdict_v2_pi_block_partial_fields():
    """coord 만 있고 celeb 없음 / 또는 그 반대 — 가능한 필드만 echo."""
    from services.verdict_v2 import _render_latest_pi_for_verdict
    # coord 만
    profile = UserTasteProfile(
        user_id="u1",
        snapshot_at=datetime.now(timezone.utc),
        latest_pi=_make_pi_entry(top_celeb_name=None, top_celeb_similarity=None),
    )
    block = _render_latest_pi_for_verdict(profile)
    assert "본질 좌표" in block
    assert "닮은꼴" not in block

    # celeb 만 (coord 없음)
    profile2 = UserTasteProfile(
        user_id="u1",
        snapshot_at=datetime.now(timezone.utc),
        latest_pi=_make_pi_entry(coord_3axis=None),
    )
    # coord_3axis Optional[dict] 강제 None
    profile2.latest_pi.coord_3axis = None  # type: ignore
    block2 = _render_latest_pi_for_verdict(profile2)
    assert "본질 좌표" not in block2
    assert "닮은꼴 셀럽" in block2


def test_aspiration_common_pi_action_hint():
    """aspiration_common._render_taste_profile_for_aspiration — pi_action_hint 키."""
    from services.aspiration_common import _render_taste_profile_for_aspiration
    profile = UserTasteProfile(
        user_id="u1",
        snapshot_at=datetime.now(timezone.utc),
        latest_pi=_make_pi_entry(),
    )
    out = _render_taste_profile_for_aspiration(profile)
    assert "pi_action_hint" in out
    assert "지난번 정밀 분석" in out["pi_action_hint"]
    assert "톤다운" in out["pi_action_hint"]


def test_aspiration_common_pi_action_hint_none_safe():
    """latest_pi=None 시 pi_action_hint 키 미추가 (회귀 0)."""
    from services.aspiration_common import _render_taste_profile_for_aspiration
    profile = UserTasteProfile(
        user_id="u1",
        snapshot_at=datetime.now(timezone.utc),
        latest_pi=None,
    )
    out = _render_taste_profile_for_aspiration(profile)
    assert "pi_action_hint" not in out


def test_aspiration_common_pi_action_hint_empty_action():
    """latest_pi.top_action_text 빈 string 시 키 미추가."""
    from services.aspiration_common import _render_taste_profile_for_aspiration
    profile = UserTasteProfile(
        user_id="u1",
        snapshot_at=datetime.now(timezone.utc),
        latest_pi=_make_pi_entry(top_action_text=""),
    )
    out = _render_taste_profile_for_aspiration(profile)
    assert "pi_action_hint" not in out
