"""
SIGAK Overlay Renderer v0.2

유저 사진 위에 메이크업 가이드 오버레이를 합성한다.
overlay_plan (zone/type/color/opacity) → landmark polygon → alpha composite → PNG

렌더 순서: shading → blush → highlight → tint
"""
import os
import re
from typing import Tuple

import cv2
import numpy as np

from pipeline.overlay_zones import ZONE_LANDMARKS, FACE_CONTOUR_INDICES, resolve_zones


# ─────────────────────────────────────────────
#  Safety Caps
# ─────────────────────────────────────────────

OVERLAY_SAFETY_CAPS = {
    "blush":     {"opacity_min": 0.12, "opacity_max": 0.22},
    "highlight": {"opacity_min": 0.06, "opacity_max": 0.18},
    "shading":   {"opacity_min": 0.08, "opacity_max": 0.20},
    "tint":      {"opacity_min": 0.15, "opacity_max": 0.28},
}

FEATHER_SIGMA_BOUNDS = {"min_px": 3, "max_px": 60}

RENDER_ORDER = ["shading", "blush", "highlight", "tint"]


def safe_opacity(overlay_type: str, raw_opacity: float) -> float:
    caps = OVERLAY_SAFETY_CAPS.get(overlay_type, {"opacity_min": 0.05, "opacity_max": 0.25})
    return max(caps["opacity_min"], min(caps["opacity_max"], raw_opacity))


def safe_sigma(zone_size: float, feather_ratio: float) -> int:
    raw = int(zone_size * feather_ratio)
    return max(FEATHER_SIGMA_BOUNDS["min_px"], min(FEATHER_SIGMA_BOUNDS["max_px"], raw))


# ─────────────────────────────────────────────
#  Input Validation
# ─────────────────────────────────────────────

COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
VALID_ZONES = {"cheek_apple", "under_eye", "lip", "overall", "jawline", "nose_bridge"}


def validate_overlay_inputs(
    img: np.ndarray,
    landmarks_106: np.ndarray,
    overlay_plan: list,
) -> Tuple[bool, str]:
    """렌더 진입 전 입력 검증."""
    if img is None or img.size == 0:
        return False, "이미지 로드 실패"
    if landmarks_106 is None or landmarks_106.shape != (106, 2):
        shape = landmarks_106.shape if landmarks_106 is not None else None
        return False, f"landmark shape 이상: {shape}"
    if not overlay_plan or not isinstance(overlay_plan, list):
        return False, "overlay_plan 비어있음"

    for item in overlay_plan:
        if item.get("zone") not in VALID_ZONES:
            item["_skip"] = True
        if not COLOR_RE.match(item.get("color", "")):
            item["color"] = "#C8B898"
        if not isinstance(item.get("opacity"), (int, float)):
            item["opacity"] = 0.15

    return True, ""


# ─────────────────────────────────────────────
#  Face Mask
# ─────────────────────────────────────────────

def create_face_mask(
    landmarks_106: np.ndarray,
    img_shape: Tuple[int, int],
    bbox: np.ndarray = None,
) -> np.ndarray:
    """
    얼굴 영역 mask 생성.
    bbox 있으면 bbox 기반 타원, 없으면 landmark convexHull 사용.
    """
    H, W = img_shape
    mask = np.zeros((H, W), dtype=np.float32)

    if bbox is not None and len(bbox) >= 4:
        # bbox 기반 타원 mask — 가장 안정적
        x1, y1, x2, y2 = [int(v) for v in bbox[:4]]
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        rx, ry = (x2 - x1) // 2, (y2 - y1) // 2
        # 약간 넓게 (5% 패딩)
        rx = int(rx * 1.05)
        ry = int(ry * 1.05)
        cv2.ellipse(mask, (cx, cy), (rx, ry), 0, 0, 360, 1.0, -1)
    else:
        # landmark 기반 fallback
        pts = landmarks_106[FACE_CONTOUR_INDICES].astype(np.int32)
        hull = cv2.convexHull(pts)
        cv2.fillConvexPoly(mask, hull, 1.0)

    # 경계 feathering
    face_w = int(mask.sum(axis=0).max())
    sigma = max(3, int(face_w * 0.04))
    ksize = sigma * 4 + 1
    mask = cv2.GaussianBlur(mask, (ksize, ksize), sigma)
    mask = np.clip(mask, 0, 1)

    return mask


