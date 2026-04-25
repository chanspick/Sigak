"""v1.5 raw R2 보존 헬퍼 단위 테스트.

검증:
  - materialize_apify_raw_to_r2: Apify raw items 가 R2 apify_raw.json 저장
  - materialize_vision_raw_to_r2: Sonnet Vision raw text 가 R2 vision_raw.json 저장
  - materialize_ig_vision_raw_to_r2: 본인 IG Vision raw 가 R2 ig_snapshots/ 저장
  - 빈값 / None 입력 시 None 반환 (저장 X)
  - R2 put 실패 시 예외 흡수 + None 반환 (메인 플로우 무영향)
  - 키 패턴 일치 (aspiration_targets/{id}/ vs ig_snapshots/{ts}/)
"""
import json
from unittest.mock import patch, MagicMock

import pytest

from services.aspiration_common import (
    materialize_apify_raw_to_r2,
    materialize_vision_raw_to_r2,
    materialize_ig_vision_raw_to_r2,
)


class TestMaterializeApifyRawToR2:
    """Apify raw items 를 R2 apify_raw.json 으로 저장."""

    def test_returns_none_for_empty_items(self):
        result = materialize_apify_raw_to_r2(
            [], user_id="u1", analysis_id="asp_001",
        )
        assert result is None

    def test_uploads_json_payload(self):
        items = [{"id": "pin_1", "title": "test"}, {"id": "pin_2"}]
        with patch("services.r2_client.put_bytes") as mock_put, \
             patch("services.r2_client.public_url", return_value="https://cdn/key"):
            result = materialize_apify_raw_to_r2(
                items, user_id="u1", analysis_id="asp_001",
            )

        assert result == "https://cdn/key"
        mock_put.assert_called_once()
        call_args = mock_put.call_args
        # key 패턴 검증
        assert "aspiration_targets/asp_001/apify_raw.json" in call_args[0][0]
        # content_type=application/json
        assert call_args[1]["content_type"] == "application/json"
        # payload 내용 검증
        payload = json.loads(call_args[0][1].decode("utf-8"))
        assert payload["item_count"] == 2
        assert payload["items"][0]["id"] == "pin_1"

    def test_returns_none_on_r2_failure(self):
        with patch(
            "services.r2_client.put_bytes",
            side_effect=Exception("R2 down"),
        ):
            result = materialize_apify_raw_to_r2(
                [{"id": "pin_1"}], user_id="u1", analysis_id="asp_001",
            )
        assert result is None  # 실패해도 메인 플로우 무영향


class TestMaterializeVisionRawToR2:
    """Sonnet Vision raw text 를 R2 vision_raw.json 으로 저장 (추구미 영역)."""

    def test_returns_none_for_none_text(self):
        result = materialize_vision_raw_to_r2(
            None, user_id="u1", analysis_id="asp_001",
        )
        assert result is None

    def test_returns_none_for_empty_text(self):
        result = materialize_vision_raw_to_r2(
            "", user_id="u1", analysis_id="asp_001",
        )
        assert result is None

    def test_uploads_vision_raw_to_aspiration_dir(self):
        raw_text = '{"tone_category": "쿨뮤트", "tone_percentage": 60}'
        with patch("services.r2_client.put_bytes") as mock_put, \
             patch("services.r2_client.public_url", return_value="https://cdn/v"):
            result = materialize_vision_raw_to_r2(
                raw_text, user_id="u1", analysis_id="asp_001",
            )

        assert result == "https://cdn/v"
        call_args = mock_put.call_args
        # 키 = aspiration_targets/{analysis_id}/vision_raw.json
        assert "aspiration_targets/asp_001/vision_raw.json" in call_args[0][0]
        payload = json.loads(call_args[0][1].decode("utf-8"))
        assert payload["raw"] == raw_text
        assert payload["char_length"] == len(raw_text)


