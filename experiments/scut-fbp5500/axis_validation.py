"""
SCUT-FBP5500 축 존재 검증 실험
- Asian Female 500장 샘플링
- InsightFace 136d 랜드마크 추출
- UMAP 2D 투영
- 매력도 점수 + 구조적 특징 오버레이
- 3축 gradient 존재 여부 확인
"""
import sys
sys.path.insert(0, "../../sigak")
sys.path.insert(0, "../..")

import os
import re
import random
from pathlib import Path
from collections import Counter

import cv2
import numpy as np

# ─── 설정 ───
DATA_DIR = Path("SCUT-FBP5500_v2")
IMAGES_DIR = DATA_DIR / "Images"
LANDMARKS_DIR = DATA_DIR / "facial landmark"
SAMPLE_N = 500
SEED = 42

random.seed(SEED)
np.random.seed(SEED)

# ─── 1. AF(Asian Female) 이미지 목록 + 샘플링 ───
af_files = sorted([f for f in IMAGES_DIR.iterdir() if f.name.startswith("AF") and f.suffix == ".jpg"])
print(f"Asian Female 전체: {len(af_files)}장")

sample_files = random.sample(af_files, min(SAMPLE_N, len(af_files)))
print(f"샘플링: {len(sample_files)}장")

# ─── 2. 매력도 점수 로드 ───
print("\n매력도 점수 로드 중...")
try:
    import openpyxl
    wb = openpyxl.load_workbook(DATA_DIR / "All_Ratings.xlsx", read_only=True)
    ws = wb.active
    ratings = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0]:
            fname = str(row[0]).strip()
            # 평균 점수 계산 (열 1~60이 개별 평가)
            scores = [float(x) for x in row[1:] if x is not None and str(x).replace('.','').isdigit()]
            if scores:
                ratings[fname] = sum(scores) / len(scores)
    print(f"  점수 로드: {len(ratings)}건")
    wb.close()
except Exception as e:
    print(f"  xlsx 로드 실패: {e}, 점수 없이 진행")
    ratings = {}

# ─── 3. InsightFace로 136d 랜드마크 + 17개 피처 추출 ───
print("\nInsightFace 특징 추출 중...")
from pipeline.face import analyze_face

results = []
fail_count = 0

for i, img_path in enumerate(sample_files):
    if (i + 1) % 50 == 0:
        print(f"  {i+1}/{len(sample_files)}...")

    try:
        img_bytes = img_path.read_bytes()
        face_result = analyze_face(img_bytes)
        if face_result is None:
            fail_count += 1
            continue

        d = face_result.to_dict()
        lm = face_result.landmarks

        # Raw 랜드마크 정규화
        lm_arr = np.array(lm)
        mins = lm_arr[:, :2].min(axis=0)
        maxs = lm_arr[:, :2].max(axis=0)
        ranges = maxs - mins
        ranges[ranges == 0] = 1
        lm_norm = (lm_arr[:, :2] - mins) / ranges
        lm_flat = lm_norm.flatten()

        # 매력도 점수
        fname = img_path.stem  # AF123
        beauty_score = ratings.get(fname, ratings.get(fname + ".jpg", None))

        results.append({
            "id": fname,
            "landmarks_136d": lm_flat,
            "features": d,
            "beauty_score": beauty_score,
            # 핵심 구조적 특징
            "jaw_angle": d.get("jaw_angle", 0),
            "cheekbone": d.get("cheekbone_prominence", 0),
            "eye_ratio": d.get("eye_ratio", 0),
            "eye_tilt": d.get("eye_tilt", 0),
            "lip_fullness": d.get("lip_fullness", 0),
            "face_length": d.get("face_length_ratio", 0),
            "forehead": d.get("forehead_ratio", 0),
            "symmetry": d.get("symmetry_score", 0),
            "skin_warmth": d.get("skin_warmth_score", 0),
            "skin_brightness": d.get("skin_brightness", 0),
            "face_shape": d.get("face_shape", "?"),
        })
    except Exception:
        fail_count += 1

print(f"\n추출 완료: {len(results)}장 성공, {fail_count}장 실패")

# ─── 4. 136d 랜드마크 UMAP ───
print(f"\n{'=' * 70}")
print("  UMAP 분석 (136d 랜드마크)")
print(f"{'=' * 70}")

from sklearn.preprocessing import StandardScaler

lm_matrix = np.array([r["landmarks_136d"] for r in results])
lm_scaled = StandardScaler().fit_transform(lm_matrix)

try:
    from umap import UMAP
    reducer = UMAP(n_components=2, random_state=SEED, n_neighbors=15, min_dist=0.1)
    embedding_2d = reducer.fit_transform(lm_scaled)
    print("  UMAP 완료")
except ImportError:
    print("  UMAP 미설치 → PCA 폴백")
    from sklearn.decomposition import PCA
    pca = PCA(n_components=2, random_state=SEED)
    embedding_2d = pca.fit_transform(lm_scaled)
    print(f"  PCA 설명력: {pca.explained_variance_ratio_[0]:.1%} + {pca.explained_variance_ratio_[1]:.1%}")

