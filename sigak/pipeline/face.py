"""
SIGAK CV Pipeline — Face Analysis
MediaPipe Face Mesh → structural features
OpenCV → preprocessing + skin analysis
"""
import math
import numpy as np
from dataclasses import dataclass, asdict
from typing import Optional
import cv2
import mediapipe as mp

mp_face_mesh = mp.solutions.face_mesh


# ─────────────────────────────────────────────
#  Landmark Index Constants (MediaPipe 468)
# ─────────────────────────────────────────────

# Key landmark indices for facial structure analysis
LM = {
    "forehead_top": 10,
    "chin_bottom": 152,
    "left_cheek": 234,
    "right_cheek": 454,
    "nose_tip": 1,
    "nose_bridge": 6,
    "left_eye_inner": 133,
    "left_eye_outer": 33,
    "right_eye_inner": 362,
    "right_eye_outer": 263,
    "left_jaw": 172,
    "right_jaw": 397,
    "jaw_tip": 152,
    "left_lip_corner": 61,
    "right_lip_corner": 291,
    "upper_lip": 13,
    "lower_lip": 14,
    "left_brow_inner": 107,
    "left_brow_outer": 70,
    "right_brow_inner": 336,
    "right_brow_outer": 300,
    "left_ear": 234,
    "right_ear": 454,
}

# Jaw contour indices for shape classification
JAW_CONTOUR = [
    10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
    397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
    172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109,
]


@dataclass
class FaceFeatures:
    """Extracted facial structure features."""
    face_shape: str              # oval, round, square, heart, oblong
    jaw_angle: float             # degrees
    cheekbone_prominence: float  # 0–1
    eye_width_ratio: float       # eye_w / face_w
    eye_spacing_ratio: float     # inner_eye_dist / face_w
    nose_length_ratio: float
    nose_width_ratio: float
    lip_fullness: float
    forehead_ratio: float
    symmetry_score: float        # 0–1 (1 = perfect symmetry)
    golden_ratio_score: float    # proximity to phi ratios
    skin_tone: str               # cool / warm / neutral
    skin_brightness: float       # 0–1
    landmarks: list              # raw 468 landmarks as list of [x,y,z]

    def to_dict(self):
        d = asdict(self)
        d.pop("landmarks")  # Too large for casual serialization
        return d


# ─────────────────────────────────────────────
#  Core Analysis Functions
# ─────────────────────────────────────────────

def _dist(a, b):
    """Euclidean distance between two 3D points."""
    return math.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b)))


def _angle(a, b, c):
    """Angle at point b formed by points a-b-c, in degrees."""
    ba = [ai - bi for ai, bi in zip(a, b)]
    bc = [ci - bi for ci, bi in zip(c, b)]
    dot = sum(x * y for x, y in zip(ba, bc))
    mag_ba = math.sqrt(sum(x**2 for x in ba))
    mag_bc = math.sqrt(sum(x**2 for x in bc))
    if mag_ba * mag_bc == 0:
        return 0
    cos_angle = max(-1, min(1, dot / (mag_ba * mag_bc)))
    return math.degrees(math.acos(cos_angle))


def _get_lm(landmarks, idx):
    """Get landmark as [x, y, z] list."""
    lm = landmarks[idx]
    return [lm.x, lm.y, lm.z]


def extract_structural_features(landmarks) -> dict:
    """Extract all structural ratios from MediaPipe landmarks."""
    g = lambda idx: _get_lm(landmarks, idx)

    # Face dimensions
    face_height = _dist(g(LM["forehead_top"]), g(LM["chin_bottom"]))
    face_width = _dist(g(LM["left_cheek"]), g(LM["right_cheek"]))

    if face_height == 0 or face_width == 0:
        raise ValueError("Invalid face dimensions")

    face_ratio = face_height / face_width

    # Jaw angle
    jaw_angle = _angle(g(LM["left_jaw"]), g(LM["jaw_tip"]), g(LM["right_jaw"]))

    # Cheekbone prominence (cheek width vs jaw width)
    jaw_width = _dist(g(LM["left_jaw"]), g(LM["right_jaw"]))
    cheekbone_prominence = min(1.0, max(0.0, (face_width - jaw_width) / face_width * 3))

    # Eye metrics
    left_eye_w = _dist(g(LM["left_eye_inner"]), g(LM["left_eye_outer"]))
    right_eye_w = _dist(g(LM["right_eye_inner"]), g(LM["right_eye_outer"]))
    avg_eye_w = (left_eye_w + right_eye_w) / 2
    eye_width_ratio = avg_eye_w / face_width
    eye_spacing = _dist(g(LM["left_eye_inner"]), g(LM["right_eye_inner"]))
    eye_spacing_ratio = eye_spacing / face_width

    # Nose
    nose_length = _dist(g(LM["nose_bridge"]), g(LM["nose_tip"]))
    nose_length_ratio = nose_length / face_height
    # Approximate nose width from landmarks near nostrils
    nose_width_ratio = 0.25  # Placeholder — refine with nostril landmarks

    # Lips
    lip_height = _dist(g(LM["upper_lip"]), g(LM["lower_lip"]))
    lip_fullness = lip_height / face_height

    # Forehead
    forehead_h = _dist(g(LM["forehead_top"]), g(LM["nose_bridge"]))
    forehead_ratio = forehead_h / face_height

    # Symmetry (compare left vs right distances from center)
    center = g(LM["nose_tip"])
    pairs = [
        (LM["left_eye_outer"], LM["right_eye_outer"]),
        (LM["left_eye_inner"], LM["right_eye_inner"]),
        (LM["left_lip_corner"], LM["right_lip_corner"]),
        (LM["left_brow_outer"], LM["right_brow_outer"]),
        (LM["left_jaw"], LM["right_jaw"]),
    ]
    sym_diffs = []
    for l_idx, r_idx in pairs:
        dl = _dist(g(l_idx), center)
        dr = _dist(g(r_idx), center)
        sym_diffs.append(1 - abs(dl - dr) / max(dl, dr, 0.001))
    symmetry_score = sum(sym_diffs) / len(sym_diffs)

    # Golden ratio score (simplified — compare key ratios to φ = 1.618)
    phi = 1.618
    ratios_to_check = [face_ratio, forehead_ratio * 3, eye_spacing_ratio * 5]
    phi_diffs = [1 - min(abs(r - phi) / phi, 1) for r in ratios_to_check]
    golden_ratio_score = sum(phi_diffs) / len(phi_diffs)

    # Face shape classification
    face_shape = classify_face_shape(face_ratio, jaw_angle, cheekbone_prominence, forehead_ratio)

    return {
        "face_shape": face_shape,
        "jaw_angle": round(jaw_angle, 1),
        "cheekbone_prominence": round(cheekbone_prominence, 3),
        "eye_width_ratio": round(eye_width_ratio, 3),
        "eye_spacing_ratio": round(eye_spacing_ratio, 3),
        "nose_length_ratio": round(nose_length_ratio, 3),
        "nose_width_ratio": round(nose_width_ratio, 3),
        "lip_fullness": round(lip_fullness, 4),
        "forehead_ratio": round(forehead_ratio, 3),
        "symmetry_score": round(symmetry_score, 3),
        "golden_ratio_score": round(golden_ratio_score, 3),
    }


