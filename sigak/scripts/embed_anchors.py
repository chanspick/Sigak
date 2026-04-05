"""
SIGAK Anchor Embedding + Visualization

셀럽 앵커 이미지를 CLIP으로 임베딩하고 UMAP/t-SNE로 시각화합니다.
축 방향을 데이터에서 발견하기 위한 탐색 도구입니다.

Usage:
    python -m sigak.scripts.embed_anchors
    python -m sigak.scripts.embed_anchors --anchors-dir sigak/data/anchors --output-dir sigak/data/embeddings
    python -m sigak.scripts.embed_anchors --use-mock  # GPU 없이 테스트
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def load_celeb_images(anchors_dir: Path) -> dict[str, list[np.ndarray]]:
    """
    앵커 디렉토리에서 셀럽별 이미지를 로드합니다.

    Args:
        anchors_dir: 앵커 이미지 루트 디렉토리

    Returns:
        {셀럽_이름: [BGR 이미지 배열 리스트]}
    """
    celeb_images: dict[str, list[np.ndarray]] = {}

    if not anchors_dir.exists():
        print("[경고] 앵커 디렉토리가 존재하지 않습니다: " + str(anchors_dir))
        return celeb_images

    # 하위 디렉토리 순회 (각 서브 디렉토리 = 셀럽 1명)
    for celeb_dir in sorted(anchors_dir.iterdir()):
        if not celeb_dir.is_dir():
            continue

        celeb_name = celeb_dir.name
        if celeb_name.startswith("."):
            continue

        images = []
        for img_path in sorted(celeb_dir.iterdir()):
            if img_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            img = cv2.imread(str(img_path))
            if img is None:
                print("  [경고] 이미지 로드 실패: " + str(img_path))
                continue

            images.append(img)

        if images:
            celeb_images[celeb_name] = images
            print(f"  {celeb_name}: {len(images)}장 로드")
        else:
            print(f"  [경고] {celeb_name}: 유효한 이미지 없음, 건너뛰")

    return celeb_images


def compute_embeddings(
    celeb_images: dict[str, list[np.ndarray]],
    use_mock: bool = False,
) -> dict[str, np.ndarray]:
    """셀럽별 평균 CLIP 임베딩을 계산합니다."""
    from sigak.pipeline.clip import CLIPEmbedder, mock_embedding

    celeb_embeddings: dict[str, np.ndarray] = {}

    if use_mock:
        # Mock 모드: 이미지 바이트 해시 기반 768d 의사 임베딩
        for celeb_name, images in celeb_images.items():
            print(f"  {celeb_name} 임베딩 중 (mock)... ({len(images)}장)")
            embeddings = []
            for img in images:
                img_bytes = cv2.imencode(".jpg", img)[1].tobytes()
                embeddings.append(mock_embedding(img_bytes))
            mean_emb = np.mean(embeddings, axis=0)
            mean_emb = mean_emb / (np.linalg.norm(mean_emb) + 1e-8)
            celeb_embeddings[celeb_name] = mean_emb
    else:
        # 실제 CLIP 모드: 싱글톤 CLIPEmbedder 사용
        embedder = CLIPEmbedder()
        for celeb_name, images in celeb_images.items():
            print(f"  {celeb_name} 임베딩 중... ({len(images)}장)")
            embeddings = [embedder.extract(img) for img in images]
            mean_emb = np.mean(embeddings, axis=0)
            mean_emb = mean_emb / (np.linalg.norm(mean_emb) + 1e-8)
            celeb_embeddings[celeb_name] = mean_emb

    return celeb_embeddings


def save_embeddings(
    celeb_embeddings: dict[str, np.ndarray],
    output_dir: Path,
) -> None:
    """임베딩을 파일로 저장합니다."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for celeb_name, embedding in celeb_embeddings.items():
        npy_path = output_dir / (celeb_name + ".npy")
        np.save(str(npy_path), embedding)

    npz_path = output_dir / "all_embeddings.npz"
    np.savez(str(npz_path), **celeb_embeddings)

    print("")
    print("임베딩 저장 완료:")
    count = len(celeb_embeddings)
    print(f"  개별 파일: {output_dir}/<셀럽이름>.npy ({count}개)")
    print(f"  통합 파일: {npz_path}")


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
    celeb_embeddings: dict[str, np.ndarray],
    output_path: Path,
) -> None:
    """UMAP 2D 투영 시각화를 생성합니다."""
    import matplotlib.pyplot as plt

    try:
        import umap
    except ImportError:
        print("  [경고] umap-learn이 설치되지 않았습니다. UMAP 시각화를 건너뜁니다.")
        print("  설치: pip install umap-learn")
        return

    names = list(celeb_embeddings.keys())
    embeddings = np.array([celeb_embeddings[n] for n in names])
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
    ax.set_title("SIGAK Anchor Embeddings - UMAP 2D Projection", fontsize=16, pad=20)
    ax.set_xlabel("UMAP-1", fontsize=12)
    ax.set_ylabel("UMAP-2", fontsize=12)
    ax.grid(True, alpha=0.3, linestyle="--")
    plt.tight_layout()
    fig.savefig(str(output_path), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  UMAP 시각화 저장: {output_path}")


def visualize_tsne(
    celeb_embeddings: dict[str, np.ndarray],
    output_path: Path,
) -> None:
    """t-SNE 2D 투영 시각화를 생성합니다."""
    import matplotlib.pyplot as plt
    from sklearn.manifold import TSNE

    names = list(celeb_embeddings.keys())
    embeddings = np.array([celeb_embeddings[n] for n in names])
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
    ax.set_title("SIGAK Anchor Embeddings - t-SNE 2D Projection", fontsize=16, pad=20)
    ax.set_xlabel("t-SNE-1", fontsize=12)
    ax.set_ylabel("t-SNE-2", fontsize=12)
    ax.grid(True, alpha=0.3, linestyle="--")
    plt.tight_layout()
    fig.savefig(str(output_path), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  t-SNE 시각화 저장: {output_path}")


def print_summary(celeb_embeddings: dict[str, np.ndarray]) -> None:
    """임베딩 요약 정보를 출력합니다."""
    names = list(celeb_embeddings.keys())
    n = len(names)

    print("")
    print("=" * 55)
    print("  셀럽 임베딩 요약")
    print("=" * 55)
    col1 = "셀럽 이름"
    col2 = "임베딩 Norm"
    col3 = "차원"
    print(f"  {col1:<20} {col2:>12} {col3:>8}")
    print("-" * 55)

    for name in names:
        emb = celeb_embeddings[name]
        norm = float(np.linalg.norm(emb))
        dim = emb.shape[0]
        print(f"  {name:<20} {norm:>12.6f} {dim:>8d}")

    print("-" * 55)
    print(f"  총 {n}명의 셀럽 임베딩 완료")

    if n < 2:
        print("")
        print("  [참고] 유사도 행렬을 위해 최소 2명의 셀럽이 필요합니다.")
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
        emb_i = celeb_embeddings[name_i]
        for j, name_j in enumerate(display_names):
            emb_j = celeb_embeddings[name_j]
            sim = float(np.dot(emb_i, emb_j))
            row += f" {sim:>8.4f}"
        print(row)

    print("-" * sep_len)
    if n > 10:
        print(f"  (상위 10명만 표시, 전체 {n}명)")


def parse_args() -> argparse.Namespace:
    """CLI 인자를 파싱합니다."""
    parser = argparse.ArgumentParser(
        description="SIGAK 앵커 임베딩 + 시각화 도구",
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
    return parser.parse_args()


def main() -> None:
    """메인 실행 함수."""
    args = parse_args()
    anchors_dir = Path(args.anchors_dir)
    output_dir = Path(args.output_dir)

    print("=" * 60)
    print("  SIGAK Anchor Embedding + Visualization")
    print("=" * 60)
    print(f"  앵커 디렉토리: {anchors_dir.resolve()}")
    print(f"  출력 디렉토리: {output_dir.resolve()}")
    mode_str = "Mock (테스트)" if args.use_mock else "CLIP (실제)"
    print(f"  모드: {mode_str}")
    print()

    # 1단계: 이미지 로드
    print("[1/5] 앵커 이미지 로드 중...")
    celeb_images = load_celeb_images(anchors_dir)

    if not celeb_images:
        print("")
        print("[오류] 로드된 셀럽 이미지가 없습니다.")
        anchors_str = str(anchors_dir)
        print(f"  '{anchors_str}' 디렉토리에 셀럽 폴더를 추가하세요.")
        print("  구조: anchors/<celeb_name>/<image>.jpg")
        print("")
        print("  예시:")
        print("    anchors/suzy/suzy_001.jpg")
        print("    anchors/suzy/suzy_002.jpg")
        print("    anchors/jungkook/jungkook_001.jpg")
        sys.exit(0)

    total_images = sum(len(imgs) for imgs in celeb_images.values())
    celeb_count = len(celeb_images)
    print(f"  총 {celeb_count}명, {total_images}장 로드 완료")
    print()

    # 2단계: CLIP 임베딩
    print("[2/5] CLIP 임베딩 추출 중...")
    celeb_embeddings = compute_embeddings(celeb_images, use_mock=args.use_mock)
    emb_count = len(celeb_embeddings)
    print(f"  {emb_count}명 임베딩 완료")
    print()

    # 3단계: 임베딩 저장
    print("[3/5] 임베딩 저장 중...")
    save_embeddings(celeb_embeddings, output_dir)
    print()

    # 4단계: 시각화 생성
    print("[4/5] 시각화 생성 중...")
    setup_korean_font()

    if len(celeb_embeddings) < 2:
        print("  [참고] 시각화를 위해 최소 2명의 셀럽이 필요합니다.")
        print(f"  현재 셀럽 수: {len(celeb_embeddings)}")
    else:
        visualize_umap(celeb_embeddings, output_dir / "umap_2d.png")
        visualize_tsne(celeb_embeddings, output_dir / "tsne_2d.png")

    # 5단계: 요약 출력
    print("")
    print("[5/5] 요약 정보")
    print_summary(celeb_embeddings)

    print("")
    print("=" * 60)
    print("  완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
