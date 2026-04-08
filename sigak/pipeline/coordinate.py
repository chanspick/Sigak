"""
SIGAK Coordinate System — Structural Feature Projection

Core IP: Maps any face into an interpretable 4-axis aesthetic space
using structural facial features only (CLIP dependency removed).

Axes:
  1. Structure  — soft(-1) ↔ sharp(+1)   골격의 부드러움 vs 날카로움
  2. Impression — soft(-1) ↔ sharp(+1)    이목구비가 주는 인상
  3. Maturity   — fresh(-1) ↔ mature(+1)  생기 vs 성숙
  4. Intensity  — natural(-1) ↔ bold(+1)  존재감/Presence
"""
import numpy as np
from dataclasses import dataclass
from typing import Optional


# ─────────────────────────────────────────────
#  Axis Definitions
# ─────────────────────────────────────────────

@dataclass
class AxisDefinition:
    name: str
    name_kr: str
    negative_label: str    # -1 pole
    positive_label: str    # +1 pole
    negative_label_kr: str
    positive_label_kr: str

AXES = [
    AxisDefinition(
        name="structure",    name_kr="구조",
        negative_label="soft", positive_label="sharp",
        negative_label_kr="부드러운", positive_label_kr="날카로운",
    ),
    AxisDefinition(
        name="impression",   name_kr="인상",
        negative_label="soft", positive_label="sharp",
        negative_label_kr="부드러운", positive_label_kr="선명한",
    ),
    AxisDefinition(
        name="maturity",     name_kr="성숙도",
        negative_label="fresh", positive_label="mature",
        negative_label_kr="프레시", positive_label_kr="성숙한",
    ),
    AxisDefinition(
        name="intensity",    name_kr="존재감",
        negative_label="natural", positive_label="bold",
        negative_label_kr="자연스러운", positive_label_kr="볼드",
    ),
]


# ─────────────────────────────────────────────
#  Observed Ranges (F-0.5: FACE_STATS p10~p90 기반)
#  실측 샘플 확보 후 교체할 것
# ─────────────────────────────────────────────

OBSERVED_RANGES: dict[str, tuple[float, float]] = {
    "eye_tilt": (-2.0, 5.0),
    "brow_arch": (0.008, 0.022),
    "eye_ratio": (0.28, 0.42),
    "lip_fullness": (0.030, 0.060),
    "eye_width_ratio": (0.20, 0.28),
    "nose_bridge_height": (0.02, 0.08),
    "brow_eye_distance": (0.1, 0.4),  # optional, 미존재 시 skip
    # structure 축 전용
    "jaw_angle": (110.0, 150.0),
    "cheekbone_prominence": (0.1, 0.6),
    "face_length_ratio": (1.15, 1.55),
    # maturity 축 전용
    "forehead_ratio": (0.25, 0.45),
    "philtrum_ratio": (0.15, 0.30),
}


# ─────────────────────────────────────────────
#  Common Helpers
# ─────────────────────────────────────────────

def _has_valid(features: dict, key: str) -> bool:
    """feature가 존재하고 None이 아닌지 확인"""
    return key in features and features[key] is not None


def _normalize(value: float, observed_range: tuple[float, float]) -> float:
    """관측 범위 기반 정규화. 범위 밖 값은 clamp. → [-1, 1]"""
    lo, hi = observed_range
    if hi <= lo:
        return 0.0
    value = min(max(value, lo), hi)
    return (value - lo) / (hi - lo) * 2 - 1


def _weighted_fallback(components: list[tuple[float, float]]) -> float:
    """
    사용 가능한 component만으로 가중 평균.
    feature 미존재 시 나머지로 가중치 자동 재분배.
    """
    if not components:
        return 0.0
    weight_sum = sum(w for _, w in components)
    score = sum(v * w for v, w in components) / weight_sum
    return max(-1.0, min(1.0, score))


# ─────────────────────────────────────────────
#  Per-Axis Structural Score Functions
#  CLIP 의존도 0% — 전축 structural 100%
# ─────────────────────────────────────────────