# ─── 5. 축별 gradient 분석 ───
print(f"\n{'=' * 70}")
print("  축별 gradient 분석 — 구조적 특징과 UMAP 좌표의 상관관계")
print(f"{'=' * 70}")

from scipy import stats

features_to_test = {
    # Structure 축 (sharp ↔ soft)
    "jaw_angle": "structure (sharp↔soft)",
    "cheekbone": "structure (sharp↔soft)",
    "lip_fullness": "structure (sharp↔soft)",
    # Impression 축 (warm ↔ cool)
    "skin_warmth": "impression (warm↔cool)",
    "skin_brightness": "impression (warm↔cool)",
    "symmetry": "impression (warm↔cool)",
    # Maturity 축 (fresh ↔ mature)
    "forehead": "maturity (fresh↔mature)",
    "eye_ratio": "maturity (fresh↔mature)",
    "face_length": "maturity (fresh↔mature)",
    # 매력도
    "beauty_score": "beauty (매력도)",
}

print(f"\n  {'Feature':<20} {'Axis':<25} {'r(UMAP1)':>10} {'p':>10} {'r(UMAP2)':>10} {'p':>10}")
print(f"  {'─'*20} {'─'*25} {'─'*10} {'─'*10} {'─'*10} {'─'*10}")

significant_gradients = []

for feat_key, axis_label in features_to_test.items():
    values = [r.get(feat_key) for r in results]
    if any(v is None for v in values):
        values = [v if v is not None else 0 for v in values]

    vals = np.array(values, dtype=np.float64)

    # UMAP dim 1과의 상관
    r1, p1 = stats.pearsonr(vals, embedding_2d[:, 0])
    r2, p2 = stats.pearsonr(vals, embedding_2d[:, 1])

    sig1 = "***" if p1 < 0.001 else "**" if p1 < 0.01 else "*" if p1 < 0.05 else ""
    sig2 = "***" if p2 < 0.001 else "**" if p2 < 0.01 else "*" if p2 < 0.05 else ""

    print(f"  {feat_key:<20} {axis_label:<25} {r1:>+8.3f}{sig1:>2} {p1:>10.2e} {r2:>+8.3f}{sig2:>2} {p2:>10.2e}")

    if p1 < 0.01 or p2 < 0.01:
        significant_gradients.append((feat_key, axis_label, r1, r2))

print(f"\n  유의한 gradient ({len(significant_gradients)}개):")
for feat, axis, r1, r2 in significant_gradients:
    dominant = "UMAP1" if abs(r1) > abs(r2) else "UMAP2"
    r_max = max(abs(r1), abs(r2))
    strength = "강함" if r_max > 0.4 else "중간" if r_max > 0.2 else "약함"
    print(f"    {feat:<20} → {dominant} (r={r_max:.3f}, {strength})")

# ─── 6. 3축 구조 존재 판정 ───
print(f"\n{'=' * 70}")
print("  3축 구조 존재 판정")
print(f"{'=' * 70}")

axis_mapping = {
    "structure": ["jaw_angle", "cheekbone", "lip_fullness"],
    "impression": ["skin_warmth", "skin_brightness", "symmetry"],
    "maturity": ["forehead", "eye_ratio", "face_length"],
}

for axis_name, feat_keys in axis_mapping.items():
    axis_feats = [(f, a, r1, r2) for f, a, r1, r2 in significant_gradients if f in feat_keys]
    if axis_feats:
        max_r = max(max(abs(r1), abs(r2)) for _, _, r1, r2 in axis_feats)
        status = "CONFIRMED" if max_r > 0.3 else "WEAK" if max_r > 0.15 else "NOT FOUND"
    else:
        max_r = 0
        status = "NOT FOUND"
    print(f"  {axis_name:<12}: {status} (max |r| = {max_r:.3f}, features: {', '.join(feat_keys)})")

# ─── 7. 요약 통계 ───
print(f"\n{'=' * 70}")
print("  데이터 요약")
print(f"{'=' * 70}")

jaw_angles = [r["jaw_angle"] for r in results]
beauty_scores = [r["beauty_score"] for r in results if r["beauty_score"] is not None]
warmth_scores = [r["skin_warmth"] for r in results]

print(f"  jaw_angle:   min={min(jaw_angles):.1f}° max={max(jaw_angles):.1f}° std={np.std(jaw_angles):.1f}°")
print(f"  beauty:      min={min(beauty_scores):.2f}  max={max(beauty_scores):.2f}  std={np.std(beauty_scores):.2f}")
print(f"  warmth:      min={min(warmth_scores):.1f}  max={max(warmth_scores):.1f}  std={np.std(warmth_scores):.1f}")
print(f"  face_shapes: {Counter(r['face_shape'] for r in results).most_common()}")

print(f"\n{'=' * 70}")
print("  EXPERIMENT COMPLETE")
print(f"{'=' * 70}")
