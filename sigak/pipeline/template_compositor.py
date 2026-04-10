"""
SIGAK Template Compositor v2
에셋 기반 헤어/메이크업 오버레이 합성 엔진

MediaPipe Face Mesh 478점 기반 (검증된 공식 인덱스)
역할 분리:
  - InsightFace: 분석 엔진 (얼굴형, 3축 좌표, 임베딩)
  - MediaPipe:   렌더링 엔진 (오버레이 앵커 포인트)
"""

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np


# ─────────────────────────────────────────────
# 1. 랜드마크 인덱스 (MediaPipe 478점 공식)
# ─────────────────────────────────────────────

class LM:
    """MediaPipe Face Mesh 478-point landmark indices"""

    # 얼굴 윤곽 (36점)
    FACE_OVAL = [
        10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
        397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
        172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109,
    ]

    # ── 눈썹 (각 10점) ──
    RIGHT_EYEBROW = [70, 63, 105, 66, 107, 55, 65, 52, 53, 46]
    LEFT_EYEBROW = [336, 296, 334, 293, 300, 276, 283, 282, 295, 285]
    # 에셋 컨트롤 포인트 매핑용 5점 (inner → peak → outer)
    RIGHT_EYEBROW_5 = [107, 66, 105, 63, 70]
    LEFT_EYEBROW_5 = [336, 296, 334, 293, 300]

    # ── 눈 (각 16점) ──
    RIGHT_EYE = [
        33, 7, 163, 144, 145, 153, 154, 155, 133, 173,
        157, 158, 159, 160, 161, 246,
    ]
    LEFT_EYE = [
        362, 382, 381, 380, 374, 373, 390, 249, 263, 466,
        388, 387, 386, 385, 384, 398,
    ]
    # 속눈썹 앵커용 상단 곡선 5점 (inner → top → outer)
    RIGHT_EYE_UPPER_5 = [133, 157, 159, 161, 33]
    LEFT_EYE_UPPER_5 = [362, 384, 386, 388, 263]

    # ── 입술 ──
    LIPS = [
        61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308,
        324, 318, 402, 317, 14, 87, 178, 88, 95, 185, 40, 39, 37,
        0, 267, 269, 270, 409, 415, 310, 311, 312, 13, 82, 81, 42, 183, 78,
    ]
    UPPER_LIPS = [
        185, 40, 39, 37, 0, 267, 269, 270, 409, 415,
        310, 311, 312, 13, 82, 81, 42, 183, 78,
    ]
    LOWER_LIPS = [
        61, 146, 91, 181, 84, 17, 314, 405, 321, 375,
        291, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95,
    ]

    # ── 단일 앵커 포인트 ──
    FOREHEAD_TOP = 10   # 이마 최상단
    GLABELLA = 9        # 미간 (양 눈썹 사이)
    NOSE_TIP = 4        # 코끝
    NOSE_BRIDGE = 6     # 코 브릿지
    CHIN = 152          # 턱 끝

    # 관자놀이 (얼굴 최대 너비)
    TEMPLE_R = 454      # subject 오른쪽 (이미지 왼쪽)
    TEMPLE_L = 234      # subject 왼쪽 (이미지 오른쪽)

    # 눈 중심 계산용 (inner, outer)
    RIGHT_EYE_CORNERS = [133, 33]
    LEFT_EYE_CORNERS = [362, 263]


def extract_landmarks_478(image: np.ndarray) -> Optional[np.ndarray]:
    """MediaPipe Face Mesh로 478점 랜드마크 추출 → (478, 2) pixel coords"""
    import mediapipe as mp

    h, w = image.shape[:2]
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    with mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
    ) as mesh:
        results = mesh.process(rgb)

    if not results.multi_face_landmarks:
        return None

    face = results.multi_face_landmarks[0]
    pts = np.array(
        [[lm.x * w, lm.y * h] for lm in face.landmark],
        dtype=np.float32,
    )
    return pts  # shape: (478, 2)


# ─────────────────────────────────────────────
# 2. 색상 유틸
# ─────────────────────────────────────────────

