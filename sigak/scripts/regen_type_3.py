r"""SIGAK PI-B — type_3.npy 재계산 (female, 누락분).

`data/anchors/female/3-1.png` + `3-2.png` (+ 더 있다면 자동 탐색) 를 CLIP 으로
임베딩하고 평균 → L2 정규화 → `data/embeddings/female/type_3.npy` 저장.

Why standalone:
  embed_types.py 의 _find_type_images() 가 `^{n}[\s\(]` 패턴이라 `3-1.png`
  (하이픈) 매칭 실패. 본 스크립트는 type_3 만 폭넓은 패턴으로 직접 처리.

Usage:
  python -m scripts.regen_type_3                # 실제 CLIP (GPU 권장, 5-10분)
  python -m scripts.regen_type_3 --use-mock     # 테스트 (즉시, 임베딩 의미 없음)

전제:
  open_clip_torch + torch + opencv 설치 (--use-mock 모드는 numpy 만 필요)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np


# ─────────────────────────────────────────────
#  Paths
# ─────────────────────────────────────────────

ROOT = Path(__file__).parent.parent
ANCHORS_DIR = ROOT / "data" / "anchors" / "female"
EMBEDDINGS_DIR = ROOT / "data" / "embeddings" / "female"
TYPE_ANCHORS_PATH = ROOT / "data" / "type_anchors.json"
TARGET_NPY = EMBEDDINGS_DIR / "type_3.npy"

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif"}


# ─────────────────────────────────────────────
#  Image discovery — type_3 전용 폭넓은 매칭
# ─────────────────────────────────────────────

def find_type_3_images() -> list[Path]:
    """type_3 후보 이미지 자동 탐색.

    매칭 규칙 — 파일명 ^3 으로 시작하고 다음 문자가 [공백/괄호/하이픈/_/.]
    예: "3-1.png", "3-2.png", "3 (1).jpg", "3_main.jpg"
    """
    import re
    pattern = re.compile(r"^3[\s\(\-_.]")
    found: list[Path] = []
    if not ANCHORS_DIR.exists():
        return found
    for f in sorted(ANCHORS_DIR.iterdir()):
        if f.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        if pattern.match(f.name):
            found.append(f)
    return found


def _read_image(img_path: Path) -> np.ndarray | None:
    """한글 경로 + avif 지원 BGR 로더."""
    try:
        buf = np.fromfile(str(img_path), dtype=np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if img is not None:
            return img
    except Exception:
        pass

    try:
        from PIL import Image
        pil_img = Image.open(str(img_path)).convert("RGB")
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────
#  Embedding compute
# ─────────────────────────────────────────────

def compute_mean_embedding(
    images: list[np.ndarray],
    *,
    use_mock: bool = False,
) -> np.ndarray:
    """이미지 리스트 → 평균 임베딩 → L2 정규화."""
    if not images:
        raise RuntimeError("no images to embed")

    if use_mock:
        from pipeline.clip import mock_embedding
        embeddings = []
        for img in images:
            img_bytes = cv2.imencode(".jpg", img)[1].tobytes()
            embeddings.append(mock_embedding(img_bytes))
    else:
        from pipeline.clip import CLIPEmbedder
        embedder = CLIPEmbedder()
        embeddings = [embedder.extract(img) for img in images]

    mean = np.mean(embeddings, axis=0)
    norm = float(np.linalg.norm(mean))
    if norm > 0:
        mean = mean / norm
    return mean.astype(np.float32)


# ─────────────────────────────────────────────
#  Verification
# ─────────────────────────────────────────────

def verify_dimension(npy_path: Path, expected: int = 768) -> None:
    emb = np.load(str(npy_path))
    assert emb.ndim == 1, f"type_3.npy ndim={emb.ndim}, want 1"
    assert emb.shape[0] == expected, (
        f"type_3.npy dim={emb.shape[0]}, want {expected}"
    )
    n = float(np.linalg.norm(emb))
    assert 0.99 < n < 1.01, f"type_3.npy not L2-normalized: norm={n:.4f}"


def verify_other_types_dimension(expected: int = 768) -> dict[str, int]:
    """동일 디렉토리 다른 type_*.npy 들이 같은 차원인지 검증."""
    result: dict[str, int] = {}
    for npy in sorted(EMBEDDINGS_DIR.glob("type_*.npy")):
        if npy.name == "type_3.npy":
            continue
        try:
            emb = np.load(str(npy))
            result[npy.name] = int(emb.shape[0])
        except Exception:
            result[npy.name] = -1
    return result


# ─────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="type_3.npy 재계산 (female)")
    parser.add_argument(
        "--use-mock", action="store_true", default=False,
        help="GPU 없이 mock 임베딩 (해시 기반 — 의미 없는 벡터, 검증용)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=False,
        help="저장 안 하고 검증만",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  SIGAK PI-B — type_3.npy 재계산 (female)")
    print("=" * 60)
    print(f"  모드: {'Mock (테스트)' if args.use_mock else 'CLIP (실제)'}")
    print(f"  대상: {TARGET_NPY}")
    print()

    # 1. 이미지 탐색
    img_paths = find_type_3_images()
    if not img_paths:
        print(f"[오류] {ANCHORS_DIR} 안에 type_3 이미지 없음")
        sys.exit(1)
    print(f"[1/4] type_3 이미지 {len(img_paths)} 장 발견:")
    for p in img_paths:
        print(f"    - {p.name}")
    print()

    # 2. 로드
    print(f"[2/4] 이미지 로드...")
    images: list[np.ndarray] = []
    for p in img_paths:
        img = _read_image(p)
        if img is None:
            print(f"  [경고] 로드 실패: {p.name}")
            continue
        images.append(img)
    if not images:
        print("[오류] 유효한 이미지 0장")
        sys.exit(1)
    print(f"  {len(images)} 장 디코드 완료")
    print()

    # 3. 임베딩
    print(f"[3/4] CLIP 임베딩 추출...")
    embedding = compute_mean_embedding(images, use_mock=args.use_mock)
    print(f"  shape={embedding.shape}, norm={np.linalg.norm(embedding):.4f}")
    print()

    # 4. 저장 + 검증
    if args.dry_run:
        print("[4/4] dry-run — 저장 안 함")
    else:
        EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
        np.save(str(TARGET_NPY), embedding)
        print(f"[4/4] 저장 완료: {TARGET_NPY}")

        verify_dimension(TARGET_NPY)
        others = verify_other_types_dimension()
        mismatches = [k for k, v in others.items() if v != 768]
        if mismatches:
            print(f"  [경고] 차원 불일치 type_*.npy: {mismatches}")
        else:
            print(f"  ✓ 다른 type_*.npy ({len(others)}개) 모두 768d")
    print()

    # type_anchors.json image_files 업데이트 (3-1.png + 3-2.png 명시)
    if not args.dry_run and TYPE_ANCHORS_PATH.exists():
        try:
            with open(TYPE_ANCHORS_PATH, encoding="utf-8") as f:
                ta = json.load(f)
            t3 = ta.get("anchors", {}).get("type_3")
            if t3 is not None:
                t3["image_files"] = [p.name for p in img_paths]
                with open(TYPE_ANCHORS_PATH, "w", encoding="utf-8") as f:
                    json.dump(ta, f, ensure_ascii=False, indent=2)
                print(
                    f"  type_anchors.json type_3.image_files 동기화: "
                    f"{[p.name for p in img_paths]}"
                )
        except Exception as e:
            print(f"  [경고] type_anchors.json 갱신 실패: {e}")
    print("=" * 60)
    print("  완료")
    print("=" * 60)


if __name__ == "__main__":
    main()
