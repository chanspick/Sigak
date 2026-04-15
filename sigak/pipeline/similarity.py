"""
SIGAK Type Similarity Engine

AI 유형 앵커 임베딩과 유저 임베딩 간 코사인 유사도를 계산하여
가장 유사한 유형 top-K를 반환한다.

두 가지 모드:
  1. CLIP 모드: .npy 임베딩 파일이 있으면 코사인 유사도 사용
  2. 좌표 폴백: 임베딩 없으면 coords 기반 유클리드 거리 사용

v2: type_anchors.json 전환 (AI 유형 앵커, 법적 리스크 제거)
v3: 3축 체계 전환 (shape/volume/age), coords 필드 사용
"""
import json
import logging
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# 기본 경로
_DATA_DIR = Path(__file__).parent.parent / "data"
_ANCHORS_JSON = _DATA_DIR / "type_anchors.json"
_EMBEDDINGS_DIR = _DATA_DIR / "embeddings"


# ─────────────────────────────────────────────
#  앵커 데이터 로더
# ─────────────────────────────────────────────

_anchors_cache: Optional[dict] = None


def load_anchors() -> dict:
    """type_anchors.json을 로드하고 캐싱한다."""
    global _anchors_cache
    if _anchors_cache is not None:
        return _anchors_cache

    if not _ANCHORS_JSON.exists():
        logger.warning("type_anchors.json 파일 없음: %s", _ANCHORS_JSON)
        return {"anchors": {}, "dimension": 768}

    with open(_ANCHORS_JSON, encoding="utf-8") as f:
        _anchors_cache = json.load(f)

    return _anchors_cache


def reload_anchors() -> dict:
    """캐시를 무효화하고 다시 로드한다."""
    global _anchors_cache
    _anchors_cache = None
    return load_anchors()


def load_anchor_embeddings(gender: str) -> dict[str, np.ndarray]:
    """
    저장된 앵커 임베딩(.npy)을 로드한다.

    Returns:
        {type_key: 768d numpy 배열}
    """
    anchors_data = load_anchors()
    dimension = anchors_data.get("dimension", 768)
    emb_dir = _EMBEDDINGS_DIR / gender
    result: dict[str, np.ndarray] = {}

    for key, info in anchors_data.get("anchors", {}).items():
        if info.get("gender") != gender:
            continue

        # embedding_path가 있으면 해당 경로, 없으면 기본 경로
        emb_path = info.get("embedding_path")
        if emb_path:
            npy_path = Path(emb_path)
        else:
            npy_path = emb_dir / f"{key}.npy"

        if not npy_path.exists():
            continue

        emb = np.load(str(npy_path))

        # 차원 검증
        if emb.shape[0] != dimension:
            logger.warning(
                "%s 임베딩 차원 불일치: 기대 %d, 실제 %d. 건너뜀.",
                key, dimension, emb.shape[0],
            )
            continue

        result[key] = emb

    if result:
        logger.info("[%s] %d명 앵커 임베딩 로드 완료", gender, len(result))
    else:
        logger.info("[%s] 앵커 임베딩 없음 — 좌표 폴백 모드", gender)

    return result


# ─────────────────────────────────────────────
#  NER 정규화
# ─────────────────────────────────────────────

def normalize_anchor_name(text: str) -> Optional[str]:
    """
    유저 입력 텍스트에서 앵커 이름을 정규화된 key로 변환한다.

    "따뜻한 첫사랑" → "type_1"
    "타입4" → "type_4"
    "알 수 없음" → None
    """
    anchors_data = load_anchors()
    text_lower = text.lower().strip()

    for key, info in anchors_data.get("anchors", {}).items():
        candidates = [
            info["name_kr"],
            info["name_en"].lower(),
            key,
        ]
        candidates.extend(info.get("aliases", []))

        for candidate in candidates:
            if text_lower == candidate.lower().strip():
                return key

    return None




def extract_anchor_mentions(text: str) -> list[str]:
    """
    텍스트에서 언급된 모든 앵커 key를 추출한다.
    인터뷰 응답처럼 여러 유형이 언급될 수 있는 경우 사용.

    "따뜻한 첫사랑이랑 차가운 우아함 사이" → ["type_1", "type_7"]
    """
    anchors_data = load_anchors()
    found: list[str] = []
    text_lower = text.lower()

    for key, info in anchors_data.get("anchors", {}).items():
        candidates = [
            info["name_kr"],
            info["name_en"].lower(),
        ]
        candidates.extend(info.get("aliases", []))

        for candidate in candidates:
            if candidate.lower() in text_lower:
                if key not in found:
                    found.append(key)
                break

    return found




