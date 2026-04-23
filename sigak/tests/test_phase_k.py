"""Phase K — Best Shot 테스트.

범위:
  - 품질 heuristic (blur/exposure/size) 경계값 + 배치 필터
  - R2 client local fallback put/get/delete
  - cost_monitor in-memory 경로
  - run_best_shot pipeline (Sonnet mock)
  - 엔진 실패 3종 — cost cap / engine error / few photos

실 Sonnet / R2 호출 0 — monkey-patch + local fallback.
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schemas.user_taste import UserTasteProfile
from services import best_shot_engine, best_shot_quality
from services import cost_monitor
from services import r2_client
from services.best_shot_engine import BestShotEngineError
from services.best_shot_quality import score_photo, filter_top_n
from services.coordinate_system import VisualCoordinate


# ─────────────────────────────────────────────
#  Pillow helper — 테스트 이미지 생성
# ─────────────────────────────────────────────

def _make_jpeg(
    *,
    size: tuple[int, int] = (1080, 1080),
    color: tuple[int, int, int] = (120, 120, 120),
    noise: bool = True,
) -> bytes:
    """정상 이미지 1장 bytes. noise=True 면 blur 점수 높아짐."""
    img = Image.new("RGB", size, color)
    if noise:
        # 간단 체커보드 패턴으로 edge 생성
        pixels = img.load()
        step = 20
        for x in range(0, size[0], step):
            for y in range(0, size[1], step):
                if (x // step + y // step) % 2:
                    pixels[x, y] = (min(color[0] + 80, 255),) * 3
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _make_blurry_small() -> bytes:
    """blur + small — heuristic 컷오프 미달."""
    img = Image.new("RGB", (200, 200), (80, 80, 80))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=70)
    return buf.getvalue()


# ─────────────────────────────────────────────
#  Fixtures — settings 격리
# ─────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_state():
    import config as config_module
    config_module._settings = None
    r2_client.reset_client()
    cost_monitor.reset_local_counter()
    yield
    config_module._settings = None
    r2_client.reset_client()
    cost_monitor.reset_local_counter()


def _set_settings(**overrides):
    import config as config_module
    config_module._settings = config_module.Settings(**overrides)


# ─────────────────────────────────────────────
#  Quality heuristic
# ─────────────────────────────────────────────

def test_score_photo_clean_image_passes_cutoff():
    data = _make_jpeg()
    result = score_photo(data, cutoff=0.35)
    assert result is not None
    assert result.passed
    assert result.quality_score >= 0.35


def test_score_photo_tiny_image_fails_size_gate():
    data = _make_blurry_small()
    result = score_photo(data, cutoff=0.35)
    assert result is not None
    assert result.size_score == 0.0
    # blur/exposure 도 낮을 것 → 최종 fail
    assert result.quality_score < 0.35 or result.passed is False


def test_score_photo_garbage_bytes_returns_none():
    result = score_photo(b"not-an-image", cutoff=0.35)
    assert result is None


def test_filter_top_n_sorts_by_quality_and_caps():
    """5 장 중 3 장 상한 — 품질 순 상위 3만 통과."""
    items = [
        ("p0", _make_jpeg(size=(1080, 1080))),   # 통과
        ("p1", _make_blurry_small()),             # 실패
        ("p2", _make_jpeg(size=(1200, 1200))),   # 통과
        ("p3", _make_jpeg(size=(800, 800))),     # 약간
        ("p4", _make_blurry_small()),             # 실패
    ]
    top = filter_top_n(items, max_count=3, cutoff=0.35)
    assert 1 <= len(top) <= 3
    # 품질 score 내림차순 정렬
    scores = [t[2].quality_score for t in top]
    assert scores == sorted(scores, reverse=True)


# ─────────────────────────────────────────────
#  R2 client — local fallback
# ─────────────────────────────────────────────

def test_r2_local_fallback_put_get_roundtrip(tmp_path):
    _set_settings(r2_local_fallback_dir=str(tmp_path))
    assert r2_client.get_client_mode() == "local"
    key = "users/u1/best_shot/uploads/s1/p1.jpg"
    r2_client.put_bytes(key, b"hello", content_type="image/jpeg")
    assert r2_client.exists(key)
    assert r2_client.get_bytes(key) == b"hello"


def test_r2_delete_prefix_removes_children(tmp_path):
    _set_settings(r2_local_fallback_dir=str(tmp_path))
    r2_client.put_bytes("users/u1/best_shot/uploads/s1/a.jpg", b"x")
    r2_client.put_bytes("users/u1/best_shot/uploads/s1/b.jpg", b"y")
    r2_client.put_bytes("users/u1/other/z.jpg", b"z")
    deleted = r2_client.delete_prefix("users/u1/best_shot/uploads/s1/")
    assert deleted == 2
    assert not r2_client.exists("users/u1/best_shot/uploads/s1/a.jpg")
    assert r2_client.exists("users/u1/other/z.jpg")   # 범위 밖 유지


def test_r2_get_missing_raises(tmp_path):
    _set_settings(r2_local_fallback_dir=str(tmp_path))
    with pytest.raises(r2_client.R2Error):
        r2_client.get_bytes("users/u1/nonexistent.jpg")


# ─────────────────────────────────────────────
#  cost_monitor
# ─────────────────────────────────────────────

def test_cost_monitor_basic_accumulation():
    total = cost_monitor.check_and_reserve(
        resource="best_shot_sonnet",
        estimated_cost_usd=0.20,
        daily_cap_usd=1.0,
    )
    assert total == pytest.approx(0.20)
    total2 = cost_monitor.check_and_reserve(
        resource="best_shot_sonnet",
        estimated_cost_usd=0.30,
        daily_cap_usd=1.0,
    )
    assert total2 == pytest.approx(0.50)


def test_cost_monitor_exceeds_cap_raises():
    cost_monitor.check_and_reserve(
        resource="bucket_a", estimated_cost_usd=0.8, daily_cap_usd=1.0,
    )
    with pytest.raises(cost_monitor.CostLimitExceeded):
        cost_monitor.check_and_reserve(
            resource="bucket_a", estimated_cost_usd=0.3, daily_cap_usd=1.0,
        )


def test_cost_monitor_isolation_across_resources():
    cost_monitor.check_and_reserve(
        resource="A", estimated_cost_usd=0.9, daily_cap_usd=1.0,
    )
    # B 는 독립 bucket — 고도 예약 가능
    cost_monitor.check_and_reserve(
        resource="B", estimated_cost_usd=0.9, daily_cap_usd=1.0,
    )


# ─────────────────────────────────────────────
#  run_best_shot — pipeline mock
# ─────────────────────────────────────────────

def _mock_profile(strength: float = 0.5) -> UserTasteProfile:
    return UserTasteProfile(
        user_id="u1",
        snapshot_at=datetime.now(timezone.utc),
        current_position=VisualCoordinate(shape=0.5, volume=0.5, age=0.5),
        strength_score=strength,
    )


def _seed_r2_uploads(tmp_path: Path, user_id: str, session_id: str, n: int) -> list[str]:
    """R2 local fallback 에 n 장 업로드 시뮬레이션. 반환: key list."""
    _set_settings(r2_local_fallback_dir=str(tmp_path))
    keys = []
    for i in range(n):
        photo_id = f"{i:04d}.jpg"
        key = r2_client.best_shot_upload_key(user_id, session_id, photo_id)
        r2_client.put_bytes(key, _make_jpeg(), content_type="image/jpeg")
        keys.append(key)
    return keys


def test_run_best_shot_happy_path(monkeypatch, tmp_path):
    user_id, session_id = "u1", "s1"
    keys = _seed_r2_uploads(tmp_path, user_id, session_id, n=60)

    # Sonnet mock — target=4, max=6 (60 // 15=4, 60 // 10=6) 범위 가정
    def _fake_call(**kwargs):
        # candidates 리스트 중 0..3 선택
        return [
            {
                "rank": i + 1,
                "photo_index": i,
                "profile_match_score": 0.8,
                "trend_match_score": 0.7,
                "associated_trend_id": None,
                "rationale": "정돈된 톤이 일관됩니다.",
            }
            for i in range(4)
        ]
    monkeypatch.setattr(best_shot_engine, "_call_sonnet_select", _fake_call)

    result = best_shot_engine.run_best_shot(
        user_id=user_id,
        session_id=session_id,
        uploaded_photo_keys=keys,
        profile=_mock_profile(0.6),
        gender="female",
    )
    assert result.target_count == 4
    assert result.max_count == 6
    assert len(result.selected_photos) == 4
    assert result.selected_photos[0].rank == 1
    # selected/ 쪽에 사진 복사됐는지
    assert r2_client.exists(
        r2_client.best_shot_selected_key(
            user_id, session_id, result.selected_photos[0].photo_id,
        )
    )


def test_run_best_shot_too_few_raises(tmp_path):
    user_id, session_id = "u2", "s2"
    keys = _seed_r2_uploads(tmp_path, user_id, session_id, n=10)
    with pytest.raises(BestShotEngineError):
        best_shot_engine.run_best_shot(
            user_id=user_id, session_id=session_id,
            uploaded_photo_keys=keys,
            profile=_mock_profile(),
            gender="female",
        )


def test_run_best_shot_sonnet_empty_raises(monkeypatch, tmp_path):
    user_id, session_id = "u3", "s3"
    keys = _seed_r2_uploads(tmp_path, user_id, session_id, n=60)

    def _fake(**kwargs):
        raise BestShotEngineError("sonnet returned empty")
    monkeypatch.setattr(best_shot_engine, "_call_sonnet_select", _fake)

    with pytest.raises(BestShotEngineError):
        best_shot_engine.run_best_shot(
            user_id=user_id, session_id=session_id,
            uploaded_photo_keys=keys,
            profile=_mock_profile(),
            gender="female",
        )


def test_run_best_shot_cost_cap_blocks(monkeypatch, tmp_path):
    """일일 cost cap 초과 시 CostLimitExceeded → caller 가 refund."""
    user_id, session_id = "u4", "s4"
    keys = _seed_r2_uploads(tmp_path, user_id, session_id, n=60)

    # 이미 cap 근접 상태로 조작
    cost_monitor.check_and_reserve(
        resource="best_shot_sonnet",
        estimated_cost_usd=19.95,
        daily_cap_usd=20.0,
    )
    # 이 호출이 cap 초과 → raise
    with pytest.raises(cost_monitor.CostLimitExceeded):
        best_shot_engine.run_best_shot(
            user_id=user_id, session_id=session_id,
            uploaded_photo_keys=keys,
            profile=_mock_profile(),
            gender="female",
        )
