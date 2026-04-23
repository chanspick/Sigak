"""
분리 PCA 검증:
1) LM 136d PCA → PC1이 구조적 sharp↔soft를 잡는가? (장원영/카리나 순서 상식 검증)
2) CLIP 768d PCA → 같은 셀럽의 다른 사진 간 좌표 안정성 (impression vs 촬영 컨디션)
3) LM PC1에서 structure/maturity 분리 가능성
"""
import sys
sys.path.insert(0, "../../sigak")
sys.path.insert(0, "../..")

import re, json, random
from pathlib import Path
from collections import defaultdict
import cv2, numpy as np
from scipy import stats

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

from pipeline.face import analyze_face
from pipeline.clip import CLIPEmbedder
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

clipper = CLIPEmbedder()

# ═══════════════════════════════════════
#  SCUT PCA 피팅 (LM / CLIP 각각)
# ═══════════════════════════════════════
DATA_DIR = Path("SCUT-FBP5500_v2/Images")
af_files = sorted([f for f in DATA_DIR.iterdir() if f.name.startswith("AF") and f.suffix == ".jpg"])
sample_files = random.sample(af_files, min(500, len(af_files)))

print("SCUT 추출 중...")
scut_lm, scut_clip = [], []
for i, p in enumerate(sample_files):
    try:
        img_bytes = p.read_bytes()
        img_bgr = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        face = analyze_face(img_bytes)
        if face is None: continue
        lm = np.array(face.landmarks)
        mins, maxs = lm[:,:2].min(0), lm[:,:2].max(0)
        r = maxs - mins; r[r==0]=1
        scut_lm.append(((lm[:,:2]-mins)/r).flatten())
        scut_clip.append(clipper.extract(img_bgr))
    except: pass
print(f"  {len(scut_lm)}장 완료")

# 각각 PCA
scaler_lm = StandardScaler().fit(np.array(scut_lm))
scaler_clip = StandardScaler().fit(np.array(scut_clip))

pca_lm = PCA(n_components=5, random_state=SEED)
pca_lm.fit(scaler_lm.transform(np.array(scut_lm)))

pca_clip = PCA(n_components=5, random_state=SEED)
pca_clip.fit(scaler_clip.transform(np.array(scut_clip)))

print(f"  LM PCA 설명력:   {[f'{v:.1%}' for v in pca_lm.explained_variance_ratio_[:5]]}")
print(f"  CLIP PCA 설명력: {[f'{v:.1%}' for v in pca_clip.explained_variance_ratio_[:5]]}")

# ═══════════════════════════════════════
#  셀럽 추출 (사진별 개별 저장 — 안정성 분석용)
# ═══════════════════════════════════════
CELEB_DIR = Path("../../sigak/data/anchors/celeb")
ANCHORS_JSON = Path("../../sigak/data/celeb_anchors.json")
with open(ANCHORS_JSON, encoding="utf-8") as f:
    ad = json.load(f)
kr2key = {v.get("name_kr",""): k for k,v in ad.get("anchors",{}).items()}
key2kr = {v:k for k,v in kr2key.items()}

celeb_per_photo = []  # 사진별 개별 결과

