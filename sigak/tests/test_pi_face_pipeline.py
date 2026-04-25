"""PI-B — pi_face_pipeline 통합 테스트.

CLIP / InsightFace 런타임 회피 — 모든 외부 의존을 monkeypatch.
PI-A 인터페이스 spec (2026-04-25) 정합 검증 포함.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest


sys.path.insert(0, str(Path(__file__).parent.parent))


# ─────────────────────────────────────────────
#  공용 helpers
# ─────────────────────────────────────────────

def _unit_vec(seed: int, dim: int = 768) -> np.ndarray:
    rng = np.random.RandomState(seed)
    v = rng.randn(dim).astype(np.float32)
    return v / (float(np.linalg.norm(v)) + 1e-12)


def _fake_face_features():
    """face.py FaceFeatures 와 호환되는 stub.

    PI-A 스펙 18 numeric key + face_shape + 기타 (skin_tone 등) 포함 — 필터 후
    face_features 에는 18개만 남아야 함 (검증 대상).
    """
    metrics = {
        # 18 PI-A keys
        "jaw_angle": 110.0,
        "cheekbone_prominence": 0.55,
        "eye_width_ratio": 0.184,
        "eye_spacing_ratio": 0.34,
        "eye_ratio": 0.32,
        "eye_tilt": 3.0,
        "nose_length_ratio": 0.42,
        "nose_width_ratio": 0.27,
        "nose_bridge_height": 0.49,
        "lip_fullness": 0.09,
        "forehead_ratio": 0.44,
        "brow_arch": 0.029,
        "philtrum_ratio": 0.22,
        "symmetry_score": 0.95,
        "golden_ratio_score": 0.78,
        "skin_brightness": 0.6,
        "skin_warmth_score": 1.5,
        "face_length_ratio": 1.30,
        # PI-A 가 face_features 에서 배제하는 categorical / extras
        "face_shape": "oval",
        "skin_tone": "warm",
        "skin_chroma": 12.0,
        "skin_hex_sample": "#D4A574",
        "personal_color": None,
        "brow_eye_distance": 0.022,
    }

    class _StubFace:
        def to_dict(self):
            return dict(metrics)

        landmarks = [[0.3, 0.3], [0.7, 0.7]]
        landmarks_106 = [[100, 100], [200, 200]]
        bbox = [50, 50, 250, 250]

    return _StubFace()


@pytest.fixture
def patched_pipeline(monkeypatch):
    """face / CLIP / R2 / similarity / coordinate 전부 monkeypatch."""
    from services import pi_face_pipeline

    fake_face = _fake_face_features()

    # face.py
    import pipeline.face
    monkeypatch.setattr(pipeline.face, "analyze_face", lambda b: fake_face)

    # CLIPEmbedder
    class _FakeEmbedder:
        def extract(self, image, bbox=None):
            return _unit_vec(123)

    import pipeline.clip
    monkeypatch.setattr(pipeline.clip, "CLIPEmbedder", _FakeEmbedder)
    monkeypatch.setattr(
        pipeline.clip, "crop_face",
        lambda image, landmarks, padding=0.3: image,
    )

    # similarity — find_similar_types 가 type_1 (실 type_anchors.json 에 존재) 반환
    import pipeline.similarity
    monkeypatch.setattr(
        pipeline.similarity, "find_similar_types",
        lambda **kw: [
            {
                "key": "type_1", "name_kr": "따뜻한 첫사랑",
                "similarity": 0.85, "similarity_pct": 92,
                "mode": "clip",
                "axis_delta": {"shape": 0.1, "volume": 0.05, "age": -0.02},
            }
        ],
    )

    # celeb_similarity — CelebMatch 반환
    from pipeline.celeb_similarity import CelebMatch
    import pipeline.celeb_similarity
    monkeypatch.setattr(
        pipeline.celeb_similarity, "find_similar_celebs",
        lambda **kw: [
            CelebMatch(
                key="jang_wonyoung", name_kr="장원영", name_en="Jang Wonyoung",
                group="IVE", similarity=0.78, similarity_pct=89,
            )
        ],
    )

    # coordinate — internal -1~+1 산출
    import pipeline.coordinate
    monkeypatch.setattr(
        pipeline.coordinate, "compute_coordinates",
        lambda features, gender="female", **kw: {
            "shape": 0.21, "volume": -0.13, "age": 0.05,
        },
    )

    # R2 client
    import services.r2_client
    monkeypatch.setattr(
        services.r2_client, "user_photo_key",
        lambda uid, suffix: f"users/{uid}/{suffix}",
    )
    monkeypatch.setattr(
        services.r2_client, "put_bytes",
        lambda key, body, content_type=None: None,
    )

    return pi_face_pipeline


# ─────────────────────────────────────────────
#  Happy path — PI-A spec 정합
# ─────────────────────────────────────────────

def test_analyze_baseline_photo_full_pipeline(patched_pipeline):
    photo_bytes = _make_dummy_jpeg()

    result = patched_pipeline.analyze_baseline_photo(
        photo_bytes,
        gender="female",
        user_id="user_test_1",
        snapshot_ts="20260425T120000Z",
    )

    # 기본 필드
    assert result.user_id == "user_test_1"
    assert result.gender == "female"
    assert result.snapshot_ts == "20260425T120000Z"
    assert result.face_shape == "oval"

    # face_features = 18 numeric (FACE_FEATURE_KEYS subset, 카테고리/PII 제외)
    from services.pi_face_pipeline import FACE_FEATURE_KEYS
    assert set(result.face_features.keys()).issubset(set(FACE_FEATURE_KEYS))
    assert "jaw_angle" in result.face_features
    assert "lip_fullness" in result.face_features
    assert "skin_warmth_score" in result.face_features
    # 배제 검증
    assert "face_shape" not in result.face_features
    assert "skin_tone" not in result.face_features
    assert "skin_chroma" not in result.face_features
    assert "skin_hex_sample" not in result.face_features
    assert "brow_eye_distance" not in result.face_features
    assert "landmarks" not in result.face_features

    # coord_3axis = VisualCoordinate (0~1 외부)
    from services.coordinate_system import VisualCoordinate
    assert isinstance(result.coord_3axis, VisualCoordinate)
    assert 0.0 <= result.coord_3axis.shape <= 1.0
    assert 0.0 <= result.coord_3axis.volume <= 1.0
    assert 0.0 <= result.coord_3axis.age <= 1.0
    # 내부 0.21 → 외부 (0.21+1)/2 = 0.605
    assert abs(result.coord_3axis.shape - 0.605) < 1e-6
    # 내부 -0.13 → 외부 0.435
    assert abs(result.coord_3axis.volume - 0.435) < 1e-6

    # CLIP 768d L2
    assert result.clip_embedding.shape == (768,)
    assert 0.99 < float(np.linalg.norm(result.clip_embedding)) < 1.01

    # matched_types — PI-A spec
    assert len(result.matched_types) == 1
    mt = result.matched_types[0]
    assert mt["type_id"] == 1                       # type_anchors.json 에서 lookup
    assert mt["name_kr"] == "따뜻한 첫사랑"
    assert mt["similarity"] == 0.85
    assert mt["rank"] == 1
    assert set(mt["coords"].keys()) == {"shape", "volume", "age"}
    assert all(0.0 <= v <= 1.0 for v in mt["coords"].values())   # 외부 스케일
    assert set(mt["delta_axis"].keys()) == {"shape", "volume", "age"}
    assert all(-1.0 <= v <= 1.0 for v in mt["delta_axis"].values())
    assert isinstance(mt["delta_note"], str)
    assert mt["delta_note"]                         # 빈 문자열 아님

    # matched_celebs — PI-A spec (3 keys only)
    assert len(result.matched_celebs) == 1
    mc = result.matched_celebs[0]
    assert mc["celeb_name"] == "장원영"
    assert mc["similarity"] == 0.78
    assert mc["rank"] == 1

    # R2 키
    assert result.baseline_photo_r2_key.endswith(".jpg")
    assert result.clip_embedding_r2_key.endswith(".npy")
    assert result.landmarks_r2_key.endswith(".json")


def test_matched_types_rank_starts_at_1(patched_pipeline, monkeypatch):
    """top-3 mock → rank 1/2/3 부여 검증."""
    import pipeline.similarity
    monkeypatch.setattr(
        pipeline.similarity, "find_similar_types",
        lambda **kw: [
            {"key": "type_1", "name_kr": "x", "similarity": 0.9,
             "axis_delta": {"shape": 0, "volume": 0, "age": 0}},
            {"key": "type_2", "name_kr": "y", "similarity": 0.8,
             "axis_delta": {"shape": 0.5, "volume": 0, "age": 0}},
            {"key": "type_4", "name_kr": "z", "similarity": 0.7,
             "axis_delta": {"shape": 0, "volume": 0.3, "age": 0}},
        ],
    )

    result = patched_pipeline.analyze_baseline_photo(
        _make_dummy_jpeg(),
        gender="female", user_id="u", persist_to_r2=False,
    )
    assert [t["rank"] for t in result.matched_types] == [1, 2, 3]


def test_matched_celebs_rank_starts_at_1(patched_pipeline, monkeypatch):
    from pipeline.celeb_similarity import CelebMatch
    import pipeline.celeb_similarity
    monkeypatch.setattr(
        pipeline.celeb_similarity, "find_similar_celebs",
        lambda **kw: [
            CelebMatch(key="a", name_kr="이름1", name_en="N1", group=None,
                       similarity=0.9, similarity_pct=95),
            CelebMatch(key="b", name_kr="이름2", name_en="N2", group=None,
                       similarity=0.8, similarity_pct=90),
        ],
    )

    result = patched_pipeline.analyze_baseline_photo(
        _make_dummy_jpeg(),
        gender="female", user_id="u", persist_to_r2=False,
    )
    ranks = [c["rank"] for c in result.matched_celebs]
    assert ranks == [1, 2]


def test_delta_note_for_near_zero_returns_거의일치(patched_pipeline, monkeypatch):
    """모든 delta < 0.05 → '거의 일치'."""
    import pipeline.similarity
    monkeypatch.setattr(
        pipeline.similarity, "find_similar_types",
        lambda **kw: [{
            "key": "type_1", "name_kr": "x", "similarity": 0.9,
            "axis_delta": {"shape": 0, "volume": 0, "age": 0},
        }],
    )
    # type_1 의 reference 좌표 (0.1, 0.15, 0.1) 외부 스케일 ~ user 와 가깝게 만들기
    # type_1 internal coords = (-0.8, -0.7, -0.8) → 외부 (0.1, 0.15, 0.1)
    # user_external 도 그 근처로 만들기 위해 coordinate mock 조정
    import pipeline.coordinate
    monkeypatch.setattr(
        pipeline.coordinate, "compute_coordinates",
        lambda features, gender="female", **kw: {
            # 내부 (-0.8, -0.7, -0.8) → 외부 (0.1, 0.15, 0.1) — type_1 과 거의 일치
            "shape": -0.8, "volume": -0.7, "age": -0.8,
        },
    )

    result = patched_pipeline.analyze_baseline_photo(
        _make_dummy_jpeg(),
        gender="female", user_id="u", persist_to_r2=False,
    )
    note = result.matched_types[0]["delta_note"]
    assert note == "거의 일치", f"got: {note!r}"


def test_persist_false_skips_r2(patched_pipeline):
    result = patched_pipeline.analyze_baseline_photo(
        _make_dummy_jpeg(),
        gender="female", user_id="u", persist_to_r2=False,
    )
    assert result.baseline_photo_r2_key is None
    assert result.clip_embedding_r2_key is None
    assert result.landmarks_r2_key is None


def test_to_prompt_safe_dict_excludes_embedding(patched_pipeline):
    result = patched_pipeline.analyze_baseline_photo(
        _make_dummy_jpeg(),
        gender="female", user_id="u", persist_to_r2=False,
    )
    safe = result.to_prompt_safe_dict()

    # PII 격리 — embedding 미노출
    assert "clip_embedding" not in safe
    assert "face_features" in safe
    assert "face_shape" in safe
    # coord_3axis 직렬화 (model_dump → dict)
    assert isinstance(safe["coord_3axis"], dict)
    assert set(safe["coord_3axis"].keys()) == {"shape", "volume", "age"}
    assert "matched_types" in safe
    assert "matched_celebs" in safe
    assert "r2_keys" in safe


# ─────────────────────────────────────────────
#  Error paths
# ─────────────────────────────────────────────

def test_invalid_image_raises(patched_pipeline):
    with pytest.raises(patched_pipeline.PIFaceError, match="image decode"):
        patched_pipeline.analyze_baseline_photo(
            b"", gender="female", user_id="u",
        )


def test_face_not_detected_raises(monkeypatch, patched_pipeline):
    import pipeline.face
    monkeypatch.setattr(pipeline.face, "analyze_face", lambda b: None)

    with pytest.raises(patched_pipeline.PIFaceError, match="face not detected"):
        patched_pipeline.analyze_baseline_photo(
            _make_dummy_jpeg(), gender="female", user_id="u",
        )


def test_clip_malformed_raises(monkeypatch, patched_pipeline):
    import pipeline.clip

    class _BadEmbedder:
        def extract(self, image, bbox=None):
            return np.zeros(256, dtype=np.float32)

    monkeypatch.setattr(pipeline.clip, "CLIPEmbedder", _BadEmbedder)

    with pytest.raises(patched_pipeline.PIFaceError, match="CLIP embedding malformed"):
        patched_pipeline.analyze_baseline_photo(
            _make_dummy_jpeg(), gender="female", user_id="u",
        )


def test_r2_failure_does_not_break_result(monkeypatch, patched_pipeline):
    """R2 put 실패 → r2_key None graceful degrade, 결과는 정상 반환."""
    import services.r2_client

    def _explode(key, body, content_type=None):
        raise RuntimeError("R2 down")

    monkeypatch.setattr(services.r2_client, "put_bytes", _explode)

    result = patched_pipeline.analyze_baseline_photo(
        _make_dummy_jpeg(), gender="female", user_id="u",
    )
    assert result.baseline_photo_r2_key is None
    assert result.clip_embedding_r2_key is None
    assert result.landmarks_r2_key is None
    assert result.coord_3axis is not None
    assert result.clip_embedding.shape == (768,)


def test_coordinate_config_error_propagates(monkeypatch, patched_pipeline):
    """미캘리브레이션 gender → CoordinateConfigError → PIFaceError."""
    import pipeline.coordinate

    def _raise(features, gender="female", **kw):
        raise pipeline.coordinate.CoordinateConfigError(
            f"observed_ranges.{gender} not found"
        )
    monkeypatch.setattr(pipeline.coordinate, "compute_coordinates", _raise)

    with pytest.raises(patched_pipeline.PIFaceError, match="coordinate config"):
        patched_pipeline.analyze_baseline_photo(
            _make_dummy_jpeg(), gender="female", user_id="u",
        )


# ─────────────────────────────────────────────
#  Snapshot ts
# ─────────────────────────────────────────────

def test_snapshot_ts_explicit_used_in_r2_keys(patched_pipeline):
    ts = "20260425T999999Z"
    result = patched_pipeline.analyze_baseline_photo(
        _make_dummy_jpeg(), gender="female", user_id="u", snapshot_ts=ts,
    )
    assert ts in result.baseline_photo_r2_key
    assert ts in result.clip_embedding_r2_key
    assert ts in result.landmarks_r2_key


def test_snapshot_ts_auto_when_omitted(patched_pipeline):
    result = patched_pipeline.analyze_baseline_photo(
        _make_dummy_jpeg(), gender="female", user_id="u",
    )
    assert len(result.snapshot_ts) == 16
    assert result.snapshot_ts.endswith("Z")


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _make_dummy_jpeg() -> bytes:
    import cv2
    img = np.full((64, 64, 3), 200, dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    return bytes(buf)
