"""Phase H-lite: load_vault 좌표 fallback 검증.

목표:
  Sia 가 structured_fields["coordinate"] 를 아직 산출하지 않는 MVP 단계에서,
  IG Vision analysis 가 있으면 derive_coordinate_from_analysis 로 fallback
  좌표가 주입돼서 current_position 이 None 이 아니어야 한다.

CLAUDE.md 준수 확인:
  - coordinate_system.py / _compose_current_position / derive_coordinate_from_analysis
    본체 수정 X
  - load_vault 의 structured_fields 주입 레이어만 추가
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from services import user_data_vault as vault_mod


# ─────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────

def _ig_analysis_dict(tone: str = "쿨뮤트") -> dict:
    """IgFeedAnalysis 로 model_validate 가능한 최소 JSON."""
    return {
        "tone_category": tone,
        "tone_percentage": 68,
        "saturation_trend": "안정",
        "environment": "실내 자연광 위주",
        "pose_frequency": "정면 > 측면",
        "observed_adjectives": ["차분한", "정돈된"],
        "style_consistency": 0.7,
        "mood_signal": "차분한 톤이 일관돼요.",
        "three_month_shift": None,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }


def _profile(
    *,
    structured_fields: dict | None = None,
    ig_feed_cache: dict | None = None,
    gender: str = "female",
) -> dict:
    return {
        "gender": gender,
        "birth_date": None,
        "ig_handle": "user1",
        "ig_feed_cache": ig_feed_cache,
        "structured_fields": structured_fields or {},
    }


class _FakeDb:
    """get_profile 만 monkeypatch 하므로 db 는 truthy object 면 됨."""
    pass


# ─────────────────────────────────────────────
#  fallback injection
# ─────────────────────────────────────────────

def test_fallback_injects_when_coordinate_missing_and_ig_analysis_present(monkeypatch):
    profile = _profile(
        structured_fields={"body_shape": "평균"},   # coordinate 없음
        ig_feed_cache={"analysis": _ig_analysis_dict(tone="쿨뮤트")},
    )
    monkeypatch.setattr(vault_mod, "get_profile", lambda db, uid: profile)
    monkeypatch.setattr(
        vault_mod, "_fetch_product_counts", lambda db, uid: {},
    )

    vault = vault_mod.load_vault(_FakeDb(), "u1")
    assert vault is not None

    # structured_fields 에 coordinate 주입됐는지
    coord = vault.structured_fields.get("coordinate")
    assert isinstance(coord, dict)
    assert 0.0 <= coord["shape"] <= 1.0
    assert 0.0 <= coord["volume"] <= 1.0
    assert 0.0 <= coord["age"] <= 1.0
    assert coord.get("source") == "ig_analysis_fallback"

    # 쿨뮤트는 shape 살짝 샤프 쪽 (0.5 이상)
    assert coord["shape"] >= 0.5

    # _compose_current_position 도 None 이 아니게 됨
    position = vault._compose_current_position()
    assert position is not None
    assert position.shape == coord["shape"]


def test_fallback_skipped_when_explicit_coordinate_present(monkeypatch):
    explicit = {"shape": 0.2, "volume": 0.3, "age": 0.4}
    profile = _profile(
        structured_fields={"coordinate": explicit},
        ig_feed_cache={"analysis": _ig_analysis_dict(tone="쿨뮤트")},
    )
    monkeypatch.setattr(vault_mod, "get_profile", lambda db, uid: profile)
    monkeypatch.setattr(vault_mod, "_fetch_product_counts", lambda db, uid: {})

    vault = vault_mod.load_vault(_FakeDb(), "u1")
    assert vault is not None

    coord = vault.structured_fields["coordinate"]
    assert coord["shape"] == 0.2
    assert coord["volume"] == 0.3
    assert coord["age"] == 0.4
    # fallback 마커 없음 — 명시값이 온전히 보존돼야 함
    assert coord.get("source") != "ig_analysis_fallback"


def test_fallback_skipped_when_no_ig_analysis(monkeypatch):
    profile = _profile(
        structured_fields={"body_shape": "평균"},
        ig_feed_cache=None,
    )
    monkeypatch.setattr(vault_mod, "get_profile", lambda db, uid: profile)
    monkeypatch.setattr(vault_mod, "_fetch_product_counts", lambda db, uid: {})

    vault = vault_mod.load_vault(_FakeDb(), "u1")
    assert vault is not None
    assert "coordinate" not in vault.structured_fields
    assert vault._compose_current_position() is None


def test_fallback_skipped_when_ig_cache_missing_analysis_key(monkeypatch):
    # scope=public_profile_only 등 — analysis None
    profile = _profile(
        structured_fields={},
        ig_feed_cache={"scope": "public_profile_only", "profile_basics": {}},
    )
    monkeypatch.setattr(vault_mod, "get_profile", lambda db, uid: profile)
    monkeypatch.setattr(vault_mod, "_fetch_product_counts", lambda db, uid: {})

    vault = vault_mod.load_vault(_FakeDb(), "u1")
    assert vault is not None
    assert "coordinate" not in vault.structured_fields


def test_fallback_silently_degrades_on_malformed_analysis(monkeypatch):
    # analysis 가 schema 불일치 — IgFeedAnalysis.model_validate 실패해야 함
    bad_analysis = {"tone_category": "invalid_tone", "tone_percentage": "not_a_number"}
    profile = _profile(
        structured_fields={},
        ig_feed_cache={"analysis": bad_analysis},
    )
    monkeypatch.setattr(vault_mod, "get_profile", lambda db, uid: profile)
    monkeypatch.setattr(vault_mod, "_fetch_product_counts", lambda db, uid: {})

    # 예외 흡수 — vault 조립 성공해야 함
    vault = vault_mod.load_vault(_FakeDb(), "u1")
    assert vault is not None
    # 잘못된 analysis 는 fallback 주입 못함 — coordinate 없이 그냥 지나감
    assert "coordinate" not in vault.structured_fields


def test_user_taste_profile_has_nonnull_current_position_with_fallback(monkeypatch):
    """E2E — UserTasteProfile.current_position 이 fallback 덕분에 non-None."""
    profile = _profile(
        structured_fields={},
        ig_feed_cache={"analysis": _ig_analysis_dict(tone="웜비비드")},
    )
    monkeypatch.setattr(vault_mod, "get_profile", lambda db, uid: profile)
    monkeypatch.setattr(vault_mod, "_fetch_product_counts", lambda db, uid: {})

    vault = vault_mod.load_vault(_FakeDb(), "u1")
    assert vault is not None
    tp = vault.get_user_taste_profile()
    assert tp.current_position is not None
    # 웜비비드는 살짝 소프트 (shape < 0.5) + 프레시 (age < 0.5)
    assert tp.current_position.shape <= 0.5
    assert tp.current_position.age <= 0.5