for f in sorted(CELEB_DIR.iterdir()):
    if f.suffix.lower() not in (".jpg",".jpeg",".png",".webp",".avif"): continue
    name_kr = re.sub(r"\d+$", "", f.stem).strip()
    photo_num = re.search(r"(\d+)$", f.stem)
    photo_id = photo_num.group(1) if photo_num else "0"
    eng_key = kr2key.get(name_kr, name_kr)
    try:
        img_bytes = f.read_bytes()
        img_bgr = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        face = analyze_face(img_bytes)
        if face is None: continue
        d = face.to_dict()
        lm = np.array(face.landmarks)
        mins, maxs = lm[:,:2].min(0), lm[:,:2].max(0)
        r = maxs-mins; r[r==0]=1
        lm_flat = ((lm[:,:2]-mins)/r).flatten()
        clip_emb = clipper.extract(img_bgr)

        # LM PCA projection
        lm_s = scaler_lm.transform(lm_flat.reshape(1,-1))
        lm_pcs = pca_lm.transform(lm_s)[0]

        # CLIP PCA projection
        clip_s = scaler_clip.transform(clip_emb.reshape(1,-1))
        clip_pcs = pca_clip.transform(clip_s)[0]

        celeb_per_photo.append({
            "key": eng_key, "name": key2kr.get(eng_key, eng_key),
            "photo": f.name, "photo_id": photo_id,
            "lm_pc1": float(lm_pcs[0]), "lm_pc2": float(lm_pcs[1]),
            "clip_pc1": float(clip_pcs[0]), "clip_pc2": float(clip_pcs[1]),
            "jaw_angle": d["jaw_angle"], "eye_tilt": d["eye_tilt"],
            "forehead": d["forehead_ratio"], "cheekbone": d["cheekbone_prominence"],
            "eye_ratio": d["eye_ratio"], "face_length": d["face_length_ratio"],
            "symmetry": d["symmetry_score"], "lip_fullness": d["lip_fullness"],
        })
    except: pass

print(f"\n셀럽 사진 개별 추출: {len(celeb_per_photo)}장")

# ═══════════════════════════════════════
#  TEST 1: LM PC1 — 구조적 sharp↔soft 상식 검증
# ═══════════════════════════════════════
print(f"\n{'='*70}")
print("  TEST 1: LM 136d PC1 — 구조적 morphology 검증")
print(f"{'='*70}")

# 셀럽별 평균
celeb_avg = defaultdict(lambda: defaultdict(list))
for p in celeb_per_photo:
    for k, v in p.items():
        if k not in ("key", "name", "photo", "photo_id"):
            celeb_avg[p["key"]][k].append(v)

celeb_summary = {}
for key, feats in celeb_avg.items():
    celeb_summary[key] = {k: np.mean(v) for k, v in feats.items()}
    celeb_summary[key]["name"] = key2kr.get(key, key)
    celeb_summary[key]["n"] = len(feats["lm_pc1"])

# LM PC1 순 정렬
print(f"\n  {'Name':<8} {'LM_PC1':>8} {'jaw°':>7} {'cheek':>7} {'eye_t':>7} {'fhd':>7} {'sym':>7} {'face_L':>7}")
print(f"  {'─'*8} {'─'*8} {'─'*7} {'─'*7} {'─'*7} {'─'*7} {'─'*7} {'─'*7}")

sorted_by_lm = sorted(celeb_summary.items(), key=lambda x: x[1]["lm_pc1"])
for key, s in sorted_by_lm:
    print(f"  {s['name']:<8} {s['lm_pc1']:>+8.2f} {s['jaw_angle']:>7.1f} {s['cheekbone']:>7.3f} "
          f"{s['eye_tilt']:>7.1f} {s['forehead']:>7.3f} {s['symmetry']:>7.3f} {s['face_length']:>7.3f}")

# LM PC1과 피처 상관관계
print(f"\n  LM PC1과 구조적 피처 상관관계:")
lm_pc1_vals = np.array([celeb_summary[k]["lm_pc1"] for k in celeb_summary])
for feat in ["jaw_angle", "cheekbone", "eye_tilt", "forehead", "eye_ratio", "face_length", "symmetry", "lip_fullness"]:
    feat_vals = np.array([celeb_summary[k][feat] for k in celeb_summary])
    r, p = stats.pearsonr(lm_pc1_vals, feat_vals)
    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    if abs(r) > 0.3:
        print(f"    {feat:<20}: r={r:>+.3f}{sig}")

# ═══════════════════════════════════════
#  TEST 2: CLIP PC1 — 사진 간 안정성
# ═══════════════════════════════════════
print(f"\n{'='*70}")
print("  TEST 2: CLIP 768d PC1 — 사진 간 좌표 안정성")
print(f"{'='*70}")

