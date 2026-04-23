"""
축 재정의 검증 v3 — 3D UMAP (morphology/impression/tone) + beauty overlay + 클러스터 수
"""
import sys
sys.path.insert(0, "../../sigak")
sys.path.insert(0, "../..")

import random
from pathlib import Path
from collections import defaultdict

import cv2
import numpy as np

DATA_DIR = Path("SCUT-FBP5500_v2")
IMAGES_DIR = DATA_DIR / "Images"
SAMPLE_N = 500
SEED = 42

random.seed(SEED)
np.random.seed(SEED)

# ─── 1. Beauty score 로드 ───
print("Beauty score 로드 중...")
import openpyxl
wb = openpyxl.load_workbook(DATA_DIR / "All_Ratings.xlsx", read_only=True)
ws = wb.active
raw_scores = defaultdict(list)
for row in ws.iter_rows(min_row=2, values_only=True):
    fname = str(row[1]).replace(".jpg", "") if row[1] else ""
    rating = row[2]
    if fname.startswith("AF") and rating is not None:
        raw_scores[fname].append(float(rating))
wb.close()

beauty_scores = {k: sum(v) / len(v) for k, v in raw_scores.items()}
print(f"  {len(beauty_scores)}명 점수 로드 (60명 평가 평균)")

# ─── 2. 동일 시드 샘플링 + 추출 ───
af_files = sorted([f for f in IMAGES_DIR.iterdir() if f.name.startswith("AF") and f.suffix == ".jpg"])
sample_files = random.sample(af_files, min(SAMPLE_N, len(af_files)))

print(f"\n특징 추출 중 (InsightFace + CLIP, {len(sample_files)}장)...")
from pipeline.face import analyze_face
from pipeline.clip import CLIPEmbedder

clipper = CLIPEmbedder()
results = []

for i, img_path in enumerate(sample_files):
    if (i + 1) % 100 == 0:
        print(f"  {i+1}/{len(sample_files)}... ({len(results)} 성공)")
    try:
        img_bytes = img_path.read_bytes()
        img_bgr = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        if img_bgr is None:
            continue
        face_result = analyze_face(img_bytes)
        if face_result is None:
            continue

        d = face_result.to_dict()
        lm = face_result.landmarks
        lm_arr = np.array(lm)
        mins = lm_arr[:, :2].min(axis=0)
        maxs = lm_arr[:, :2].max(axis=0)
        ranges = maxs - mins
        ranges[ranges == 0] = 1
        lm_norm = (lm_arr[:, :2] - mins) / ranges
        lm_flat = lm_norm.flatten()

        clip_emb = clipper.extract(img_bgr)

        results.append({
            "id": img_path.stem,
            "lm_136d": lm_flat,
            "clip_768d": clip_emb,
            "beauty": beauty_scores.get(img_path.stem, None),
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
            "nose_length": d.get("nose_length_ratio", 0),
            "brow_arch": d.get("brow_arch", 0),
        })
    except Exception:
        pass

print(f"  완료: {len(results)}장")
n_with_beauty = sum(1 for r in results if r["beauty"] is not None)
print(f"  beauty score 있는 샘플: {n_with_beauty}/{len(results)}")

# ─── 3. 904d → 3D UMAP ───
print(f"\n{'=' * 70}")
print("  3D UMAP (904d = 136d LM + 768d CLIP)")
print(f"{'=' * 70}")

from sklearn.preprocessing import StandardScaler
from umap import UMAP
from scipy import stats

lm_matrix = np.array([r["lm_136d"] for r in results])
clip_matrix = np.array([r["clip_768d"] for r in results])
lm_scaled = StandardScaler().fit_transform(lm_matrix)
clip_scaled = StandardScaler().fit_transform(clip_matrix)
combined = np.hstack([lm_scaled, clip_scaled])

