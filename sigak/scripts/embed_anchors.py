"""
SIGAK Anchor Embedding + Visualization (성별 분리)

앵커 유형 이미지를 CLIP으로 임베딩하고 UMAP/t-SNE로 시각화합니다.
축 방향을 데이터에서 발견하기 위한 탐색 도구입니다.

Usage:
    python -m sigak.scripts.embed_anchors
    python -m sigak.scripts.embed_anchors --gender female
    python -m sigak.scripts.embed_anchors --gender male
    python -m sigak.scripts.embed_anchors --use-mock
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif"}
GENDERS = ["female", "male"]

# 한글 유형명 → type_anchors.json 영문 키 매핑
_KR_TO_KEY: dict[str, str] = {}


def _load_kr_mapping() -> dict[str, str]:
    """type_anchors.json에서 한글→영문 키 매핑을 로드한다."""
    global _KR_TO_KEY
    if _KR_TO_KEY:
        return _KR_TO_KEY

    anchors_path = Path(__file__).parent.parent / "data" / "type_anchors.json"
    if not anchors_path.exists():
        return {}

    with open(anchors_path, encoding="utf-8") as f:
        data = json.load(f)

    for key, info in data.get("anchors", {}).items():
        name_kr = info.get("name_kr", "")
        if name_kr:
            _KR_TO_KEY[name_kr] = key
        # 별명도 매핑
        for alias in info.get("aliases", []):
            _KR_TO_KEY[alias] = key

    return _KR_TO_KEY


def _read_image(img_path: Path) -> np.ndarray | None:
    """
    이미지를 로드한다. 한글 경로 + avif 지원.

    1차: np.fromfile + cv2.imdecode (한글 경로 안전, jpg/png/webp)
    2차: Pillow (avif 등 OpenCV 미지원 포맷)
    """
    # 1차: OpenCV (한글 경로 대응)
    try:
        buf = np.fromfile(str(img_path), dtype=np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if img is not None:
            return img
    except Exception:
        pass

    # 2차: Pillow 폴백 (avif 등)
    try:
        from PIL import Image
        pil_img = Image.open(str(img_path)).convert("RGB")
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        return img
    except Exception:
        pass

    return None


def _extract_anchor_name(filename: str) -> str:
    """
    파일명에서 앵커 이름 부분을 추출한다.
    '김유정1.jpg' → '김유정'
    'suzy_001.jpg' → 'suzy'
    """
    import re
    stem = Path(filename).stem
    # 한글 이름 + 숫자 패턴: '김유정1' → '김유정'
    match = re.match(r"^([가-힣]+)\d*", stem)
    if match:
        return match.group(1)
    # 영문_숫자 패턴: 'suzy_001' → 'suzy'
    match = re.match(r"^([a-zA-Z_]+?)_?\d*$", stem)
    if match:
        return match.group(1)
    return stem


def load_anchor_images(anchors_dir: Path) -> dict[str, list[np.ndarray]]:
    """
    앵커 디렉토리에서 유형별 이미지를 로드합니다.

    두 가지 구조를 모두 지원:
    A) 하위 폴더 구조: anchors/female/suzy/suzy_001.jpg
    B) flat 구조: anchors/female/수지1.jpg (한글 파일명)

    한글 유형명은 type_anchors.json의 영문 키로 자동 매핑됩니다.

    Returns:
        {영문_키: [BGR 이미지 배열 리스트]}
    """
    anchor_images: dict[str, list[np.ndarray]] = {}
    kr_map = _load_kr_mapping()

    if not anchors_dir.exists():
        print("[경고] 앵커 디렉토리가 존재하지 않습니다: " + str(anchors_dir))
        return anchor_images

    # 하위 디렉토리가 있으면 기존 구조 (A), 없으면 flat 구조 (B)
    subdirs = [d for d in anchors_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]

    if subdirs:
        # ── 구조 A: 하위 폴더 구조 ──
        print("  [모드] 하위 폴더 구조 감지")
        for type_dir in sorted(subdirs):
            type_name = type_dir.name
            # 한글 폴더명이면 영문 키로 매핑
            type_key = kr_map.get(type_name, type_name)

            images = []
            for img_path in sorted(type_dir.iterdir()):
                if img_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                    continue
                img = _read_image(img_path)
                if img is None:
                    print(f"  [경고] 이미지 로드 실패: {img_path.name}")
                    continue
                images.append(img)

            if images:
                anchor_images[type_key] = images
                label = f"{type_name} → {type_key}" if type_name != type_key else type_key
                print(f"  {label}: {len(images)}장 로드")
    else:
        # ── 구조 B: flat 구조 (파일명에서 유형명 파싱) ──
        print("  [모드] flat 구조 감지 (파일명에서 유형명 파싱)")
        temp: dict[str, list[tuple[Path, str]]] = {}

        for img_path in sorted(anchors_dir.iterdir()):
            if img_path.is_dir() or img_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            raw_name = _extract_anchor_name(img_path.name)
            if not raw_name:
                continue
            temp.setdefault(raw_name, []).append((img_path, raw_name))

        for raw_name, file_list in sorted(temp.items()):
            type_key = kr_map.get(raw_name, raw_name)
            images = []
            for img_path, _ in file_list:
                img = _read_image(img_path)
                if img is None:
                    print(f"  [경고] 이미지 로드 실패: {img_path.name}")
                    continue
                images.append(img)

            if images:
                anchor_images[type_key] = images
                label = f"{raw_name} → {type_key}" if raw_name != type_key else type_key
                print(f"  {label}: {len(images)}장 로드")
            else:
                print(f"  [경고] {raw_name}: 유효한 이미지 없음, 건너뛰")

    return anchor_images


def compute_embeddings(
    anchor_images: dict[str, list[np.ndarray]],
    use_mock: bool = False,
) -> dict[str, np.ndarray]:
    """앵커 유형별 평균 CLIP 임베딩을 계산합니다."""
    from pipeline.clip import CLIPEmbedder, mock_embedding

    anchor_embeddings: dict[str, np.ndarray] = {}

    if use_mock:
        # Mock 모드: 이미지 바이트 해시 기반 768d 의사 임베딩
        for anchor_name, images in anchor_images.items():
            print(f"  {anchor_name} 임베딩 중 (mock)... ({len(images)}장)")
            embeddings = []
            for img in images:
                img_bytes = cv2.imencode(".jpg", img)[1].tobytes()
                embeddings.append(mock_embedding(img_bytes))
            mean_emb = np.mean(embeddings, axis=0)
            mean_emb = mean_emb / (np.linalg.norm(mean_emb) + 1e-8)
            anchor_embeddings[anchor_name] = mean_emb
    else:
        # 실제 CLIP 모드: 싱글톤 CLIPEmbedder 사용
        embedder = CLIPEmbedder()
        for anchor_name, images in anchor_images.items():
            print(f"  {anchor_name} 임베딩 중... ({len(images)}장)")
            embeddings = [embedder.extract(img) for img in images]
            mean_emb = np.mean(embeddings, axis=0)
            mean_emb = mean_emb / (np.linalg.norm(mean_emb) + 1e-8)
            anchor_embeddings[anchor_name] = mean_emb

    return anchor_embeddings


def save_embeddings(
    anchor_embeddings: dict[str, np.ndarray],
    output_dir: Path,
) -> None:
    """임베딩을 파일로 저장합니다."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for anchor_name, embedding in anchor_embeddings.items():
        npy_path = output_dir / (anchor_name + ".npy")
        np.save(str(npy_path), embedding)

    npz_path = output_dir / "all_embeddings.npz"
    np.savez(str(npz_path), **anchor_embeddings)

    print("")
    print("임베딩 저장 완료:")
    count = len(anchor_embeddings)
    print(f"  개별 파일: {output_dir}/<유형이름>.npy ({count}개)")
    print(f"  통합 파일: {npz_path}")


