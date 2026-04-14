"""
SIGAK Cluster Discovery & Labeling Engine

앵커 유형의 **구조적 얼굴 특징**(InsightFace/MediaPipe 랜드마크 기반)에서
자연 클러스터를 발견하고, 3축 좌표 특성(shape/volume/age) + community_score 기반으로 라벨링한다.

v2: CLIP 임베딩 대신 type_features_cache.json의 13개 수치 특징 벡터를
    StandardScaler 정규화 → K-Means 클러스터링하는 structural 모드를 기본값으로 전환.
    PCA loadings로 각 축에 대한 원래 특징의 기여도를 확인 가능.

Usage:
    # Phase 2a: 클러스터 발견 (구조적 특징 기반, 기본)
    from pipeline.cluster import discover_clusters, save_cluster_labels
    clusters = discover_clusters(gender="female")  # mode="structural" 기본
    save_cluster_labels(clusters)

    # PCA loadings 확인
    from pipeline.cluster import compute_pca_loadings
    loadings = compute_pca_loadings(gender="female")

    # Phase 2b: 유저 분류
    from pipeline.cluster import classify_user
    result = classify_user(user_coords, gender="female")
    # → {"cluster_id": "cool_goddess", "label": "Cool Goddess", "representative": "제니", ...}
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Optional

import numpy as np


# ─────────────────────────────────────────────
#  자동 라벨링 규칙
# ─────────────────────────────────────────────

# 축 부호 조합 → 클러스터 라벨 후보
# 각 튜플: (shape_sign, volume_sign, age_sign)
# "any"는 해당 축 값이 약해서 (|v| < 0.3) 방향성이 불분명한 경우
LABEL_CANDIDATES = [
    {
        "id": "cool_goddess",
        "label_kr": "쿨 갓데스",
        "label_en": "Cool Goddess",
        "signature": {"shape": "sharp", "volume": "bold", "age": "mature"},
        "description": "날카로운 이목구비 + 강렬한 볼륨 + 성숙한 분위기의 미감",
        "keywords": ["시크", "도시적", "하이엔드", "강렬한 눈매"],
    },
    {
        "id": "warm_natural",
        "label_kr": "웜 내추럴",
        "label_en": "Warm Natural",
        "signature": {"shape": "soft", "volume": "subtle", "age": "any"},
        "description": "부드러운 라인 + 은은한 볼륨 + 자연스러운 매력",
        "keywords": ["친근", "청순", "자연스러운", "첫사랑"],
    },
    {
        "id": "ice_princess",
        "label_kr": "아이스 프린세스",
        "label_en": "Ice Princess",
        "signature": {"shape": "sharp", "volume": "bold", "age": "fresh"},
        "description": "날카로운 라인 + 강렬한 볼륨 + 프레시함이 공존하는 차가운 아름다움",
        "keywords": ["신비로운", "몽환", "청량+시크", "인형같은"],
    },
    {
        "id": "elegant_classic",
        "label_kr": "엘레강트 클래식",
        "label_en": "Elegant Classic",
        "signature": {"shape": "any", "volume": "subtle", "age": "mature"},
        "description": "절제된 우아함 + 성숙한 분위기",
        "keywords": ["단아", "고급스러운", "배우같은", "클래식"],
    },
    {
        "id": "fresh_face",
        "label_kr": "프레시 페이스",
        "label_en": "Fresh Face",
        "signature": {"shape": "any", "volume": "any", "age": "fresh"},
        "description": "연령대가 주는 생기와 청량함이 핵심",
        "keywords": ["청량", "어린", "생기발랄", "10대~20대초"],
    },
    {
        "id": "soft_bold",
        "label_kr": "소프트 볼드",
        "label_en": "Soft Bold",
        "signature": {"shape": "soft", "volume": "bold", "age": "any"},
        "description": "부드러운 골격에 강렬한 매력이 공존하는 반전 미감",
        "keywords": ["반전매력", "글래머러스", "자유분방", "화려하지만 부드러운"],
    },
    {
        "id": "bold_queen",
        "label_kr": "볼드 퀸",
        "label_en": "Bold Queen",
        "signature": {"shape": "any", "volume": "bold", "age": "mature"},
        "description": "압도적인 존재감과 대담한 스타일의 미감",
        "keywords": ["카리스마", "퍼포먼스", "무대형", "독보적"],
    },
]

# 축 부호 판별 기준
AXIS_SIGN_THRESHOLD = 0.25  # 이 값 미만이면 "any"

# ─────────────────────────────────────────────
#  구조적 특징 기반 클러스터링 설정
# ─────────────────────────────────────────────

# 클러스터링에 사용할 13개 수치 특징 (얼굴 구조 실측 데이터)
STRUCTURAL_FEATURES = [
    "jaw_angle",
    "cheekbone_prominence",
    "eye_width_ratio",
    "eye_spacing_ratio",
    "eye_ratio",
    "eye_tilt",
    "nose_length_ratio",
    "lip_fullness",
    "face_length_ratio",
    "forehead_ratio",
    "brow_arch",
    "philtrum_ratio",
    "symmetry_score",
]

_FEATURES_CACHE_PATH = Path(__file__).parent.parent / "data" / "type_features_cache.json"


def _load_structural_features(gender_keys: list[str]) -> tuple[np.ndarray, list[str]]:
    """
    type_features_cache.json에서 13개 수치 특징을 로드하고 StandardScaler로 정규화.

    Args:
        gender_keys: type_anchors.json의 앵커 키 목록

    Returns:
        (정규화된 특징 행렬 [N, 13], 실제 매칭된 키 목록)
    """
    if not _FEATURES_CACHE_PATH.exists():
        return np.array([]), []

    with open(_FEATURES_CACHE_PATH, encoding="utf-8") as f:
        features_data = json.load(f)

    matched_keys = []
    feature_rows = []

    for key in gender_keys:
        if key in features_data:
            feat = features_data[key]
            row = [feat.get(f, 0.0) for f in STRUCTURAL_FEATURES]
            feature_rows.append(row)
            matched_keys.append(key)

    if len(feature_rows) < 3:
        return np.array([]), matched_keys

    matrix = np.array(feature_rows, dtype=np.float64)

    # StandardScaler 정규화: (x - mean) / std
    mean = matrix.mean(axis=0)
    std = matrix.std(axis=0)
    std[std == 0] = 1.0  # 0-division 방지
    scaled = (matrix - mean) / std

    return scaled, matched_keys


# ─────────────────────────────────────────────
#  클러스터 라벨 저장/로드
# ─────────────────────────────────────────────

_CLUSTER_LABELS_PATH = Path(__file__).parent.parent / "data" / "cluster_labels.json"
_cluster_cache: dict | None = None


def load_cluster_labels() -> dict:
    """저장된 클러스터 라벨을 로드한다."""
    global _cluster_cache
    if _cluster_cache is not None:
        return _cluster_cache
    if _CLUSTER_LABELS_PATH.exists():
        with open(_CLUSTER_LABELS_PATH, encoding="utf-8") as f:
            _cluster_cache = json.load(f)
        return _cluster_cache
    _cluster_cache = {"clusters": [], "version": "0.0.0"}
    return _cluster_cache


def save_cluster_labels(cluster_data: dict) -> None:
    """클러스터 라벨을 JSON에 저장한다."""
    global _cluster_cache
    _cluster_cache = cluster_data
    _CLUSTER_LABELS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CLUSTER_LABELS_PATH, "w", encoding="utf-8") as f:
        json.dump(cluster_data, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────
#  클러스터 발견 (사진 임베딩 후 실행)
# ─────────────────────────────────────────────

def discover_clusters(
    gender: str = "female",
    method: str = "auto",
    n_clusters: Optional[int] = None,
    mode: str = "structural",
) -> dict:
    """
    앵커의 얼굴 구조 특징에서 자연 클러스터를 발견한다.

    Args:
        gender: "female" or "male"
        method: "kmeans", "hdbscan", or "auto" (데이터 크기에 따라 선택)
        n_clusters: kmeans일 때 클러스터 수 (None이면 자동, structural 모드에서는 4~5)
        mode: "structural" (기본, 13개 구조적 특징) or "coords" (3축 좌표 폴백)
              ※ CLIP 임베딩 모드("clip")는 폐기됨 — 사진 분위기가 아닌 얼굴 구조로 클러스터링

    Returns:
        {
            "version": "2.0.0",
            "gender": "female",
            "method": str,
            "mode": "structural",
            "feature_names": [...],  # structural 모드일 때 사용된 특징명
            "clusters": [...],
            "pca_loadings": {...},  # structural 모드일 때 PCA 기여도
        }
    """
    # 앵커 데이터 로드
    anchors_path = Path(__file__).parent.parent / "data" / "type_anchors.json"
    if not anchors_path.exists():
        return {"version": "0.0.0", "gender": gender, "method": "none", "clusters": []}

    with open(anchors_path, encoding="utf-8") as f:
        anchors_data = json.load(f)

    anchors = anchors_data.get("anchors", {})
    gender_anchors = {k: v for k, v in anchors.items() if v.get("gender") == gender}

    if len(gender_anchors) < 3:
        return {"version": "0.0.0", "gender": gender, "method": "insufficient", "clusters": []}

    # 좌표 행렬 구성 (라벨링용 — 모든 모드에서 필요)
    keys = sorted(gender_anchors.keys())
    coords_matrix = []
    for key in keys:
        rc = gender_anchors[key].get("coords", {})
        coords_matrix.append([
            rc.get("shape", 0),
            rc.get("volume", 0),
            rc.get("age", 0),
        ])
    coords_array = np.array(coords_matrix, dtype=np.float32)

    # ─── structural 모드: 구조적 특징 벡터 기반 클러스터링 ───
    pca_loadings = None
    feature_names = None

    if mode == "structural":
        scaled_features, matched_keys = _load_structural_features(keys)

        if len(matched_keys) >= 3:
            # 매칭된 키 기준으로 coords_array도 재정렬
            key_to_idx = {k: i for i, k in enumerate(keys)}
            matched_indices = [key_to_idx[k] for k in matched_keys]
            coords_array_matched = coords_array[matched_indices]
            keys = matched_keys

            # K-Means 클러스터링 (k=4~5, 구조적 특징으로)
            k = n_clusters or min(5, max(4, _estimate_k(len(keys))))
            if k > len(keys):
                k = max(2, len(keys) // 2)
            labels = _cluster_kmeans(scaled_features, k)
            cluster_method = "kmeans"

            # PCA loadings 계산
            pca_loadings = _compute_pca_loadings(scaled_features)
            feature_names = list(STRUCTURAL_FEATURES)

            # 클러스터 구성
            clusters = _build_cluster_info(keys, labels, gender_anchors, coords_array_matched)

            result = {
                "version": "2.0.0",
                "gender": gender,
                "method": cluster_method,
                "mode": "structural",
                "feature_names": feature_names,
                "n_anchors": len(keys),
                "n_clusters": len(clusters),
                "clusters": clusters,
                "pca_loadings": pca_loadings,
            }

            save_cluster_labels(result)
            return result
        else:
            # structural 특징 부족 → coords 폴백
            mode = "coords"

    # ─── coords 모드: 3축 좌표 기반 폴백 ───
    # (CLIP 임베딩 모드는 폐기 — "사진 분위기"가 아닌 "얼굴 구조"로 클러스터링해야 함)
    #
    # [폐기된 CLIP 임베딩 코드]
    # embeddings_dir = Path(__file__).parent.parent / "data" / "embeddings" / gender
    # use_embeddings = False
    # emb_matrix = None
    # if embeddings_dir.exists():
    #     emb_list = []
    #     emb_keys = []
    #     for key in keys:
    #         npy_path = embeddings_dir / f"{key}.npy"
    #         if npy_path.exists():
    #             emb = np.load(str(npy_path))
    #             emb_list.append(emb)
    #             emb_keys.append(key)
    #     if len(emb_list) >= len(keys) * 0.8:
    #         emb_matrix = np.stack(emb_list)
    #         use_embeddings = True
    #         keys = emb_keys
    # clustering_input = emb_matrix if use_embeddings else coords_array

    clustering_input = coords_array
    cluster_method = method

    if method == "auto":
        if len(keys) < 8:
            cluster_method = "manual"
        elif len(keys) < 20:
            cluster_method = "kmeans"
        else:
            cluster_method = "hdbscan"

    if cluster_method == "kmeans":
        labels = _cluster_kmeans(clustering_input, n_clusters or _estimate_k(len(keys)))
    elif cluster_method == "hdbscan":
        labels = _cluster_hdbscan(clustering_input)
    else:
        labels = _cluster_by_rules(keys, gender_anchors)

    clusters = _build_cluster_info(keys, labels, gender_anchors, coords_array)

    result = {
        "version": "2.0.0",
        "gender": gender,
        "method": cluster_method,
        "mode": "coords",
        "n_anchors": len(keys),
        "n_clusters": len(clusters),
        "clusters": clusters,
    }

    save_cluster_labels(result)
    return result


def _compute_pca_loadings(scaled_matrix: np.ndarray, n_components: int = 4) -> dict:
    """
    PCA loadings를 계산하여 각 주성분에 대한 원래 특징의 기여도를 반환.

    Returns:
        {
            "PC1": {"jaw_angle": 0.82, "cheekbone_prominence": 0.61, ...},
            "PC2": {...},
            ...
            "explained_variance_ratio": [0.35, 0.22, 0.15, 0.10],
        }
    """
    n_samples, n_features = scaled_matrix.shape
    n_components = min(n_components, n_samples, n_features)

    # 공분산 행렬 기반 PCA (sklearn 없이도 동작)
    try:
        from sklearn.decomposition import PCA
        pca = PCA(n_components=n_components)
        pca.fit(scaled_matrix)
        components = pca.components_  # [n_components, n_features]
        explained = pca.explained_variance_ratio_.tolist()
    except ImportError:
        # sklearn 없을 때 numpy SVD 사용
        cov = np.cov(scaled_matrix, rowvar=False)
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        # 내림차순 정렬
        idx = np.argsort(eigenvalues)[::-1][:n_components]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]
        components = eigenvectors.T  # [n_components, n_features]
        total_var = eigenvalues.sum()
        explained = (eigenvalues / total_var).tolist() if total_var > 0 else [0.0] * n_components

    result = {}
    for i in range(n_components):
        pc_name = f"PC{i + 1}"
        loadings = {}
        for j, feat_name in enumerate(STRUCTURAL_FEATURES):
            loadings[feat_name] = round(float(components[i, j]), 4)
        # 기여도 절대값 기준 내림차순 정렬
        result[pc_name] = dict(sorted(loadings.items(), key=lambda x: abs(x[1]), reverse=True))

    result["explained_variance_ratio"] = [round(v, 4) for v in explained]

    return result


def compute_pca_loadings(gender: str = "female", n_components: int = 4) -> dict | None:
    """
    공개 API: 구조적 특징의 PCA loadings를 계산하여 반환.

    각 주성분(PC)에 어떤 원래 특징이 가장 기여하는지 확인 가능.
    예: "PC1 = jaw_angle 0.82 + cheekbone 0.61 → shape 축"

    Args:
        gender: "female" or "male"
        n_components: 반환할 주성분 수 (기본 4)

    Returns:
        PCA loadings dict, 또는 데이터 부족 시 None
    """
    anchors_path = Path(__file__).parent.parent / "data" / "type_anchors.json"
    if not anchors_path.exists():
        return None

    with open(anchors_path, encoding="utf-8") as f:
        anchors_data = json.load(f)

    anchors = anchors_data.get("anchors", {})
    gender_keys = sorted(k for k, v in anchors.items() if v.get("gender") == gender)

    scaled_features, matched_keys = _load_structural_features(gender_keys)
    if len(matched_keys) < 3:
        return None

    return _compute_pca_loadings(scaled_features, n_components)


def _estimate_k(n: int) -> int:
    """데이터 크기에 맞는 적절한 K를 추정."""
    if n <= 6:
        return 2
    elif n <= 10:
        return 3
    elif n <= 15:
        return 4
    elif n <= 25:
        return 5
    else:
        return min(6, int(math.sqrt(n)))


def _cluster_kmeans(data: np.ndarray, k: int) -> list[int]:
    """K-Means 클러스터링. sklearn 없으면 간단 구현."""
    try:
        from sklearn.cluster import KMeans
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        return km.fit_predict(data).tolist()
    except ImportError:
        # sklearn 없으면 간단한 K-Means 구현
        return _simple_kmeans(data, k)


def _simple_kmeans(data: np.ndarray, k: int, max_iter: int = 100) -> list[int]:
    """sklearn 없을 때 사용하는 간단 K-Means."""
    n = len(data)
    rng = np.random.RandomState(42)
    indices = rng.choice(n, size=k, replace=False)
    centroids = data[indices].copy()

    labels = [0] * n
    for _ in range(max_iter):
        # 할당
        new_labels = []
        for i in range(n):
            dists = [np.linalg.norm(data[i] - c) for c in centroids]
            new_labels.append(int(np.argmin(dists)))

        if new_labels == labels:
            break
        labels = new_labels

        # 갱신
        for j in range(k):
            members = [data[i] for i in range(n) if labels[i] == j]
            if members:
                centroids[j] = np.mean(members, axis=0)

    return labels


def _cluster_hdbscan(data: np.ndarray) -> list[int]:
    """HDBSCAN 클러스터링. 라이브러리 없으면 K-Means 폴백."""
    try:
        import hdbscan
        clusterer = hdbscan.HDBSCAN(min_cluster_size=2, min_samples=1)
        labels = clusterer.fit_predict(data)
        return labels.tolist()
    except ImportError:
        k = _estimate_k(len(data))
        return _cluster_kmeans(data, k)


def _cluster_by_rules(keys: list[str], anchors: dict) -> list[int]:
    """좌표 기반 규칙 매칭으로 클러스터 할당."""
    labels = []
    for key in keys:
        rc = anchors[key].get("coords", {})
        best_match = _match_label_rule(rc)
        # LABEL_CANDIDATES의 인덱스를 라벨로 사용
        labels.append(best_match)
    return labels


def _get_axis_sign(value: float) -> str:
    """축 값을 부호 문자열로 변환."""
    if value > AXIS_SIGN_THRESHOLD:
        return "positive"
    elif value < -AXIS_SIGN_THRESHOLD:
        return "negative"
    return "any"


# 축별 부호 → 라벨 시그니처 매핑
_SIGN_TO_LABEL = {
    "shape": {"negative": "soft", "positive": "sharp", "any": "any"},
    "volume": {"negative": "subtle", "positive": "bold", "any": "any"},
    "age": {"negative": "fresh", "positive": "mature", "any": "any"},
}


def _match_label_rule(coords: dict) -> int:
    """좌표를 LABEL_CANDIDATES와 매칭하여 가장 적합한 라벨 인덱스를 반환."""
    user_sig = {}
    for axis in ["shape", "volume", "age"]:
        val = coords.get(axis, 0)
        sign = _get_axis_sign(val)
        user_sig[axis] = _SIGN_TO_LABEL[axis][sign]

    best_idx = len(LABEL_CANDIDATES) - 1  # 기본: 마지막 (가장 관대한 규칙)
    best_score = -1

    for idx, candidate in enumerate(LABEL_CANDIDATES):
        sig = candidate["signature"]
        score = 0
        for axis in ["shape", "volume", "age"]:
            if sig[axis] == "any" or user_sig[axis] == "any":
                score += 0.5  # 부분 매치
            elif sig[axis] == user_sig[axis]:
                score += 1.0  # 완전 매치
            # else: 0 (불일치)
        if score > best_score:
            best_score = score
            best_idx = idx

    return best_idx


# ─────────────────────────────────────────────
#  컬러 서브타입 (퍼스널컬러 4계절, 앵커 풀 상대 분류)
# ─────────────────────────────────────────────

# 퍼스널컬러 매핑
COLOR_SUBTYPE_MAP = {
    ("warm", "light"): {"season": "spring", "label_kr": "봄 웜", "label_en": "Spring Warm", "tone": "밝고 따뜻한"},
    ("warm", "dark"): {"season": "autumn", "label_kr": "가을 웜", "label_en": "Autumn Warm", "tone": "깊고 따뜻한"},
    ("cool", "light"): {"season": "summer", "label_kr": "여름 쿨", "label_en": "Summer Cool", "tone": "밝고 차가운"},
    ("cool", "dark"): {"season": "winter", "label_kr": "겨울 쿨", "label_en": "Winter Cool", "tone": "깊고 차가운"},
    ("neutral", "light"): {"season": "spring", "label_kr": "봄 뉴트럴", "label_en": "Spring Neutral", "tone": "밝고 중성적인"},
    ("neutral", "dark"): {"season": "autumn", "label_kr": "가을 뉴트럴", "label_en": "Autumn Neutral", "tone": "깊고 중성적인"},
}


def _compute_relative_thresholds(features_data: dict) -> dict:
    """
    앵커 풀의 warmth_score와 brightness 분포에서 상대 분류 기준을 계산.

    warmth_score: 하위 33% → cool, 상위 33% → warm, 중간 → neutral
    brightness: 하위 50% → dark, 상위 50% → light

    Returns:
        {"warmth_p33": float, "warmth_p67": float, "brightness_median": float}
    """
    warmth_values = [
        v.get("skin_warmth_score", 0.0)
        for v in features_data.values()
        if isinstance(v.get("skin_warmth_score"), (int, float))
    ]
    brightness_values = [
        v.get("skin_brightness", 0.0)
        for v in features_data.values()
        if isinstance(v.get("skin_brightness"), (int, float))
    ]

    if warmth_values:
        warmth_p33 = float(np.percentile(warmth_values, 33.3))
        warmth_p67 = float(np.percentile(warmth_values, 66.7))
    else:
        warmth_p33, warmth_p67 = -3.0, 8.0  # 절대 기준 폴백

    brightness_median = float(np.median(brightness_values)) if brightness_values else 0.46

    return {
        "warmth_p33": warmth_p33,
        "warmth_p67": warmth_p67,
        "brightness_median": brightness_median,
    }


def _assign_color_subtype(
    features_data: dict,
    type_key: str,
    thresholds: dict,
) -> dict:
    """
    유형의 skin_warmth_score + skin_brightness에서 퍼스널컬러 서브타입을 결정.
    앵커 풀 내 상대 분류 기준 사용.

    Returns:
        {"season": "spring", "label_kr": "봄 웜", ...,
         "relative_tone": "warm", "warmth_score": 12.3, "brightness_level": "light"}
    """
    feat = features_data.get(type_key, {})
    warmth_score = feat.get("skin_warmth_score", 0.0)
    skin_brightness = feat.get("skin_brightness", thresholds["brightness_median"])

    # 상대 분류: warmth_score 기준
    if warmth_score <= thresholds["warmth_p33"]:
        relative_tone = "cool"
    elif warmth_score >= thresholds["warmth_p67"]:
        relative_tone = "warm"
    else:
        relative_tone = "neutral"

    # 상대 분류: brightness 기준
    brightness_level = "light" if skin_brightness >= thresholds["brightness_median"] else "dark"

    key = (relative_tone, brightness_level)
    subtype = COLOR_SUBTYPE_MAP.get(key, COLOR_SUBTYPE_MAP[("neutral", "light")])

    return {
        **subtype,
        "relative_tone": relative_tone,
        "original_tone": feat.get("skin_tone", "neutral"),
        "warmth_score": round(warmth_score, 4),
        "skin_brightness": round(skin_brightness, 4),
        "brightness_level": brightness_level,
    }


def _compute_color_subtypes(member_keys: list[str]) -> list[dict]:
    """클러스터 멤버들의 컬러 서브타입을 일괄 계산 (앵커 풀 상대 분류)."""
    if not _FEATURES_CACHE_PATH.exists():
        return []

    with open(_FEATURES_CACHE_PATH, encoding="utf-8") as f:
        features_data = json.load(f)

    thresholds = _compute_relative_thresholds(features_data)

    subtypes = []
    for key in member_keys:
        subtype = _assign_color_subtype(features_data, key, thresholds)
        subtypes.append({"key": key, **subtype})

    return subtypes


def assign_user_color_subtype(skin_warmth_score: float, skin_brightness: float) -> dict:
    """
    공개 API: 유저의 퍼스널컬러 서브타입을 결정 (앵커 풀 상대 분류 기준).

    Args:
        skin_warmth_score: LAB 기반 raw warmth 값
        skin_brightness: 0.0 ~ 1.0 범위의 피부 밝기

    Returns:
        퍼스널컬러 서브타입 dict
    """
    if _FEATURES_CACHE_PATH.exists():
        with open(_FEATURES_CACHE_PATH, encoding="utf-8") as f:
            features_data = json.load(f)
        thresholds = _compute_relative_thresholds(features_data)
    else:
        thresholds = {"warmth_p33": -3.0, "warmth_p67": 8.0, "brightness_median": 0.46}

    user_data = {"_user": {"skin_warmth_score": skin_warmth_score, "skin_brightness": skin_brightness}}
    return _assign_color_subtype(user_data, "_user", thresholds)


def _build_cluster_info(
    keys: list[str],
    labels: list[int],
    anchors: dict,
    coords_array: np.ndarray,
) -> list[dict]:
    """클러스터별 정보를 구성한다."""
    # 라벨별 그룹화
    groups: dict[int, list[int]] = {}
    for i, label in enumerate(labels):
        groups.setdefault(label, []).append(i)

    clusters = []
    used_label_ids: set[str] = set()  # 중복 라벨 방지

    for label_idx, member_indices in sorted(groups.items()):
        member_keys = [keys[i] for i in member_indices]

        # centroid 계산
        member_coords = coords_array[member_indices]
        centroid = np.mean(member_coords, axis=0)
        centroid_dict = {
            "shape": round(float(centroid[0]), 3),
            "volume": round(float(centroid[1]), 3),
            "age": round(float(centroid[2]), 3),
        }

        # community_score 기반 대표 유형 (null이면 0으로 처리)
        best_rep = member_keys[0]
        best_score = 0
        for mk in member_keys:
            cs = anchors[mk].get("community_score") or 0
            if cs > best_score:
                best_score = cs
                best_rep = mk

        # 라벨 결정 — centroid 좌표를 규칙에 매칭 + 중복 방지
        matched_label_idx = _match_label_rule(centroid_dict)
        label_info = None

        # 1차: 최적 매칭 시도
        if matched_label_idx < len(LABEL_CANDIDATES):
            candidate = LABEL_CANDIDATES[matched_label_idx]
            if candidate["id"] not in used_label_ids:
                label_info = candidate

        # 2차: 중복이면 차선 라벨 찾기
        if label_info is None:
            for candidate in LABEL_CANDIDATES:
                if candidate["id"] in used_label_ids:
                    continue
                sig = candidate["signature"]
                user_sig = {}
                for axis in ["shape", "volume", "age"]:
                    val = centroid_dict.get(axis, 0)
                    sign = _get_axis_sign(val)
                    user_sig[axis] = _SIGN_TO_LABEL[axis][sign]
                # 최소 2축 이상 매칭이면 수용
                match_count = sum(
                    1 for ax in sig
                    if sig[ax] == "any" or user_sig.get(ax) == "any" or sig[ax] == user_sig.get(ax)
                )
                if match_count >= 2:
                    label_info = candidate
                    break

        # 3차: 아무것도 안 맞으면 자동 생성
        if label_info is None:
            label_info = _auto_generate_label(centroid_dict)

        used_label_ids.add(label_info["id"])

        # 클러스터 크기 분류
        n = len(member_keys)
        if n >= 3:
            size = "major"
        elif n == 2:
            size = "minor"
        else:
            size = "micro"

        rep_name = anchors[best_rep].get("name_kr", best_rep)

        # 컬러 서브타입 계산 (퍼스널컬러 4계절)
        color_subtypes = _compute_color_subtypes(member_keys)
        member_color_map = {}
        for cs in color_subtypes:
            k = cs.pop("key")
            member_color_map[k] = cs

        clusters.append({
            "id": label_info["id"],
            "label_kr": label_info["label_kr"],
            "label_en": label_info["label_en"],
            "members": member_keys,
            "member_names": [anchors[k].get("name_kr", k) for k in member_keys],
            "centroid_coords": centroid_dict,
            "representative_key": best_rep,
            "representative_name": rep_name,
            "representative_score": best_score,
            "size": size,
            "n_members": n,
            "description": label_info.get("description", ""),
            "keywords": label_info.get("keywords", []),
            "color_subtypes": member_color_map,
        })

    # 크기 순 정렬
    size_order = {"major": 0, "minor": 1, "micro": 2}
    clusters.sort(key=lambda c: (size_order.get(c["size"], 3), -c["n_members"]))

    return clusters


def _auto_generate_label(centroid: dict) -> dict:
    """규칙에 없는 클러스터를 centroid 좌표에서 자동 라벨링."""
    parts = []
    if abs(centroid.get("shape", 0)) > AXIS_SIGN_THRESHOLD:
        parts.append("Sharp" if centroid["shape"] > 0 else "Soft")
    if abs(centroid.get("volume", 0)) > AXIS_SIGN_THRESHOLD:
        parts.append("Bold" if centroid["volume"] > 0 else "Subtle")
    if abs(centroid.get("age", 0)) > AXIS_SIGN_THRESHOLD:
        parts.append("Mature" if centroid["age"] > 0 else "Fresh")

    label_en = " ".join(parts) if parts else "Neutral"
    label_kr = label_en  # 추후 번역 매핑 추가 가능

    return {
        "id": "_".join(p.lower() for p in parts) if parts else "neutral",
        "label_kr": label_kr,
        "label_en": label_en,
        "description": f"자동 생성 라벨: {label_en}",
        "keywords": [p.lower() for p in parts],
    }


# ─────────────────────────────────────────────
#  유저 분류
# ─────────────────────────────────────────────

def classify_user(
    user_coords: dict,
    gender: str = "female",
) -> dict:
    """
    유저 좌표를 가장 가까운 클러스터에 분류한다.

    Args:
        user_coords: {"shape": float, "volume": float, "age": float}
        gender: "female" or "male"

    Returns:
        {
            "cluster_id": "cool_goddess",
            "cluster_label_kr": "쿨 갓데스",
            "cluster_label_en": "Cool Goddess",
            "representative": "제니",
            "distance": 0.35,
            "confidence": 0.82,  # 1 - normalized_distance
            "position_in_cluster": "edge",  # "core" or "edge"
            "nearest_other": {"id": "ice_princess", "distance": 0.72},
            "description": "...",
        }
    """
    cluster_data = load_cluster_labels()
    clusters = cluster_data.get("clusters", [])

    if not clusters:
        return {
            "cluster_id": "unknown",
            "cluster_label_kr": "미분류",
            "cluster_label_en": "Unclassified",
            "representative": None,
            "distance": float("inf"),
            "confidence": 0,
            "position_in_cluster": "unknown",
            "nearest_other": None,
            "description": "클러스터 데이터가 없습니다. discover_clusters()를 먼저 실행하세요.",
        }

    user_vec = np.array([
        user_coords.get("shape", 0),
        user_coords.get("volume", 0),
        user_coords.get("age", 0),
    ], dtype=np.float32)

    # 각 클러스터 centroid와의 거리
    distances = []
    for c in clusters:
        centroid = c["centroid_coords"]
        c_vec = np.array([
            centroid.get("shape", 0),
            centroid.get("volume", 0),
            centroid.get("age", 0),
        ], dtype=np.float32)
        dist = float(np.linalg.norm(user_vec - c_vec))
        distances.append((c, dist))

    distances.sort(key=lambda x: x[1])
    nearest = distances[0]
    second = distances[1] if len(distances) > 1 else None

    cluster = nearest[0]
    dist = nearest[1]

    # 신뢰도: 거리가 0이면 1.0, 최대 거리(3축 × 2범위 = ~3.5)에서 0
    max_possible_dist = 3.5
    confidence = round(max(0, 1.0 - dist / max_possible_dist), 3)

    # core vs edge: 클러스터 반경의 50% 이내면 core
    avg_radius = _estimate_cluster_radius(cluster)
    position = "core" if dist < avg_radius * 0.5 else "edge"

    result = {
        "cluster_id": cluster["id"],
        "cluster_label_kr": cluster["label_kr"],
        "cluster_label_en": cluster["label_en"],
        "representative": cluster.get("representative_name"),
        "representative_key": cluster.get("representative_key"),
        "distance": round(dist, 4),
        "confidence": confidence,
        "position_in_cluster": position,
        "size": cluster.get("size", "unknown"),
        "n_members": cluster.get("n_members", 0),
        "description": cluster.get("description", ""),
        "keywords": cluster.get("keywords", []),
    }

    if second:
        result["nearest_other"] = {
            "id": second[0]["id"],
            "label_kr": second[0]["label_kr"],
            "distance": round(second[1], 4),
        }

    return result


def _estimate_cluster_radius(cluster: dict) -> float:
    """클러스터의 대략적 반경을 추정."""
    # 멤버가 1명이면 고정 반경
    if cluster.get("n_members", 1) <= 1:
        return 0.5
    # 멤버 수에 반비례하게 반경 추정 (major일수록 넓음)
    return 0.3 + 0.1 * cluster.get("n_members", 2)


# ─────────────────────────────────────────────
#  리포트용 포매팅
# ─────────────────────────────────────────────

def format_cluster_for_report(
    classification: dict,
    tier: str = "full",
) -> str:
    """
    유저 클러스터 분류 결과를 LLM 프롬프트용 문자열로 포매팅.
    """
    parts = ["\n[클러스터 분석]"]

    label = classification.get("cluster_label_kr", "미분류")
    label_en = classification.get("cluster_label_en", "")
    rep = classification.get("representative", "")
    conf = classification.get("confidence", 0)
    pos = classification.get("position_in_cluster", "")

    if tier == "free":
        # Free: 클러스터명만
        parts.append(f"  당신의 미감 유형: {label}")
        parts.append(f"  (자세한 분석은 Standard 이상에서 확인 가능)")

    elif tier in ("standard", "basic"):
        # Standard: 클러스터명 + 대표 유형 + 설명
        parts.append(f"  미감 유형: {label} ({label_en})")
        if rep:
            parts.append(f"  대표 유형: {rep}")
        parts.append(f"  소속 확신도: {conf * 100:.0f}%")
        desc = classification.get("description", "")
        if desc:
            parts.append(f"  설명: {desc}")

    else:
        # Full/Creator/Wedding: 전체 + 인접 클러스터 + 키워드
        parts.append(f"  미감 유형: {label} ({label_en})")
        if rep:
            parts.append(f"  대표 유형: {rep}")
        parts.append(f"  소속 확신도: {conf * 100:.0f}% / 위치: {'중심부' if pos == 'core' else '경계'}")

        desc = classification.get("description", "")
        if desc:
            parts.append(f"  설명: {desc}")

        keywords = classification.get("keywords", [])
        if keywords:
            parts.append(f"  키워드: {', '.join(keywords)}")

        nearest = classification.get("nearest_other")
        if nearest:
            parts.append(f"  인접 유형: {nearest['label_kr']} (거리 {nearest['distance']:.2f})")
            parts.append(f"  → 스타일링에 따라 {nearest['label_kr']} 방향으로의 전환도 가능합니다")

    parts.append("  → 리포트의 '미감 유형' 섹션에 위 내용을 반영해주세요.")
    return "\n".join(parts)
