"""
셀럽 앵커 사진으로 얼굴형 + 피부톤 분류 검증.

사용법:
    cd sigak
    python scripts/verify_celeb_classification.py
"""
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.face import analyze_face

CELEB_DIR = Path(__file__).parent.parent / "data" / "anchors" / "celeb"


def run():
    shape_counter = Counter()
    tone_counter = Counter()
    results = []
    failed = []

    image_files = sorted(CELEB_DIR.glob("*"))
    image_files = [f for f in image_files if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".avif")]

    print(f"셀럽 이미지 {len(image_files)}장 분석 시작\n")

    for img_path in image_files:
        name = img_path.stem  # e.g. "카리나1"
        try:
            features = analyze_face(img_path.read_bytes())
            if features is None:
                failed.append(name)
                continue
            d = features.to_dict()
            shape = d["face_shape"]
            tone = d["skin_tone"]
            jaw = d.get("jaw_angle", 0)
            ratio = d.get("face_length_ratio", 0)
            cheek = d.get("cheekbone_prominence", 0)
            fore = d.get("forehead_ratio", 0)
            warmth = d.get("skin_warmth_score", 0)
            brightness = d.get("skin_brightness", 0)

            shape_counter[shape] += 1
            tone_counter[tone] += 1
            results.append({
                "name": name, "shape": shape, "tone": tone,
                "jaw": round(jaw, 1), "ratio": round(ratio, 3),
                "cheek": round(cheek, 3), "fore": round(fore, 3),
                "warmth": round(warmth, 1), "brightness": round(brightness, 3),
            })
        except Exception as e:
            failed.append(f"{name}: {e}")

    # 결과 출력
    print(f"{'이름':<12} {'얼굴형':<20} {'피부톤':<10} {'턱각도':>7} {'종횡비':>7} {'광대':>6} {'이마':>6} {'warmth':>7} {'밝기':>6}")
    print("-" * 100)
    for r in results:
        print(f"{r['name']:<12} {r['shape']:<20} {r['tone']:<10} {r['jaw']:>7} {r['ratio']:>7} {r['cheek']:>6} {r['fore']:>6} {r['warmth']:>7} {r['brightness']:>6}")

    print(f"\n── 얼굴형 분포 ──")
    total = sum(shape_counter.values())
    for shape, cnt in shape_counter.most_common():
        print(f"  {shape:<20} {cnt:>3}  ({cnt/total*100:.1f}%)")

    print(f"\n── 피부톤 분포 ──")
    total_t = sum(tone_counter.values())
    for tone, cnt in tone_counter.most_common():
        print(f"  {tone:<10} {cnt:>3}  ({cnt/total_t*100:.1f}%)")

    if failed:
        print(f"\n── 실패 ({len(failed)}건) ──")
        for f in failed:
            print(f"  {f}")

    print(f"\n총 {len(results)}장 분석 완료, {len(failed)}장 실패")


if __name__ == "__main__":
    run()