def _extract_features_from_loaded(
    anchor_images: dict[str, list[np.ndarray]],
) -> dict[str, dict]:
    """이미 로드된 이미지에서 구조적 특징을 추출한다."""
    from pipeline.face import analyze_face

    result: dict[str, dict] = {}

    for type_key, images in anchor_images.items():
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
            print(f"  [경고] {type_key}: 얼굴 분석 실패, 건너뜀")
            continue

        # 수치 특징 평균
        avg: dict = {}
        all_keys = set()
        for feat in all_features:
            all_keys.update(feat.keys())
        for key in all_keys:
            values = [float(f[key]) for f in all_features if key in f and isinstance(f[key], (int, float, np.floating, np.integer))]
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

    return result


def setup_korean_font():
    """matplotlib 한국어 폰트를 설정합니다."""
    import matplotlib
    import matplotlib.font_manager as fm

    font_candidates = [
        "Pretendard", "Noto Sans KR", "Malgun Gothic",
        "AppleGothic", "NanumGothic", "DejaVu Sans",
    ]
    available_fonts = {f.name for f in fm.fontManager.ttflist}

    for font_name in font_candidates:
        if font_name in available_fonts:
            matplotlib.rcParams["font.family"] = font_name
            matplotlib.rcParams["axes.unicode_minus"] = False
            print(f"  폰트 설정: {font_name}")
            return font_name

    matplotlib.rcParams["axes.unicode_minus"] = False
    print("  [경고] 한국어 폰트를 찾지 못했습니다. 기본 폰트 사용.")
    return None


