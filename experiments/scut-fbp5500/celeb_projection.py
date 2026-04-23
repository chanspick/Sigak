"""
한국 셀럽 48장 → SCUT PCA 공간 projection → 6유형 분포 검증

1. SCUT 295장 904d PCA 피팅 → PC1 로딩 저장
2. 한국 셀럽 48장 → 136d LM + 768d CLIP 추출
3. 셀럽 벡터를 SCUT PCA 공간에 projection
4. morphology(PC1) × tone(skin_warmth) 2D scatter
5. 6유형 분포 확인
"""
import sys
sys.path.insert(0, "../../sigak")
sys.path.insert(0, "../..")

import re
import json
import random
from pathlib import Path
from collections import Counter, defaultdict

import cv2
import numpy as np

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# ═══════════════════════════════════════════
#  STEP 1: SCUT PCA 피팅
# ═══════════════════════════════════════════
print("=" * 70)
print("  STEP 1: SCUT PCA 피팅 (295장 → PC1 로딩 벡터)")
print("=" * 70)

DATA_DIR = Path("SCUT-FBP5500_v2")
IMAGES_DIR = DATA_DIR / "Images"

from pipeline.face import analyze_face
from pipeline.clip import CLIPEmbedder
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

clipper = CLIPEmbedder()

# 동일 시드 샘플링
af_files = sorted([f for f in IMAGES_DIR.iterdir() if f.name.startswith("AF") and f.suffix == ".jpg"])
sample_files = random.sample(af_files, min(500, len(af_files)))

print(f"  SCUT AF 샘플: {len(sample_files)}장")
print("  추출 중...")

scut_lm = []
scut_clip = []
scut_warmth = []

for i, img_path in enumerate(sample_files):
    if (i + 1) % 100 == 0:
        print(f"    {i+1}/{len(sample_files)}... ({len(scut_lm)} 성공)")
    try:
        img_bytes = img_path.read_bytes()
        img_bgr = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        if img_bgr is None:
            continue
        face = analyze_face(img_bytes)
        if face is None:
            continue

        lm_arr = np.array(face.landmarks)
        mins = lm_arr[:, :2].min(axis=0)
        maxs = lm_arr[:, :2].max(axis=0)
        ranges = maxs - mins
        ranges[ranges == 0] = 1
        lm_flat = ((lm_arr[:, :2] - mins) / ranges).flatten()

        clip_emb = clipper.extract(img_bgr)

        scut_lm.append(lm_flat)
        scut_clip.append(clip_emb)
        scut_warmth.append(face.to_dict().get("skin_warmth_score", 0))
    except Exception:
        pass

print(f"  SCUT 추출 완료: {len(scut_lm)}장")

# PCA 피팅
scut_lm_arr = np.array(scut_lm)
scut_clip_arr = np.array(scut_clip)

scaler_lm = StandardScaler().fit(scut_lm_arr)
scaler_clip = StandardScaler().fit(scut_clip_arr)

scut_combined = np.hstack([scaler_lm.transform(scut_lm_arr), scaler_clip.transform(scut_clip_arr)])
pca = PCA(n_components=5, random_state=SEED)
pca.fit(scut_combined)

print(f"  PCA 설명력: {[f'{v:.1%}' for v in pca.explained_variance_ratio_[:5]]}")
print(f"  PC1 = morphology 축 constant 저장됨")

# SCUT의 morphology 분포 (경계 설정용)
scut_pc1 = pca.transform(scut_combined)[:, 0]
scut_warmth_arr = np.array(scut_warmth)
scut_morph_p33 = float(np.percentile(scut_pc1, 33.3))
scut_morph_p67 = float(np.percentile(scut_pc1, 66.7))
scut_warmth_median = float(np.median(scut_warmth_arr))

print(f"\n  SCUT Morphology 경계: P33={scut_morph_p33:.2f}, P67={scut_morph_p67:.2f}")
print(f"  SCUT Tone 경계: median warmth={scut_warmth_median:.2f}")

# ═══════════════════════════════════════════
#  STEP 2: 한국 셀럽 48장 추출
# ═══════════════════════════════════════════
print(f"\n{'=' * 70}")
print("  STEP 2: 한국 셀럽 48장 추출 (InsightFace + CLIP)")
print("=" * 70)

