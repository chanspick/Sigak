"""
SIGAK Hair Color Overlay — BiSeNet Face Parsing 기반 헤어컬러 시뮬레이션

BiSeNet 19-class face parsing → hair(17) + eyebrow(2,3) 마스크 추출
→ HSV color shift (V 보존으로 텍스처 유지) → 원본 블렌딩

Classes: 0=bg, 1=skin, 2=l_brow, 3=r_brow, 4=l_eye, 5=r_eye,
6=glasses, 7=l_ear, 8=r_ear, 9=earring, 10=nose, 11=mouth,
12=upper_lip, 13=lower_lip, 14=neck, 15=necklace, 16=cloth, 17=hair, 18=hat
"""
import os
import re
from typing import Optional

import cv2
import numpy as np

# ─────────────────────────────────────────────
#  BiSeNet ONNX 모델 로더 (싱글톤)
# ─────────────────────────────────────────────

_MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
_DEFAULT_MODEL_PATH = os.path.join(_MODEL_DIR, "bisenet_face_parsing.onnx")

# ImageNet 정규화 (BiSeNet 표준)
_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
_INPUT_SIZE = 512

# BiSeNet class indices
CLASS_HAIR = 17
CLASS_LEFT_BROW = 2
CLASS_RIGHT_BROW = 3

_session = None


def _get_session():
    """BiSeNet ONNX 세션 싱글톤. 앱 시작 시 1회 로드."""
    global _session
    if _session is not None:
        return _session

    model_path = os.getenv("BISENET_MODEL_PATH", _DEFAULT_MODEL_PATH)
    if not os.path.exists(model_path):
        print(f"[HAIR_OVERLAY] 모델 파일 없음: {model_path}")
        return None

    try:
        import onnxruntime as ort
        _session = ort.InferenceSession(
            model_path,
            providers=["CPUExecutionProvider"],
        )
        print(f"[HAIR_OVERLAY] BiSeNet 모델 로드 완료: {model_path}")
        return _session
    except Exception as e:
        print(f"[HAIR_OVERLAY] 모델 로드 실패: {e}")
        return None


# ─────────────────────────────────────────────
#  Face Parsing (19-class segmentation)
# ─────────────────────────────────────────────

def _parse_face(image: np.ndarray) -> Optional[np.ndarray]:
    """
    BiSeNet inference → (H, W) class map.
    입력: BGR 원본 이미지 (임의 해상도)
    출력: (H, W) int8 — 각 픽셀이 0~18 클래스
    """
    session = _get_session()
    if session is None:
        return None

    h, w = image.shape[:2]

    # 전처리: BGR→RGB, 리사이즈, 정규화
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(rgb, (_INPUT_SIZE, _INPUT_SIZE), interpolation=cv2.INTER_LINEAR)
    normalized = (resized.astype(np.float32) / 255.0 - _MEAN) / _STD
    # (H, W, 3) → (1, 3, H, W)
    tensor = normalized.transpose(2, 0, 1)[np.newaxis, ...]

    # inference
    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: tensor})
    logits = outputs[0]  # (1, 19, 512, 512)

    # argmax → class map
    class_map = logits[0].argmax(axis=0).astype(np.uint8)  # (512, 512)

    # 원본 해상도로 복원
    if h != _INPUT_SIZE or w != _INPUT_SIZE:
        class_map = cv2.resize(class_map, (w, h), interpolation=cv2.INTER_NEAREST)

    return class_map


# ─────────────────────────────────────────────
#  Hair / Eyebrow Mask 생성
# ─────────────────────────────────────────────

def create_hair_mask(image: np.ndarray) -> Optional[dict]:
    """
    BiSeNet → hair + eyebrow 마스크 분리.

    Returns:
        {
            "hair": (H, W) float32 0~1 feathered mask,
            "eyebrow": (H, W) float32 0~1 feathered mask,
        }
        또는 None (모델 미사용/실패)
    """
    class_map = _parse_face(image)
    if class_map is None:
        return None

    h, w = image.shape[:2]

    # 바이너리 마스크 추출
    hair_raw = (class_map == CLASS_HAIR).astype(np.float32)
    brow_raw = ((class_map == CLASS_LEFT_BROW) | (class_map == CLASS_RIGHT_BROW)).astype(np.float32)

    # feathering (경계 자연스럽게)
    feather_sigma = max(3, int(min(h, w) * 0.005))
    ksize = feather_sigma * 4 + 1
    hair_mask = cv2.GaussianBlur(hair_raw, (ksize, ksize), feather_sigma)
    brow_mask = cv2.GaussianBlur(brow_raw, (ksize, ksize), feather_sigma)

    # normalize
    if hair_mask.max() > 0:
        hair_mask = np.clip(hair_mask / hair_mask.max(), 0, 1)
    if brow_mask.max() > 0:
        brow_mask = np.clip(brow_mask / brow_mask.max(), 0, 1)

    return {"hair": hair_mask, "eyebrow": brow_mask}


