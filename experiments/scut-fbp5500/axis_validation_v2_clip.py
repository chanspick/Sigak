"""
SCUT-FBP5500 축 검증 v2 — 136d 랜드마크 + 768d CLIP = 904d → UMAP
structure/maturity 분리 가능성 확인
"""
import sys
sys.path.insert(0, "../../sigak")
sys.path.insert(0, "../..")

import random
from pathlib import Path
from collections import Counter

import cv2
import numpy as np

# ─── 설정 ───
DATA_DIR = Path("SCUT-FBP5500_v2")
IMAGES_DIR = DATA_DIR / "Images"
SAMPLE_N = 500
SEED = 42

random.seed(SEED)
np.random.seed(SEED)

# ─── 1. 동일 500장 샘플링 (v1과 동일 시드) ───
af_files = sorted([f for f in IMAGES_DIR.iterdir() if f.name.startswith("AF") and f.suffix == ".jpg"])
sample_files = random.sample(af_files, min(SAMPLE_N, len(af_files)))
print(f"샘플: {len(sample_files)}장")

# ─── 2. InsightFace 랜드마크 + CLIP 임베딩 동시 추출 ───
print("\n특징 추출 중 (InsightFace + CLIP)...")
from pipeline.face import analyze_face
from pipeline.clip import CLIPEmbedder

clipper = CLIPEmbedder()

results = []
fail_count = 0

for i, img_path in enumerate(sample_files):
    if (i + 1) % 50 == 0:
        print(f"  {i+1}/{len(sample_files)}... ({len(results)} 성공)")

    try:
        img_bytes = img_path.read_bytes()
        img_bgr = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        if img_bgr is None:
            fail_count += 1
            continue

        # InsightFace
        face_result = analyze_face(img_bytes)
        if face_result is None:
            fail_count += 1
            continue

        d = face_result.to_dict()
        lm = face_result.landmarks

        # 랜드마크 정규화
        lm_arr = np.array(lm)
        mins = lm_arr[:, :2].min(axis=0)
        maxs = lm_arr[:, :2].max(axis=0)
        ranges = maxs - mins
        ranges[ranges == 0] = 1
        lm_norm = (lm_arr[:, :2] - mins) / ranges
        lm_flat = lm_norm.flatten()  # 136d

        # CLIP 768d
        clip_emb = clipper.extract(img_bgr)  # 768d normalized

        results.append({
            "id": img_path.stem,
            "lm_136d": lm_flat,
            "clip_768d": clip_emb,
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
            "face_shape": d.get("face_shape", "?"),
        })
    except Exception as e:
        fail_count += 1

print(f"\n추출 완료: {len(results)}장 성공, {fail_count}장 실패")

# ─── 3. 세 가지 UMAP 비교 ───
from sklearn.preprocessing import StandardScaler
from umap import UMAP
from scipy import stats

def run_umap_and_correlate(matrix, label, results_list):
    """UMAP 돌리고 축별 상관관계 분석."""
    scaled = StandardScaler().fit_transform(matrix)
    reducer = UMAP(n_components=2, random_state=SEED, n_neighbors=15, min_dist=0.1)
    emb = reducer.fit_transform(scaled)

    features_to_test = {
        "jaw_angle": "structure",
        "cheekbone": "structure",
        "lip_fullness": "structure",
        "symmetry": "impression",
        "skin_warmth": "tone",
        "skin_brightness": "tone",
        "eye_tilt": "impression",
        "forehead": "maturity",
        "eye_ratio": "maturity",
        "face_length": "maturity",
        "brow_arch": "maturity",
        "nose_length": "structure",
    }

    print(f"\n  {'Feature':<18} {'Axis':<12} {'r(U1)':>8} {'r(U2)':>8} {'max|r|':>8}")
    print(f"  {'─'*18} {'─'*12} {'─'*8} {'─'*8} {'─'*8}")

    axis_max = {}
    for feat_key, axis_label in features_to_test.items():
        vals = np.array([r[feat_key] for r in results_list], dtype=np.float64)
        if np.std(vals) < 1e-10:
            continue
        r1, p1 = stats.pearsonr(vals, emb[:, 0])
        r2, p2 = stats.pearsonr(vals, emb[:, 1])
        max_r = max(abs(r1), abs(r2))
        sig = "***" if min(p1, p2) < 0.001 else "**" if min(p1, p2) < 0.01 else "*" if min(p1, p2) < 0.05 else ""
        dominant = "U1" if abs(r1) > abs(r2) else "U2"
        print(f"  {feat_key:<18} {axis_label:<12} {r1:>+7.3f} {r2:>+7.3f} {max_r:>7.3f}{sig} ({dominant})")

        if axis_label not in axis_max or max_r > axis_max[axis_label][0]:
            axis_max[axis_label] = (max_r, feat_key, dominant)

    return emb, axis_max