# ─────────────────────────────────────────────
#  Zone Mask
# ─────────────────────────────────────────────

def create_zone_mask(
    landmarks_106: np.ndarray,
    zone_def: dict,
    img_shape: Tuple[int, int],
    face_mask: np.ndarray,
    debug_prefix: str = None,
) -> np.ndarray:
    H, W = img_shape
    mask = np.zeros((H, W), dtype=np.float32)
    shape_type = zone_def["shape"]

    # ── lip: outer - inner hole ──
    if shape_type == "polygon_with_hole":
        outer_idx = zone_def.get("indices_outer", [])
        inner_idx = zone_def.get("indices_inner", [])
        if not outer_idx:
            return mask

        outer_pts = landmarks_106[outer_idx].astype(np.int32)
        cv2.fillConvexPoly(mask, cv2.convexHull(outer_pts), 1.0)

        if debug_prefix:
            _save_debug(mask, f"{debug_prefix}_outer.png")

        # inner hole 빼기
        if inner_idx:
            inner_pts = landmarks_106[inner_idx].astype(np.int32)
            inner_mask = np.zeros_like(mask)
            cv2.fillConvexPoly(inner_mask, cv2.convexHull(inner_pts), 1.0)
            mask = np.clip(mask - inner_mask, 0, 1)

        if debug_prefix:
            _save_debug(mask, f"{debug_prefix}_after_hole.png")

    # ── ellipse (blush) — 최소 크기 보장 ──
    elif shape_type == "ellipse":
        pts = landmarks_106[zone_def["indices"]].astype(np.int32)
        cx = int(pts[:, 0].mean())
        cy = int(pts[:, 1].mean())
        # 포인트 분포 크기
        spread_x = int(pts[:, 0].max() - pts[:, 0].min())
        spread_y = int(pts[:, 1].max() - pts[:, 1].min())
        # 최소 반경: 포인트 분포의 1.2배 또는 전체 랜드마크 범위의 12%
        face_size = max(
            landmarks_106[:, 0].max() - landmarks_106[:, 0].min(),
            landmarks_106[:, 1].max() - landmarks_106[:, 1].min(),
        )
        min_radius = int(face_size * 0.08)
        rx = max(spread_x, min_radius)
        ry = max(spread_y, min_radius)
        # 사과존 중심부만 — 볼 전체 X
        rx = int(rx * 0.7)
        ry = int(ry * 0.7)
        cv2.ellipse(mask, (cx, cy), (rx, ry), 0, 0, 360, 1.0, -1)

    # ── polygon (highlight, shading) — dilate로 면적 확보 ──
    else:
        indices = zone_def.get("indices", [])
        if not indices:
            return mask
        pts = landmarks_106[indices].astype(np.int32)
        hull = cv2.convexHull(pts)
        cv2.fillConvexPoly(mask, hull, 1.0)
        # shading은 영역이 너무 좁으면 dilate
        if zone_def["type"] == "shading":
            face_size = max(
                landmarks_106[:, 0].max() - landmarks_106[:, 0].min(),
                landmarks_106[:, 1].max() - landmarks_106[:, 1].min(),
            )
            dilate_k = max(3, int(face_size * 0.03))
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate_k, dilate_k))
            mask = cv2.dilate(mask, kernel, iterations=1)

    if debug_prefix:
        _save_debug(mask, f"{debug_prefix}_raw.png")

    # ── feathering ──
    pts_key = zone_def.get("indices", zone_def.get("indices_outer", []))
    if pts_key:
        pts_all = landmarks_106[pts_key].astype(np.int32)
        zone_size = max(pts_all.max(axis=0) - pts_all.min(axis=0))
        sigma = safe_sigma(zone_size, zone_def["feather_ratio"])
        if sigma > 0:
            ksize = sigma * 4 + 1
            mask = cv2.GaussianBlur(mask, (ksize, ksize), sigma)

    if debug_prefix:
        _save_debug(mask, f"{debug_prefix}_feathered.png")

    # normalize
    max_val = mask.max()
    if max_val > 0:
        mask = mask / max_val

    # ── face mask clipping ──
    if zone_def.get("clip_to_face", False):
        mask = np.minimum(mask, face_mask)

    if debug_prefix:
        _save_debug(mask, f"{debug_prefix}_clipped.png")

    return mask


