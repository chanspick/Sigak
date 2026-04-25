"""v1.5 LLM 격리 검증 — raw 키가 history_injector 출력에 절대 들어가지 않음.

핵심: raw_items / vision_raw / r2_apify_raw_key / r2_vision_raw_key 가
history_injector.build_history_context 의 마크다운 출력에 0건 포함되어야 함.

근거:
  - AspirationHistoryEntry (schemas/user_history.py) 에 r2_*_key 필드 미포함
  - history_injector._render_aspiration 은 entry.gap_narrative /
    sia_overall_message / target_handle 만 사용
  - 자동 격리 — 의도된 설계
"""
import pytest


class TestAspirationHistoryEntryNoRawKeys:
    """AspirationHistoryEntry 모델 자체에 raw 키 미포함."""

    def test_no_r2_apify_raw_key_field(self):
        from schemas.user_history import AspirationHistoryEntry
        fields = AspirationHistoryEntry.model_fields
        assert "r2_apify_raw_key" not in fields, (
            "AspirationHistoryEntry 에 r2_apify_raw_key 추가하면 LLM 격리 위반!"
        )

    def test_no_r2_vision_raw_key_field(self):
        from schemas.user_history import AspirationHistoryEntry
        fields = AspirationHistoryEntry.model_fields
        assert "r2_vision_raw_key" not in fields, (
            "AspirationHistoryEntry 에 r2_vision_raw_key 추가하면 LLM 격리 위반!"
        )

    def test_no_raw_items_field(self):
        from schemas.user_history import AspirationHistoryEntry
        fields = AspirationHistoryEntry.model_fields
        assert "raw_items" not in fields
        assert "raw_scraper_response" not in fields


class TestHistoryInjectorOutputNoRawKeys:
    """build_history_context 출력 마크다운에 raw 키 0건."""

    def test_aspiration_render_excludes_raw_keys(self):
        from services.history_injector import _render_aspiration

        # 가상 entry — raw_items 와 같은 키가 입력에 들어와도 무시되어야 함
        entry_with_raw = {
            "analysis_id": "asp_test",
            "target_handle": "@test",
            "source": "instagram",
            "gap_narrative": "test gap",
            "sia_overall_message": "test message",
            "target_analysis_snapshot": {"tone_category": "쿨뮤트"},
            # 다음 키들은 출력에 절대 들어가지 말 것 (미사용)
            "r2_apify_raw_key": "https://cdn/apify_raw.json",
            "r2_vision_raw_key": "https://cdn/vision_raw.json",
            "raw_items": [{"pinner": {"username": "third_party"}}],
        }
        rendered = _render_aspiration([entry_with_raw], mode="full")

        # 격리 검증 — raw 키 / 값 어디에도 노출 X
        assert "r2_apify_raw_key" not in rendered
        assert "r2_vision_raw_key" not in rendered
        assert "raw_items" not in rendered
        assert "apify_raw.json" not in rendered
        assert "vision_raw.json" not in rendered
        assert "third_party" not in rendered  # PII 미노출


class TestHistoryRenderUsesOnlyAllowedFields:
    """_render_aspiration 이 사용하는 필드 확인 (allowlist)."""

    def test_render_includes_target_and_gap(self):
        from services.history_injector import _render_aspiration

        entry = {
            "target_handle": "@yuni",
            "source": "instagram",
            "gap_narrative": "shape 축이 0.2 정도 샤프해지는 방향이에요",
            "sia_overall_message": "결이 잘 잡혀있어요",
        }
        rendered = _render_aspiration([entry], mode="full")

        # 허용된 필드는 출력에 포함
        assert "@yuni" in rendered or "yuni" in rendered
        assert "shape 축" in rendered or "gap" in rendered.lower()
