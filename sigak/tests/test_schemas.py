"""Pydantic schema validation tests (v2 Priority 1 D2).

Covers `sigak/schemas/user_profile.py`:
  - ConversationMessage
  - StructuredFields / StructuredFieldsConfidence
  - IgFeedProfileBasics / IgFeedCache
  - ExtractionResult

No DB, no network — pure model validation.
"""
import sys
import os
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pydantic import ValidationError

from schemas.user_profile import (
    ConversationMessage,
    ExtractionResult,
    IgFeedCache,
    IgFeedProfileBasics,
    StructuredFields,
    StructuredFieldsConfidence,
)


# ─────────────────────────────────────────────
#  ConversationMessage
# ─────────────────────────────────────────────

def test_conversation_message_basic():
    msg = ConversationMessage(
        role="user",
        content="hello",
        ts=datetime(2026, 4, 23, 10, 0, 0, tzinfo=timezone.utc),
    )
    assert msg.role == "user"
    assert msg.content == "hello"


def test_conversation_message_iso_string_coerced_to_datetime():
    msg = ConversationMessage.model_validate(
        {"role": "assistant", "content": "안녕하세요", "ts": "2026-04-23T10:00:00+00:00"}
    )
    assert isinstance(msg.ts, datetime)


def test_conversation_message_rejects_unknown_role():
    with pytest.raises(ValidationError):
        ConversationMessage(role="system", content="x", ts=datetime.now(timezone.utc))


# ─────────────────────────────────────────────
#  StructuredFields
# ─────────────────────────────────────────────

def test_structured_fields_all_nullable():
    sf = StructuredFields()
    assert sf.desired_image is None
    assert sf.height is None


def test_structured_fields_height_enum_valid():
    sf = StructuredFields(height="165_170")
    assert sf.height == "165_170"


def test_structured_fields_height_enum_invalid():
    with pytest.raises(ValidationError):
        StructuredFields(height="165cm")


def test_structured_fields_shoulder_width_enum():
    sf = StructuredFields(shoulder_width="medium")
    assert sf.shoulder_width == "medium"
    with pytest.raises(ValidationError):
        StructuredFields(shoulder_width="보통")


def test_structured_fields_as_merge_dict_excludes_none():
    sf = StructuredFields(desired_image="정돈된 뮤트", height="165_170")
    merge = sf.as_merge_dict()
    assert merge == {"desired_image": "정돈된 뮤트", "height": "165_170"}
    assert "reference_style" not in merge   # None 이므로 제외


def test_structured_fields_confidence_range():
    conf = StructuredFieldsConfidence(desired_image=0.8, height=0.5)
    assert conf.desired_image == 0.8
    with pytest.raises(ValidationError):
        StructuredFieldsConfidence(desired_image=1.5)
    with pytest.raises(ValidationError):
        StructuredFieldsConfidence(height=-0.1)


def test_structured_fields_extra_fields_ignored():
    """forward-compat — 알 수 없는 키 무시."""
    sf = StructuredFields.model_validate(
        {"desired_image": "x", "new_field_added_later": "something"}
    )
    assert sf.desired_image == "x"


# ─────────────────────────────────────────────
#  IgFeedCache
# ─────────────────────────────────────────────

def _sample_profile_basics(**overrides):
    base = dict(username="yuni", follower_count=100)
    base.update(overrides)
    return IgFeedProfileBasics(**base)


def test_ig_feed_cache_public():
    cache = IgFeedCache(
        scope="full",
        profile_basics=_sample_profile_basics(),
        feed_highlights=["hello", "world"],
        fetched_at=datetime.now(timezone.utc),
    )
    assert cache.scope == "full"
    assert cache.feed_highlights == ["hello", "world"]


def test_ig_feed_cache_private_has_no_feed():
    cache = IgFeedCache(
        scope="public_profile_only",
        profile_basics=_sample_profile_basics(is_private=True),
        fetched_at=datetime.now(timezone.utc),
    )
    assert cache.scope == "public_profile_only"
    assert cache.feed_highlights is None
    assert cache.current_style_mood is None


def test_ig_feed_cache_invalid_scope():
    with pytest.raises(ValidationError):
        IgFeedCache(
            scope="partial",
            profile_basics=_sample_profile_basics(),
            fetched_at=datetime.now(timezone.utc),
        )


def test_ig_profile_basics_counts_non_negative():
    with pytest.raises(ValidationError):
        IgFeedProfileBasics(username="x", follower_count=-1)


# ─────────────────────────────────────────────
#  ExtractionResult
# ─────────────────────────────────────────────

def test_extraction_result_basic():
    result = ExtractionResult(
        fields=StructuredFields(desired_image="정돈된 뮤트"),
        fallback_needed=["height", "weight"],
    )
    assert result.fields.desired_image == "정돈된 뮤트"
    assert result.fallback_needed == ["height", "weight"]


def test_extraction_result_fallback_needed_default_empty():
    result = ExtractionResult(fields=StructuredFields())
    assert result.fallback_needed == []


def test_extraction_result_roundtrip_via_json_dict():
    """DB read path 시뮬레이션: JSON dict → model."""
    raw = {
        "fields": {
            "desired_image": "정돈된 뮤트",
            "height": "165_170",
            "confidence": {"desired_image": 0.9, "height": 0.6},
        },
        "fallback_needed": [],
    }
    result = ExtractionResult.model_validate(raw)
    assert result.fields.confidence is not None
    assert result.fields.confidence.desired_image == 0.9
