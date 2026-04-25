"""Verdict 2.0 routes integration tests (Priority 1 D5 Phase 2).

Covers `/api/v2/verdict/{create, {id}/unlock, {id}}` via FastAPI TestClient.
DB + LLM both mocked — no live Sonnet API, no Postgres.

시나리오:
  create happy path (3 장 / 10 장)
  create input validation (<3, >10, unsupported type, empty)
  create no profile (409)
  unlock atomic — insufficient tokens (402), already unlocked (idempotent),
                   not owner (403), v1 verdict (409), not found (404)
  GET — preview only (locked), preview + full (unlocked), 403 not owner
"""
import base64
import io
import json
import os
import sys
from typing import Any, Optional
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from schemas.verdict_v2 import VerdictV2Result
from services import tokens as tokens_service
from services import verdict_v2 as v2_engine


# ─────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────

# Valid 1x1 PNG (8 bytes header + minimal IHDR). Smallest-possible PNG.
MIN_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a"
    "0000000d49484452"
    "0000000100000001"
    "08020000009077dd"
    "52000000014944415408"
    "99636000000000050001"
    "0d0a2db40000000049"
    "454e44ae426082"
)


def _fake_profile() -> dict:
    return {
        "user_id": "u1",
        "gender": "female",
        "birth_date": "1999-03-15",
        "ig_handle": None,
        "ig_feed_cache": None,
        "ig_fetch_status": "skipped",
        "structured_fields": {
            "desired_image": "편안한 인상",
            "height": "160_165",
        },
    }


def _fake_verdict_result() -> VerdictV2Result:
    return VerdictV2Result.model_validate({
        "preview": {
            "hook_line": "추구미와 피드 방향이 일치합니다",
            "reason_summary": (
                "쿨뮤트 방향이 유저 추구와 맞습니다. 다만 1장이 무드 변수입니다."
            ),
        },
        "full_content": {
            "verdict": "분석 결과입니다. 쿨뮤트 톤이 일관되게 유지되었습니다.",
            "photo_insights": [
                {"photo_index": 0, "insight": "톤 일치", "improvement": "측광 권장"},
                {"photo_index": 1, "insight": "채도 유지", "improvement": "지속"},
                {"photo_index": 2, "insight": "구도 안정", "improvement": "약간 낮게"},
            ],
            "recommendation": {
                "style_direction": "쿨뮤트 유지",
                "next_action": "측광 시도",
                "why": "일치 강화를 위한 선택",
            },
            "numbers": {
                "photo_count": 3,
                "dominant_tone": "쿨뮤트",
                "dominant_tone_pct": 68,
                "alignment_with_profile": "일치",
            },
        },
    })


class _FakeUser:
    """get_current_user 반환 dict 대체."""

    @staticmethod
    def dep() -> dict:
        return {
            "id": "u1",
            "kakao_id": "k1",
            "email": "",
            "name": "정세현",
            "gender": "female",
            "tier": "standard",
        }


class _FakeDB:
    """Minimal Session mock — execute + commit + rollback."""

    def __init__(self):
        self.executes: list[tuple[str, dict]] = []
        self.committed = 0
        self.rolled_back = 0
        self._responses: dict[str, Any] = {}

    def execute(self, stmt, params: Optional[dict] = None):
        sql = str(stmt)
        self.executes.append((sql, params or {}))
        # Lookup queued response by SQL substring match
        for key, resp in self._responses.items():
            if key in sql:
                return resp
        # Default: empty result
        result = MagicMock()
        result.first.return_value = None
        result.rowcount = 0
        return result

    def commit(self):
        self.committed += 1

    def rollback(self):
        self.rolled_back += 1

    def queue_result(self, sql_substring: str, value):
        self._responses[sql_substring] = value


def _make_result_row(**kwargs):
    result = MagicMock()
    row = MagicMock()
    for k, v in kwargs.items():
        setattr(row, k, v)
    result.first.return_value = row
    return result


def _make_scalar_result(value):
    result = MagicMock()
    result.scalar.return_value = value
    return result


# ─────────────────────────────────────────────
#  App fixture — isolated FastAPI with only verdict_v2 router
# ─────────────────────────────────────────────

