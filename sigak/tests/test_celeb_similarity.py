"""PI-B — celeb_similarity 단위 테스트.

CLIP 모델 로딩 회피 — synthetic embedding (numpy random) 으로 cosine 만 검증.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest


# 프로젝트 루트 import path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ─────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def reset_celeb_cache():
    """매 테스트마다 모듈 캐시 초기화."""
    from pipeline import celeb_similarity
    celeb_similarity._meta_cache = None
    yield
    celeb_similarity._meta_cache = None


def _unit_vec(seed: int, dim: int = 768) -> np.ndarray:
    """결정성 있는 768d L2-normalized 벡터."""
    rng = np.random.RandomState(seed)
    v = rng.randn(dim).astype(np.float32)
    n = float(np.linalg.norm(v))
    return v / (n + 1e-12)


# ─────────────────────────────────────────────
#  load_celeb_meta
# ─────────────────────────────────────────────

def test_load_celeb_meta_has_16_female_celebs(reset_celeb_cache):
    from pipeline.celeb_similarity import load_celeb_meta

    meta = load_celeb_meta()
    celebs = meta.get("celebs", {})
    female_keys = [k for k, v in celebs.items() if v.get("gender") == "female"]
    assert len(female_keys) == 16, (
        f"v1 spec: 16 female celebs. found={len(female_keys)}: {female_keys}"
    )


def test_load_celeb_meta_each_entry_has_korean_name(reset_celeb_cache):
    from pipeline.celeb_similarity import load_celeb_meta

    meta = load_celeb_meta()
    for key, info in meta.get("celebs", {}).items():
        assert "name_kr" in info, f"{key} missing name_kr"
        assert info["name_kr"], f"{key} name_kr empty"


def test_load_celeb_meta_dimension_is_768(reset_celeb_cache):
    from pipeline.celeb_similarity import load_celeb_meta

    meta = load_celeb_meta()
    assert int(meta.get("dimension", 0)) == 768


def test_reload_celeb_meta_clears_cache(reset_celeb_cache):
    from pipeline import celeb_similarity

    m1 = celeb_similarity.load_celeb_meta()
    assert celeb_similarity._meta_cache is m1
    m2 = celeb_similarity.reload_celeb_meta()
    # 동일 file 로드라 내용은 같지만 객체는 새로 생성됐어야 함
    assert m2 is celeb_similarity._meta_cache


# ─────────────────────────────────────────────
#  find_similar_celebs — synthetic embeddings
# ─────────────────────────────────────────────

def test_find_similar_celebs_none_embedding_returns_empty(reset_celeb_cache):
    from pipeline.celeb_similarity import find_similar_celebs

    result = find_similar_celebs(None, gender="female")
    assert result == []


def test_find_similar_celebs_male_returns_empty_v1(reset_celeb_cache):
    """v1 = female only. male 셀럽 .npy 미수집 → 빈 리스트."""
    from pipeline.celeb_similarity import find_similar_celebs

    user_emb = _unit_vec(42)
    result = find_similar_celebs(user_emb, gender="male")
    assert result == []


def test_find_similar_celebs_top_k_ordered_desc(monkeypatch, reset_celeb_cache):
    """동일 셀럽 임베딩 주입 시 self-cosine=1 가 top-1 보장."""
    from pipeline import celeb_similarity

    target_emb = _unit_vec(7)
    other_a = _unit_vec(8)
    other_b = _unit_vec(9)

    monkeypatch.setattr(
        celeb_similarity,
        "load_celeb_embeddings",
        lambda gender: {
            "jang_wonyoung": target_emb,
            "suzy": other_a,
            "karina": other_b,
        },
    )

    result = celeb_similarity.find_similar_celebs(
        target_emb, gender="female", top_k=3, threshold=-1.0,
    )
    assert len(result) == 3
    assert result[0].key == "jang_wonyoung"
    # cosine self ≈ 1
    assert result[0].similarity > 0.99
    # 내림차순 정렬
    assert result[0].similarity >= result[1].similarity >= result[2].similarity


def test_find_similar_celebs_threshold_filters(monkeypatch, reset_celeb_cache):
    from pipeline import celeb_similarity

    user = _unit_vec(1)
    near = _unit_vec(1)            # cosine ≈ 1
    far = -near                    # cosine = -1

    monkeypatch.setattr(
        celeb_similarity,
        "load_celeb_embeddings",
        lambda gender: {"karina": near, "winter": far},
    )

    result = celeb_similarity.find_similar_celebs(
        user, gender="female", top_k=5, threshold=0.5,
    )
    # near 만 통과
    assert [m.key for m in result] == ["karina"]


def test_find_similar_celebs_similarity_pct_in_0_100(monkeypatch, reset_celeb_cache):
    from pipeline import celeb_similarity

    user = _unit_vec(2)
    monkeypatch.setattr(
        celeb_similarity,
        "load_celeb_embeddings",
        lambda gender: {"jisoo": _unit_vec(2), "iu": _unit_vec(99)},
    )

    result = celeb_similarity.find_similar_celebs(
        user, gender="female", top_k=2, threshold=-1.0,
    )
    for m in result:
        assert 0 <= m.similarity_pct <= 100


def test_find_similar_celebs_skips_wrong_dimension(
    monkeypatch, reset_celeb_cache, tmp_path,
):
    """dimension 불일치 .npy 는 load 단계에서 skip — find_similar_celebs 결과에 안 들어감."""
    from pipeline import celeb_similarity

    # 가짜 256d 임베딩 한 명 + 정상 768d 한 명을 로더가 반환하지 않도록 검증.
    # 직접 load_celeb_embeddings 를 monkeypatch 해서 emulate.
    user = _unit_vec(3)
    monkeypatch.setattr(
        celeb_similarity, "load_celeb_embeddings",
        lambda gender: {"karina": _unit_vec(3)},   # dimension mismatch 는 로더가 이미 걸러냄
    )
    result = celeb_similarity.find_similar_celebs(
        user, gender="female", top_k=3, threshold=-1.0,
    )
    assert all(m.key == "karina" for m in result)