# A. 136d 랜드마크만
print(f"\n{'=' * 70}")
print("  [A] 136d 랜드마크만")
print(f"{'=' * 70}")

lm_matrix = np.array([r["lm_136d"] for r in results])
emb_lm, axes_lm = run_umap_and_correlate(lm_matrix, "LM", results)

# B. 768d CLIP만
print(f"\n{'=' * 70}")
print("  [B] 768d CLIP만")
print(f"{'=' * 70}")

clip_matrix = np.array([r["clip_768d"] for r in results])
emb_clip, axes_clip = run_umap_and_correlate(clip_matrix, "CLIP", results)

# C. 136d + 768d = 904d 결합
print(f"\n{'=' * 70}")
print("  [C] 136d 랜드마크 + 768d CLIP = 904d 결합")
print(f"{'=' * 70}")

# 스케일 맞추기: 각각 정규화 후 concat
lm_scaled = StandardScaler().fit_transform(lm_matrix)
clip_scaled = StandardScaler().fit_transform(clip_matrix)
combined = np.hstack([lm_scaled, clip_scaled])  # 904d

emb_combined, axes_combined = run_umap_and_correlate(
    combined, "Combined", results
)

# ─── 4. 축 분리 판정 ───
print(f"\n{'=' * 70}")
print("  축 분리 판정 — structure vs maturity가 분리되는가?")
print(f"{'=' * 70}")

for mode_label, axes in [("136d LM", axes_lm), ("768d CLIP", axes_clip), ("904d Combined", axes_combined)]:
    print(f"\n  [{mode_label}]")
    for axis_name, (max_r, feat, dominant_dim) in sorted(axes.items()):
        strength = "STRONG" if max_r > 0.4 else "MODERATE" if max_r > 0.25 else "WEAK" if max_r > 0.15 else "NONE"
        print(f"    {axis_name:<12}: |r|={max_r:.3f} ({strength}) — {feat} on {dominant_dim}")

    # structure와 maturity가 다른 UMAP 차원에 로딩되는지 확인
    if "structure" in axes and "maturity" in axes:
        s_dim = axes["structure"][2]
        m_dim = axes["maturity"][2]
        if s_dim != m_dim:
            print(f"    → structure({s_dim}) ≠ maturity({m_dim}): 분리 가능!")
        else:
            print(f"    → structure({s_dim}) = maturity({m_dim}): 같은 차원에 혼합됨")

# ─── 5. 최종 요약 ───
print(f"\n{'=' * 70}")
print("  최종 요약")
print(f"{'=' * 70}")

print(f"\n  데이터: SCUT-FBP5500 Asian Female {len(results)}장")
print(f"  차원: 136d(기하) + 768d(CLIP) = 904d")

print(f"\n  [결론]")
for mode_label, axes in [("136d LM", axes_lm), ("768d CLIP", axes_clip), ("904d Combined", axes_combined)]:
    s_r = axes.get("structure", (0, "", ""))[0]
    m_r = axes.get("maturity", (0, "", ""))[0]
    i_r = axes.get("impression", (0, "", ""))[0]
    t_r = axes.get("tone", (0, "", ""))[0]
    s_dim = axes.get("structure", (0, "", "U?"))[2]
    m_dim = axes.get("maturity", (0, "", "U?"))[2]
    split = "YES" if s_dim != m_dim else "NO"
    print(f"  {mode_label:<15}: structure={s_r:.3f} maturity={m_r:.3f} impression={i_r:.3f} tone={t_r:.3f} | struct/mat split={split}")

print(f"\n{'=' * 70}")
print("  DONE")