@pytest.fixture
def client():
    """Fresh FastAPI app with verdict_v2 router + mocked deps."""
    from routes.verdict_v2 import router
    import deps

    app = FastAPI()
    app.include_router(router)

    # Fake db + user dependency overrides
    fake_db = _FakeDB()
    app.dependency_overrides[deps.db_session] = lambda: fake_db
    app.dependency_overrides[deps.get_current_user] = _FakeUser.dep

    with TestClient(app) as c:
        yield c, fake_db


# ─────────────────────────────────────────────
#  POST /create — happy path
# ─────────────────────────────────────────────

def test_create_verdict_happy_3_photos(client, monkeypatch):
    c, fake_db = client
    # Mock profile + engine
    monkeypatch.setattr(
        "routes.verdict_v2.get_profile",
        lambda db, uid: _fake_profile(),
    )
    # NOTE: bound name — routes/verdict_v2.py 의 top-level import 가 local rebind.
    # services.verdict_v2 module attr 이 아니라 routes.verdict_v2 attr 을 patch.
    monkeypatch.setattr(
        "routes.verdict_v2.build_verdict_v2",
        lambda **kw: _fake_verdict_result(),
    )

    files = [
        ("photos", (f"p{i}.png", io.BytesIO(MIN_PNG_BYTES), "image/png"))
        for i in range(3)
    ]
    r = c.post("/api/v2/verdict/create", files=files)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["version"] == "v2"
    assert body["full_unlocked"] is False
    assert body["photo_count"] == 3
    assert body["preview"]["hook_line"] == "추구미와 피드 방향이 일치합니다"
    # DB INSERT + commit 호출 확인
    insert_calls = [e for e in fake_db.executes if "INSERT INTO verdicts" in e[0]]
    assert len(insert_calls) == 1
    params = insert_calls[0][1]
    assert params["cc"] == 3
    # version 은 SQL 에 'v2' 하드코딩
    assert "'v2'" in insert_calls[0][0]
    assert fake_db.committed == 1


def test_create_verdict_happy_10_photos(client, monkeypatch):
    c, fake_db = client
    monkeypatch.setattr("routes.verdict_v2.get_profile", lambda db, uid: _fake_profile())
    monkeypatch.setattr("routes.verdict_v2.build_verdict_v2", lambda **kw: _fake_verdict_result())
    files = [
        ("photos", (f"p{i}.jpg", io.BytesIO(MIN_PNG_BYTES), "image/jpeg"))
        for i in range(10)
    ]
    r = c.post("/api/v2/verdict/create", files=files)
    assert r.status_code == 200
    assert r.json()["photo_count"] == 10


# ─────────────────────────────────────────────
#  POST /create — input validation
# ─────────────────────────────────────────────

def test_create_rejects_too_few_photos(client, monkeypatch):
    c, _ = client
    monkeypatch.setattr("routes.verdict_v2.get_profile", lambda db, uid: _fake_profile())
    files = [
        ("photos", (f"p{i}.png", io.BytesIO(MIN_PNG_BYTES), "image/png"))
        for i in range(2)
    ]
    r = c.post("/api/v2/verdict/create", files=files)
    assert r.status_code == 400
    assert "최소 3장" in r.json()["detail"]


def test_create_rejects_too_many_photos(client, monkeypatch):
    c, _ = client
    monkeypatch.setattr("routes.verdict_v2.get_profile", lambda db, uid: _fake_profile())
    files = [
        ("photos", (f"p{i}.png", io.BytesIO(MIN_PNG_BYTES), "image/png"))
        for i in range(11)
    ]
    r = c.post("/api/v2/verdict/create", files=files)
    assert r.status_code == 400
    assert "최대 10장" in r.json()["detail"]


def test_create_rejects_unsupported_content_type(client, monkeypatch):
    c, _ = client
    monkeypatch.setattr("routes.verdict_v2.get_profile", lambda db, uid: _fake_profile())
    files = [
        ("photos", (f"p{i}.gif", io.BytesIO(MIN_PNG_BYTES), "image/gif"))
        for i in range(3)
    ]
    r = c.post("/api/v2/verdict/create", files=files)
    assert r.status_code == 400
    assert "지원하지 않는" in r.json()["detail"]


def test_create_rejects_empty_photo(client, monkeypatch):
    c, _ = client
    monkeypatch.setattr("routes.verdict_v2.get_profile", lambda db, uid: _fake_profile())
    files = [
        ("photos", (f"p{i}.png", io.BytesIO(b""), "image/png"))
        for i in range(3)
    ]
    r = c.post("/api/v2/verdict/create", files=files)
    assert r.status_code == 400
    assert "비어있음" in r.json()["detail"]


