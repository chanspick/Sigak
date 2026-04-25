"""PI-B — anchor .npy 차원 일관성 회귀 가드.

목적:
  data/embeddings/{gender}/*.npy 들이 모두 768d 인지 확인.
  새로운 type_3.npy 가 들어왔을 때 다른 type_*.npy 와 차원 어긋나지 않는지 보장.

type_3.npy 는 PI-B 시점에 누락 가능 (regen_type_3 스크립트 미실행) — pytest.skip.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest


sys.path.insert(0, str(Path(__file__).parent.parent))

EMBEDDINGS_DIR = Path(__file__).parent.parent / "data" / "embeddings"
EXPECTED_DIM = 768


# ─────────────────────────────────────────────
#  Type embeddings dimension uniformity
# ─────────────────────────────────────────────

@pytest.mark.parametrize("gender", ["female", "male"])
def test_all_type_npys_are_768d(gender):
    emb_dir = EMBEDDINGS_DIR / gender
    if not emb_dir.exists():
        pytest.skip(f"{gender} embeddings dir 없음")

    type_npys = sorted(emb_dir.glob("type_*.npy"))
    if not type_npys:
        pytest.skip(f"{gender} type_*.npy 0건")

    bad: list[tuple[str, int]] = []
    for npy in type_npys:
        emb = np.load(str(npy))
        if emb.ndim != 1 or emb.shape[0] != EXPECTED_DIM:
            bad.append((npy.name, emb.shape[0] if emb.ndim == 1 else -1))

    assert not bad, (
        f"[{gender}] dimension 불일치 .npy 발견: {bad}. "
        f"기대: 1D {EXPECTED_DIM}d (CLIP ViT-L-14)"
    )


@pytest.mark.parametrize("gender", ["female", "male"])
def test_all_type_npys_are_l2_normalized(gender):
    emb_dir = EMBEDDINGS_DIR / gender
    if not emb_dir.exists():
        pytest.skip(f"{gender} embeddings dir 없음")

    type_npys = sorted(emb_dir.glob("type_*.npy"))
    if not type_npys:
        pytest.skip(f"{gender} type_*.npy 0건")

    bad: list[tuple[str, float]] = []
    for npy in type_npys:
        emb = np.load(str(npy))
        if emb.ndim != 1:
            continue
        n = float(np.linalg.norm(emb))
        if not (0.95 < n < 1.05):
            bad.append((npy.name, n))

    assert not bad, (
        f"[{gender}] L2 정규화 안 된 .npy: {bad}. "
        f"CLIP extract 후 / np.linalg.norm 으로 정규화되어야 함."
    )


# ─────────────────────────────────────────────
#  Female type_3.npy 누락 가드 (PI-B 신규 — 재계산 후 통과)
# ─────────────────────────────────────────────

def test_female_type_3_npy_exists_or_documented():
    """type_3.npy 가 존재하면 차원/정규화 검증.

    부재 시 — `python -m scripts.regen_type_3` 실행 안내로 skip.
    """
    type_3 = EMBEDDINGS_DIR / "female" / "type_3.npy"
    if not type_3.exists():
        pytest.skip(
            "data/embeddings/female/type_3.npy 누락 — "
            "`python -m scripts.regen_type_3` 으로 재계산 필요"
        )
    emb = np.load(str(type_3))
    assert emb.ndim == 1
    assert emb.shape[0] == EXPECTED_DIM
    assert 0.95 < float(np.linalg.norm(emb)) < 1.05


# ─────────────────────────────────────────────
#  Female celeb embeddings — celeb_anchors_meta 와 1:1 정합
# ─────────────────────────────────────────────

def test_female_celeb_npys_match_meta():
    """celeb_anchors_meta.json 의 female 셀럽 16명 vs 실제 .npy 파일 매핑 검증.

    - meta 에 있는데 .npy 없음 → 실패
    - .npy 차원이 768 아님 → 실패
    """
    from pipeline.celeb_similarity import load_celeb_meta, reload_celeb_meta

    reload_celeb_meta()  # 캐시 초기화
    meta = load_celeb_meta()

    female_keys = [
        k for k, v in meta.get("celebs", {}).items()
        if v.get("gender") == "female"
    ]
    assert len(female_keys) == 16, (
        f"female 셀럽 16명 spec, 실제 {len(female_keys)}: {female_keys}"
    )

    emb_dir = EMBEDDINGS_DIR / "female"
    if not emb_dir.exists():
        pytest.skip("female embeddings dir 없음")

    missing: list[str] = []
    bad_dim: list[tuple[str, int]] = []

    for key in female_keys:
        npy_path = emb_dir / f"{key}.npy"
        if not npy_path.exists():
            missing.append(key)
            continue
        emb = np.load(str(npy_path))
        if emb.ndim != 1 or emb.shape[0] != EXPECTED_DIM:
            bad_dim.append((key, emb.shape[0] if emb.ndim == 1 else -1))

    assert not missing, (
        f"celeb_anchors_meta 에 있지만 .npy 누락: {missing}. "
        f"`python -m scripts.embed_anchors` 재실행 필요."
    )
    assert not bad_dim, (
        f"celeb .npy 차원 불일치: {bad_dim}. CLIP ViT-L-14 = 768d"
    )