def classify_face_shape(ratio, jaw_angle, cheekbone, forehead) -> str:
    """Classify face shape from structural features."""
    if ratio > 1.5 and jaw_angle < 125:
        return "oblong"
    elif ratio < 1.2 and jaw_angle > 140:
        return "round"
    elif ratio < 1.3 and jaw_angle < 120:
        return "square"
    elif cheekbone > 0.5 and forehead > 0.38:
        return "heart"
    else:
        return "oval"


# ─────────────────────────────────────────────
#  Skin Tone Analysis (OpenCV)
# ─────────────────────────────────────────────

def analyze_skin_tone(image: np.ndarray, landmarks) -> dict:
    """
    Analyze skin tone from face region.
    Returns category (cool/warm/neutral) and brightness (0–1).

    Note: Zoom/webcam 영상 한계로 정밀 피부 분석은 불가.
    상대적 분류(cool vs warm) 수준으로 활용.
    """
    h, w = image.shape[:2]

    # Sample skin from cheek regions (less affected by shadow)
    cheek_points = [
        (int(landmarks[50].x * w), int(landmarks[50].y * h)),   # Left cheek
        (int(landmarks[280].x * w), int(landmarks[280].y * h)), # Right cheek
    ]

    skin_pixels = []
    sample_radius = int(w * 0.03)  # ~3% of face width

    for cx, cy in cheek_points:
        y1, y2 = max(0, cy - sample_radius), min(h, cy + sample_radius)
        x1, x2 = max(0, cx - sample_radius), min(w, cx + sample_radius)
        region = image[y1:y2, x1:x2]
        if region.size > 0:
            skin_pixels.append(region.reshape(-1, 3))

    if not skin_pixels:
        return {"skin_tone": "neutral", "skin_brightness": 0.5}

    pixels = np.concatenate(skin_pixels, axis=0)

    # Convert to LAB for perceptual analysis
    pixels_bgr = pixels.reshape(1, -1, 3).astype(np.uint8)
    pixels_lab = cv2.cvtColor(pixels_bgr, cv2.COLOR_BGR2LAB).reshape(-1, 3)

    l_mean = pixels_lab[:, 0].mean() / 255  # Brightness (0–1)
    a_mean = pixels_lab[:, 1].mean()         # Green–Red axis
    b_mean = pixels_lab[:, 2].mean()         # Blue–Yellow axis

    # Tone classification based on a* and b* channels
    # High b* (yellow) + high a* (red) = warm
    # Low b* + moderate a* = cool
    warmth = (b_mean - 128) + (a_mean - 128) * 0.5

    if warmth > 8:
        tone = "warm"
    elif warmth < -3:
        tone = "cool"
    else:
        tone = "neutral"

    return {
        "skin_tone": tone,
        "skin_brightness": round(float(l_mean), 3),
    }


# ─────────────────────────────────────────────
#  Main Analysis Entry Point
# ─────────────────────────────────────────────

def analyze_face(image_bytes: bytes) -> Optional[FaceFeatures]:
    """
    Full face analysis pipeline.
    Input: raw image bytes (JPEG/PNG)
    Output: FaceFeatures dataclass or None if no face detected
    """
    # Decode image
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        return None

    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Run MediaPipe Face Mesh
    with mp_face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
    ) as face_mesh:
        results = face_mesh.process(image_rgb)

    if not results.multi_face_landmarks:
        return None

    landmarks = results.multi_face_landmarks[0].landmark

    # Extract structural features
    features = extract_structural_features(landmarks)

    # Analyze skin tone
    skin = analyze_skin_tone(image, landmarks)

    # Package landmarks for storage
    raw_landmarks = [[lm.x, lm.y, lm.z] for lm in landmarks]

    return FaceFeatures(
        **features,
        skin_tone=skin["skin_tone"],
        skin_brightness=skin["skin_brightness"],
        landmarks=raw_landmarks,
    )