# ─────────────────────────────────────────────
#  Alpha Composite
# ─────────────────────────────────────────────

def hex_to_bgr(hex_color: str) -> Tuple[int, int, int]:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (b, g, r)


def apply_overlay(
    img: np.ndarray,
    mask: np.ndarray,
    color_hex: str,
    opacity: float,
    overlay_type: str,
) -> np.ndarray:
    """v0: 단순 alpha composite. v1: overlay_type별 blend mode 분기."""
    color_bgr = hex_to_bgr(color_hex)
    color_layer = np.full_like(img, color_bgr, dtype=np.uint8)

    alpha = (mask * opacity)[:, :, np.newaxis]
    result = (color_layer.astype(np.float32) * alpha +
              img.astype(np.float32) * (1.0 - alpha))

    return np.clip(result, 0, 255).astype(np.uint8)


# ─────────────────────────────────────────────
#  Main Render
# ─────────────────────────────────────────────

def render_overlay(
    img: np.ndarray,
    landmarks_106: np.ndarray,
    overlay_plan: list,
    face_type: str = "하트형",
    bbox: np.ndarray = None,
    debug: bool = False,
    debug_dir: str = "debug_overlay",
) -> np.ndarray | None:
    """
    overlay_plan의 모든 zone을 합성. 실패 시 None 반환.

    Args:
        img: BGR 원본 이미지 (원본 해상도)
        landmarks_106: (106, 2) float 배열 (원본 좌표계)
        overlay_plan: [{"zone": str, "type": str, "color": str, "opacity": float}, ...]
        face_type: 한국어 얼굴형 ("하트형", "각진형" 등)
        bbox: InsightFace bbox [x1, y1, x2, y2] (face mask용)
        debug: True이면 중간 단계 이미지 저장
        debug_dir: debug 산출물 저장 경로

    Returns:
        합성된 BGR 이미지 또는 None (실패 시)
    """
    ok, err = validate_overlay_inputs(img, landmarks_106, overlay_plan)
    if not ok:
        print(f"[overlay] skip: {err}")
        return None

    if debug:
        os.makedirs(debug_dir, exist_ok=True)

    # face mask 생성
    face_mask = create_face_mask(landmarks_106, img.shape[:2], bbox=bbox)
    if debug:
        _save_debug(face_mask, f"{debug_dir}/face_mask.png")

    result = img.copy()

    # 렌더 순서 정렬
    plan_sorted = sorted(
        [p for p in overlay_plan if not p.get("_skip")],
        key=lambda x: RENDER_ORDER.index(x["type"]) if x["type"] in RENDER_ORDER else 99,
    )

    for step_idx, item in enumerate(plan_sorted):
        zone_name = item["zone"]
        overlay_type = item["type"]
        color = item["color"]
        raw_opacity = item["opacity"]

        opacity = safe_opacity(overlay_type, raw_opacity)
        actual_zones = resolve_zones(zone_name, face_type)

        for z in actual_zones:
            zone_def = ZONE_LANDMARKS.get(z)
            if not zone_def:
                continue

            has_indices = zone_def.get("indices") or zone_def.get("indices_outer")
            if not has_indices:
                continue

            debug_prefix = f"{debug_dir}/zone_{z}" if debug else None

            mask = create_zone_mask(
                landmarks_106, zone_def, img.shape[:2],
                face_mask=face_mask,
                debug_prefix=debug_prefix,
            )

            result = apply_overlay(result, mask, color, opacity, overlay_type)

            if debug:
                _save_debug(result, f"{debug_dir}/step_{step_idx}_{overlay_type}_{z}.png")

    if debug:
        _save_debug(result, f"{debug_dir}/overlay_final.png")

    return result


# ─────────────────────────────────────────────
#  Debug Helper
# ─────────────────────────────────────────────

def _save_debug(data: np.ndarray, path: str):
    """mask (float 0~1) 또는 이미지 (uint8)를 PNG로 저장."""
    if data.dtype in (np.float32, np.float64):
        cv2.imwrite(path, (data * 255).astype(np.uint8))
    else:
        cv2.imwrite(path, data)
