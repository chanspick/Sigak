"""Extraction engine tests (v2 Priority 1 D4).

Sonnet 4.6 응답은 mock 으로 대체 (실제 API 호출 없음).
실 API 검증은 probe_sonnet_extraction.py 로 D4 E2E 시점.

커버리지:
  - happy path (완전 대화 → 8 필드 모두 추출 성공)
  - 부분 추출 (일부 필드 confidence < 0.4 → null + fallback_needed)
  - parse 실패 → 재시도 → 최종 실패 (ExtractionError)
  - Sonnet API 오류 → 재시도 → 최종 실패
  - confidence 하한 enforce (Sonnet 이 confidence 0.2 주고 값 있으면 null 로 강등)
  - JSON fence 방어 (Sonnet 이 ```json...``` 래핑해도 parse 성공)
  - empty messages → 즉시 ExtractionError
"""
import json
import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import anthropic

from schemas.user_profile import ConversationMessage, ExtractionResult
from services import extraction
from services.extraction import ExtractionError


# ─────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_extraction_client():
    extraction.reset_client()
    yield
    extraction.reset_client()


def _ts() -> datetime:
    return datetime(2026, 4, 25, 10, 0, 0, tzinfo=timezone.utc)


def _messages_full_turn() -> list[ConversationMessage]:
    """완전 대화 샘플 (extraction 성공 시나리오 입력)."""
    return [
        ConversationMessage(role="user", content="(대화 시작)", ts=_ts()),
        ConversationMessage(role="assistant", content="정세현님, Sia입니다. 피드 분석 완료...", ts=_ts()),
        ConversationMessage(role="user", content="1번이요 (편안함)", ts=_ts()),
        ConversationMessage(role="user", content="키 165, 몸무게 50 초반, 어깨 보통", ts=_ts()),
        ConversationMessage(role="user", content="프리랜서 기획자예요", ts=_ts()),
        ConversationMessage(role="user", content="이만하면 됐어요", ts=_ts()),
    ]


def _messages_short() -> list[ConversationMessage]:
    """짧은 대화 (부분 추출 시나리오)."""
    return [
        ConversationMessage(role="user", content="(대화 시작)", ts=_ts()),
        ConversationMessage(role="assistant", content="Sia입니다.", ts=_ts()),
        ConversationMessage(role="user", content="이만하면 됐어요", ts=_ts()),
    ]


SONNET_RESPONSE_HAPPY = json.dumps({
    "fields": {
        "desired_image": "편안하고 친밀한 인상 추구",
        "reference_style": None,
        "current_concerns": ["피드 분위기와 추구 방향 갭"],
        "self_perception": "정돈된 인상이라는 평을 받음",
        "lifestyle_context": "프리랜서 기획자, 주말 캐주얼 활동",
        "height": "160_165",
        "weight": "50_55",
        "shoulder_width": "medium",
        "confidence": {
            "desired_image": 0.85,
            "reference_style": 0.0,
            "current_concerns": 0.75,
            "self_perception": 0.70,
            "lifestyle_context": 0.80,
            "height": 0.95,
            "weight": 0.85,
            "shoulder_width": 0.75,
        },
    },
    "fallback_needed": ["reference_style"],
})

SONNET_RESPONSE_PARTIAL = json.dumps({
    "fields": {
        "desired_image": "편안함",
        "reference_style": None,
        "current_concerns": None,
        "self_perception": None,
        "lifestyle_context": None,
        "height": None,
        "weight": None,
        "shoulder_width": None,
        "confidence": {
            "desired_image": 0.50,
            "reference_style": 0.0,
            "current_concerns": 0.20,
            "self_perception": 0.25,
            "lifestyle_context": 0.15,
            "height": 0.0,
            "weight": 0.0,
            "shoulder_width": 0.0,
        },
    },
    "fallback_needed": [
        "reference_style", "current_concerns", "self_perception",
        "lifestyle_context", "height", "weight", "shoulder_width",
    ],
})

# confidence < 0.4 인데 값 있는 케이스 — _enforce_confidence_nulls 가 null 로 강등해야
SONNET_RESPONSE_LOW_CONF_WITH_VALUE = json.dumps({
    "fields": {
        "desired_image": "편안함",
        "reference_style": "카리나",   # 실제 언급 없으면 Sonnet 실수로 환각한 값
        "current_concerns": None,
        "self_perception": None,
        "lifestyle_context": None,
        "height": None,
        "weight": None,
        "shoulder_width": None,
        "confidence": {
            "desired_image": 0.85,
            "reference_style": 0.20,   # 낮은 확신 = 환각 가능성
            "current_concerns": 0.0,
            "self_perception": 0.0,
            "lifestyle_context": 0.0,
            "height": 0.0,
            "weight": 0.0,
            "shoulder_width": 0.0,
        },
    },
    "fallback_needed": [],
})