def test_create_without_profile_returns_409(client, monkeypatch):
    c, _ = client
    monkeypatch.setattr("routes.verdict_v2.get_profile", lambda db, uid: None)
    files = [
        ("photos", (f"p{i}.png", io.BytesIO(MIN_PNG_BYTES), "image/png"))
        for i in range(3)
    ]
    r = c.post("/api/v2/verdict/create", files=files)
    assert r.status_code == 409
    assert "Onboarding" in r.json()["detail"]


def test_create_sonnet_failure_returns_500(client, monkeypatch):
    c, _ = client
    monkeypatch.setattr("routes.verdict_v2.get_profile", lambda db, uid: _fake_profile())

    def _boom(**kwargs):
        raise v2_engine.VerdictV2Error("Hard Rules 위반")
    monkeypatch.setattr("routes.verdict_v2.build_verdict_v2", _boom)

    files = [
        ("photos", (f"p{i}.png", io.BytesIO(MIN_PNG_BYTES), "image/png"))
        for i in range(3)
    ]
    r = c.post("/api/v2/verdict/create", files=files)
    assert r.status_code == 500


# ─────────────────────────────────────────────
#  POST /unlock — atomic transaction
# ─────────────────────────────────────────────

def test_unlock_happy_path(client, monkeypatch):
    c, fake_db = client
    # SELECT verdict 응답 — v2, owner 일치, unlocked=False, full_content 있음
    fake_db.queue_result(
        "SELECT id, user_id, version, full_unlocked",
        _make_result_row(
            id="vrd_xyz",
            user_id="u1",
            version="v2",
            full_unlocked=False,
            preview_content=_fake_verdict_result().preview.model_dump(mode="json"),
            full_content=_fake_verdict_result().full_content.model_dump(mode="json"),
        ),
    )
    # tokens balance
    monkeypatch.setattr(tokens_service, "get_balance", lambda db, uid: 50)

    # credit_tokens mock — 차감 후 40 반환
    monkeypatch.setattr(
        tokens_service, "credit_tokens",
        lambda db, **kw: 40,
    )

    r = c.post("/api/v2/verdict/vrd_xyz/unlock")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["full_unlocked"] is True
    assert body["balance"] == 40
    assert body["full_content"]["verdict"].startswith("분석 결과입니다")


def test_unlock_insufficient_tokens_returns_402(client, monkeypatch):
    c, fake_db = client
    fake_db.queue_result(
        "SELECT id, user_id, version, full_unlocked",
        _make_result_row(
            id="vrd_xyz",
            user_id="u1",
            version="v2",
            full_unlocked=False,
            preview_content=_fake_verdict_result().preview.model_dump(mode="json"),
            full_content=_fake_verdict_result().full_content.model_dump(mode="json"),
        ),
    )
    monkeypatch.setattr(tokens_service, "get_balance", lambda db, uid: 5)

    r = c.post("/api/v2/verdict/vrd_xyz/unlock")
    assert r.status_code == 402
    assert "토큰 부족" in r.json()["detail"]


def test_unlock_already_unlocked_is_idempotent(client, monkeypatch):
    c, fake_db = client
    fake_db.queue_result(
        "SELECT id, user_id, version, full_unlocked",
        _make_result_row(
            id="vrd_xyz",
            user_id="u1",
            version="v2",
            full_unlocked=True,   # 이미 해제됨
            preview_content=_fake_verdict_result().preview.model_dump(mode="json"),
            full_content=_fake_verdict_result().full_content.model_dump(mode="json"),
        ),
    )
    monkeypatch.setattr(tokens_service, "get_balance", lambda db, uid: 30)

    r = c.post("/api/v2/verdict/vrd_xyz/unlock")
    assert r.status_code == 200
    body = r.json()
    assert body["full_unlocked"] is True
    assert body["balance"] == 30


def test_unlock_not_owner_returns_403(client, monkeypatch):
    c, fake_db = client
    fake_db.queue_result(
        "SELECT id, user_id, version, full_unlocked",
        _make_result_row(
            id="vrd_xyz",
            user_id="someone_else",
            version="v2",
            full_unlocked=False,
            preview_content={},
            full_content={},
        ),
    )
    r = c.post("/api/v2/verdict/vrd_xyz/unlock")
    assert r.status_code == 403