HAIR_COLORS = {
    "black":       {"h": 25, "s": 30, "l": 10},
    "dark_brown":  {"h": 25, "s": 60, "l": 20},
    "brown":       {"h": 25, "s": 55, "l": 30},
    "light_brown": {"h": 28, "s": 50, "l": 45},
    "ash":         {"h": 35, "s": 30, "l": 35},
}

BLUSHER_PRESETS = {
    "warm_pink":  {"h": 350, "s": 60, "l": 70},
    "coral":      {"h": 15,  "s": 65, "l": 65},
    "peach":      {"h": 25,  "s": 50, "l": 75},
    "rose":       {"h": 340, "s": 55, "l": 60},
}

LIP_PRESETS = {
    "mlbb":   {"h": 355, "s": 45, "l": 55},
    "coral":  {"h": 10,  "s": 70, "l": 60},
    "red":    {"h": 0,   "s": 80, "l": 45},
    "rose":   {"h": 340, "s": 60, "l": 50},
    "nude":   {"h": 20,  "s": 35, "l": 65},
}


def hsl_to_bgr(h: float, s: float, l: float) -> tuple:
    """HSL (h:0-360, s:0-100, l:0-100) → BGR"""
    s /= 100
    l /= 100
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2

    if h < 60:    r, g, b = c, x, 0
    elif h < 120: r, g, b = x, c, 0
    elif h < 180: r, g, b = 0, c, x
    elif h < 240: r, g, b = 0, x, c
    elif h < 300: r, g, b = x, 0, c
    else:         r, g, b = c, 0, x

    return (int((b + m) * 255), int((g + m) * 255), int((r + m) * 255))


def shift_asset_color(asset_bgra: np.ndarray, target_hsl: dict) -> np.ndarray:
    """
    에셋(dark brown 기준)의 색조를 target HSL로 변환.
    밝기 대비는 유지, H/S만 교체, L은 상대적 shift.
    """
    result = asset_bgra.copy()
    bgr = result[:, :, :3]
    alpha = result[:, :, 3]

    # BGR → HLS (OpenCV: H 0-180, L 0-255, S 0-255)
    hls = cv2.cvtColor(bgr, cv2.COLOR_BGR2HLS).astype(np.float32)

    mask = alpha > 0

    # H 교체
    hls[:, :, 0][mask] = (target_hsl["h"] / 2) % 180  # OpenCV H = 0~180

    # S 교체
    hls[:, :, 2][mask] = target_hsl["s"] * 2.55  # 0~100 → 0~255

    # L: 원본 대비 유지하면서 target 기준으로 shift
    base_l = 20 * 2.55  # dark_brown base L
    target_l = target_hsl["l"] * 2.55
    l_shift = target_l - base_l
    hls[:, :, 1][mask] = np.clip(hls[:, :, 1][mask] + l_shift, 0, 255)

    result[:, :, :3] = cv2.cvtColor(hls.astype(np.uint8), cv2.COLOR_HLS2BGR)
    return result


# ─────────────────────────────────────────────
# 3. 에셋 로더
# ─────────────────────────────────────────────

@dataclass
class AssetMeta:
    """에셋 메타데이터"""
    id: str
    path: str
    control_points: Optional[list] = None  # [[x,y], ...]
    offset: Optional[dict] = None          # {"dx": float, "dy": float}


class AssetLoader:
    def __init__(self, assets_dir: str):
        self.dir = Path(assets_dir)
        self._cache: dict[str, np.ndarray] = {}
        self._meta: dict[str, AssetMeta] = {}
        self._load_meta()

    def _load_meta(self):
        meta_path = self.dir / "meta.json"
        if meta_path.exists():
            with open(meta_path) as f:
                raw = json.load(f)
            for k, v in raw.items():
                self._meta[k] = AssetMeta(id=k, **v)

    def get(self, asset_id: str) -> np.ndarray:
        """BGRA 이미지 반환 (캐시)"""
        if asset_id not in self._cache:
            for subdir in ["bang", "back", "eyebrow", "eyelash", "blusher", "lip"]:
                path = self.dir / subdir / f"{asset_id}.png"
                if path.exists():
                    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
                    if img is not None:
                        self._cache[asset_id] = img
                        break
            else:
                raise FileNotFoundError(f"Asset not found: {asset_id}")
        return self._cache[asset_id]

    def get_meta(self, asset_id: str) -> Optional[AssetMeta]:
        return self._meta.get(asset_id)