CELEB_DIR = Path("../../sigak/data/anchors/celeb")
ANCHORS_JSON = Path("../../sigak/data/celeb_anchors.json")

# 한글→영문 매핑
with open(ANCHORS_JSON, encoding="utf-8") as f:
    anchors_data = json.load(f)
name_kr_to_key = {}
key_to_name_kr = {}
for key, info in anchors_data.get("anchors", {}).items():
    nk = info.get("name_kr", "")
    if nk:
        name_kr_to_key[nk] = key
        key_to_name_kr[key] = nk

celeb_results = {}  # key → {lm, clip, warmth, features...}

for f in sorted(CELEB_DIR.iterdir()):
    if f.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp", ".avif"):
        continue
    name_kr = re.sub(r"\d+$", "", f.stem).strip()
    eng_key = name_kr_to_key.get(name_kr, name_kr)

    try:
        img_bytes = f.read_bytes()
        img_bgr = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        if img_bgr is None:
            continue
        face = analyze_face(img_bytes)
        if face is None:
            print(f"  SKIP: {f.name} (얼굴 미감지)")
            continue

        d = face.to_dict()
        lm_arr = np.array(face.landmarks)
        mins = lm_arr[:, :2].min(axis=0)
        maxs = lm_arr[:, :2].max(axis=0)
        ranges = maxs - mins
        ranges[ranges == 0] = 1
        lm_flat = ((lm_arr[:, :2] - mins) / ranges).flatten()
        clip_emb = clipper.extract(img_bgr)

        celeb_results.setdefault(eng_key, []).append({
            "lm": lm_flat,
            "clip": clip_emb,
            "warmth": d.get("skin_warmth_score", 0),
            "jaw_angle": d.get("jaw_angle", 0),
            "eye_tilt": d.get("eye_tilt", 0),
            "forehead": d.get("forehead_ratio", 0),
            "symmetry": d.get("symmetry_score", 0),
            "brightness": d.get("skin_brightness", 0),
        })
    except Exception as e:
        print(f"  ERROR: {f.name} ({e})")

print(f"\n  셀럽 추출: {len(celeb_results)}명")
for k, v in sorted(celeb_results.items()):
    print(f"    {k}: {len(v)}장")

# ═══════════════════════════════════════════
#  STEP 3: SCUT PCA 공간에 셀럽 projection
# ═══════════════════════════════════════════
print(f"\n{'=' * 70}")
print("  STEP 3: 셀럽 → SCUT PCA 공간 projection")
print("=" * 70)

celeb_coords = {}  # key → {morphology, tone, name_kr}

for key, samples in celeb_results.items():
    # 평균 벡터
    lm_avg = np.mean([s["lm"] for s in samples], axis=0)
    clip_avg = np.mean([s["clip"] for s in samples], axis=0)
    warmth_avg = np.mean([s["warmth"] for s in samples])

    # SCUT scaler 적용 → PCA projection
    lm_scaled = scaler_lm.transform(lm_avg.reshape(1, -1))
    clip_scaled = scaler_clip.transform(clip_avg.reshape(1, -1))
    combined = np.hstack([lm_scaled, clip_scaled])

    pc_scores = pca.transform(combined)[0]
    morphology = float(pc_scores[0])
    tone = float(warmth_avg)

    name = key_to_name_kr.get(key, key)
    celeb_coords[key] = {
        "morphology": morphology,
        "tone": tone,
        "name_kr": name,
        "jaw_angle": np.mean([s["jaw_angle"] for s in samples]),
        "eye_tilt": np.mean([s["eye_tilt"] for s in samples]),
        "n_samples": len(samples),
    }

# ═══════════════════════════════════════════
#  STEP 4: 2D Scatter + 6유형 분포
# ═══════════════════════════════════════════
print(f"\n{'=' * 70}")
print("  STEP 4: Morphology × Tone 2D Scatter")
print("=" * 70)

# 셀럽 기준 경계 설정 (SCUT 경계와 비교)
morph_values = [c["morphology"] for c in celeb_coords.values()]
tone_values = [c["tone"] for c in celeb_coords.values()]