class TestMaterializeIgVisionRawToR2:
    """본인 IG Vision raw — ig_snapshots/{ts}/ 디렉터리 (추구미 영역과 분리)."""

    def test_returns_none_for_none_text(self):
        result = materialize_ig_vision_raw_to_r2(
            None, user_id="u1", snapshot_ts="20260425T120000Z",
        )
        assert result is None

    def test_uploads_to_ig_snapshots_dir(self):
        raw_text = '{"tone_category": "웜뮤트"}'
        with patch("services.r2_client.put_bytes") as mock_put, \
             patch("services.r2_client.public_url", return_value="https://cdn/ig"):
            result = materialize_ig_vision_raw_to_r2(
                raw_text, user_id="u1", snapshot_ts="20260425T120000Z",
            )

        assert result == "https://cdn/ig"
        call_args = mock_put.call_args
        # 키 = ig_snapshots/{ts}/vision_raw.json (aspiration_targets 와 분리)
        assert "ig_snapshots/20260425T120000Z/vision_raw.json" in call_args[0][0]
        assert "aspiration_targets" not in call_args[0][0]


class TestR2KeyHelpers:
    """r2_client 헬퍼 키 패턴 검증."""

    def test_aspiration_apify_raw_key_pattern(self):
        from services.r2_client import aspiration_apify_raw_key
        key = aspiration_apify_raw_key("user_abc", "asp_xyz")
        assert key == "user_media/user_abc/aspiration_targets/asp_xyz/apify_raw.json"

    def test_aspiration_vision_raw_key_pattern(self):
        from services.r2_client import aspiration_vision_raw_key
        key = aspiration_vision_raw_key("user_abc", "asp_xyz")
        assert key == "user_media/user_abc/aspiration_targets/asp_xyz/vision_raw.json"

    def test_ig_snapshot_vision_raw_key_pattern(self):
        from services.r2_client import ig_snapshot_vision_raw_key
        key = ig_snapshot_vision_raw_key("user_abc", "20260425T120000Z")
        assert key == "user_media/user_abc/ig_snapshots/20260425T120000Z/vision_raw.json"


class TestSchemaFieldsAdded:
    """스키마 필드 추가 검증 (작업 4)."""

    def test_aspiration_analysis_has_r2_raw_keys(self):
        from schemas.aspiration import AspirationAnalysis
        # 모델 인스턴스 생성 (필수 필드만)
        from datetime import datetime, timezone
        from services.coordinate_system import VisualCoordinate, GapVector
        from schemas.aspiration import PhotoPair

        a = AspirationAnalysis(
            analysis_id="asp_test",
            user_id="u1",
            target_type="ig",
            target_identifier="test",
            created_at=datetime.now(timezone.utc),
            target_coordinate=VisualCoordinate(shape=0.5, volume=0.5, age=0.5),
            gap_vector=GapVector(
                primary_axis="shape", primary_delta=0.1,
                secondary_axis="volume", secondary_delta=0.0,
                tertiary_axis="age", tertiary_delta=0.0,
            ),
            gap_narrative="test",
            sia_overall_message="test",
        )
        # v1.5 신규 필드 확인 (기본값 None)
        assert hasattr(a, "r2_apify_raw_key")
        assert hasattr(a, "r2_vision_raw_key")
        assert hasattr(a, "matched_trends_snapshot")
        assert a.r2_apify_raw_key is None
        assert a.r2_vision_raw_key is None
        assert a.matched_trends_snapshot is None

    def test_ig_feed_cache_has_r2_vision_raw_key(self):
        from schemas.user_profile import IgFeedCache, IgFeedProfileBasics
        from datetime import datetime, timezone

        cache = IgFeedCache(
            scope="full",
            profile_basics=IgFeedProfileBasics(username="test"),
            fetched_at=datetime.now(timezone.utc),
        )
        assert hasattr(cache, "r2_vision_raw_key")
        assert cache.r2_vision_raw_key is None
