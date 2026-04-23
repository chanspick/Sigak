"""
정규화 3축 검증:
축1 — Morphology: LM 136d / face_width 정규화 후 PCA PC1
축2 — Impression: CLIP 768d PCA PC1
축3 — Tone: skin_warmth
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

def extract_normalized_lm(face_result):
    """랜드마크를 face_width 기준 비율로 정규화."""
    lm = np.array(face_result.landmarks)
    xs, ys = lm[:, 0], lm[:, 1]
    face_width = xs.max() - xs.min()
    if face_width < 1: face_width = 1
    # 모든 좌표를 face_width 대비 비율로 변환
    # x: 좌측 기준 비율, y: 상단 기준이되 face_width로 나눔 (종횡비 보존)
    x_min, y_min = xs.min(), ys.min()
    lm_norm = np.column_stack([
        (xs - x_min) / face_width,
        (ys - y_min) / face_width,  # face_width로 나눠서 종횡비 정보 보존
    ])
    return lm_norm.flatten()  # 136d

# ═══════════════════════════════════════
#  SCUT PCA 피팅 (정규화 LM / CLIP 각각)
# ═══════════════════════════════════════
DATA_DIR = Path("SCUT-FBP5500_v2/Images")
af_files = sorted([f for f in DATA_DIR.iterdir() if f.name.startswith("AF") and f.suffix == ".jpg"])
sample_files = random.sample(af_files, min(500, len(af_files)))

print("SCUT 추출 중 (face_width 정규화)...")
scut_lm, scut_clip = [], []
for i, p in enumerate(sample_files):
    try:
        img_bytes = p.read_bytes()
        img_bgr = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        face = analyze_face(img_bytes)
        if face is None: continue
        scut_lm.append(extract_normalized_lm(face))
        scut_clip.append(clipper.extract(img_bgr))
    except: pass
print(f"  {len(scut_lm)}장")

scaler_lm = StandardScaler().fit(np.array(scut_lm))
scaler_clip = StandardScaler().fit(np.array(scut_clip))

pca_lm = PCA(n_components=5, random_state=SEED)
pca_lm.fit(scaler_lm.transform(np.array(scut_lm)))

pca_clip = PCA(n_components=5, random_state=SEED)
pca_clip.fit(scaler_clip.transform(np.array(scut_clip)))

print(f"  LM PCA (정규화): {[f'{v:.1%}' for v in pca_lm.explained_variance_ratio_[:5]]}")
print(f"  CLIP PCA:        {[f'{v:.1%}' for v in pca_clip.explained_variance_ratio_[:5]]}")

# ═══════════════════════════════════════
#  셀럽 추출 + 3축 projection
# ═══════════════════════════════════════
CELEB_DIR = Path("../../sigak/data/anchors/celeb")
ANCHORS_JSON = Path("../../sigak/data/celeb_anchors.json")
with open(ANCHORS_JSON, encoding="utf-8") as f:
    ad = json.load(f)
kr2key = {v.get("name_kr",""): k for k,v in ad.get("anchors",{}).items()}
key2kr = {v:k for k,v in kr2key.items()}

celeb_per_photo = []
for f in sorted(CELEB_DIR.iterdir()):
    if f.suffix.lower() not in (".jpg",".jpeg",".png",".webp",".avif"): continue
    name_kr = re.sub(r"\d+$", "", f.stem).strip()
    eng_key = kr2key.get(name_kr, name_kr)
    try:
        img_bytes = f.read_bytes()
        img_bgr = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        face = analyze_face(img_bytes)
        if face is None: continue
        d = face.to_dict()
        lm_norm = extract_normalized_lm(face)
        clip_emb = clipper.extract(img_bgr)

        lm_s = scaler_lm.transform(lm_norm.reshape(1,-1))
        clip_s = scaler_clip.transform(clip_emb.reshape(1,-1))
        lm_pc = pca_lm.transform(lm_s)[0]
        clip_pc = pca_clip.transform(clip_s)[0]

        celeb_per_photo.append({
            "key": eng_key, "name": key2kr.get(eng_key, eng_key),
            "photo": f.name,
            "morphology": float(lm_pc[0]),   # LM PC1
            "lm_pc2": float(lm_pc[1]),
            "impression": float(clip_pc[0]),  # CLIP PC1
            "tone": d.get("skin_warmth_score", 0),
            "jaw_angle": d["jaw_angle"],
            "cheekbone": d["cheekbone_prominence"],
            "eye_tilt": d["eye_tilt"],
            "forehead": d["forehead_ratio"],
            "eye_ratio": d["eye_ratio"],
            "face_length": d["face_length_ratio"],
            "symmetry": d["symmetry_score"],
            "lip_fullness": d["lip_fullness"],
        })
    except: pass

print(f"\n셀럽 사진: {len(celeb_per_photo)}장")

# 셀럽별 평균
celeb_avg = defaultdict(lambda: defaultdict(list))
for p in celeb_per_photo:
    for k, v in p.items():
        if k not in ("key", "name", "photo"):
            celeb_avg[p["key"]][k].append(v)

celeb_summary = {}
for key, feats in celeb_avg.items():
    celeb_summary[key] = {k: np.mean(v) for k, v in feats.items()}
    celeb_summary[key]["name"] = key2kr.get(key, key)
    celeb_summary[key]["n"] = len(feats["morphology"])

# ═══════════════════════════════════════
#  TEST 1: 정규화 LM PC1 = morphology 검증
# ═══════════════════════════════════════
print(f"\n{'='*70}")
print("  TEST 1: 정규화 LM PC1 — Morphology 축 검증")
print(f"{'='*70}")

print(f"\n  {'Name':<8} {'Morph':>8} {'jaw°':>7} {'cheek':>7} {'eye_t':>7} {'fhd':>7} {'face_L':>7} {'eye_r':>7}")
print(f"  {'─'*8} {'─'*8} {'─'*7} {'─'*7} {'─'*7} {'─'*7} {'─'*7} {'─'*7}")

sorted_morph = sorted(celeb_summary.items(), key=lambda x: x[1]["morphology"])
for key, s in sorted_morph:
    print(f"  {s['name']:<8} {s['morphology']:>+8.2f} {s['jaw_angle']:>7.1f} {s['cheekbone']:>7.3f} "
          f"{s['eye_tilt']:>7.1f} {s['forehead']:>7.3f} {s['face_length']:>7.3f} {s['eye_ratio']:>7.3f}")

# 상관관계
print(f"\n  Morphology(LM PC1)과 피처 상관:")
morph_vals = np.array([celeb_summary[k]["morphology"] for k in celeb_summary])
for feat in ["jaw_angle", "cheekbone", "eye_tilt", "forehead", "eye_ratio", "face_length", "symmetry", "lip_fullness"]:
    feat_vals = np.array([celeb_summary[k][feat] for k in celeb_summary])
    r, p = stats.pearsonr(morph_vals, feat_vals)
    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    print(f"    {feat:<20}: r={r:>+.3f}{sig}")

# ═══════════════════════════════════════
#  TEST 2: CLIP PC1 = Impression 축 검증
# ═══════════════════════════════════════
print(f"\n{'='*70}")
print("  TEST 2: CLIP PC1 — Impression 축 검증")
print(f"{'='*70}")

print(f"\n  {'Name':<8} {'Impr':>8} {'Morph':>8}")
print(f"  {'─'*8} {'─'*8} {'─'*8}")

sorted_impr = sorted(celeb_summary.items(), key=lambda x: x[1]["impression"])
for key, s in sorted_impr:
    print(f"  {s['name']:<8} {s['impression']:>+8.2f} {s['morphology']:>+8.2f}")

# Morphology vs Impression 독립성
morph_arr = np.array([celeb_summary[k]["morphology"] for k in celeb_summary])
impr_arr = np.array([celeb_summary[k]["impression"] for k in celeb_summary])
r_mi, p_mi = stats.pearsonr(morph_arr, impr_arr)
print(f"\n  Morphology × Impression 상관: r={r_mi:+.3f} (p={p_mi:.3f})")
print(f"  → {'독립' if abs(r_mi) < 0.3 else '상관 있음'}")

# ═══════════════════════════════════════
#  TEST 3: 3축 직교성 매트릭스
# ═══════════════════════════════════════
print(f"\n{'='*70}")
print("  TEST 3: 3축 직교성 (상관 매트릭스)")
print(f"{'='*70}")

tone_arr = np.array([celeb_summary[k]["tone"] for k in celeb_summary])

axes = {"Morphology": morph_arr, "Impression": impr_arr, "Tone": tone_arr}
print(f"\n  {'':>12} {'Morph':>10} {'Impr':>10} {'Tone':>10}")
for name1, arr1 in axes.items():
    row = f"  {name1:<12}"
    for name2, arr2 in axes.items():
        r, _ = stats.pearsonr(arr1, arr2)
        row += f" {r:>+9.3f}"
    print(row)

# ═══════════════════════════════════════
#  TEST 4: 6유형 분포 (정규화 축 기준)
# ═══════════════════════════════════════
print(f"\n{'='*70}")
print("  TEST 4: 6유형 분포 (Morphology × Tone)")
print(f"{'='*70}")

morph_values = [celeb_summary[k]["morphology"] for k in celeb_summary]
tone_values = [celeb_summary[k]["tone"] for k in celeb_summary]

morph_p33 = float(np.percentile(morph_values, 33.3))
morph_p67 = float(np.percentile(morph_values, 66.7))
tone_median = float(np.median(tone_values))

print(f"\n  Morphology: P33={morph_p33:.2f}, P67={morph_p67:.2f}")
print(f"  Tone median: {tone_median:.2f}")

from collections import Counter
type_counts = Counter()
type_members = defaultdict(list)

print(f"\n  {'Name':<8} {'Morph':>8} {'Tone':>8} {'Type':<16}")
print(f"  {'─'*8} {'─'*8} {'─'*8} {'─'*16}")

for key, s in sorted(celeb_summary.items(), key=lambda x: x[1]["morphology"]):
    m = s["morphology"]
    t = s["tone"]
    m_label = "Sharp" if m < morph_p33 else "Soft" if m > morph_p67 else "Balanced"
    t_label = "Warm" if t >= tone_median else "Cool"
    typ = f"{m_label}+{t_label}"
    type_counts[typ] += 1
    type_members[typ].append(s["name"])
    print(f"  {s['name']:<8} {m:>+8.2f} {t:>8.1f} {typ}")

print(f"\n  6유형 분포:")
all_types = ["Sharp+Warm", "Sharp+Cool", "Balanced+Warm", "Balanced+Cool", "Soft+Warm", "Soft+Cool"]
for typ in all_types:
    n = type_counts.get(typ, 0)
    members = ", ".join(type_members.get(typ, []))
    bar = "█" * n
    empty = " ← EMPTY" if n == 0 else ""
    print(f"    {typ:<16} {n} {bar} {members}{empty}")

filled = sum(1 for t in all_types if type_counts.get(t, 0) > 0)
print(f"\n  채워진 유형: {filled}/6")

# ═══════════════════════════════════════
#  상식 체크: 핵심 셀럽 위치
# ═══════════════════════════════════════
print(f"\n{'='*70}")
print("  상식 체크: 핵심 셀럽의 3축 위치")
print(f"{'='*70}")

checks = ["장원영", "카리나", "제니", "한소희", "김유정", "민지", "수지", "아이유", "해린"]
for name in checks:
    key = kr2key.get(name)
    if key and key in celeb_summary:
        s = celeb_summary[key]
        m_label = "Sharp" if s["morphology"] < morph_p33 else "Soft" if s["morphology"] > morph_p67 else "Balanced"
        print(f"  {name:<6}: Morph={s['morphology']:>+6.2f}({m_label:<8}) "
              f"Impr={s['impression']:>+6.2f} Tone={s['tone']:>5.1f} "
              f"jaw={s['jaw_angle']:.0f}°")

print(f"\n{'='*70}")
print("  DONE")