def test_unlock_v1_verdict_returns_409(client, monkeypatch):
    c, fake_db = client
    fake_db.queue_result(
        "SELECT id, user_id, version, full_unlocked",
        _make_result_row(
            id="vrd_xyz",
            user_id="u1",
            version="v1",   # v1 verdict 은 거절
            full_unlocked=False,
            preview_content={},
            full_content={},
        ),
    )
    r = c.post("/api/v2/verdict/vrd_xyz/unlock")
    assert r.status_code == 409
    assert "v1" in r.json()["detail"]


def test_unlock_not_found_returns_404(client, monkeypatch):
    c, fake_db = client
    # 기본 queue empty → first() None
    r = c.post("/api/v2/verdict/vrd_ghost/unlock")
    assert r.status_code == 404


# ─────────────────────────────────────────────
#  GET /{verdict_id}
# ─────────────────────────────────────────────

def test_get_verdict_preview_only_when_locked(client, monkeypatch):
    c, fake_db = client
    preview = _fake_verdict_result().preview.model_dump(mode="json")
    full = _fake_verdict_result().full_content.model_dump(mode="json")
    fake_db.queue_result(
        "SELECT id, user_id, version, full_unlocked",
        _make_result_row(
            id="vrd_xyz",
            user_id="u1",
            version="v2",
            full_unlocked=False,
            preview_content=preview,
            full_content=full,
        ),
    )
    r = c.get("/api/v2/verdict/vrd_xyz")
    assert r.status_code == 200
    body = r.json()
    assert body["full_unlocked"] is False
    assert body["preview"]["hook_line"] == preview["hook_line"]
    assert body["full_content"] is None


def test_get_verdict_returns_full_when_unlocked(client, monkeypatch):
    c, fake_db = client
    preview = _fake_verdict_result().preview.model_dump(mode="json")
    full = _fake_verdict_result().full_content.model_dump(mode="json")
    fake_db.queue_result(
        "SELECT id, user_id, version, full_unlocked",
        _make_result_row(
            id="vrd_xyz",
            user_id="u1",
            version="v2",
            full_unlocked=True,
            preview_content=preview,
            full_content=full,
        ),
    )
    r = c.get("/api/v2/verdict/vrd_xyz")
    assert r.status_code == 200
    body = r.json()
    assert body["full_unlocked"] is True
    assert body["full_content"]["verdict"].startswith("분석 결과")


def test_get_verdict_not_owner_403(client, monkeypatch):
    c, fake_db = client
    fake_db.queue_result(
        "SELECT id, user_id, version, full_unlocked",
        _make_result_row(
            id="vrd_xyz",
            user_id="other",
            version="v2",
            full_unlocked=False,
            preview_content=_fake_verdict_result().preview.model_dump(mode="json"),
            full_content={},
        ),
    )
    r = c.get("/api/v2/verdict/vrd_xyz")
    assert r.status_code == 403


def test_get_verdict_not_found_404(client):
    c, _ = client
    r = c.get("/api/v2/verdict/vrd_ghost")
    assert r.status_code == 404


# ─────────────────────────────────────────────
#  WTP 가설 — best_fit_photo_url mapping (helper unit tests)
# ─────────────────────────────────────────────


def test_best_fit_url_helper_returns_url_at_index():
    """photo_urls[best_fit_index] 정상 매핑."""
    from routes.verdict_v2 import _best_fit_url
    urls = ["https://x.com/0.jpg", "https://x.com/1.jpg", "https://x.com/2.jpg"]
    assert _best_fit_url(urls, 1) == "https://x.com/1.jpg"
    assert _best_fit_url(urls, 0) == "https://x.com/0.jpg"


def test_best_fit_url_helper_none_index():
    """best_fit_index None → None."""
    from routes.verdict_v2 import _best_fit_url
    urls = ["https://x.com/0.jpg"]
    assert _best_fit_url(urls, None) is None


def test_best_fit_url_helper_out_of_range():
    """인덱스 범위 밖 → None (안전)."""
    from routes.verdict_v2 import _best_fit_url
    urls = ["https://x.com/0.jpg"]
    assert _best_fit_url(urls, 5) is None
    assert _best_fit_url(urls, -1) is None


def test_best_fit_url_helper_url_is_none():
    """photo_urls[idx] 자체가 None (R2 실패) → None."""
    from routes.verdict_v2 import _best_fit_url
    urls = ["https://x.com/0.jpg", None, "https://x.com/2.jpg"]
    assert _best_fit_url(urls, 1) is None