# ─────────────────────────────────────────────
#  HSV Color Shift
# ─────────────────────────────────────────────

_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _hex_to_hsv(hex_color: str) -> tuple:
    """#RRGGBB → (H, S, V) OpenCV 범위: H=0~180, S=0~255, V=0~255"""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    pixel = np.array([[[b, g, r]]], dtype=np.uint8)
    hsv = cv2.cvtColor(pixel, cv2.COLOR_BGR2HSV)
    return int(hsv[0, 0, 0]), int(hsv[0, 0, 1]), int(hsv[0, 0, 2])


def apply_color_shift(
    image: np.ndarray,
    mask: np.ndarray,
    target_hex: str,
    value_darken: float = 0.0,
    saturation_blend: float = 0.6,
) -> np.ndarray:
    """
    마스크 영역에 target 색상으로 HSV shift.

    핵심: V(밝기)는 원본 유지 → 머리카락 텍스처(그라데이션, 결) 보존.

    Args:
        image: BGR 원본
        mask: (H, W) float32 0~1
        target_hex: 목표 색상 (#RRGGBB)
        value_darken: V를 추가로 낮추는 비율 (눈썹용, 0.15 = 15% 어둡게)
        saturation_blend: S 블렌딩 비율 (0=원본 유지, 1=타겟 완전 교체)

    Returns:
        합성된 BGR 이미지
    """
    if not _COLOR_RE.match(target_hex):
        return image

    target_h, target_s, target_v = _hex_to_hsv(target_hex)

    # 원본 → HSV
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
    h_ch, s_ch, v_ch = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

    # 색 변환된 HSV
    new_h = np.full_like(h_ch, target_h)
    new_s = s_ch * (1 - saturation_blend) + target_s * saturation_blend
    new_v = v_ch * (1 - value_darken)  # V 원본 유지 (텍스처 보존), darken만 적용

    shifted_hsv = np.stack([new_h, new_s, new_v], axis=-1).clip(0, [180, 255, 255])
    shifted_bgr = cv2.cvtColor(shifted_hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    # 마스크 알파 블렌딩
    alpha = mask[:, :, np.newaxis]
    result = shifted_bgr.astype(np.float32) * alpha + image.astype(np.float32) * (1 - alpha)

    return np.clip(result, 0, 255).astype(np.uint8)


# ─────────────────────────────────────────────
#  메인 렌더러
# ─────────────────────────────────────────────

def render_hair_simulation(
    image: np.ndarray,
    target_hair_hex: str,
    eyebrow_darken: float = 0.20,
    eyebrow_opacity: float = 0.4,
) -> Optional[np.ndarray]:
    """
    헤어컬러 시뮬레이션 전체 파이프라인.

    1. BiSeNet face parsing → hair/eyebrow 마스크 분리
    2. hair 영역: target 색으로 HSV shift (V 보존)
    3. eyebrow 영역: 같은 색 + 20% 어둡게 + opacity 40% (원본 60% 보존)
    4. 원본과 블렌딩 → 최종 이미지

    Args:
        image: BGR 원본 사진
        target_hair_hex: 목표 헤어 컬러 (#RRGGBB)
        eyebrow_darken: 눈썹 V(밝기) 추가 감소 비율 (기본 20%)
        eyebrow_opacity: 눈썹 색 교체 강도 (기본 0.4 = 40%, 나머지 60%는 원본 유지)

    Returns:
        합성된 BGR 이미지 또는 None (모델 미사용)
    """
    masks = create_hair_mask(image)
    if masks is None:
        print("[HAIR_OVERLAY] 마스크 생성 실패 — 건너뜀")
        return None

    hair_mask = masks["hair"]
    brow_mask = masks["eyebrow"]

    # hair 영역이 너무 작으면 (전체 픽셀의 1% 미만) 건너뜀
    hair_ratio = hair_mask.sum() / (hair_mask.shape[0] * hair_mask.shape[1])
    if hair_ratio < 0.01:
        print(f"[HAIR_OVERLAY] hair 영역 너무 작음 ({hair_ratio:.3f}) — 건너뜀")
        return None

    # 1. hair 영역 색 변환
    result = apply_color_shift(image, hair_mask, target_hair_hex)

    # 2. eyebrow: opacity 낮춰서 은은하게 (100% 교체하면 부자연스러움)
    if brow_mask.sum() > 0:
        brow_mask_soft = brow_mask * eyebrow_opacity
        result = apply_color_shift(
            result, brow_mask_soft, target_hair_hex,
            value_darken=eyebrow_darken,
        )

    return result