reducer_3d = UMAP(n_components=3, random_state=SEED, n_neighbors=15, min_dist=0.1)
emb_3d = reducer_3d.fit_transform(combined)
print("  3D UMAP 완료")

# ─── 4. 새 축 체계와 3D UMAP 상관관계 ───
print(f"\n{'=' * 70}")
print("  새 축 체계: Morphology / Impression / Tone")
print(f"{'=' * 70}")

features_by_axis = {
    "morphology": ["jaw_angle", "cheekbone", "forehead", "face_length", "nose_length", "lip_fullness", "brow_arch"],
    "impression": ["eye_tilt", "symmetry", "eye_ratio"],
    "tone": ["skin_warmth", "skin_brightness"],
    "beauty": ["beauty"],
}

print(f"\n  {'Feature':<18} {'Axis':<12} {'r(D1)':>8} {'r(D2)':>8} {'r(D3)':>8} {'max|r|':>8} {'dom':<4}")
print(f"  {'─'*18} {'─'*12} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*4}")

for axis_name, feat_keys in features_by_axis.items():
    for feat_key in feat_keys:
        vals = np.array([r.get(feat_key, 0) or 0 for r in results], dtype=np.float64)
        if np.std(vals) < 1e-10:
            print(f"  {feat_key:<18} {axis_name:<12} {'(constant)':>8}")
            continue

        rs = []
        for dim in range(3):
            r, p = stats.pearsonr(vals, emb_3d[:, dim])
            rs.append((r, p))

        max_r_idx = max(range(3), key=lambda i: abs(rs[i][0]))
        max_r = abs(rs[max_r_idx][0])
        sig = "***" if min(r[1] for r in rs) < 0.001 else "**" if min(r[1] for r in rs) < 0.01 else "*" if min(r[1] for r in rs) < 0.05 else ""

        print(f"  {feat_key:<18} {axis_name:<12} {rs[0][0]:>+7.3f} {rs[1][0]:>+7.3f} {rs[2][0]:>+7.3f} {max_r:>7.3f}{sig} D{max_r_idx+1}")

# ─── 5. 축별 dominant dimension 판정 ───
print(f"\n{'=' * 70}")
print("  축별 dominant UMAP dimension")
print(f"{'=' * 70}")

axis_dim_map = {}
for axis_name, feat_keys in features_by_axis.items():
    dim_votes = defaultdict(float)
    for feat_key in feat_keys:
        vals = np.array([r.get(feat_key, 0) or 0 for r in results], dtype=np.float64)
        if np.std(vals) < 1e-10:
            continue
        for dim in range(3):
            r, _ = stats.pearsonr(vals, emb_3d[:, dim])
            dim_votes[dim] += abs(r)
    if dim_votes:
        best_dim = max(dim_votes, key=dim_votes.get)
        axis_dim_map[axis_name] = best_dim
        print(f"  {axis_name:<12} → D{best_dim+1} (votes: D1={dim_votes[0]:.3f} D2={dim_votes[1]:.3f} D3={dim_votes[2]:.3f})")

# 3축이 3개 다른 차원에 로딩되는지
dims_used = set(axis_dim_map.values())
print(f"\n  사용된 차원: {len(dims_used)}개 / 3개")
if len(dims_used) == 3:
    print("  → 3축이 3개 독립 차원에 분리됨!")
elif len(dims_used) == 2:
    print("  → 2개 차원에 분포 (1축 혼합)")
else:
    print("  → 전부 같은 차원 (축 분리 실패)")

# ─── 6. Beauty score와 축의 상관관계 ───
print(f"\n{'=' * 70}")
print("  Beauty Score × 새 축 상관관계")
print(f"{'=' * 70}")

beauty_vals = np.array([r["beauty"] for r in results if r["beauty"] is not None])
beauty_idx = [i for i, r in enumerate(results) if r["beauty"] is not None]