# ─────────────────────────────────────────────
#  코사인 유사도 계산
# ─────────────────────────────────────────────

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """두 벡터 간 코사인 유사도를 계산한다. 이미 L2 정규화된 경우 dot product와 동일."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _coord_similarity(user_coords: dict[str, float], ref_coords: dict[str, float]) -> float:
    """
    좌표 기반 유사도 (폴백용).
    3축 유클리드 거리를 가우시안 커널로 변환하여 현실적 유사도 산출.

    기존 선형 스케일링은 대부분 70%+ 로 나와서 비현실적이었음.
    가우시안: 거리 0 → 0.90, 거리 0.5 → 0.78, 거리 1.0 → 0.61, 거리 2.0 → 0.25
    """
    axes = ["shape", "volume", "age"]
    dist_sq = sum(
        (user_coords.get(ax, 0) - ref_coords.get(ax, 0)) ** 2
        for ax in axes
    )
    # 가우시안 커널: exp(-dist² / 2σ²), σ=1.2로 설정
    # σ=1.2이면 거리 1.0에서 ~0.66, 거리 1.5에서 ~0.46
    sigma = 1.2
    sim = float(np.exp(-dist_sq / (2 * sigma * sigma)))
    # 0~1 범위를 0.15~0.90으로 스케일링 (좌표만으로 90% 이상은 비현실적)
    return 0.15 + sim * 0.75


# ─────────────────────────────────────────────
#  Top-K 유사 유형 검색
# ─────────────────────────────────────────────

def find_similar_types(
    user_embedding: Optional[np.ndarray],
    user_coords: dict[str, float],
    gender: str,
    top_k: int = 3,
) -> list[dict]:
    """
    유저와 가장 유사한 앵커 유형 top-K를 반환한다.

    CLIP 임베딩이 있으면 코사인 유사도, 없으면 좌표 기반 거리 사용.

    Args:
        user_embedding: 유저 사진의 CLIP 768d 임베딩 (없으면 None)
        user_coords: 유저의 3축 좌표
        gender: "female" 또는 "male"
        top_k: 반환할 유형 수

    Returns:
        [
            {
                "key": "type_1",
                "name_kr": "따뜻한 첫사랑",
                "name_en": "Warm First Love",
                "group": null,
                "similarity": 0.78,
                "similarity_pct": 78,
                "mode": "clip" | "coord",
                "axis_delta": {"shape": 0.12, ...},
                "description_kr": "...",
            },
            ...
        ]
    """
    anchors_data = load_anchors()
    threshold = anchors_data.get("similarity_threshold", 0.3)
    anchor_embeddings = load_anchor_embeddings(gender)
    use_clip = user_embedding is not None and len(anchor_embeddings) > 0

    results = []

    for key, info in anchors_data.get("anchors", {}).items():
        if info.get("gender") != gender:
            continue

        ref_coords = info.get("coords", {})

        # 유사도 계산
        if use_clip and key in anchor_embeddings:
            sim = cosine_similarity(user_embedding, anchor_embeddings[key])
            # 코사인 유사도 [-1, 1] → 백분율 [0, 100]으로 스케일링
            sim_pct = int(round((sim + 1) / 2 * 100))
            sim_pct = max(0, min(100, sim_pct))
            mode = "clip"
        else:
            sim = _coord_similarity(user_coords, ref_coords)
            sim_pct = int(round(sim * 100))
            mode = "coord"

        # 축별 차이 벡터
        axis_delta = {}
        for ax in ["shape", "volume", "age"]:
            axis_delta[ax] = round(
                user_coords.get(ax, 0) - ref_coords.get(ax, 0), 3
            )

        results.append({
            "key": key,
            "name_kr": info["name_kr"],
            "name_en": info.get("name_en", ""),
            "group": info.get("group"),
            "similarity": round(sim, 4),
            "similarity_pct": sim_pct,
            "mode": mode,
            "axis_delta": axis_delta,
            "community_score": info.get("community_score"),
            "description_kr": info.get("description_kr", ""),
            "type_id": info.get("type_id"),
        })

    # 유사도 내림차순 정렬
    results.sort(key=lambda x: x["similarity"], reverse=True)

    # threshold 적용
    results = [r for r in results if r["similarity"] >= threshold]

    return results[:top_k]


# ─────────────────────────────────────────────
#  티저 유형 선택
# ─────────────────────────────────────────────

def select_teaser_type(similar_types: list[dict]) -> Optional[dict]:
    """
    티저(무료 구간)에 노출할 유형 1개를 선택한다.

    전략: similarity 70% + community_score 30%
    → 유사도 높으면서 인지도 높은 유형이 티저에 → 전환율 최적화
    """
    if not similar_types:
        return None

    anchors_data = load_anchors()
    weights = anchors_data.get("teaser_weights", {"similarity": 0.7, "community": 0.3})
    w_sim = weights["similarity"]
    w_com = weights["community"]

    best = None
    best_score = -1

    for type_item in similar_types:
        score = type_item["similarity"] * w_sim
        cs = type_item.get("community_score")
        if cs is not None:
            score += (cs / 100) * w_com
        if score > best_score:
            best_score = score
            best = type_item

    return best


# ─────────────────────────────────────────────
#  앵커 프로젝터 빌더 (coordinate.py 연동)
# ─────────────────────────────────────────────

def build_anchor_poles(gender: str) -> dict[str, dict[str, np.ndarray]]:
    """
    앵커 임베딩을 coords 값에 따라 극별 평균 벡터로 집계한다.
    coordinate.py의 AnchorProjector.fit()에 넘길 수 있는 형태로 반환.

    coords 값이 음수이면 negative 극, 양수이면 positive 극으로 분류.

    Returns:
        {
            "shape": {
                "negative": np.array(768d),  # soft 극 평균
                "positive": np.array(768d),  # sharp 극 평균
            },
            ...
        }
    """
    anchors_data = load_anchors()
    anchor_embeddings = load_anchor_embeddings(gender)

    if not anchor_embeddings:
        return {}

    # 축별 극성 수집
    poles: dict[str, dict[str, list[np.ndarray]]] = {}
    for ax_name in ["shape", "volume", "age"]:
        poles[ax_name] = {"negative": [], "positive": []}

    for key, info in anchors_data.get("anchors", {}).items():
        if info.get("gender") != gender:
            continue
        if key not in anchor_embeddings:
            continue

        emb = anchor_embeddings[key]
        coords = info.get("coords", {})

        for ax_name in ["shape", "volume", "age"]:
            val = coords.get(ax_name, 0)
            if val < 0:
                poles[ax_name]["negative"].append(emb)
            elif val > 0:
                poles[ax_name]["positive"].append(emb)

    # 극별 평균 계산
    result: dict[str, dict[str, np.ndarray]] = {}
    for ax_name, pole_data in poles.items():
        neg_list = pole_data["negative"]
        pos_list = pole_data["positive"]

        if not neg_list or not pos_list:
            logger.warning(
                "[%s] %s 축: negative=%d, positive=%d — 양쪽 모두 필요. 건너뜀.",
                gender, ax_name, len(neg_list), len(pos_list),
            )
            continue

        neg_mean = np.mean(neg_list, axis=0).astype(np.float32)
        pos_mean = np.mean(pos_list, axis=0).astype(np.float32)

        result[ax_name] = {
            "negative": neg_mean,
            "positive": pos_mean,
        }
        logger.info(
            "[%s] %s 축: negative %d명, positive %d명",
            gender, ax_name, len(neg_list), len(pos_list),
        )

    return result


# ─────────────────────────────────────────────
#  LLM 프롬프트용 유형 레퍼런스 생성
# ─────────────────────────────────────────────

def get_type_reference_prompt(gender: str = "female") -> str:
    """
    LLM 프롬프트에 삽입할 유형 좌표 레퍼런스 문자열을 생성한다.

    Returns:
        "- 따뜻한 첫사랑 (Type 1): shape=-0.8, volume=-0.7, age=-0.8 (부드러운, 은은한, 발랄한)"
    """
    from pipeline.coordinate import get_axis_labels as _get_axis_labels

    anchors_data = load_anchors()
    lines = []

    # coordinate.py axis_config.yaml 기준 (SSOT)
    # -1 = low_kr, +1 = high_kr
    axis_labels = {}
    for ax_name in ["shape", "volume", "age"]:
        labels = _get_axis_labels(ax_name)
        axis_labels[ax_name] = {-1: labels["low"], 1: labels["high"]}

    for key, info in anchors_data.get("anchors", {}).items():
        if info.get("gender") != gender:
            continue

        coords = info.get("coords", {})
        type_id = info.get("type_id", "?")

        coord_str = ", ".join(
            f"{ax}={coords.get(ax, 0)}" for ax in ["shape", "volume", "age"]
        )

        traits = []
        for ax, val in coords.items():
            if abs(val) >= 0.4:
                labels = axis_labels.get(ax, {})
                label = labels.get(1 if val > 0 else -1, "")
                if label:
                    traits.append(label)
        trait_str = ", ".join(traits) if traits else "중립적"

        aliases = info.get("aliases", [])
        alias_str = f" (별명: {', '.join(aliases[:3])})" if aliases else ""

        desc = info.get("description_kr", "")
        desc_str = f" — {desc}" if desc else ""

        lines.append(
            f"- {info['name_kr']} (Type {type_id}): {coord_str} ({trait_str}){alias_str}{desc_str}"
        )

    return "\n".join(lines)


