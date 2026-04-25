"""Pinterest 어댑터 (_call_pinterest_actor) 단위 테스트 — v1.5.

검증:
  1. is_product_pin / 비디오 핀 / 이미지 없는 핀 필터링
  2. size_keys fallback 우선순위 (orig → 736x → 474x → 236x)
  3. raw_items 전수 보존 (필터 후)
  4. board_name lazy capture
  5. 반환 tuple 구조 (urls, board_meta)
  6. DEBUG_PINTEREST_RAW_DUMP=1 환경변수 시 픽스처 dump

Apify 실 응답은 본인 (창업자) E2E 시 DEBUG dump 로 캡처. 본 테스트는 픽스처 기반.
"""
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from services.aspiration_engine_pinterest import _call_pinterest_actor


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "pinterest_response_sample.json"


@pytest.fixture
def fixture_data():
    """Pinterest scraper 응답 픽스처 — 5개 핀 (1 유효, 1 product, 1 video, 1 no-image, 1 fallback)."""
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def mock_httpx_response(fixture_data):
    """httpx.Client.post 가 픽스처 응답을 반환하도록 mock."""
    def _mock_post(*args, **kwargs):
        resp = MagicMock()
        resp.json.return_value = fixture_data
        resp.raise_for_status.return_value = None
        return resp
    return _mock_post


class TestCallPinterestActorReturn:
    """반환 tuple 구조 + 메타 검증."""

    def test_returns_tuple_of_urls_and_meta(self, mock_httpx_response):
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post = mock_httpx_response
            result = _call_pinterest_actor(
                board_url="https://www.pinterest.com/u/b/",
                api_key="test",
                actor_id="devcake~pinterest-data-scraper",
                timeout=30.0,
            )
        assert isinstance(result, tuple)
        assert len(result) == 2
        urls, meta = result
        assert isinstance(urls, list)
        assert isinstance(meta, dict)

    def test_meta_contains_required_keys(self, mock_httpx_response):
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post = mock_httpx_response
            _, meta = _call_pinterest_actor(
                board_url="https://www.pinterest.com/u/b/",
                api_key="test",
                actor_id="devcake~pinterest-data-scraper",
                timeout=30.0,
            )
        assert "board_name" in meta
        assert "raw_items" in meta
        assert "total_pins_raw" in meta
        assert "pins_after_filter" in meta


class TestCallPinterestActorFiltering:
    """is_product_pin / 비디오 / 이미지 없음 필터링 검증."""

    def test_filters_product_pin(self, mock_httpx_response):
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post = mock_httpx_response
            urls, meta = _call_pinterest_actor(
                board_url="https://www.pinterest.com/u/b/",
                api_key="test",
                actor_id="devcake~pinterest-data-scraper",
                timeout=30.0,
            )
        # placeholder_pin_002 (is_product_pin=True) 는 raw_items 에서 제외
        for item in meta["raw_items"]:
            assert item.get("is_product_pin") is not True

    def test_filters_video_pin(self, mock_httpx_response):
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post = mock_httpx_response
            urls, meta = _call_pinterest_actor(
                board_url="https://www.pinterest.com/u/b/",
                api_key="test",
                actor_id="devcake~pinterest-data-scraper",
                timeout=30.0,
            )
        # placeholder_pin_003 (videos 필드 있음) 제외
        for item in meta["raw_items"]:
            assert not item.get("videos")

    def test_filters_no_image_pin(self, mock_httpx_response):
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post = mock_httpx_response
            urls, meta = _call_pinterest_actor(
                board_url="https://www.pinterest.com/u/b/",
                api_key="test",
                actor_id="devcake~pinterest-data-scraper",
                timeout=30.0,
            )
        # placeholder_pin_004 (images=None) 제외 — urls 길이 = 유효 핀 수
        # 5개 핀 - 1 product - 1 video - 1 no-image = 2개 유효
        assert len(urls) == 2
        assert meta["pins_after_filter"] == 2
        assert meta["total_pins_raw"] == 5


class TestCallPinterestActorSizeKeysFallback:
    """size_keys 우선순위 fallback 검증."""

    def test_prefers_orig_when_available(self, mock_httpx_response):
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post = mock_httpx_response
            urls, meta = _call_pinterest_actor(
                board_url="https://www.pinterest.com/u/b/",
                api_key="test",
                actor_id="devcake~pinterest-data-scraper",
                timeout=30.0,
            )
        # placeholder_pin_001 = orig 있음 → orig URL 사용
        assert "originals/placeholder_001" in urls[0]

    def test_falls_back_to_474x_when_orig_736x_missing(self, mock_httpx_response):
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post = mock_httpx_response
            urls, _ = _call_pinterest_actor(
                board_url="https://www.pinterest.com/u/b/",
                api_key="test",
                actor_id="devcake~pinterest-data-scraper",
                timeout=30.0,
            )
        # placeholder_pin_005 = 474x 부터 있음 → 474x URL 사용
        assert "474x/placeholder_005" in urls[1]


class TestCallPinterestActorBoardName:
    """board_name lazy capture 검증."""

    def test_captures_board_name_from_first_valid_pin(self, mock_httpx_response):
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post = mock_httpx_response
            _, meta = _call_pinterest_actor(
                board_url="https://www.pinterest.com/u/b/",
                api_key="test",
                actor_id="devcake~pinterest-data-scraper",
                timeout=30.0,
            )
        assert meta["board_name"] == "Aesthetic Reference"


class TestCallPinterestActorRawPreservation:
    """raw_items 전수 보존 검증."""

    def test_raw_items_preserves_full_pin_dict(self, mock_httpx_response):
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post = mock_httpx_response
            _, meta = _call_pinterest_actor(
                board_url="https://www.pinterest.com/u/b/",
                api_key="test",
                actor_id="devcake~pinterest-data-scraper",
                timeout=30.0,
            )
        # raw_items 의 첫 항목은 placeholder_pin_001 전체 dict
        first_pin = meta["raw_items"][0]
        assert first_pin["id"] == "placeholder_pin_001"
        # PII 필드도 보존 (R2 저장 후 caller 가 분리 격리)
        assert "pinner" in first_pin
        assert "description" in first_pin
        assert "saves" in first_pin


class TestCallPinterestActorDebugDump:
    """DEBUG_PINTEREST_RAW_DUMP=1 환경변수 시 픽스처 dump."""

    def test_debug_env_dumps_response(self, mock_httpx_response, tmp_path, monkeypatch):
        # tmp_path 로 작업 디렉터리 변경 (실 fixtures 경로 보호)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("DEBUG_PINTEREST_RAW_DUMP", "1")

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post = mock_httpx_response
            _call_pinterest_actor(
                board_url="https://www.pinterest.com/u/b/",
                api_key="test",
                actor_id="devcake~pinterest-data-scraper",
                timeout=30.0,
            )

        dumped = tmp_path / "tests" / "fixtures" / "pinterest_response_sample.json"
        assert dumped.exists()
        content = json.loads(dumped.read_text(encoding="utf-8"))
        assert isinstance(content, list)
        assert len(content) == 5  # 픽스처 핀 5개 그대로 dump

    def test_debug_env_off_no_dump(self, mock_httpx_response, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("DEBUG_PINTEREST_RAW_DUMP", raising=False)

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post = mock_httpx_response
            _call_pinterest_actor(
                board_url="https://www.pinterest.com/u/b/",
                api_key="test",
                actor_id="devcake~pinterest-data-scraper",
                timeout=30.0,
            )

        dumped = tmp_path / "tests" / "fixtures" / "pinterest_response_sample.json"
        assert not dumped.exists()