def test_resolve_best_fit_index_full_priority():
    """full.best_fit_photo_index 가 source of truth (preview 와 다르면 full 채택)."""
    from routes.verdict_v2 import _resolve_best_fit_index
    from schemas.verdict_v2 import FullContent, PreviewContent, Recommendation
    pv = PreviewContent(
        hook_line="훅", reason_summary="근거", best_fit_photo_index=0,
    )
    fc = FullContent(
        verdict="x",
        photo_insights=[],
        recommendation=Recommendation(style_direction="x", next_action="y", why="z"),
        best_fit_photo_index=2,
    )
    assert _resolve_best_fit_index(pv, fc) == 2


def test_resolve_best_fit_index_preview_fallback():
    """full 없으면 preview 사용."""
    from routes.verdict_v2 import _resolve_best_fit_index
    from schemas.verdict_v2 import PreviewContent
    pv = PreviewContent(
        hook_line="훅", reason_summary="근거", best_fit_photo_index=1,
    )
    assert _resolve_best_fit_index(pv, None) == 1


def test_resolve_best_fit_index_none_when_both_missing():
    """둘 다 부재 → None."""
    from routes.verdict_v2 import _resolve_best_fit_index
    from schemas.verdict_v2 import PreviewContent
    pv = PreviewContent(hook_line="훅", reason_summary="근거")
    assert _resolve_best_fit_index(pv, None) is None
    assert _resolve_best_fit_index(None, None) is None


# ─────────────────────────────────────────────
#  WTP 가설 — best_fit_photo_url in HTTP responses
# ─────────────────────────────────────────────


def _fake_verdict_result_with_best_fit(idx: int = 1) -> VerdictV2Result:
    """best_fit_photo_index 명시 포함 verdict result."""
    return VerdictV2Result.model_validate({
        "preview": {
            "hook_line": "추구미와 일치합니다",
            "reason_summary": "쿨뮤트 톤이 유지됩니다.",
            "best_fit_photo_index": idx,
            "best_fit_insight": f"{idx+1}번 사진이 가장 부합합니다.",
            "best_fit_improvement": f"{idx+1}번은 측광 활용 시 자연스럽습니다.",
        },
        "full_content": {
            "verdict": "분석 결과입니다.",
            "photo_insights": [
                {
                    "photo_index": i,
                    "insight": f"{i+1}번 insight",
                    "improvement": f"{i+1}번 improvement",
                }
                for i in range(3)
            ],
            "recommendation": {
                "style_direction": "유지",
                "next_action": "측광 시도",
                "why": "일치 강화",
            },
            "numbers": {"photo_count": 3},
            "best_fit_photo_index": idx,
        },
    })


def test_unlock_response_includes_best_fit_photo_url(client, monkeypatch):
    """unlock 응답에 best_fit_photo_url 포함."""
    c, fake_db = client
    full = _fake_verdict_result_with_best_fit(1)
    fake_db.queue_result(
        "SELECT id, user_id, version, full_unlocked",
        _make_result_row(
            id="vrd_xyz",
            user_id="u1",
            version="v2",
            full_unlocked=True,
            preview_content=full.preview.model_dump(mode="json"),
            full_content=full.full_content.model_dump(mode="json"),
            ranked_photo_ids=[
                {
                    "photo_index": 0,
                    "r2_key": "users/u1/verdicts/vrd_xyz/photo_0.jpg",
                    "content_type": "image/jpeg",
                },
                {
                    "photo_index": 1,
                    "r2_key": "users/u1/verdicts/vrd_xyz/photo_1.jpg",
                    "content_type": "image/jpeg",
                },
                {
                    "photo_index": 2,
                    "r2_key": "users/u1/verdicts/vrd_xyz/photo_2.jpg",
                    "content_type": "image/jpeg",
                },
            ],
        ),
    )
    monkeypatch.setattr(tokens_service, "get_balance", lambda db, uid: 30)
    monkeypatch.setattr(
        "routes.verdict_v2.r2_client.public_url",
        lambda key: f"https://r2.example.com/{key}",
    )

    r = c.post("/api/v2/verdict/vrd_xyz/unlock")
    assert r.status_code == 200, r.text
    body = r.json()
    # idempotent 경로 (이미 unlocked) — best_fit_photo_url 매핑 확인
    assert body["best_fit_photo_url"] == (
        "https://r2.example.com/users/u1/verdicts/vrd_xyz/photo_1.jpg"
    )