def compute_structure(features: dict) -> float:
    """
    soft(-1) ↔ sharp(+1)
    턱선 각도 + 광대 돌출 + 얼굴 종횡비가 만드는 골격 인상.
    """
    components = []

    # 턱선 각도: 낮을수록 sharp
    if _has_valid(features, "jaw_angle"):
        val = -_normalize(features["jaw_angle"], OBSERVED_RANGES["jaw_angle"])
        components.append((val, 0.40))

    # 광대 돌출: 높을수록 sharp
    if _has_valid(features, "cheekbone_prominence"):
        val = _normalize(features["cheekbone_prominence"], OBSERVED_RANGES["cheekbone_prominence"])
        components.append((val, 0.30))

    # 얼굴 종횡비: 길수록 sharp
    if _has_valid(features, "face_length_ratio"):
        val = _normalize(features["face_length_ratio"], OBSERVED_RANGES["face_length_ratio"])
        components.append((val, 0.30))

    return _weighted_fallback(components)


def compute_impression(features: dict) -> float:
    """
    soft(-1) ↔ sharp(+1)
    눈매 방향성 + 눈썹 형태 + 눈 비율 + 입술 볼륨이 만드는 전체 인상.
    """
    components = []

    # 눈꼬리 각도: 올라갈수록 sharp
    if _has_valid(features, "eye_tilt"):
        val = _normalize(features["eye_tilt"], OBSERVED_RANGES["eye_tilt"])
        components.append((val, 0.35))

    # 눈썹 아치: 높을수록 sharp
    if _has_valid(features, "brow_arch"):
        val = _normalize(features["brow_arch"], OBSERVED_RANGES["brow_arch"])
        components.append((val, 0.25))

    # 눈 비율(높이/너비): 가로로 길수록(값이 작을수록) sharp
    if _has_valid(features, "eye_ratio"):
        raw = _normalize(features["eye_ratio"], OBSERVED_RANGES["eye_ratio"])
        val = -raw  # 반전: 작을수록 sharp
        components.append((val, 0.25))

    # 입술 두께: 도톰할수록 soft
    if _has_valid(features, "lip_fullness"):
        val = -_normalize(features["lip_fullness"], OBSERVED_RANGES["lip_fullness"])
        components.append((val, 0.15))

    return _weighted_fallback(components)


def compute_maturity(features: dict) -> float:
    """
    fresh(-1) ↔ mature(+1)
    이마/인중 비율 + 눈 크기가 만드는 연령감.
    """
    components = []

    # 이마 비율: 클수록 mature (넓은 이마 = 성숙한 인상)
    if _has_valid(features, "forehead_ratio"):
        val = _normalize(features["forehead_ratio"], OBSERVED_RANGES["forehead_ratio"])
        components.append((val, 0.35))

    # 인중 비율: 길수록 mature
    if _has_valid(features, "philtrum_ratio"):
        val = _normalize(features["philtrum_ratio"], OBSERVED_RANGES["philtrum_ratio"])
        components.append((val, 0.35))

    # 눈 크기: 작을수록 mature
    if _has_valid(features, "eye_width_ratio"):
        val = -_normalize(features["eye_width_ratio"], OBSERVED_RANGES["eye_width_ratio"])
        components.append((val, 0.30))

    return _weighted_fallback(components)


def compute_intensity(features: dict) -> float:
    """
    natural(-1) ↔ bold(+1)
    이목구비의 존재감. symmetry_score는 이 축에서 제외.
    """
    components = []

    # 눈 크기: 클수록 bold
    if _has_valid(features, "eye_width_ratio"):
        val = _normalize(features["eye_width_ratio"], OBSERVED_RANGES["eye_width_ratio"])
        components.append((val, 0.30))

    # 입술 두께: 도톰할수록 bold
    if _has_valid(features, "lip_fullness"):
        val = _normalize(features["lip_fullness"], OBSERVED_RANGES["lip_fullness"])
        components.append((val, 0.25))

    # 코 높이: 높을수록 bold
    if _has_valid(features, "nose_bridge_height"):
        val = _normalize(features["nose_bridge_height"], OBSERVED_RANGES["nose_bridge_height"])
        components.append((val, 0.25))

    # 눈-눈썹 거리: 가까울수록 bold (optional feature)
    if _has_valid(features, "brow_eye_distance"):
        val = -_normalize(features["brow_eye_distance"], OBSERVED_RANGES["brow_eye_distance"])
        components.append((val, 0.20))

    return _weighted_fallback(components)