# 셀럽 데이터 기준 3분위 + 중앙값
celeb_morph_p33 = float(np.percentile(morph_values, 33.3))
celeb_morph_p67 = float(np.percentile(morph_values, 66.7))
celeb_tone_median = float(np.median(tone_values))

print(f"\n  경계 비교:")
print(f"    SCUT  Morphology: P33={scut_morph_p33:.2f}, P67={scut_morph_p67:.2f}")
print(f"    Celeb Morphology: P33={celeb_morph_p33:.2f}, P67={celeb_morph_p67:.2f}")
print(f"    SCUT  Tone: median={scut_warmth_median:.2f}")
print(f"    Celeb Tone: median={celeb_tone_median:.2f}")

# 6유형 분류 (셀럽 경계 사용)
def classify_6type(morphology, tone, morph_p33, morph_p67, tone_med):
    if morphology < morph_p33:
        m_label = "Sharp"
    elif morphology > morph_p67:
        m_label = "Soft"
    else:
        m_label = "Balanced"
    t_label = "Warm" if tone >= tone_med else "Cool"
    return f"{m_label}+{t_label}"

print(f"\n  {'Name':<10} {'Morphology':>12} {'Tone':>8} {'Type':<16} {'jaw°':>6} {'eye_tilt':>8}")
print(f"  {'─'*10} {'─'*12} {'─'*8} {'─'*16} {'─'*6} {'─'*8}")

type_counts = Counter()
type_members = defaultdict(list)

for key in sorted(celeb_coords.keys(), key=lambda k: celeb_coords[k]["morphology"]):
    c = celeb_coords[key]
    t = classify_6type(c["morphology"], c["tone"], celeb_morph_p33, celeb_morph_p67, celeb_tone_median)
    type_counts[t] += 1
    type_members[t].append(c["name_kr"])
    print(f"  {c['name_kr']:<10} {c['morphology']:>+12.3f} {c['tone']:>8.1f} {t:<16} {c['jaw_angle']:>6.1f} {c['eye_tilt']:>8.1f}")

# ═══════════════════════════════════════════
#  STEP 5: 6유형 분포 검증
# ═══════════════════════════════════════════
print(f"\n{'=' * 70}")
print("  STEP 5: 6유형 분포 검증")
print("=" * 70)

all_types = ["Sharp+Warm", "Sharp+Cool", "Balanced+Warm", "Balanced+Cool", "Soft+Warm", "Soft+Cool"]
print(f"\n  {'Type':<16} {'Count':>5} {'Members'}")
print(f"  {'─'*16} {'─'*5} {'─'*40}")

empty_count = 0
for t in all_types:
    n = type_counts.get(t, 0)
    members = ", ".join(type_members.get(t, []))
    bar = "█" * n
    status = "" if n > 0 else " ← EMPTY"
    print(f"  {t:<16} {n:>5} {bar} {members}{status}")
    if n == 0:
        empty_count += 1

filled = 6 - empty_count
max_pct = max(type_counts.values()) / len(celeb_coords) * 100 if type_counts else 0

print(f"\n  채워진 유형: {filled}/6")
print(f"  최대 집중도: {max_pct:.0f}%")

if filled >= 5 and max_pct < 80:
    print(f"  → PASS: 6유형 분포 양호")
elif filled >= 5:
    print(f"  → WARN: 특정 유형에 집중 ({max_pct:.0f}% > 80%)")
else:
    print(f"  → FAIL: {6 - filled}개 유형이 비어있음 — 경계 또는 앵커 조정 필요")

# SCUT 경계 사용 시 분포 (비교용)
print(f"\n  [참고] SCUT 경계 기준 분포:")
type_counts_scut = Counter()
for key, c in celeb_coords.items():
    t = classify_6type(c["morphology"], c["tone"], scut_morph_p33, scut_morph_p67, scut_warmth_median)
    type_counts_scut[t] += 1
for t in all_types:
    n = type_counts_scut.get(t, 0)
    print(f"    {t:<16} {n:>3}")

print(f"\n{'=' * 70}")
print("  EXPERIMENT COMPLETE")
print("=" * 70)