def visualize_umap(
    anchor_embeddings: dict[str, np.ndarray],
    output_path: Path,
    gender: str,
) -> None:
    """UMAP 2D 투영 시각화를 생성합니다."""
    import matplotlib.pyplot as plt

    try:
        import umap
    except ImportError:
        print("  [경고] umap-learn이 설치되지 않았습니다. UMAP 시각화를 건너뜁니다.")
        print("  설치: pip install umap-learn")
        return

    names = list(anchor_embeddings.keys())
    embeddings = np.array([anchor_embeddings[n] for n in names])
    n_samples = len(names)
    n_neighbors = min(15, max(2, n_samples - 1))

    print(f"  UMAP 투영 중... (n={n_samples}, n_neighbors={n_neighbors})")

    reducer = umap.UMAP(
        n_components=2, n_neighbors=n_neighbors,
        min_dist=0.3, metric="cosine", random_state=42,
    )
    coords_2d = reducer.fit_transform(embeddings)

    fig, ax = plt.subplots(figsize=(12, 10))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.scatter(
        coords_2d[:, 0], coords_2d[:, 1], s=120,
        c=range(n_samples), cmap="viridis", alpha=0.8,
        edgecolors="white", linewidths=1.5, zorder=5,
    )
    for i, name in enumerate(names):
        ax.annotate(
            name, (coords_2d[i, 0], coords_2d[i, 1]),
            textcoords="offset points", xytext=(8, 8),
            fontsize=10, fontweight="bold", color="#333333", zorder=10,
        )
    gender_label = gender.upper()
    ax.set_title(f"SIGAK Anchor Embeddings [{gender_label}] - UMAP 2D Projection", fontsize=16, pad=20)
    ax.set_xlabel("UMAP-1", fontsize=12)
    ax.set_ylabel("UMAP-2", fontsize=12)
    ax.grid(True, alpha=0.3, linestyle="--")
    plt.tight_layout()
    fig.savefig(str(output_path), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  UMAP 시각화 저장: {output_path}")


def visualize_tsne(
    anchor_embeddings: dict[str, np.ndarray],
    output_path: Path,
    gender: str,
) -> None:
    """t-SNE 2D 투영 시각화를 생성합니다."""
    import matplotlib.pyplot as plt
    from sklearn.manifold import TSNE

    names = list(anchor_embeddings.keys())
    embeddings = np.array([anchor_embeddings[n] for n in names])
    n_samples = len(names)
    perplexity = min(30.0, max(2.0, float(n_samples - 1)))

    print(f"  t-SNE 투영 중... (n={n_samples}, perplexity={perplexity})")

    tsne = TSNE(
        n_components=2, perplexity=perplexity,
        random_state=42, max_iter=1000, metric="cosine",
    )
    coords_2d = tsne.fit_transform(embeddings)

    fig, ax = plt.subplots(figsize=(12, 10))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.scatter(
        coords_2d[:, 0], coords_2d[:, 1], s=120,
        c=range(n_samples), cmap="plasma", alpha=0.8,
        edgecolors="white", linewidths=1.5, zorder=5,
    )
    for i, name in enumerate(names):
        ax.annotate(
            name, (coords_2d[i, 0], coords_2d[i, 1]),
            textcoords="offset points", xytext=(8, 8),
            fontsize=10, fontweight="bold", color="#333333", zorder=10,
        )
    gender_label = gender.upper()
    ax.set_title(f"SIGAK Anchor Embeddings [{gender_label}] - t-SNE 2D Projection", fontsize=16, pad=20)
    ax.set_xlabel("t-SNE-1", fontsize=12)
    ax.set_ylabel("t-SNE-2", fontsize=12)
    ax.grid(True, alpha=0.3, linestyle="--")
    plt.tight_layout()
    fig.savefig(str(output_path), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  t-SNE 시각화 저장: {output_path}")


def print_summary(anchor_embeddings: dict[str, np.ndarray], gender: str) -> None:
    """임베딩 요약 정보를 출력합니다."""
    names = list(anchor_embeddings.keys())
    n = len(names)

    print("")
    print("=" * 55)
    print(f"  앵커 유형 임베딩 요약 [{gender.upper()}]")
    print("=" * 55)
    col1 = "유형 이름"
    col2 = "임베딩 Norm"
    col3 = "차원"
    print(f"  {col1:<20} {col2:>12} {col3:>8}")
    print("-" * 55)

    for name in names:
        emb = anchor_embeddings[name]
        norm = float(np.linalg.norm(emb))
        dim = emb.shape[0]
        print(f"  {name:<20} {norm:>12.6f} {dim:>8d}")

    print("-" * 55)
    print(f"  총 {n}개 유형 임베딩 완료")

    if n < 2:
        print("")
        print("  [참고] 유사도 행렬을 위해 최소 2개 유형이 필요합니다.")
        return

    display_names = names[:10]
    display_n = len(display_names)
    sep_len = 16 + display_n * 10

    print("")
    print("=" * sep_len)
    print("  코사인 유사도 행렬")
    print("=" * sep_len)

    header = "  " + " " * 14
    for name in display_names:
        short = name[:7] if len(name) > 7 else name
        header += f" {short:>8}"
    print(header)
    print("-" * sep_len)

    for i, name_i in enumerate(display_names):
        short_i = name_i[:12] if len(name_i) > 12 else name_i
        row = f"  {short_i:>14}"
        emb_i = anchor_embeddings[name_i]
        for j, name_j in enumerate(display_names):
            emb_j = anchor_embeddings[name_j]
            sim = float(np.dot(emb_i, emb_j))
            row += f" {sim:>8.4f}"
        print(row)

    print("-" * sep_len)
    if n > 10:
        print(f"  (상위 10명만 표시, 전체 {n}명)")


def process_gender(
    gender: str,
    anchors_root: Path,
    output_root: Path,
    use_mock: bool,
) -> None:
    """한 성별의 전체 임베딩 파이프라인을 실행합니다."""
    anchors_dir = anchors_root / gender
    output_dir = output_root / gender

    print("")
    print(f"{'=' * 60}")
    print(f"  [{gender.upper()}] 앵커 처리 시작")
    print(f"{'=' * 60}")
    print(f"  앵커 디렉토리: {anchors_dir.resolve()}")
    print(f"  출력 디렉토리: {output_dir.resolve()}")
    print()

    # 1단계: 이미지 로드
    print(f"[1/6] [{gender.upper()}] 앵커 이미지 로드 중...")
    anchor_images = load_anchor_images(anchors_dir)

    if not anchor_images:
        print("")
        print(f"[건너뛰] [{gender.upper()}] 로드된 앵커 이미지가 없습니다.")
        anchors_str = str(anchors_dir)
        print(f"  '{anchors_str}' 디렉토리에 앵커 폴더를 추가하세요.")
        print(f"  구조: anchors/{gender}/<type_name>/<image>.jpg")
        return

    total_images = sum(len(imgs) for imgs in anchor_images.values())
    anchor_count = len(anchor_images)
    print(f"  총 {anchor_count}개, {total_images}장 로드 완료")
    print()

    # 2단계: CLIP 임베딩
    print(f"[2/6] [{gender.upper()}] CLIP 임베딩 추출 중...")
    anchor_embeddings = compute_embeddings(anchor_images, use_mock=use_mock)
    emb_count = len(anchor_embeddings)
    print(f"  {emb_count}명 임베딩 완료")
    print()

    # 3단계: 구조적 특징 추출 + 캐시 (이미 로드된 이미지 재활용)
    print(f"[3/6] [{gender.upper()}] 구조적 특징 추출 중...")
    anchor_features = _extract_features_from_loaded(anchor_images)
    if anchor_features:
        from pipeline.face_comparison import save_anchor_features, load_anchor_features
        # 기존 캐시와 병합
        existing = load_anchor_features()
        existing.update(anchor_features)
        save_anchor_features(existing)
        feat_count = len(anchor_features)
        print(f"  {feat_count}개 구조적 특징 캐시 완료 (type_features_cache.json)")
    else:
        print("  [경고] 구조적 특징 추출 실패 — 비교 기능 비활성화")
    print()

    # 4단계: 임베딩 저장
    print(f"[4/6] [{gender.upper()}] 임베딩 저장 중...")
    save_embeddings(anchor_embeddings, output_dir)
    print()

    # 5단계: 시각화 생성
    print(f"[5/6] [{gender.upper()}] 시각화 생성 중...")
    setup_korean_font()

    if len(anchor_embeddings) < 2:
        print("  [참고] 시각화를 위해 최소 2개 유형이 필요합니다.")
        print(f"  현재 유형 수: {len(anchor_embeddings)}")
    else:
        visualize_umap(anchor_embeddings, output_dir / "umap_2d.png", gender)
        visualize_tsne(anchor_embeddings, output_dir / "tsne_2d.png", gender)

    # 6단계: 요약 출력
    print("")
    print(f"[6/6] [{gender.upper()}] 요약 정보")
    print_summary(anchor_embeddings, gender)


def parse_args() -> argparse.Namespace:
    """CLI 인자를 파싱합니다."""
    parser = argparse.ArgumentParser(
        description="SIGAK 앵커 임베딩 + 시각화 도구 (성별 분리)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--anchors-dir", type=str, default="sigak/data/anchors",
        help="앵커 이미지 루트 디렉토리 (기본: sigak/data/anchors)",
    )
    parser.add_argument(
        "--output-dir", type=str, default="sigak/data/embeddings",
        help="출력 디렉토리 (기본: sigak/data/embeddings)",
    )
    parser.add_argument(
        "--use-mock", action="store_true", default=False,
        help="GPU 없이 mock 임베딩 사용 (테스트용)",
    )
    parser.add_argument(
        "--gender", type=str, default=None, choices=["female", "male"],
        help="특정 성별만 처리 (기본: 둘 다 처리)",
    )
    return parser.parse_args()


def main() -> None:
    """메인 실행 함수."""
    args = parse_args()
    anchors_root = Path(args.anchors_dir)
    output_root = Path(args.output_dir)

    print("=" * 60)
    print("  SIGAK Anchor Embedding + Visualization (성별 분리)")
    print("=" * 60)
    print(f"  앵커 루트: {anchors_root.resolve()}")
    print(f"  출력 루트: {output_root.resolve()}")
    mode_str = "Mock (테스트)" if args.use_mock else "CLIP (실제)"
    print(f"  모드: {mode_str}")

    genders = [args.gender] if args.gender else GENDERS

    for gender in genders:
        process_gender(gender, anchors_root, output_root, args.use_mock)

    print("")
    print("=" * 60)
    print("  완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
