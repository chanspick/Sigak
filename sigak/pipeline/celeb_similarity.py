"""SIGAK Celebrity Anchor Similarity — PI-B 신규.

`type_anchors.json` 가 8 유형만 다루는 반면, `data/embeddings/female/` 에는
유형 외에도 셀럽 16명 .npy 가 존재. 본 모듈은 그 셀럽 매칭을 담당한다.

분리 이유:
  - 유형 매칭은 "유저가 어느 유형에 가까운가" (3축 좌표 비교 포함)
  - 셀럽 매칭은 "유저와 닮은 인물 top-N" (CLIP cosine 만, 좌표/축 차이 불필요)
  - 한 함수에 섞으면 가중치 / 메타 / 출력 형태가 달라 가독성 저하

법적 안전:
  - 셀럽 이름은 "외부 reference"이 아니라 유저-셀럽 유사도 % 만 노출 (v1 정책).
  - 셀럽 사진 자체를 리포트에 노출하지 않음 (image_files 부재).

v1 범위: female only (male 셀럽 .npy 미수집).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np


logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent / "data"
_CELEB_META_PATH = _DATA_DIR / "celeb_anchors_meta.json"
_EMBEDDINGS_DIR = _DATA_DIR / "embeddings"


# ─────────────────────────────────────────────
#  데이터 모델
# ─────────────────────────────────────────────

@dataclass(frozen=True)
class CelebMatch:
    """유저 ↔ 셀럽 cosine similarity top-N 단일 결과."""
    key: str                    # "jang_wonyoung"
    name_kr: str                # "장원영"
    name_en: str
    group: Optional[str]
    similarity: float           # raw cosine [-1, 1]
    similarity_pct: int         # UI용 0-100 (linearized: (sim+1)/2*100)


# ─────────────────────────────────────────────
#  메타 / 임베딩 로더 (캐싱)
# ─────────────────────────────────────────────

_meta_cache: Optional[dict] = None


def load_celeb_meta() -> dict:
    """celeb_anchors_meta.json 로드 + 캐싱."""
    global _meta_cache
    if _meta_cache is not None:
        return _meta_cache

    if not _CELEB_META_PATH.exists():
        logger.warning("celeb_anchors_meta.json 없음: %s", _CELEB_META_PATH)
        _meta_cache = {"celebs": {}, "dimension": 768, "similarity_threshold": 0.3}
        return _meta_cache

    with open(_CELEB_META_PATH, encoding="utf-8") as f:
        _meta_cache = json.load(f)
    return _meta_cache


def reload_celeb_meta() -> dict:
    """캐시 무효화 후 재로드. 테스트용."""
    global _meta_cache
    _meta_cache = None
    return load_celeb_meta()


def load_celeb_embeddings(gender: str) -> dict[str, np.ndarray]:
    """celeb_anchors_meta 의 셀럽 .npy 를 로드.

    type_*.npy 는 무시 (similarity.py 가 다룸).
    차원이 meta.dimension 과 다르면 경고 + 건너뜀.

    Returns:
        {celeb_key: 768d L2-normalized embedding}
    """
    meta = load_celeb_meta()
    dimension = int(meta.get("dimension", 768))
    emb_dir = _EMBEDDINGS_DIR / gender
    result: dict[str, np.ndarray] = {}

    if not emb_dir.exists():
        logger.warning("embeddings/%s 디렉토리 없음", gender)
        return result

    for key, info in meta.get("celebs", {}).items():
        if info.get("gender") != gender:
            continue
        npy_path = emb_dir / f"{key}.npy"
        if not npy_path.exists():
            logger.debug("celeb embedding 없음: %s", npy_path.name)
            continue

        try:
            emb = np.load(str(npy_path))
        except Exception:
            logger.warning("celeb npy 로드 실패: %s", npy_path.name)
            continue

        if emb.ndim != 1 or emb.shape[0] != dimension:
            logger.warning(
                "celeb '%s' 차원 불일치 (기대 %d, 실제 %s) — 건너뜀",
                key, dimension, emb.shape,
            )
            continue
        result[key] = emb.astype(np.float32)

    if result:
        logger.info("[%s] celeb 임베딩 %d명 로드", gender, len(result))
    else:
        logger.info("[%s] celeb 임베딩 0명 — top-3 빈 리스트 반환", gender)
    return result


# ─────────────────────────────────────────────
#  Top-K 매칭
# ─────────────────────────────────────────────

def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    """이미 L2 정규화된 벡터면 dot product 와 동일."""
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def find_similar_celebs(
    user_embedding: Optional[np.ndarray],
    gender: str,
    *,
    top_k: int = 3,
    threshold: Optional[float] = None,
) -> list[CelebMatch]:
    """유저 CLIP 임베딩과 가장 유사한 셀럽 top-K 반환.

    user_embedding 가 None 이거나 gender 셀럽이 0명이면 빈 리스트.
    threshold 미만 항목은 제외 (default = meta.similarity_threshold).
    """
    if user_embedding is None:
        return []
    if user_embedding.ndim != 1:
        logger.warning("user_embedding 형태 이상: %s — 빈 리스트 반환", user_embedding.shape)
        return []

    meta = load_celeb_meta()
    if threshold is None:
        threshold = float(meta.get("similarity_threshold", 0.3))

    celeb_embs = load_celeb_embeddings(gender)
    if not celeb_embs:
        return []

    matches: list[CelebMatch] = []
    for key, emb in celeb_embs.items():
        info = meta["celebs"].get(key, {})
        sim = _cosine(user_embedding, emb)
        if sim < threshold:
            continue
        # cosine [-1, 1] → percentage [0, 100] (linearized)
        pct = int(round((sim + 1) / 2 * 100))
        pct = max(0, min(100, pct))
        matches.append(CelebMatch(
            key=key,
            name_kr=info.get("name_kr", key),
            name_en=info.get("name_en", key),
            group=info.get("group"),
            similarity=round(sim, 4),
            similarity_pct=pct,
        ))

    matches.sort(key=lambda m: m.similarity, reverse=True)
    return matches[:top_k]
