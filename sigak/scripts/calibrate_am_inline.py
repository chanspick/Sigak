"""AM calibration inline runner — temp script.

calibrate_face_stats.py 를 bypass (background 실행에서 2000/2000 실패 나왔음).
직접 루프 돌면서 stdout flush 로 실시간 진행 확인.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.face import analyze_face  # noqa: E402

import numpy as np  # noqa: E402


METRICS = [
    "jaw_angle", "face_length_ratio", "symmetry_score", "golden_ratio_score",
    "cheekbone_prominence", "eye_tilt", "eye_width_ratio", "nose_bridge_height",
    "lip_fullness", "brow_arch", "eye_ratio", "forehead_ratio",
    "philtrum_ratio", "skin_brightness", "brow_eye_distance",
]


def main():
    img_dir = Path(r"C:/Users/PC/Desktop/Sigak/experiments/scut-fbp5500/SCUT-FBP5500_v2/Images")
    out_path = Path(r"C:/Users/PC/Desktop/Sigak/experiments/scut-fbp5500/calibration_am_insightface.json")
    image_files = sorted(img_dir.glob("AM*.jpg"))
    print(f"found {len(image_files)} AM images", flush=True)

    results = {m: [] for m in METRICS}
    success = 0
    fail = 0
    t0 = time.time()

    for i, f in enumerate(image_files):
        try:
            features = analyze_face(f.read_bytes())
            if features is None:
                fail += 1
            else:
                d = features.to_dict()
                for m in METRICS:
                    v = d.get(m)
                    if v is not None and isinstance(v, (int, float)):
                        results[m].append(float(v))
                success += 1
        except Exception as e:
            fail += 1
            if fail <= 10:
                print(f"  SKIP {f.name}: {type(e).__name__} {e}", flush=True)

        if (i + 1) % 100 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            remaining = (len(image_files) - i - 1) / rate
            print(
                f"  [{i+1}/{len(image_files)}] success={success} fail={fail} "
                f"elapsed={elapsed:.0f}s rate={rate:.2f}/s eta={remaining/60:.1f}min",
                flush=True,
            )

    elapsed = time.time() - t0
    print(f"done. total={len(image_files)} success={success} fail={fail} elapsed={elapsed/60:.1f}min", flush=True)

    stats = {}
    for m, values in results.items():
        if len(values) < 10:
            print(f"  WARNING: {m} only {len(values)} samples", flush=True)
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
        "source": "SCUT-FBP5500 AM subset (inline)",
        "total_attempted": len(image_files),
        "successful": success,
        "failed": fail,
    }

    out_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False))
    print(f"saved to {out_path}", flush=True)

    print("\n# --- OBSERVED_RANGES (p10~p90) ---", flush=True)
    for m in METRICS:
        if m in stats:
            s = stats[m]
            print(f'  {m}: [{s["p10"]}, {s["p90"]}]  # n={s["n"]}', flush=True)


if __name__ == "__main__":
    main()
