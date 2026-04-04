"""
SIGAK Coordinate System — Aesthetic Anchor Projection

Core IP: Maps any face into an interpretable 4-axis aesthetic space
by projecting CLIP embeddings onto anchor-defined direction vectors.

Axes:
  1. Structure   — Sharp ↔ Soft    (structural features + CLIP)
  2. Impression   — Warm ↔ Cool     (CLIP dominant)
  3. Maturity     — Fresh ↔ Mature  (structural + CLIP)
  4. Intensity    — Natural ↔ Bold  (CLIP dominant)
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
    structural_weight: float  # 0–1: how much structural features contribute
    clip_weight: float        # 0–1: how much CLIP embedding contributes

AXES = [
    AxisDefinition(
        name="structure",    name_kr="구조",
        negative_label="sharp", positive_label="soft",
        negative_label_kr="날카로운", positive_label_kr="부드러운",
        structural_weight=0.6, clip_weight=0.4,
    ),
    AxisDefinition(
        name="impression",   name_kr="인상",
        negative_label="warm", positive_label="cool",
        negative_label_kr="따뜻한", positive_label_kr="쿨한",
        structural_weight=0.2, clip_weight=0.8,
    ),
    AxisDefinition(
        name="maturity",     name_kr="성숙도",
        negative_label="fresh", positive_label="mature",
        negative_label_kr="프레시", positive_label_kr="성숙한",
        structural_weight=0.4, clip_weight=0.6,
    ),
    AxisDefinition(
        name="intensity",    name_kr="강도",
        negative_label="natural", positive_label="bold",
        negative_label_kr="자연스러운", positive_label_kr="볼드",
        structural_weight=0.1, clip_weight=0.9,
    ),
]


# ─────────────────────────────────────────────
#  Structural Score Derivation
# ─────────────────────────────────────────────

def structural_to_axis_scores(features: dict) -> dict:
    """
    Convert raw facial structure features into per-axis scores (-1 to +1).
    This is the 'hard' signal — measurable, reproducible.

    features: dict from face.py → extract_structural_features()
    """
    scores = {}

    # ── Structure axis (sharp ↔ soft) ──
    # Sharp = low jaw angle + high cheekbone + angular features
    # Soft  = high jaw angle + round face + full lips
    jaw_norm = (features["jaw_angle"] - 110) / 40  # 110°=sharp → 150°=soft, normalized 0–1
    cheek_inv = 1 - features["cheekbone_prominence"]  # Low prominence = softer
    lip_factor = features["lip_fullness"] * 15         # Fuller lips = softer (scaled)
    structure_raw = (jaw_norm * 0.5 + cheek_inv * 0.3 + lip_factor * 0.2)
    scores["structure"] = np.clip(structure_raw * 2 - 1, -1, 1)  # Map to [-1, 1]

    # ── Impression axis (warm ↔ cool) ──
    # Structural contribution is minor — mostly from face proportions
    # Wide-set eyes + round features → warmer impression
    eye_space = features["eye_spacing_ratio"]
    symmetry = features["symmetry_score"]
    impression_raw = (eye_space * 3 - 0.5) * 0.5 + (1 - symmetry) * 0.5
    scores["impression"] = np.clip(impression_raw * 2 - 1, -1, 1)

    # ── Maturity axis (fresh ↔ mature) ──
    # Larger forehead ratio + smaller eyes = more mature look
    forehead = features["forehead_ratio"]
    eye_size = features["eye_width_ratio"]
    maturity_raw = (forehead * 2) * 0.5 + (1 - eye_size * 5) * 0.5
    scores["maturity"] = np.clip(maturity_raw * 2 - 1, -1, 1)

    # ── Intensity axis (natural ↔ bold) ──
    # Structural contribution minimal — mostly from CLIP
    golden = features["golden_ratio_score"]
    scores["intensity"] = np.clip((golden - 0.5) * 2, -1, 1)

    return scores


# ─────────────────────────────────────────────
#  CLIP Anchor Projection
# ─────────────────────────────────────────────

class AnchorProjector:
    """
    Projects CLIP embeddings onto interpretable axes using
    pre-computed anchor direction vectors.

    Each axis has two poles, each defined by the mean embedding
    of ~10 reference celeb faces. The direction vector between
    the two poles IS the axis in CLIP space.
    """

    def __init__(self):
        # axis_name → (negative_pole_mean_embedding, positive_pole_mean_embedding)
        self.anchor_vectors: dict[str, np.ndarray] = {}
        self._fitted = False

    def fit(self, anchors: dict[str, dict[str, np.ndarray]]):
        """
        Compute axis direction vectors from anchor embeddings.

        anchors: {
            "structure": {
                "negative": np.array([...512d...]),  # mean of 'sharp' celebs
                "positive": np.array([...512d...]),  # mean of 'soft' celebs
            },
            ...
        }
        """
        for axis_name, poles in anchors.items():
            neg = poles["negative"] / (np.linalg.norm(poles["negative"]) + 1e-8)
            pos = poles["positive"] / (np.linalg.norm(poles["positive"]) + 1e-8)
            # Direction vector: negative → positive
            direction = pos - neg
            direction = direction / (np.linalg.norm(direction) + 1e-8)
            self.anchor_vectors[axis_name] = direction

        self._fitted = True

    def project(self, embedding: np.ndarray) -> dict[str, float]:
        """
        Project a CLIP embedding onto all axes.
        Returns scores in [-1, 1] range.
        """
        if not self._fitted:
            raise RuntimeError("AnchorProjector not fitted. Call fit() first.")

        embedding_norm = embedding / (np.linalg.norm(embedding) + 1e-8)
        scores = {}

        for axis_name, direction in self.anchor_vectors.items():
            # Dot product = projection onto axis direction
            raw_score = float(np.dot(embedding_norm, direction))
            # Scale to roughly [-1, 1] (calibrate with data later)
            scores[axis_name] = np.clip(raw_score * 5, -1, 1)

        return scores


# ─────────────────────────────────────────────
#  Combined Coordinate Computation
# ─────────────────────────────────────────────

def compute_coordinates(
    structural_features: dict,
    clip_embedding: Optional[np.ndarray],
    projector: AnchorProjector,
) -> dict[str, float]:
    """
    Combine structural scores + CLIP projection into final 4-axis coordinates.
    Uses axis-specific weights defined in AXES.

    Returns: {"structure": 0.35, "impression": -0.22, "maturity": 0.1, "intensity": -0.45}
    """
    structural_scores = structural_to_axis_scores(structural_features)

    if clip_embedding is not None and projector._fitted:
        clip_scores = projector.project(clip_embedding)
    else:
        # WoZ fallback: use structural only
        clip_scores = {ax.name: 0.0 for ax in AXES}

    coords = {}
    for ax in AXES:
        s_score = structural_scores.get(ax.name, 0.0)
        c_score = clip_scores.get(ax.name, 0.0)
        combined = s_score * ax.structural_weight + c_score * ax.clip_weight
        coords[ax.name] = round(float(np.clip(combined, -1, 1)), 3)

    return coords


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
            "secondary_shift": "cool",
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
#  Mock CLIP for WoZ Phase
# ─────────────────────────────────────────────

def mock_clip_embedding(image_bytes: bytes) -> np.ndarray:
    """
    WoZ phase: generate a deterministic pseudo-embedding from image hash.
    NOT a real aesthetic embedding — placeholder until CLIP is integrated.
    """
    import hashlib
    h = hashlib.sha256(image_bytes).digest()
    seed = int.from_bytes(h[:4], "big")
    rng = np.random.RandomState(seed)
    emb = rng.randn(512).astype(np.float32)
    return emb / (np.linalg.norm(emb) + 1e-8)


def mock_anchor_projector() -> AnchorProjector:
    """
    WoZ phase: create projector with random anchor vectors.
    Replace with real celeb embeddings when CLIP pipeline is live.
    """
    rng = np.random.RandomState(42)
    projector = AnchorProjector()
    anchors = {}
    for ax in AXES:
        anchors[ax.name] = {
            "negative": rng.randn(512).astype(np.float32),
            "positive": rng.randn(512).astype(np.float32),
        }
    projector.fit(anchors)
    return projector
