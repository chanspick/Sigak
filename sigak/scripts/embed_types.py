"""
SIGAK Type Anchor Embedding Generator

AI 생성 유형 앵커 이미지를 CLIP으로 임베딩하고,
MediaPipe로 구조적 특징을 추출하여 캐시한다.

type_anchors.json의 image_files 필드를 기반으로 이미지를 로드하므로
파일명 패턴 파싱이 불필요하다.

Usage:
    python -m sigak.scripts.embed_types
    python -m sigak.scripts.embed_types --use-mock
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np


ANCHORS_DIR = Path(__file__).parent.parent / "data" / "anchors"
EMBEDDINGS_DIR = Path(__file__).parent.parent / "data" / "embeddings"
TYPE_ANCHORS_PATH = Path(__file__).parent.parent / "data" / "type_anchors.json"
TYPE_FEATURES_CACHE_PATH = Path(__file__).parent.parent / "data" / "type_features_cache.json"


def _read_image(img_path: Path) -> np.ndarray | None:
    """이미지를 로드한다. 한글 경로 + avif 지원."""
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
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        return img
    except Exception:
        pass

    return None


def _find_type_images(img_dir: Path, type_id: int) -> list[Path]:
    """
    유형 번호 접두사로 이미지를 자동 탐색한다.
    파일명 패턴: "{type_id} (1).jpg", "{type_id} (1) - 편집함.jpg" 등
    접두사 "{type_id}" 뒤에 공백/괄호/하이픈이 오는 모든 이미지를 매칭.
    """
    import re
    prefix = str(type_id)
    pattern = re.compile(rf"^{re.escape(prefix)}[\s\(]")
    found = []
    for f in sorted(img_dir.iterdir()):
        if f.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        if pattern.match(f.name):
            found.append(f)
    return found


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif"}


def load_type_images(gender: str = "female") -> dict[str, list[np.ndarray]]:
    """
    type_anchors.json에서 유형 정의를 읽고, 접두사 매칭으로 이미지를 로드한다.

    Returns:
        {type_key: [BGR numpy 배열 리스트]}
    """
    if not TYPE_ANCHORS_PATH.exists():
        print(f"[오류] type_anchors.json 없음: {TYPE_ANCHORS_PATH}")
        return {}

    with open(TYPE_ANCHORS_PATH, encoding="utf-8") as f:
        data = json.load(f)

    type_images: dict[str, list[np.ndarray]] = {}
    img_dir = ANCHORS_DIR / gender

    if not img_dir.exists():
        print(f"[오류] 이미지 디렉토리 없음: {img_dir}")
        return {}

    for key, info in data.get("anchors", {}).items():
        if info.get("gender") != gender:
            continue

        type_id = info.get("type_id")
        if type_id is None:
            print(f"  [경고] {key}: type_id 없음, 건너뜀")
            continue

        # 1. image_files 필드의 literal 파일명 우선 시도 (남성 앵커 등 단순 파일명)
        matched_files: list[Path] = []
        for fname in info.get("image_files", []) or []:
            candidate = img_dir / fname
            if candidate.exists() and candidate.suffix.lower() in SUPPORTED_EXTENSIONS:
                matched_files.append(candidate)

        # 2. literal 미발견 시 접두사 기반 자동 탐색으로 fallback
        #    (여성 앵커 "1 (3) - 편집함.jpg" 같이 원본과 파일명이 다른 경우)
        if not matched_files:
            matched_files = _find_type_images(img_dir, type_id)

        images = []
        for img_path in matched_files:
            img = _read_image(img_path)
            if img is None:
                print(f"  [경고] 이미지 로드 실패: {img_path.name}")
                continue
            images.append(img)

        if images:
            type_images[key] = images
            label = info.get("name_kr", key)
            print(f"  {key} ({label}): {len(images)}장 로드")
        else:
            print(f"  [경고] {key} (id={type_id}): 유효한 이미지 없음")

    return type_images


def compute_type_embeddings(
    type_images: dict[str, list[np.ndarray]],
    use_mock: bool = False,
) -> dict[str, np.ndarray]:
    """유형별 평균 CLIP 임베딩을 계산한다."""
    from pipeline.clip import CLIPEmbedder, mock_embedding

    type_embeddings: dict[str, np.ndarray] = {}

    if use_mock:
        for type_key, images in type_images.items():
            print(f"  {type_key} 임베딩 중 (mock)... ({len(images)}장)")
            embeddings = []
            for img in images:
                img_bytes = cv2.imencode(".jpg", img)[1].tobytes()
                embeddings.append(mock_embedding(img_bytes))
            mean_emb = np.mean(embeddings, axis=0)
            mean_emb = mean_emb / (np.linalg.norm(mean_emb) + 1e-8)
            type_embeddings[type_key] = mean_emb
    else:
        embedder = CLIPEmbedder()
        for type_key, images in type_images.items():
            print(f"  {type_key} 임베딩 중... ({len(images)}장)")
            embeddings = [embedder.extract(img) for img in images]
            mean_emb = np.mean(embeddings, axis=0)
            mean_emb = mean_emb / (np.linalg.norm(mean_emb) + 1e-8)
            type_embeddings[type_key] = mean_emb

    return type_embeddings


def extract_type_features(
    type_images: dict[str, list[np.ndarray]],
) -> dict[str, dict]:
    """유형별 구조적 특징을 추출하고 캐시에 저장한다."""
    from pipeline.face import analyze_face

    result: dict[str, dict] = {}

    for type_key, images in type_images.items():
        print(f"  {type_key} 구조 분석 중... ({len(images)}장)")
        all_features: list[dict] = []

        for img in images:
            try:
                img_bytes = cv2.imencode(".jpg", img)[1].tobytes()
                face_result = analyze_face(img_bytes)
                if face_result is not None:
                    all_features.append(face_result.to_dict())
            except Exception:
                continue

        if not all_features:
            print(f"  [경고] {type_key}: 얼굴 분석 실패")
            continue

        # 수치 특징 평균
        avg: dict = {}
        all_keys = set()
        for feat in all_features:
            all_keys.update(feat.keys())
        for key in all_keys:
            values = [
                float(f[key]) for f in all_features
                if key in f and isinstance(f[key], (int, float))
            ]
            if values:
                avg[key] = round(sum(values) / len(values), 4)

        # 범주형 특징 최빈값
        for cat_key in ("face_shape", "skin_tone"):
            vals = [f[cat_key] for f in all_features if cat_key in f]
            if vals:
                avg[cat_key] = max(set(vals), key=vals.count)

        avg["sample_count"] = len(all_features)
        result[type_key] = avg
        print(f"  {type_key}: {len(all_features)}장 분석 완료")

    # 캐시 저장
    if result:
        TYPE_FEATURES_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TYPE_FEATURES_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  구조적 특징 캐시 저장: {TYPE_FEATURES_CACHE_PATH.name}")

    return result


def save_type_embeddings(
    type_embeddings: dict[str, np.ndarray],
    gender: str = "female",
) -> None:
    """임베딩을 .npy 파일로 저장하고 type_anchors.json의 embedding_path를 업데이트한다."""
    output_dir = EMBEDDINGS_DIR / gender
    output_dir.mkdir(parents=True, exist_ok=True)

    for type_key, embedding in type_embeddings.items():
        npy_path = output_dir / f"{type_key}.npy"
        np.save(str(npy_path), embedding)

    # type_anchors.json 업데이트
    if TYPE_ANCHORS_PATH.exists():
        with open(TYPE_ANCHORS_PATH, encoding="utf-8") as f:
            data = json.load(f)

        for type_key in type_embeddings:
            if type_key in data.get("anchors", {}):
                rel_path = f"sigak/data/embeddings/{gender}/{type_key}.npy"
                data["anchors"][type_key]["embedding_path"] = rel_path

        with open(TYPE_ANCHORS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    count = len(type_embeddings)
    print(f"  {count}개 유형 임베딩 저장 완료: {output_dir}")


def print_summary(type_embeddings: dict[str, np.ndarray]) -> None:
    """유사도 행렬을 출력한다."""
    names = list(type_embeddings.keys())
    n = len(names)

    print("")
    print("=" * 55)
    print("  유형 임베딩 요약")
    print("=" * 55)
    print(f"  {'유형 키':<20} {'Norm':>12} {'차원':>8}")
    print("-" * 55)

    for name in names:
        emb = type_embeddings[name]
        norm = float(np.linalg.norm(emb))
        print(f"  {name:<20} {norm:>12.6f} {emb.shape[0]:>8d}")

    if n >= 2:
        print("")
        print("  코사인 유사도 행렬:")
        header = "  " + " " * 12
        for name in names:
            header += f" {name[-6:]:>8}"
        print(header)
        print("-" * (14 + n * 9))

        for i, ni in enumerate(names):
            row = f"  {ni[-10:]:>12}"
            for j, nj in enumerate(names):
                sim = float(np.dot(type_embeddings[ni], type_embeddings[nj]))
                row += f" {sim:>8.4f}"
            print(row)

    print("")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SIGAK 유형 앵커 임베딩 생성기",
    )
    parser.add_argument(
        "--use-mock", action="store_true", default=False,
        help="GPU 없이 mock 임베딩 사용 (테스트용)",
    )
    parser.add_argument(
        "--gender", type=str, default="female", choices=["female", "male"],
        help="처리할 성별 (기본: female)",
    )
    parser.add_argument(
        "--skip-features", action="store_true", default=False,
        help="구조적 특징 추출 건너뜀 (임베딩만 생성)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  SIGAK Type Anchor Embedding Generator")
    print("=" * 60)
    mode_str = "Mock (테스트)" if args.use_mock else "CLIP (실제)"
    print(f"  모드: {mode_str}")
    print(f"  성별: {args.gender}")
    print()

    # 1단계: 이미지 로드
    print(f"[1/4] 유형 이미지 로드 중...")
    type_images = load_type_images(args.gender)
    if not type_images:
        print("[오류] 로드된 유형 이미지가 없습니다.")
        sys.exit(1)

    total = sum(len(imgs) for imgs in type_images.values())
    print(f"  총 {len(type_images)}유형, {total}장 로드 완료")
    print()

    # 2단계: CLIP 임베딩
    print(f"[2/4] CLIP 임베딩 추출 중...")
    type_embeddings = compute_type_embeddings(type_images, use_mock=args.use_mock)
    print(f"  {len(type_embeddings)}유형 임베딩 완료")
    print()

    # 3단계: 구조적 특징 추출
    if not args.skip_features:
        print(f"[3/4] 구조적 특징 추출 중...")
        extract_type_features(type_images)
        print()
    else:
        print(f"[3/4] 구조적 특징 추출 건너뜀")
        print()

    # 4단계: 저장
    print(f"[4/4] 임베딩 저장 중...")
    save_type_embeddings(type_embeddings, args.gender)
    print()

    print_summary(type_embeddings)

    print("=" * 60)
    print("  완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