# ─────────────────────────────────────────────
# 4. 앵커 정렬
# ─────────────────────────────────────────────

class AnchorAligner:
    """MediaPipe 478점 랜드마크 기반 에셋 변환"""

    @staticmethod
    def get_face_angle(lm: np.ndarray) -> float:
        """두 눈 중심 기울기 (라디안)"""
        r_center = (lm[LM.RIGHT_EYE_CORNERS[0]] + lm[LM.RIGHT_EYE_CORNERS[1]]) / 2
        l_center = (lm[LM.LEFT_EYE_CORNERS[0]] + lm[LM.LEFT_EYE_CORNERS[1]]) / 2
        dy = l_center[1] - r_center[1]
        dx = l_center[0] - r_center[0]
        return math.atan2(dy, dx)

    @staticmethod
    def get_temple_width(lm: np.ndarray) -> float:
        """관자놀이 간 거리"""
        return float(np.linalg.norm(lm[LM.TEMPLE_L] - lm[LM.TEMPLE_R]))

    @staticmethod
    def get_forehead_center(lm: np.ndarray) -> np.ndarray:
        """이마 중앙점 (앞머리 앵커) — 이마 상단과 미간의 중간"""
        return (lm[LM.FOREHEAD_TOP] + lm[LM.GLABELLA]) / 2

    @staticmethod
    def get_crown_center(lm: np.ndarray) -> np.ndarray:
        """정수리 추정점 (뒷머리 앵커)"""
        r = lm[LM.TEMPLE_R]
        l = lm[LM.TEMPLE_L]
        mid = (r + l) / 2.0
        face_height = lm[LM.CHIN][1] - mid[1]
        mid = mid.copy()
        mid[1] -= face_height * 0.3
        return mid

    @staticmethod
    def align_bang(
        asset: np.ndarray,
        lm: np.ndarray,
        canvas_shape: tuple,
        scale_factor: float = 1.3,
    ) -> np.ndarray:
        """앞머리 에셋을 유저 얼굴에 정렬"""
        h, w = asset.shape[:2]

        center = AnchorAligner.get_forehead_center(lm)
        temple_w = AnchorAligner.get_temple_width(lm)
        target_w = temple_w * scale_factor
        angle = AnchorAligner.get_face_angle(lm)

        scale = target_w / w
        anchor_src = np.float32([w / 2, h])  # 에셋 앵커 (중앙 하단)

        M = cv2.getRotationMatrix2D(
            center=(float(center[0]), float(center[1])),
            angle=math.degrees(angle),
            scale=scale,
        )
        tx = center[0] - anchor_src[0] * scale
        ty = center[1] - anchor_src[1] * scale
        M[0, 2] += tx
        M[1, 2] += ty

        canvas_h, canvas_w = canvas_shape[:2]
        return cv2.warpAffine(
            asset, M, (canvas_w, canvas_h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_TRANSPARENT,
        )

    @staticmethod
    def align_back_hair(
        asset: np.ndarray,
        lm: np.ndarray,
        canvas_shape: tuple,
        scale_factor: float = 1.8,
    ) -> np.ndarray:
        """뒷머리 에셋 정렬 (유저 사진 뒤에 깔림)"""
        h, w = asset.shape[:2]

        center = AnchorAligner.get_crown_center(lm)
        temple_w = AnchorAligner.get_temple_width(lm)
        target_w = temple_w * scale_factor
        angle = AnchorAligner.get_face_angle(lm)

        scale = target_w / w
        anchor_src = np.float32([w / 2, h / 3])  # 에셋 앵커 (중앙 상단 1/3)

        M = cv2.getRotationMatrix2D(
            center=(float(center[0]), float(center[1])),
            angle=math.degrees(angle),
            scale=scale,
        )
        tx = center[0] - anchor_src[0] * scale
        ty = center[1] - anchor_src[1] * scale
        M[0, 2] += tx
        M[1, 2] += ty

        canvas_h, canvas_w = canvas_shape[:2]
        return cv2.warpAffine(
            asset, M, (canvas_w, canvas_h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_TRANSPARENT,
        )

    @staticmethod
    def align_eyebrow(
        asset: np.ndarray,
        lm: np.ndarray,
        canvas_shape: tuple,
        side: str = "right",
    ) -> np.ndarray:
        """눈썹 에셋을 5포인트 어파인 정렬 (MediaPipe 좌/우 독립 인덱스)"""
        if side == "left":
            asset = cv2.flip(asset, 1)  # 에셋은 오른쪽 기준 제작 → flip
            target_pts = lm[LM.LEFT_EYEBROW_5]
        else:
            target_pts = lm[LM.RIGHT_EYEBROW_5]

        h, w = asset.shape[:2]

        # 에셋 5포인트 (좌→우 균등 분배)
        src_pts = np.float32([
            [w * 0.05, h * 0.6],   # inner
            [w * 0.25, h * 0.4],
            [w * 0.55, h * 0.3],   # peak
            [w * 0.78, h * 0.45],
            [w * 0.95, h * 0.6],   # outer
        ])

        # 3포인트 어파인 (inner, peak, outer)
        src_3 = np.float32([src_pts[0], src_pts[2], src_pts[4]])
        dst_3 = np.float32([target_pts[0], target_pts[2], target_pts[4]])

        M = cv2.getAffineTransform(src_3, dst_3)

        canvas_h, canvas_w = canvas_shape[:2]
        return cv2.warpAffine(
            asset, M, (canvas_w, canvas_h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_TRANSPARENT,
        )

    @staticmethod
    def align_eyelash(
        asset: np.ndarray,
        lm: np.ndarray,
        canvas_shape: tuple,
        side: str = "right",
    ) -> np.ndarray:
        """속눈썹 에셋을 눈 상단 곡선에 정렬"""
        if side == "left":
            asset = cv2.flip(asset, 1)
            target_pts = lm[LM.LEFT_EYE_UPPER_5]
        else:
            target_pts = lm[LM.RIGHT_EYE_UPPER_5]

        h, w = asset.shape[:2]

        # 에셋 3포인트 → 눈 상단 3포인트 (inner, top, outer)
        src_3 = np.float32([
            [w * 0.05, h * 0.7],
            [w * 0.5, h * 0.3],
            [w * 0.95, h * 0.7],
        ])
        dst_3 = np.float32([target_pts[0], target_pts[2], target_pts[4]])

        M = cv2.getAffineTransform(src_3, dst_3)

        canvas_h, canvas_w = canvas_shape[:2]
        return cv2.warpAffine(
            asset, M, (canvas_w, canvas_h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_TRANSPARENT,
        )

    @staticmethod
    def align_blusher(
        mask: np.ndarray,
        lm: np.ndarray,
        canvas_shape: tuple,
        offset: dict,
        color_bgr: tuple,
        opacity: float = 0.4,
    ) -> np.ndarray:
        """블러셔 마스크를 코끝 기준으로 배치 (좌우 대칭)"""
        canvas_h, canvas_w = canvas_shape[:2]
        result = np.zeros((canvas_h, canvas_w, 4), dtype=np.uint8)

        nose_tip = lm[LM.NOSE_TIP]  # index 4
        face_w = AnchorAligner.get_temple_width(lm)

        dx = offset.get("dx", 0.18)
        dy = offset.get("dy", 0.02)

        for sign in [-1, +1]:  # 좌우 대칭
            cx = nose_tip[0] + sign * dx * face_w
            cy = nose_tip[1] + dy * face_w

            target_size = int(face_w * 0.35)
            resized = cv2.resize(mask, (target_size, target_size))

            # grayscale mask → alpha
            if len(resized.shape) == 2:
                alpha_ch = resized
            else:
                alpha_ch = resized[:, :, 0]

            alpha_ch = (alpha_ch.astype(np.float32) * opacity).astype(np.uint8)

            # 배치
            x1 = int(cx - target_size // 2)
            y1 = int(cy - target_size // 2)
            x2 = x1 + target_size
            y2 = y1 + target_size

            # 경계 클리핑
            sx1 = max(0, -x1)
            sy1 = max(0, -y1)
            sx2 = target_size - max(0, x2 - canvas_w)
            sy2 = target_size - max(0, y2 - canvas_h)

            dx1 = max(0, x1)
            dy1 = max(0, y1)
            dx2 = min(canvas_w, x2)
            dy2 = min(canvas_h, y2)

            if dx2 > dx1 and dy2 > dy1:
                region = alpha_ch[sy1:sy2, sx1:sx2]
                result[dy1:dy2, dx1:dx2, 0] = color_bgr[0]
                result[dy1:dy2, dx1:dx2, 1] = color_bgr[1]
                result[dy1:dy2, dx1:dx2, 2] = color_bgr[2]
                result[dy1:dy2, dx1:dx2, 3] = np.maximum(
                    result[dy1:dy2, dx1:dx2, 3], region
                )

        return result

    @staticmethod
    def align_lip(
        mask: np.ndarray,
        lm: np.ndarray,
        canvas_shape: tuple,
        color_bgr: tuple,
        opacity: float = 0.7,
    ) -> np.ndarray:
        """립 마스크를 입술 랜드마크에 정렬"""
        canvas_h, canvas_w = canvas_shape[:2]

        lip_pts = lm[LM.LIPS]  # 39포인트 (MediaPipe)

        # 입술 바운딩 박스
        x_min, y_min = lip_pts.min(axis=0)
        x_max, y_max = lip_pts.max(axis=0)
        lip_w = x_max - x_min
        lip_h = y_max - y_min
        lip_cx = (x_min + x_max) / 2
        lip_cy = (y_min + y_max) / 2

        # 마스크 리사이즈
        mh, mw = mask.shape[:2]
        scale_x = lip_w * 1.1 / mw
        scale_y = lip_h * 1.2 / mh

        new_w = int(mw * scale_x)
        new_h = int(mh * scale_y)
        if new_w < 1 or new_h < 1:
            return np.zeros((canvas_h, canvas_w, 4), dtype=np.uint8)
        resized = cv2.resize(mask, (new_w, new_h))

        if len(resized.shape) == 2:
            alpha_ch = resized
        else:
            alpha_ch = resized[:, :, 0]

        alpha_ch = (alpha_ch.astype(np.float32) * opacity).astype(np.uint8)

        # 배치 (입술 중앙 정렬)
        result = np.zeros((canvas_h, canvas_w, 4), dtype=np.uint8)

        x1 = int(lip_cx - new_w // 2)
        y1 = int(lip_cy - new_h // 2)
        x2 = x1 + new_w
        y2 = y1 + new_h

        sx1 = max(0, -x1)
        sy1 = max(0, -y1)
        sx2 = new_w - max(0, x2 - canvas_w)
        sy2 = new_h - max(0, y2 - canvas_h)

        dx1 = max(0, x1)
        dy1 = max(0, y1)
        dx2 = min(canvas_w, x2)
        dy2 = min(canvas_h, y2)

        if dx2 > dx1 and dy2 > dy1:
            region = alpha_ch[sy1:sy2, sx1:sx2]
            result[dy1:dy2, dx1:dx2, 0] = color_bgr[0]
            result[dy1:dy2, dx1:dx2, 1] = color_bgr[1]
            result[dy1:dy2, dx1:dx2, 2] = color_bgr[2]
            result[dy1:dy2, dx1:dx2, 3] = region

        return result


# ─────────────────────────────────────────────
# 5. 레이어 합성
# ─────────────────────────────────────────────

class LayerCompositor:
    """z-order 기반 BGRA 레이어 합성"""

    @staticmethod
    def alpha_blend(base: np.ndarray, overlay: np.ndarray) -> np.ndarray:
        """기본 alpha blend (normal mode)"""
        if overlay.shape[2] < 4:
            return base

        alpha = overlay[:, :, 3:4].astype(np.float32) / 255.0
        blended = base.copy().astype(np.float32)
        blended[:, :, :3] = (
            overlay[:, :, :3].astype(np.float32) * alpha
            + blended[:, :, :3] * (1 - alpha)
        )
        return np.clip(blended, 0, 255).astype(np.uint8)

    @staticmethod
    def multiply_blend(base: np.ndarray, overlay: np.ndarray) -> np.ndarray:
        """multiply blend (블러셔용)"""
        if overlay.shape[2] < 4:
            return base

        alpha = overlay[:, :, 3:4].astype(np.float32) / 255.0
        base_f = base[:, :, :3].astype(np.float32)
        over_f = overlay[:, :, :3].astype(np.float32)

        multiplied = (base_f * over_f) / 255.0
        blended = base.copy().astype(np.float32)
        blended[:, :, :3] = multiplied * alpha + base_f * (1 - alpha)
        return np.clip(blended, 0, 255).astype(np.uint8)

    @staticmethod
    def soft_light_blend(base: np.ndarray, overlay: np.ndarray) -> np.ndarray:
        """soft light blend (립용)"""
        if overlay.shape[2] < 4:
            return base

        alpha = overlay[:, :, 3:4].astype(np.float32) / 255.0
        b = base[:, :, :3].astype(np.float32) / 255.0
        o = overlay[:, :, :3].astype(np.float32) / 255.0

        # Photoshop soft light 공식
        result = np.where(
            o <= 0.5,
            b - (1 - 2 * o) * b * (1 - b),
            b + (2 * o - 1) * (np.sqrt(b) - b),
        )

        blended = base.copy().astype(np.float32)
        blended[:, :, :3] = (result * alpha + b * (1 - alpha)) * 255
        return np.clip(blended, 0, 255).astype(np.uint8)


# ─────────────────────────────────────────────
# 6. 메인 컴포지터
# ─────────────────────────────────────────────

@dataclass
class CompositorConfig:
    hair_bang: str = "bang_side_asym"
    hair_back: str = "back_mid_layered"
    eyebrow: str = "eb_semi_arch"
    eyelash: str = "lash_natural"
    blusher: str = "blush_center"
    lip: str = "lip_gradient"

    hair_color: dict = field(default_factory=lambda: HAIR_COLORS["dark_brown"])
    blusher_color: dict = field(default_factory=lambda: BLUSHER_PRESETS["coral"])
    lip_color: dict = field(default_factory=lambda: LIP_PRESETS["mlbb"])

    blusher_opacity: float = 0.4
    lip_opacity: float = 0.7


# 블러셔 offset 테이블
BLUSHER_OFFSETS = {
    "blush_center":         {"dx": 0.18, "dy": 0.02},
    "blush_diagonal":       {"dx": 0.22, "dy": -0.03},
    "blush_undereye":       {"dx": 0.12, "dy": -0.04},
    "blush_noseside":       {"dx": 0.08, "dy": 0.00},
    "blush_outer_vertical": {"dx": 0.28, "dy": -0.02},
}


class TemplateCompositor:
    def __init__(self, assets_dir: str):
        self.loader = AssetLoader(assets_dir)

    def compose(
        self,
        user_photo: np.ndarray,
        lm: np.ndarray,
        config: CompositorConfig = CompositorConfig(),
    ) -> np.ndarray:
        """
        전체 합성 파이프라인

        Args:
            user_photo: BGR 유저 사진
            lm: MediaPipe 478점 랜드마크 (478, 2) pixel coords
            config: 합성 설정

        레이어 순서:
        1. back hair (behind user)
        2. user photo
        3. blusher (multiply)
        4. lip (soft light)
        5. eyebrow (normal)
        6. eyelash (normal)
        7. bang (normal, topmost)
        """
        h, w = user_photo.shape[:2]

        # 유저 사진을 BGRA로
        if user_photo.shape[2] == 3:
            canvas = cv2.cvtColor(user_photo, cv2.COLOR_BGR2BGRA)
        else:
            canvas = user_photo.copy()

        # ── Layer 1: 뒷머리 ──
        if config.hair_back != "none":
            back_asset = self.loader.get(config.hair_back)
            back_colored = shift_asset_color(back_asset, config.hair_color)
            back_aligned = AnchorAligner.align_back_hair(
                back_colored, lm, (h, w)
            )
            # 뒷머리 먼저 깔고 유저를 위에
            temp = back_aligned.copy()
            canvas = LayerCompositor.alpha_blend(temp, canvas)

        # ── Layer 3: 블러셔 ──
        if config.blusher != "none":
            blush_mask = self.loader.get(config.blusher)
            blush_color = hsl_to_bgr(**config.blusher_color)
            offset = BLUSHER_OFFSETS.get(config.blusher, {"dx": 0.18, "dy": 0.02})
            blush_layer = AnchorAligner.align_blusher(
                blush_mask, lm, (h, w),
                offset=offset,
                color_bgr=blush_color,
                opacity=config.blusher_opacity,
            )
            canvas = LayerCompositor.multiply_blend(canvas, blush_layer)

        # ── Layer 4: 립 ──
        if config.lip != "none":
            lip_mask = self.loader.get(config.lip)
            lip_color = hsl_to_bgr(**config.lip_color)
            lip_layer = AnchorAligner.align_lip(
                lip_mask, lm, (h, w),
                color_bgr=lip_color,
                opacity=config.lip_opacity,
            )
            canvas = LayerCompositor.soft_light_blend(canvas, lip_layer)

        # ── Layer 5: 눈썹 (좌우) ──
        if config.eyebrow != "none":
            eb_asset = self.loader.get(config.eyebrow)
            eb_colored = shift_asset_color(
                eb_asset,
                {"h": config.hair_color["h"],
                 "s": config.hair_color["s"],
                 "l": config.hair_color["l"] * 0.8},
            )
            for side in ["right", "left"]:
                eb_aligned = AnchorAligner.align_eyebrow(
                    eb_colored, lm, (h, w), side=side
                )
                canvas = LayerCompositor.alpha_blend(canvas, eb_aligned)

        # ── Layer 6: 속눈썹 (좌우) ──
        if config.eyelash != "none":
            lash_asset = self.loader.get(config.eyelash)
            for side in ["right", "left"]:
                lash_aligned = AnchorAligner.align_eyelash(
                    lash_asset, lm, (h, w), side=side
                )
                canvas = LayerCompositor.alpha_blend(canvas, lash_aligned)

        # ── Layer 7: 앞머리 ──
        if config.hair_bang != "bang_none":
            bang_asset = self.loader.get(config.hair_bang)
            bang_colored = shift_asset_color(bang_asset, config.hair_color)
            bang_aligned = AnchorAligner.align_bang(
                bang_colored, lm, (h, w)
            )
            canvas = LayerCompositor.alpha_blend(canvas, bang_aligned)

        return canvas


# ─────────────────────────────────────────────
# 7. CLI / 테스트
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python template_compositor.py <photo> <assets_dir> [output]")
        print("Example: python template_compositor.py user.jpg assets/overlay result.png")
        sys.exit(1)

    photo_path = sys.argv[1]
    assets_dir = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else "composed.png"

    # MediaPipe 478점 랜드마크 추출
    photo = cv2.imread(photo_path)
    lm = extract_landmarks_478(photo)

    if lm is None:
        print("No face detected")
        sys.exit(1)

    # 합성
    compositor = TemplateCompositor(assets_dir)
    config = CompositorConfig()

    result = compositor.compose(photo, lm, config)
    cv2.imwrite(output_path, result)
    print(f"Saved: {output_path}")