# Sonnet 이 ```json ... ``` 래핑한 경우 (방어적 strip 검증)
SONNET_RESPONSE_FENCED = "```json\n" + SONNET_RESPONSE_HAPPY + "\n```"

# 잘못된 JSON
SONNET_RESPONSE_BAD_JSON = "{fields: this is not valid json"

# 스키마 위반 (height enum 이 아닌 값)
SONNET_RESPONSE_SCHEMA_INVALID = json.dumps({
    "fields": {
        "desired_image": "편안함",
        "reference_style": None,
        "current_concerns": None,
        "self_perception": None,
        "lifestyle_context": None,
        "height": "165cm",   # enum 위반
        "weight": None,
        "shoulder_width": None,
        "confidence": {
            "desired_image": 0.85,
            "reference_style": 0.0,
            "current_concerns": 0.0,
            "self_perception": 0.0,
            "lifestyle_context": 0.0,
            "height": 0.9,
            "weight": 0.0,
            "shoulder_width": 0.0,
        },
    },
    "fallback_needed": [],
})


# ─────────────────────────────────────────────
#  Helpers for mocking Sonnet
# ─────────────────────────────────────────────

def _make_mock_response(text: str) -> MagicMock:
    """anthropic Messages.create() 응답 shape 모사."""
    content_block = MagicMock()
    content_block.type = "text"
    content_block.text = text
    resp = MagicMock()
    resp.content = [content_block]
    return resp


def _install_mock_client(monkeypatch, response_sequence: list[str]):
    """_call_sonnet 내부가 사용하는 singleton client 를 교체.

    response_sequence: 여러 호출 시 순서대로 반환. 1개면 매번 동일 반환.
    """
    call_count = {"n": 0}

    def _fake_create(*args, **kwargs):
        idx = min(call_count["n"], len(response_sequence) - 1)
        call_count["n"] += 1
        text = response_sequence[idx]
        if isinstance(text, Exception):
            raise text
        return _make_mock_response(text)

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = _fake_create
    monkeypatch.setattr(extraction, "_get_client", lambda: mock_client)
    return mock_client


# ─────────────────────────────────────────────
#  Happy path
# ─────────────────────────────────────────────

def test_extract_happy_path(monkeypatch):
    _install_mock_client(monkeypatch, [SONNET_RESPONSE_HAPPY])
    result = extraction.extract_structured_fields(_messages_full_turn())
    assert isinstance(result, ExtractionResult)
    assert result.fields.desired_image == "편안하고 친밀한 인상 추구"
    assert result.fields.height == "160_165"
    assert result.fields.weight == "50_55"
    assert result.fields.shoulder_width == "medium"
    assert result.fallback_needed == ["reference_style"]
    assert result.fields.confidence.desired_image == 0.85


def test_extract_partial_low_confidence(monkeypatch):
    """confidence <0.4 필드 전부 null + fallback_needed 에 포함."""
    _install_mock_client(monkeypatch, [SONNET_RESPONSE_PARTIAL])
    result = extraction.extract_structured_fields(_messages_short())
    # desired_image 0.50 → 유지
    assert result.fields.desired_image == "편안함"
    # 나머지 confidence < 0.4 → 이미 null
    assert result.fields.current_concerns is None
    assert result.fields.self_perception is None
    assert result.fields.lifestyle_context is None
    assert result.fields.height is None
    assert result.fields.weight is None
    # fallback_needed 에 7 필드 포함
    assert "current_concerns" in result.fallback_needed
    assert "height" in result.fallback_needed


def test_extract_low_confidence_value_demoted_to_null(monkeypatch):
    """Sonnet 이 confidence 0.2 인데 값 있게 준 경우 → null 로 강등."""
    _install_mock_client(monkeypatch, [SONNET_RESPONSE_LOW_CONF_WITH_VALUE])
    result = extraction.extract_structured_fields(_messages_full_turn())
    # reference_style: Sonnet 은 "카리나" 줬지만 conf 0.2 → null 로 demote
    assert result.fields.reference_style is None
    # fallback_needed 에 자동 추가
    assert "reference_style" in result.fallback_needed
    # desired_image: conf 0.85 → 유지
    assert result.fields.desired_image == "편안함"


# ─────────────────────────────────────────────
#  JSON fence defense
# ─────────────────────────────────────────────

def test_extract_strips_json_code_fence(monkeypatch):
    """Sonnet 이 ```json ... ``` 래핑해도 parse 성공."""
    _install_mock_client(monkeypatch, [SONNET_RESPONSE_FENCED])
    result = extraction.extract_structured_fields(_messages_full_turn())
    assert result.fields.desired_image == "편안하고 친밀한 인상 추구"


