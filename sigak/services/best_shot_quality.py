"""Best Shot 품질 heuristic 필터 (Phase K3).

ML 모델 없이 Pillow 만 사용. Sonnet 호출 전 1차 축소용.

Signals:
  1. blur_score       — Laplacian variance (흔들림 / 초점 안 맞음)
  2. exposure_score   — luminance histogram (너무 어두움 / 과노출)
  3. size_score       — 너무 작은 이미지 감점

최종 quality_score ∈ [0, 1] = weighted avg.
score ≥ cutoff (기본 0.35) → 통과.
"""
from __future__ import annotations

import io
import logging
import math
from typing import Optional

from PIL import Image, ImageFilter, ImageStat


logger = logging.getLogger(__name__)


MIN_DIMENSION = 400       # 가장 짧은 변 이 값 미만이면 강한 감점
IDEAL_DIMENSION = 1080    # 이상이면 size 만점


class QualityResult:
    """단일 사진 품질 판정 결과."""

    __slots__ = ("blur_score", "exposure_score", "size_score", "quality_score", "passed")

    def __init__(
        self,
        blur_score: float,
        exposure_score: float,
        size_score: float,
        cutoff: float,
    ):
        self.blur_score = blur_score
        self.exposure_score = exposure_score
        self.size_score = size_score
        # 가중 평균: blur 40% / exposure 40% / size 20%
        self.quality_score = (
            blur_score * 0.4
            + exposure_score * 0.4
            + size_score * 0.2
        )
        self.passed = self.quality_score >= cutoff


def score_photo(image_bytes: bytes, cutoff: float = 0.35) -> Optional[QualityResult]:
    """image_bytes → QualityResult. 파싱 실패 / 이상 이미지는 None."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.load()
    except Exception:
        logger.warning("image open failed — skipping")
        return None

    # RGB 변환 (heuristic 단순화)
    try:
        rgb = img.convert("RGB")
    except Exception:
        logger.warning("image convert failed")
        return None

    blur = _blur_score(rgb)
    exposure = _exposure_score(rgb)
    size = _size_score(rgb.width, rgb.height)

    return QualityResult(blur, exposure, size, cutoff)


# ─────────────────────────────────────────────
#  Individual scorers
# ─────────────────────────────────────────────

def _blur_score(img: Image.Image) -> float:
    """Laplacian variance proxy.

    Pillow 기본 필터 조합으로 edge 강도 분산 추정. 실제 OpenCV 의 Laplacian
    variance 와 완벽 일치하진 않지만 경향은 비슷. 0-1 로 normalize.
    """
    # thumbnail + grayscale 로 빠른 추정 (모바일 고해상도 300+장 대응)
    small = img.copy()
    small.thumbnail((512, 512))
    gray = small.convert("L")
    edge = gray.filter(ImageFilter.FIND_EDGES)
    stat = ImageStat.Stat(edge)
    stddev = stat.stddev[0] if stat.stddev else 0.0
    # 경험적 normalize — stddev 15 이하는 흐림 (0 점), 50+ 는 선명 (1 점)
    if stddev <= 15:
        return 0.0
    if stddev >= 50:
        return 1.0
    return (stddev - 15) / 35.0


def _exposure_score(img: Image.Image) -> float:
    """luminance histogram 기반 — 평균 밝기 극단치 penalize.

    이상적 평균 luma: 100~170 (0-255). 밖으로 갈수록 감점.
    """
    gray = img.convert("L")
    stat = ImageStat.Stat(gray)
    mean = stat.mean[0] if stat.mean else 128.0
    # 120 중심으로 가우시안 감점. stddev = 50 으로 완만.
    # 정확한 정규분포 확률 아닌 bounded score.
    distance = abs(mean - 120.0)
    if distance <= 20:
        return 1.0
    if distance >= 100:
        return 0.0
    return max(0.0, 1.0 - (distance - 20) / 80.0)


def _size_score(width: int, height: int) -> float:
    """가장 짧은 변 기준 score."""
    short = min(width, height)
    if short < MIN_DIMENSION:
        return 0.0
    if short >= IDEAL_DIMENSION:
        return 1.0
    # linear
    return (short - MIN_DIMENSION) / (IDEAL_DIMENSION - MIN_DIMENSION)


# ─────────────────────────────────────────────
#  Batch helper — heuristic 축소 단계
# ─────────────────────────────────────────────

def filter_top_n(
    items: list[tuple[str, bytes]],
    *,
    max_count: int,
    cutoff: float = 0.35,
) -> list[tuple[str, bytes, QualityResult]]:
    """(photo_id, bytes) 리스트 → 품질 상위 max_count 통과 리스트.

    반환: (id, bytes, QualityResult) — quality_score 내림차순 정렬.
    cutoff 미달은 제외. max_count 상한.
    """
    scored: list[tuple[str, bytes, QualityResult]] = []
    for photo_id, data in items:
        result = score_photo(data, cutoff=cutoff)
        if result is None or not result.passed:
            continue
        scored.append((photo_id, data, result))
    scored.sort(key=lambda t: t[2].quality_score, reverse=True)
    return scored[:max_count]