# ─────────────────────────────────────────────
#  Combined Coordinate Computation
# ─────────────────────────────────────────────

def compute_coordinates(
    structural_features: dict,
    clip_embedding: Optional[np.ndarray] = None,
    projector=None,
) -> dict[str, float]:
    """
    Structural features → 4-axis coordinates.
    CLIP 의존 제거 완료 — clip_embedding/projector 파라미터는 하위 호환용.

    Returns: {"structure": 0.35, "impression": -0.22, "maturity": 0.1, "intensity": -0.45}
    """
    return {
        "structure": round(compute_structure(structural_features), 3),
        "impression": round(compute_impression(structural_features), 3),
        "maturity": round(compute_maturity(structural_features), 3),
        "intensity": round(compute_intensity(structural_features), 3),
    }


# ─────────────────────────────────────────────
#  Gap Calculation
# ─────────────────────────────────────────────

def compute_gap(
    current: dict[str, float],
    aspiration: dict[str, float],
) -> dict:
    """
    Compute the gap vector and derive actionable directions.

    Returns:
        {
            "vector": {"structure": -0.45, ...},
            "magnitude": 0.72,
            "primary_direction": "structure",
            "primary_shift": "sharp",
            "secondary_direction": "impression",
            "secondary_shift": "sharp",
        }
    """
    vector = {}
    for ax in AXES:
        vector[ax.name] = round(aspiration.get(ax.name, 0) - current.get(ax.name, 0), 3)

    # Overall gap magnitude
    magnitude = float(np.sqrt(sum(v**2 for v in vector.values())))

    # Find primary and secondary gap directions
    sorted_axes = sorted(vector.items(), key=lambda x: abs(x[1]), reverse=True)

    primary_name = sorted_axes[0][0]
    primary_val = sorted_axes[0][1]
    primary_ax = next(ax for ax in AXES if ax.name == primary_name)
    primary_shift = primary_ax.positive_label if primary_val > 0 else primary_ax.negative_label

    secondary_name = sorted_axes[1][0] if len(sorted_axes) > 1 else primary_name
    secondary_val = sorted_axes[1][1] if len(sorted_axes) > 1 else 0
    secondary_ax = next(ax for ax in AXES if ax.name == secondary_name)
    secondary_shift = secondary_ax.positive_label if secondary_val > 0 else secondary_ax.negative_label

    return {
        "vector": vector,
        "magnitude": round(magnitude, 3),
        "primary_direction": primary_name,
        "primary_shift": primary_shift,
        "primary_shift_kr": (primary_ax.positive_label_kr if primary_val > 0
                             else primary_ax.negative_label_kr),
        "secondary_direction": secondary_name,
        "secondary_shift": secondary_shift,
        "secondary_shift_kr": (secondary_ax.positive_label_kr if secondary_val > 0
                               else secondary_ax.negative_label_kr),
    }


# ─────────────────────────────────────────────
#  Legacy compatibility (CLIP 관련 — 하위 호환)
#  CLIP 정상화 후 점진적 복원을 위해 유지
# ─────────────────────────────────────────────

EMBEDDING_DIM = 768  # ViT-L-14 출력 차원


class AnchorProjector:
    """CLIP projector — 현재 미사용. 하위 호환용."""
    def __init__(self):
        self.anchor_vectors: dict[str, np.ndarray] = {}
        self._fitted = False

    def fit(self, anchors):
        self._fitted = True

    def project(self, embedding):
        return {ax.name: 0.0 for ax in AXES}


def mock_clip_embedding(image_bytes: bytes) -> np.ndarray:
    """WoZ phase mock — 좌표에 영향 없음."""
    import hashlib
    h = hashlib.sha256(image_bytes).digest()
    seed = int.from_bytes(h[:4], "big")
    rng = np.random.RandomState(seed)
    emb = rng.randn(EMBEDDING_DIM).astype(np.float32)
    return emb / (np.linalg.norm(emb) + 1e-8)


def mock_anchor_projector(gender: str = "female") -> AnchorProjector:
    """WoZ phase mock projector."""
    return AnchorProjector()


def load_anchor_projector(gender: str = "female") -> AnchorProjector:
    """하위 호환 — CLIP 비활성 상태에서는 빈 프로젝터 반환."""
    return AnchorProjector()