# ─────────────────────────────────────────────
#  Retry + failure paths
# ─────────────────────────────────────────────

def test_extract_retries_on_bad_json_then_succeeds(monkeypatch):
    """첫 시도 bad JSON → 재시도 → 두 번째에 성공."""
    _install_mock_client(monkeypatch, [SONNET_RESPONSE_BAD_JSON, SONNET_RESPONSE_HAPPY])
    result = extraction.extract_structured_fields(_messages_full_turn())
    assert result.fields.desired_image == "편안하고 친밀한 인상 추구"


def test_extract_fails_after_retries(monkeypatch):
    """max_retries=1 → 2회 모두 bad JSON → ExtractionError."""
    _install_mock_client(
        monkeypatch,
        [SONNET_RESPONSE_BAD_JSON, SONNET_RESPONSE_BAD_JSON],
    )
    with pytest.raises(ExtractionError):
        extraction.extract_structured_fields(_messages_full_turn(), max_retries=1)


def test_extract_schema_validation_failure_counts_as_retry(monkeypatch):
    """스키마 위반 응답 → 재시도 1회 후 성공."""
    _install_mock_client(
        monkeypatch,
        [SONNET_RESPONSE_SCHEMA_INVALID, SONNET_RESPONSE_HAPPY],
    )
    result = extraction.extract_structured_fields(_messages_full_turn())
    assert result.fields.desired_image == "편안하고 친밀한 인상 추구"


def test_extract_api_error_triggers_retry(monkeypatch):
    """anthropic.APIError → 재시도 1회 → 성공."""
    import httpx
    # Create a proper APIError instance (anthropic 0.39 uses this shape)
    mock_request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    api_err = anthropic.APIError(
        message="transient error", request=mock_request, body=None,
    )
    _install_mock_client(monkeypatch, [api_err, SONNET_RESPONSE_HAPPY])
    result = extraction.extract_structured_fields(_messages_full_turn())
    assert result.fields.desired_image == "편안하고 친밀한 인상 추구"


def test_extract_api_error_final_failure(monkeypatch):
    import httpx
    mock_request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    api_err = anthropic.APIError(
        message="persistent error", request=mock_request, body=None,
    )
    _install_mock_client(monkeypatch, [api_err, api_err])
    with pytest.raises(ExtractionError):
        extraction.extract_structured_fields(_messages_full_turn(), max_retries=1)


# ─────────────────────────────────────────────
#  Edge cases
# ─────────────────────────────────────────────

def test_empty_messages_raises_immediately():
    with pytest.raises(ExtractionError, match="empty messages"):
        extraction.extract_structured_fields([])


def test_empty_sonnet_response_raises_error(monkeypatch):
    """Sonnet 이 content=[] 반환 → ExtractionError."""
    mock_client = MagicMock()
    resp = MagicMock()
    resp.content = []
    mock_client.messages.create.return_value = resp
    monkeypatch.setattr(extraction, "_get_client", lambda: mock_client)
    with pytest.raises(ExtractionError, match="empty"):
        extraction.extract_structured_fields(
            _messages_full_turn(), max_retries=0,
        )


def test_extract_render_messages_format():
    """내부 helper — 메시지 로그가 prompt 용 텍스트로 변환되는지 확인."""
    msgs = [
        ConversationMessage(role="user", content="hello", ts=_ts()),
        ConversationMessage(role="assistant", content="Sia 응답", ts=_ts()),
    ]
    rendered = extraction._render_messages_for_prompt(msgs)
    assert "[턴 1 · 사용자]" in rendered
    assert "hello" in rendered
    assert "[턴 2 · Sia]" in rendered
    assert "Sia 응답" in rendered


# ─────────────────────────────────────────────
#  confidence enforce 단독 테스트
# ─────────────────────────────────────────────

def test_enforce_confidence_nulls_demotes_low_confidence():
    """value 있지만 confidence <0.4 → null + fallback_needed."""
    from schemas.user_profile import (
        StructuredFields,
        StructuredFieldsConfidence,
    )
    fields = StructuredFields(
        desired_image="편안함",
        reference_style="카리나",
        height="160_165",
        confidence=StructuredFieldsConfidence(
            desired_image=0.85,
            reference_style=0.20,   # low — demote
            height=0.30,             # low — demote
        ),
    )
    result = ExtractionResult(fields=fields, fallback_needed=[])
    out = extraction._enforce_confidence_nulls(result)
    assert out.fields.desired_image == "편안함"         # 유지
    assert out.fields.reference_style is None            # demoted
    assert out.fields.height is None                     # demoted
    assert "reference_style" in out.fallback_needed
    assert "height" in out.fallback_needed
