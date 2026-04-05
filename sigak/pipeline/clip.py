"""
SIGAK CLIP Pipeline -- Face Embedding Extraction

open-clip-torch 기반 ViT-L-14 모델로 768차원 미적 임베딩을 추출한다.
얼굴 크롭 -> CLIP 전처리 -> L2 정규화된 임베딩 반환.
"""
import hashlib
import logging
import threading
from typing import Optional

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  CLIPEmbedder (싱글톤)
# ─────────────────────────────────────────────

class CLIPEmbedder:
    """
    CLIP 모델을 로드하고 이미지에서 768차원 임베딩을 추출한다.

    GPU 메모리 관리를 위해 싱글톤 패턴으로 동작한다.
    모델은 최초 접근 시 lazy-load 되며, float16 으로 GPU 메모리를 절약한다.
    """

    _instance: Optional["CLIPEmbedder"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "CLIPEmbedder":
        if cls._instance is None:
            with cls._lock:
                # 더블-체크 락킹
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._model = None
        self._preprocess = None
        self._tokenizer = None
        self._device = None
        self._initialized = True

    # ── 모델 로드 (lazy) ──

    def _ensure_loaded(self) -> None:
        """모델이 아직 로드되지 않았으면 로드한다."""
        if self._model is not None:
            return

        import torch
        import open_clip

        # 디바이스 결정: CUDA 가능하면 GPU, 아니면 CPU
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info("CLIP 모델 로드 중: ViT-L-14 (pretrained=openai) -> %s", self._device)

        model, _, preprocess = open_clip.create_model_and_transforms(
            "ViT-L-14",
            pretrained="openai",
            device=self._device,
        )
        model.eval()

        # GPU에서 float16 으로 메모리 절약 (CPU에서는 float32 유지)
        if self._device.type == "cuda":
            model = model.half()

        self._model = model
        self._preprocess = preprocess
        self._tokenizer = open_clip.get_tokenizer("ViT-L-14")

        logger.info("CLIP 모델 로드 완료 (device=%s)", self._device)

    # ── 임베딩 추출 ──

    def extract(
        self,
        image: np.ndarray,
        bbox: Optional[tuple] = None,
    ) -> np.ndarray:
        """
        이미지(BGR 또는 RGB numpy 배열)에서 768차원 임베딩을 추출한다.

        Args:
            image: (H, W, 3) numpy 배열.
            bbox: (x, y, w, h) 크롭 영역. 제공되면 해당 영역만 사용.

        Returns:
            L2 정규화된 768차원 float32 numpy 배열.
        """
        import torch

        self._ensure_loaded()

        # bbox 가 주어지면 크롭
        if bbox is not None:
            x, y, w, h = bbox
            image = image[y : y + h, x : x + w]

        # numpy(BGR) -> PIL(RGB)
        if image.ndim == 3 and image.shape[2] == 3:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = image

        pil_image = Image.fromarray(image_rgb)

        # CLIP 전처리 (리사이즈, 정규화 등)
        input_tensor = self._preprocess(pil_image).unsqueeze(0).to(self._device)

        # float16 모드일 때 입력도 맞춰줌
        if self._device.type == "cuda":
            input_tensor = input_tensor.half()

        # 추론 (그래디언트 비활성화)
        with torch.no_grad():
            features = self._model.encode_image(input_tensor)

        # CPU로 이동 후 numpy 변환
        embedding = features.squeeze(0).float().cpu().numpy()

        # L2 정규화
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding.astype(np.float32)


# ─────────────────────────────────────────────
#  얼굴 크롭 유틸리티
# ─────────────────────────────────────────────

def crop_face(
    image: np.ndarray,
    landmarks: list,
    padding: float = 0.3,
) -> np.ndarray:
    """
    MediaPipe 랜드마크를 이용하여 얼굴 영역을 크롭한다.
    앵커 이미지와 사용자 이미지 간 도메인 갭을 최소화하기 위해
    일관된 패딩과 크롭 방식을 적용한다.

    Args:
        image: (H, W, 3) numpy 배열 (BGR).
        landmarks: MediaPipe 468개 랜드마크 리스트.
                   각 원소는 [x, y, z] (정규화 좌표 0~1) 또는
                   .x, .y 속성을 가진 객체.
        padding: 바운딩 박스 확장 비율 (기본값 0.3 = 30%).

    Returns:
        크롭된 얼굴 영역 numpy 배열.
    """
    h, w = image.shape[:2]

    # 랜드마크에서 x, y 좌표 추출 (객체 또는 리스트 둘 다 지원)
    xs, ys = [], []
    for lm in landmarks:
        if hasattr(lm, "x"):
            xs.append(lm.x)
            ys.append(lm.y)
        else:
            xs.append(lm[0])
            ys.append(lm[1])

    # 정규화 좌표 -> 픽셀 좌표
    x_min = int(min(xs) * w)
    x_max = int(max(xs) * w)
    y_min = int(min(ys) * h)
    y_max = int(max(ys) * h)

    # 패딩 적용 (도메인 갭 최소화를 위해 충분한 컨텍스트 포함)
    bbox_w = x_max - x_min
    bbox_h = y_max - y_min
    pad_x = int(bbox_w * padding)
    pad_y = int(bbox_h * padding)

    x_min = max(0, x_min - pad_x)
    y_min = max(0, y_min - pad_y)
    x_max = min(w, x_max + pad_x)
    y_max = min(h, y_max + pad_y)

    return image[y_min:y_max, x_min:x_max]


# ─────────────────────────────────────────────
#  Mock 임베딩 (WoZ / 테스트용)
# ─────────────────────────────────────────────

def mock_embedding(image_bytes: bytes) -> np.ndarray:
    """
    WoZ 단계 및 테스트용 결정적 의사(pseudo) 임베딩 생성.
    이미지 해시로부터 768차원 벡터를 재현 가능하게 생성한다.

    실제 미적 임베딩이 아님 -- CLIP 파이프라인 통합 전까지의 대체용.

    Args:
        image_bytes: 원본 이미지 바이트 데이터.

    Returns:
        L2 정규화된 768차원 float32 numpy 배열.
    """
    h = hashlib.sha256(image_bytes).digest()
    seed = int.from_bytes(h[:4], "big")
    rng = np.random.RandomState(seed)
    emb = rng.randn(768).astype(np.float32)
    return emb / (np.linalg.norm(emb) + 1e-8)