if len(beauty_vals) > 10:
    # Beauty vs UMAP 3D
    for dim in range(3):
        r, p = stats.pearsonr(beauty_vals, emb_3d[beauty_idx, dim])
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
        print(f"  beauty × UMAP D{dim+1}: r={r:>+.3f}{sig} (p={p:.2e})")

    # Beauty vs 개별 피처
    print()
    all_feats = ["jaw_angle", "cheekbone", "eye_ratio", "eye_tilt", "lip_fullness",
                 "face_length", "forehead", "symmetry", "skin_warmth", "skin_brightness",
                 "nose_length", "brow_arch"]
    for feat in all_feats:
        vals = np.array([results[i][feat] for i in beauty_idx], dtype=np.float64)
        if np.std(vals) < 1e-10:
            continue
        r, p = stats.pearsonr(beauty_vals, vals)
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
        if abs(r) > 0.1:
            print(f"  beauty × {feat:<18}: r={r:>+.3f}{sig}")
else:
    print("  beauty score 부족 — 스킵")

# ─── 7. 자연 클러스터 수 탐색 ───
print(f"\n{'=' * 70}")
print("  자연 클러스터 수 탐색 (3D UMAP 공간)")
print(f"{'=' * 70}")

from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

k_range = range(3, 10)
results_k = []

for k in k_range:
    km = KMeans(n_clusters=k, random_state=SEED, n_init=10)
    labels = km.fit_predict(emb_3d)
    sil = silhouette_score(emb_3d, labels)
    inertia = km.inertia_
    results_k.append((k, sil, inertia))
    sizes = [int(np.sum(labels == i)) for i in range(k)]
    print(f"  k={k}: silhouette={sil:>+.3f} inertia={inertia:>8.1f} sizes={sorted(sizes, reverse=True)}")

best_k = max(results_k, key=lambda x: x[1])
print(f"\n  최적 k: {best_k[0]} (silhouette={best_k[1]:.3f})")

# 최적 k로 클러스터 특성 분석
print(f"\n{'=' * 70}")
print(f"  최적 k={best_k[0]} 클러스터 특성 분석")
print(f"{'=' * 70}")

km_best = KMeans(n_clusters=best_k[0], random_state=SEED, n_init=10)
best_labels = km_best.fit_predict(emb_3d)

for c in range(best_k[0]):
    members = [i for i, l in enumerate(best_labels) if l == c]
    n = len(members)

    # 클러스터별 피처 평균
    mean_feats = {}
    for feat in ["jaw_angle", "cheekbone", "eye_tilt", "forehead", "symmetry",
                 "skin_warmth", "skin_brightness", "eye_ratio", "lip_fullness"]:
        vals = [results[i][feat] for i in members]
        mean_feats[feat] = sum(vals) / len(vals)

    # beauty 평균
    b_vals = [results[i]["beauty"] for i in members if results[i]["beauty"] is not None]
    b_mean = sum(b_vals) / len(b_vals) if b_vals else 0

    # 성격 판별
    morph = "soft" if mean_feats["jaw_angle"] > 108 else "sharp"
    impr = "tilt↑" if mean_feats["eye_tilt"] > 3.5 else "tilt↓"
    tone = "bright" if mean_feats["skin_brightness"] > 0.45 else "dark"

    print(f"\n  Cluster {c} ({n}명, beauty={b_mean:.2f}):")
    print(f"    jaw={mean_feats['jaw_angle']:.1f}° cheek={mean_feats['cheekbone']:.3f} "
          f"eye_tilt={mean_feats['eye_tilt']:.1f}° forehead={mean_feats['forehead']:.3f}")
    print(f"    symmetry={mean_feats['symmetry']:.3f} warmth={mean_feats['skin_warmth']:.1f} "
          f"brightness={mean_feats['skin_brightness']:.3f}")
    print(f"    → {morph} / {impr} / {tone}")

print(f"\n{'=' * 70}")
print("  EXPERIMENT COMPLETE")
print(f"{'=' * 70}")