def test_get_response_includes_best_fit_photo_url_on_unlocked(client, monkeypatch):
    """GET 응답 (unlocked) 에 best_fit_photo_url 포함."""
    c, fake_db = client
    full = _fake_verdict_result_with_best_fit(2)
    fake_db.queue_result(
        "SELECT id, user_id, version, full_unlocked",
        _make_result_row(
            id="vrd_xyz",
            user_id="u1",
            version="v2",
            full_unlocked=True,
            preview_content=full.preview.model_dump(mode="json"),
            full_content=full.full_content.model_dump(mode="json"),
            ranked_photo_ids=[
                {
                    "photo_index": i,
                    "r2_key": f"users/u1/verdicts/vrd_xyz/photo_{i}.jpg",
                    "content_type": "image/jpeg",
                }
                for i in range(3)
            ],
        ),
    )
    monkeypatch.setattr(
        "routes.verdict_v2.r2_client.public_url",
        lambda key: f"https://r2.example.com/{key}",
    )

    r = c.get("/api/v2/verdict/vrd_xyz")
    assert r.status_code == 200
    body = r.json()
    assert body["best_fit_photo_url"] == (
        "https://r2.example.com/users/u1/verdicts/vrd_xyz/photo_2.jpg"
    )


def test_get_response_best_fit_url_none_when_no_index(client, monkeypatch):
    """preview / full 둘 다 best_fit_photo_index 없으면 best_fit_photo_url None."""
    c, fake_db = client
    legacy = _fake_verdict_result()  # 기존 fixture, best_fit 미포함
    fake_db.queue_result(
        "SELECT id, user_id, version, full_unlocked",
        _make_result_row(
            id="vrd_xyz",
            user_id="u1",
            version="v2",
            full_unlocked=True,
            preview_content=legacy.preview.model_dump(mode="json"),
            full_content=legacy.full_content.model_dump(mode="json"),
            ranked_photo_ids=[
                {
                    "photo_index": i,
                    "r2_key": f"users/u1/verdicts/vrd_xyz/photo_{i}.jpg",
                    "content_type": "image/jpeg",
                }
                for i in range(3)
            ],
        ),
    )
    monkeypatch.setattr(
        "routes.verdict_v2.r2_client.public_url",
        lambda key: f"https://r2.example.com/{key}",
    )

    r = c.get("/api/v2/verdict/vrd_xyz")
    assert r.status_code == 200
    body = r.json()
    assert body["best_fit_photo_url"] is None


def test_get_response_legacy_preview_no_best_fit_field(client, monkeypatch):
    """기존 v2 row (preview 에 best_fit_* 컬럼 자체 없음) backward compat."""
    c, fake_db = client
    # 의도적으로 best_fit_* 필드 누락한 레거시 preview / full
    legacy_preview = {
        "hook_line": "기존 훅",
        "reason_summary": "기존 근거",
    }
    legacy_full = {
        "verdict": "기존 분석.",
        "photo_insights": [
            {"photo_index": 0, "insight": "x", "improvement": "y"},
        ],
        "recommendation": {
            "style_direction": "방향", "next_action": "행동", "why": "이유",
        },
        "numbers": {},
    }
    fake_db.queue_result(
        "SELECT id, user_id, version, full_unlocked",
        _make_result_row(
            id="vrd_xyz",
            user_id="u1",
            version="v2",
            full_unlocked=True,
            preview_content=legacy_preview,
            full_content=legacy_full,
            ranked_photo_ids=[
                {
                    "photo_index": 0,
                    "r2_key": "users/u1/verdicts/vrd_xyz/photo_0.jpg",
                    "content_type": "image/jpeg",
                },
            ],
        ),
    )
    monkeypatch.setattr(
        "routes.verdict_v2.r2_client.public_url",
        lambda key: f"https://r2.example.com/{key}",
    )

    r = c.get("/api/v2/verdict/vrd_xyz")
    assert r.status_code == 200
    body = r.json()
    # 기존 동작 100% 보존: best_fit_photo_url None, preview/full 정상
    assert body["best_fit_photo_url"] is None
    assert body["preview"]["hook_line"] == "기존 훅"
    assert body["full_content"]["verdict"] == "기존 분석."