print(f"\n  {'Name':<8} {'CLIP_PC1 mean':>12} {'std':>8} {'range':>8} {'LM_PC1 std':>12} {'판정'}")
print(f"  {'─'*8} {'─'*12} {'─'*8} {'─'*8} {'─'*12} {'─'*8}")

clip_stds = []
lm_stds = []

for key in sorted(celeb_avg.keys(), key=lambda k: key2kr.get(k, k)):
    clip_vals = celeb_avg[key]["clip_pc1"]
    lm_vals = celeb_avg[key]["lm_pc1"]
    if len(clip_vals) < 2: continue

    c_mean = np.mean(clip_vals)
    c_std = np.std(clip_vals)
    c_range = max(clip_vals) - min(clip_vals)
    l_std = np.std(lm_vals)

    clip_stds.append(c_std)
    lm_stds.append(l_std)

    stability = "안정" if c_std < 2.0 else "불안정" if c_std < 4.0 else "매우 불안정"
    name = key2kr.get(key, key)
    print(f"  {name:<8} {c_mean:>+12.2f} {c_std:>8.2f} {c_range:>8.2f} {l_std:>12.2f} {stability}")

avg_clip_std = np.mean(clip_stds)
avg_lm_std = np.mean(lm_stds)
print(f"\n  평균 std — CLIP: {avg_clip_std:.2f}, LM: {avg_lm_std:.2f}")
print(f"  CLIP/LM 비율: {avg_clip_std/avg_lm_std:.1f}x")

if avg_clip_std > avg_lm_std * 3:
    print(f"  → CLIP이 LM 대비 {avg_clip_std/avg_lm_std:.0f}배 불안정 — 사진 스타일 오염 의심")
elif avg_clip_std > avg_lm_std * 1.5:
    print(f"  → CLIP이 약간 더 불안정하지만 허용 범위")
else:
    print(f"  → CLIP과 LM 안정성 유사")

# ═══════════════════════════════════════
#  TEST 3: LM PC1 vs PC2 — structure/maturity 분리?
# ═══════════════════════════════════════
print(f"\n{'='*70}")
print("  TEST 3: LM PC1 vs PC2 — structure/maturity 분리 여부")
print(f"{'='*70}")

structure_feats = ["jaw_angle", "cheekbone", "lip_fullness"]
maturity_feats = ["forehead", "eye_ratio", "face_length"]

for pc_name, pc_idx in [("LM_PC1", "lm_pc1"), ("LM_PC2", "lm_pc2")]:
    print(f"\n  {pc_name}과의 상관:")
    pc_vals = np.array([celeb_summary[k][pc_idx] for k in celeb_summary])
    for feat in structure_feats + maturity_feats:
        feat_vals = np.array([celeb_summary[k][feat] for k in celeb_summary])
        r, p = stats.pearsonr(pc_vals, feat_vals)
        axis = "STRUCTURE" if feat in structure_feats else "MATURITY"
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
        print(f"    {feat:<20} [{axis:<9}] r={r:>+.3f}{sig}")

# ═══════════════════════════════════════
#  최종 정리
# ═══════════════════════════════════════
print(f"\n{'='*70}")
print("  SUMMARY")
print(f"{'='*70}")

# 장원영/카리나/김태리 위치 확인
for name in ["장원영", "카리나", "김태리", "한소희", "민지", "제니"]:
    key = kr2key.get(name)
    if key and key in celeb_summary:
        s = celeb_summary[key]
        print(f"  {name:<6}: LM_PC1={s['lm_pc1']:>+6.2f} (jaw={s['jaw_angle']:.0f}° cheek={s['cheekbone']:.2f}) "
              f"| CLIP_PC1={s['clip_pc1']:>+6.2f}")

print(f"\n{'='*70}")
print("  DONE")
