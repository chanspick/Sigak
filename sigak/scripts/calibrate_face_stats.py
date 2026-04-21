"""
SCUT-FBP5500 AF subset → SIGAK Step 1 배치 실행 → FACE_STATS 실측값 산출

사용법:
    python scripts/calibrate_face_stats.py \
        --image-dir ./data/scut-fbp5500/Images/ \
        --subset AF \
        --output ./data/calibration_result.json

출력: metric별 mean, std, p5, p25, p50, p75, p95, min, max, n
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

# 프로젝트 root를 path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.face import analyze_face

METRICS_TO_CALIBRATE = [
    "jaw_angle",
    "face_length_ratio",
    "symmetry_score",
    "golden_ratio_score",
    "cheekbone_prominence",
    "eye_tilt",
    "eye_width_ratio",
    "nose_bridge_height",
    "lip_fullness",
    "brow_arch",
    "eye_ratio",
    "forehead_ratio",
    "philtrum_ratio",
    "skin_brightness",
    "brow_eye_distance",
]


def run_calibration(image_dir: Path, subset: str, output_path: Path):
    results = {m: [] for m in METRICS_TO_CALIBRATE}
    total = 0
    failed = 0

    pattern = f"{subset}*.jpg"
    image_files = sorted(image_dir.glob(pattern))
    if not image_files:
        image_files = sorted(image_dir.glob("*.jpg"))
        image_files = [f for f in image_files if f.stem.startswith(subset)]

    print(f"Found {len(image_files)} images matching '{pattern}'")

    for i, img_path in enumerate(image_files):
        total += 1
        try:
            features = analyze_face(img_path.read_bytes())
            feat_dict = features.to_dict()
            for m in METRICS_TO_CALIBRATE:
                val = feat_dict.get(m)
                if val is not None and isinstance(val, (int, float)):
                    results[m].append(float(val))
        except Exception as e:
            failed += 1
            if failed <= 5:
                print(f"  SKIP {img_path.name}: {e}")
            continue

        if (i + 1) % 100 == 0:
            print(f"  Processed {i + 1}/{len(image_files)} (failed: {failed})")

    # 통계 산출
    stats = {}
    for m, values in results.items():
        if len(values) < 10:
            print(f"  WARNING: {m} has only {len(values)} samples, skipping")
            continue
        arr = np.array(values)
        stats[m] = {
            "mean": round(float(np.mean(arr)), 4),
            "std": round(float(np.std(arr)), 4),
            "p5": round(float(np.percentile(arr, 5)), 4),
            "p10": round(float(np.percentile(arr, 10)), 4),
            "p25": round(float(np.percentile(arr, 25)), 4),
            "p50": round(float(np.percentile(arr, 50)), 4),
            "p75": round(float(np.percentile(arr, 75)), 4),
            "p90": round(float(np.percentile(arr, 90)), 4),
            "p95": round(float(np.percentile(arr, 95)), 4),
            "min": round(float(np.min(arr)), 4),
            "max": round(float(np.max(arr)), 4),
            "n": len(values),
        }

    stats["_meta"] = {
        "source": f"SCUT-FBP5500 {subset} subset",
        "total_attempted": total,
        "successful": total - failed,
        "failed": failed,
        "note": "연구 캘리브레이션용. 유저 데이터 확보 시 교체 예정.",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False))
    print(f"\nCalibration complete → {output_path}")

    # FACE_STATS 교체용 코드 스니펫 출력
    print("\n# --- FACE_STATS 교체용 (report_formatter.py에 복사) ---")
    print("FACE_STATS = {")
    for m in METRICS_TO_CALIBRATE:
        if m in stats:
            s = stats[m]
            print(f'    "{m}": {{"mean": {s["mean"]}, "std": {s["std"]}}},')
    print("}")

    # OBSERVED_RANGES 비교용 출력
    print("\n# --- OBSERVED_RANGES 비교용 (p10~p90) ---")
    for m in METRICS_TO_CALIBRATE:
        if m in stats:
            s = stats[m]
            print(f'#   "{m}": ({s["p10"]}, {s["p90"]}),  # measured')

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-dir", type=Path, required=True)
    parser.add_argument("--subset", default="AF", help="AF, AM, CF, CM")
    parser.add_argument("--output", type=Path, default=Path("data/calibration_result.json"))
    args = parser.parse_args()
    run_calibration(args.image_dir, args.subset, args.output)
