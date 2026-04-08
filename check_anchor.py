"""
앵커 이미지 InsightFace 탐지 검증 스크립트

사용법:
    # 단일 이미지
    python check_anchor.py image.jpg

    # 폴더 전체
    python check_anchor.py anchor_candidates/

    # 여러 파일
    python check_anchor.py img1.jpg img2.jpg img3.jpg
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "sigak"))
from pipeline.face import analyze_face

SUPPORTED = {".jpg", ".jpeg", ".png", ".webp"}


def check_one(path: Path) -> bool:
    data = path.read_bytes()
    features = analyze_face(data)
    if features is None:
        print(f"  ❌ {path.name} — 얼굴 미검출")
        return False
    lm = len(features.landmarks)
    if lm <= 68:
        print(f"  ✅ {path.name} — InsightFace ({lm} landmarks)")
        return True
    else:
        print(f"  ❌ {path.name} — MediaPipe fallback ({lm} landmarks) → 교체 필요")
        return False


def main():
    if len(sys.argv) < 2:
        print("사용법: python check_anchor.py <이미지 또는 폴더>")
        sys.exit(1)

    targets = []
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.is_dir():
            targets.extend(sorted(f for f in p.iterdir() if f.suffix.lower() in SUPPORTED))
        elif p.is_file():
            targets.append(p)
        else:
            print(f"  ⚠️ {arg} — 파일 없음")

    if not targets:
        print("검증할 이미지가 없습니다.")
        sys.exit(1)

    print(f"\n총 {len(targets)}장 검증 시작\n")
    ok = 0
    fail = 0
    for t in targets:
        if check_one(t):
            ok += 1
        else:
            fail += 1

    print(f"\n결과: ✅ {ok}장 통과 / ❌ {fail}장 실패 (총 {ok + fail}장)")
    if fail > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
