"""Verdict 2.0 engine tests (v2 Priority 1 D5 Phase 1).

Sonnet 4.6 응답은 mock. 실 API 호출 0건.
실 API 검증은 probe_verdict_v2.py (D5 Phase 2 tooling) 에서.

커버리지:
  - happy path 1 장/3 장/10 장
  - preview/full 분리 검증
  - Hard Rules 자동 거절 (verdict/판정/마크다운/이모지 in 유저 노출 텍스트)
  - JSON fence strip
  - retry on parse/validation 실패
  - photos validation (0 장, 11 장 거부)
  - photo content block rendering (url / base64 양쪽)
"""
import json
import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import anthropic

from schemas.verdict_v2 import VerdictV2Result
from services import verdict_v2
from services.verdict_v2 import VerdictV2Error


# ─────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_client():
    verdict_v2.reset_client()
    yield
    verdict_v2.reset_client()


SAMPLE_USER_PROFILE = {
    "structured_fields": {
        "desired_image": "편안하고 친밀한 인상 추구",
        "reference_style": "한소희 초반",
        "current_concerns": ["추구미와 피드 분위기 갭"],
        "self_perception": "정돈된 인상이라는 평",
        "lifestyle_context": "프리랜서 기획자",
        "height": "165_170",
        "weight": "50_55",
        "shoulder_width": "medium",
    },
    "ig_feed_cache": {
        "scope": "full",
        "profile_basics": {"username": "testuser", "post_count": 38},
        "current_style_mood": [{"tag": "쿨뮤트", "ratio": 0.68}],
    },
}

SAMPLE_PHOTOS_1 = [{"url": "https://example.com/p1.jpg"}]
SAMPLE_PHOTOS_3 = [
    {"url": "https://example.com/p1.jpg"},
    {"url": "https://example.com/p2.jpg"},
    {"url": "https://example.com/p3.jpg"},
]
SAMPLE_PHOTOS_10 = [{"url": f"https://example.com/p{i}.jpg"} for i in range(10)]
SAMPLE_PHOTOS_11 = [{"url": f"https://example.com/p{i}.jpg"} for i in range(11)]
SAMPLE_PHOTOS_BASE64 = [{
    "base64": "iVBORw0KGgoAAAANSUhEUgAA...",
    "media_type": "image/png",
}]


def _make_response_with_n_insights(n: int) -> dict:
    """N 장 사진 대응 Sonnet 응답 fixture."""
    return {
        "preview": {
            "hook_line": "추구미와 피드 분위기가 일치합니다",
            "reason_summary": (
                "쿨뮤트 톤이 유저 추구 방향과 일치합니다. "
                f"다만 {n}장 중 1장이 무드 변수로 작용합니다."
            ),
        },
        "full_content": {
            "verdict": (
                "전반적으로 유저가 추구하는 편안한 인상과 사진 분위기가 일치합니다. "
                "쿨뮤트 톤이 일관되게 유지되고 있습니다. 채도는 평균보다 낮게 관리된 편입니다."
            ),
            "photo_insights": [
                {
                    "photo_index": i,
                    "insight": f"{i+1}번 사진은 쿨뮤트 톤과 맞는 구도입니다.",
                    "improvement": "측광 활용 시 더 자연스러워집니다.",
                }
                for i in range(n)
            ],
            "recommendation": {
                "style_direction": "쿨뮤트 방향 유지, 채도 조금 올리기",
                "next_action": "다음 촬영 시 측광 포즈 시도",
                "why": "추구미와 피드 방향 일치를 더 강화합니다",
            },
            "numbers": {
                "photo_count": n,
                "dominant_tone": "쿨뮤트",
                "dominant_tone_pct": 68,
                "alignment_with_profile": "일치",
            },
        },
    }


def _mock_response(text: str) -> MagicMock:
    content = MagicMock()
    content.type = "text"
    content.text = text
    resp = MagicMock()
    resp.content = [content]
    return resp


def _install_mock_client(monkeypatch, response_sequence: list):
    """여러 응답 순차 반환. exception 넣으면 raise."""
    call_count = {"n": 0}

    def _fake(*args, **kwargs):
        idx = min(call_count["n"], len(response_sequence) - 1)
        call_count["n"] += 1
        item = response_sequence[idx]
        if isinstance(item, Exception):
            raise item
        text = item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)
        return _mock_response(text)

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = _fake
    monkeypatch.setattr(verdict_v2, "_get_client", lambda: mock_client)
    return mock_client


# ─────────────────────────────────────────────
#  Happy path
# ─────────────────────────────────────────────

def test_build_verdict_1_photo(monkeypatch):
    _install_mock_client(monkeypatch, [_make_response_with_n_insights(1)])
    result = verdict_v2.build_verdict_v2(
        user_profile=SAMPLE_USER_PROFILE,
        photos=SAMPLE_PHOTOS_1,
    )
    assert isinstance(result, VerdictV2Result)
    assert result.preview.hook_line == "추구미와 피드 분위기가 일치합니다"
    assert len(result.full_content.photo_insights) == 1
    assert result.full_content.numbers.photo_count == 1


def test_build_verdict_3_photos(monkeypatch):
    _install_mock_client(monkeypatch, [_make_response_with_n_insights(3)])
    result = verdict_v2.build_verdict_v2(
        user_profile=SAMPLE_USER_PROFILE,
        photos=SAMPLE_PHOTOS_3,
    )
    assert len(result.full_content.photo_insights) == 3
    assert result.full_content.photo_insights[0].photo_index == 0


def test_build_verdict_10_photos(monkeypatch):
    _install_mock_client(monkeypatch, [_make_response_with_n_insights(10)])
    result = verdict_v2.build_verdict_v2(
        user_profile=SAMPLE_USER_PROFILE,
        photos=SAMPLE_PHOTOS_10,
    )
    assert len(result.full_content.photo_insights) == 10


# ─────────────────────────────────────────────
#  Photo validation (input side)
# ─────────────────────────────────────────────

def test_build_verdict_rejects_empty_photos():
    with pytest.raises(ValueError, match="photos required"):
        verdict_v2.build_verdict_v2(
            user_profile=SAMPLE_USER_PROFILE,
            photos=[],
        )


def test_build_verdict_rejects_too_many_photos():
    with pytest.raises(ValueError, match="too many"):
        verdict_v2.build_verdict_v2(
            user_profile=SAMPLE_USER_PROFILE,
            photos=SAMPLE_PHOTOS_11,
        )


# ─────────────────────────────────────────────
#  Photo content block rendering
# ─────────────────────────────────────────────

def test_photo_to_content_block_url():
    block = verdict_v2._photo_to_content_block({"url": "https://x.com/a.jpg"})
    assert block == {
        "type": "image",
        "source": {"type": "url", "url": "https://x.com/a.jpg"},
    }


def test_photo_to_content_block_base64():
    block = verdict_v2._photo_to_content_block({
        "base64": "abc123",
        "media_type": "image/png",
    })
    assert block == {
        "type": "image",
        "source": {"type": "base64", "media_type": "image/png", "data": "abc123"},
    }


def test_photo_to_content_block_base64_default_jpeg():
    block = verdict_v2._photo_to_content_block({"base64": "abc"})
    assert block["source"]["media_type"] == "image/jpeg"


def test_photo_to_content_block_missing_data():
    with pytest.raises(ValueError, match="requires 'url' or 'base64'"):
        verdict_v2._photo_to_content_block({})


# ─────────────────────────────────────────────
#  Hard Rules enforcement (user-facing text)
# ─────────────────────────────────────────────

def test_rejects_verdict_word_in_output(monkeypatch):
    """Sonnet 응답의 verdict 텍스트에 'verdict' 단어 포함 → Hard Rule 위반 → 재시도 후 실패."""
    bad = _make_response_with_n_insights(1)
    bad["full_content"]["verdict"] = "This verdict says 쿨뮤트 유지합니다."

    _install_mock_client(monkeypatch, [bad, bad])   # 2회 모두 같은 응답
    with pytest.raises(VerdictV2Error, match="Hard Rules 위반"):
        verdict_v2.build_verdict_v2(
            user_profile=SAMPLE_USER_PROFILE,
            photos=SAMPLE_PHOTOS_1,
            max_retries=1,
        )


def test_rejects_judgment_word(monkeypatch):
    bad = _make_response_with_n_insights(1)
    bad["preview"]["hook_line"] = "피드 분석 판정 완료"   # "판정" 금지
    _install_mock_client(monkeypatch, [bad, bad])
    with pytest.raises(VerdictV2Error):
        verdict_v2.build_verdict_v2(
            user_profile=SAMPLE_USER_PROFILE,
            photos=SAMPLE_PHOTOS_1,
            max_retries=1,
        )


def test_rejects_markdown_in_output(monkeypatch):
    bad = _make_response_with_n_insights(1)
    bad["full_content"]["recommendation"]["why"] = "**강조** 는 금지됩니다."
    _install_mock_client(monkeypatch, [bad, bad])
    with pytest.raises(VerdictV2Error):
        verdict_v2.build_verdict_v2(
            user_profile=SAMPLE_USER_PROFILE,
            photos=SAMPLE_PHOTOS_1,
            max_retries=1,
        )


def test_rejects_emoji_in_output(monkeypatch):
    bad = _make_response_with_n_insights(1)
    bad["full_content"]["photo_insights"][0]["insight"] = "좋은 각도입니다 😊"
    _install_mock_client(monkeypatch, [bad, bad])
    with pytest.raises(VerdictV2Error):
        verdict_v2.build_verdict_v2(
            user_profile=SAMPLE_USER_PROFILE,
            photos=SAMPLE_PHOTOS_1,
            max_retries=1,
        )


def test_rejects_eval_language(monkeypatch):
    bad = _make_response_with_n_insights(1)
    bad["preview"]["reason_summary"] = "사진이 좋아 보입니다. 계속 이 방향 유지하세요."
    _install_mock_client(monkeypatch, [bad, bad])
    with pytest.raises(VerdictV2Error):
        verdict_v2.build_verdict_v2(
            user_profile=SAMPLE_USER_PROFILE,
            photos=SAMPLE_PHOTOS_1,
            max_retries=1,
        )


def test_rejects_confirmation_request(monkeypatch):
    bad = _make_response_with_n_insights(1)
    bad["full_content"]["verdict"] = "이 결과가 맞으신가요? 확인해 주십시오."
    _install_mock_client(monkeypatch, [bad, bad])
    with pytest.raises(VerdictV2Error):
        verdict_v2.build_verdict_v2(
            user_profile=SAMPLE_USER_PROFILE,
            photos=SAMPLE_PHOTOS_1,
            max_retries=1,
        )


# ─────────────────────────────────────────────
#  Retry + recovery
# ─────────────────────────────────────────────

def test_retry_on_bad_json_succeeds_on_second(monkeypatch):
    bad_json = "{not valid json"
    good = _make_response_with_n_insights(1)
    _install_mock_client(monkeypatch, [bad_json, good])
    result = verdict_v2.build_verdict_v2(
        user_profile=SAMPLE_USER_PROFILE,
        photos=SAMPLE_PHOTOS_1,
    )
    assert result.preview.hook_line == "추구미와 피드 분위기가 일치합니다"


def test_retry_on_hard_rules_then_succeeds(monkeypatch):
    """첫 응답은 HR 위반, 재시도에 clean 응답."""
    bad = _make_response_with_n_insights(1)
    bad["full_content"]["verdict"] = "verdict 단어 포함 금지."  # HR1 위반
    good = _make_response_with_n_insights(1)
    _install_mock_client(monkeypatch, [bad, good])
    result = verdict_v2.build_verdict_v2(
        user_profile=SAMPLE_USER_PROFILE,
        photos=SAMPLE_PHOTOS_1,
    )
    assert "verdict" not in result.full_content.verdict.lower()


def test_fails_after_retries_exhausted(monkeypatch):
    _install_mock_client(monkeypatch, ["{bad", "{bad"])
    with pytest.raises(VerdictV2Error):
        verdict_v2.build_verdict_v2(
            user_profile=SAMPLE_USER_PROFILE,
            photos=SAMPLE_PHOTOS_1,
            max_retries=1,
        )


def test_api_error_triggers_retry(monkeypatch):
    import httpx
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    api_err = anthropic.APIError(message="transient", request=req, body=None)
    good = _make_response_with_n_insights(1)
    _install_mock_client(monkeypatch, [api_err, good])
    result = verdict_v2.build_verdict_v2(
        user_profile=SAMPLE_USER_PROFILE,
        photos=SAMPLE_PHOTOS_1,
    )
    assert result.full_content.numbers.photo_count == 1


# ─────────────────────────────────────────────
#  JSON fence stripping
# ─────────────────────────────────────────────

def test_json_fence_stripped(monkeypatch):
    payload = _make_response_with_n_insights(1)
    fenced = "```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```"
    _install_mock_client(monkeypatch, [fenced])
    result = verdict_v2.build_verdict_v2(
        user_profile=SAMPLE_USER_PROFILE,
        photos=SAMPLE_PHOTOS_1,
    )
    assert result.preview.hook_line == "추구미와 피드 분위기가 일치합니다"


# ─────────────────────────────────────────────
#  Preview/full separation (schema enforcement)
# ─────────────────────────────────────────────

def test_preview_hook_line_length_enforced():
    """hook_line 50 chars hard limit (Pydantic Field max_length=50)."""
    from schemas.verdict_v2 import PreviewContent
    with pytest.raises(Exception):
        PreviewContent(
            hook_line="x" * 100,   # 100 chars > 50
            reason_summary="ok",
        )


def test_full_content_photo_insights_are_list():
    """FullContent.photo_insights 는 list. 0 길이도 유효 (스키마만 검증)."""
    from schemas.verdict_v2 import FullContent, Recommendation
    fc = FullContent(
        verdict="분석 결과.",
        photo_insights=[],
        recommendation=Recommendation(
            style_direction="x", next_action="y", why="z",
        ),
    )
    assert fc.photo_insights == []


# ─────────────────────────────────────────────
#  user_facing_text collection (Hard Rules scope)
# ─────────────────────────────────────────────

def test_collect_user_facing_text_includes_all_fields():
    good = _make_response_with_n_insights(2)
    result = VerdictV2Result.model_validate(good)
    combined = verdict_v2._collect_user_facing_text(result)
    # preview 양쪽
    assert result.preview.hook_line in combined
    assert result.preview.reason_summary in combined
    # full_content verdict + insights + recommendation
    assert result.full_content.verdict in combined
    assert result.full_content.photo_insights[0].insight in combined
    assert result.full_content.photo_insights[1].improvement in combined
    assert result.full_content.recommendation.style_direction in combined
    assert result.full_content.recommendation.why in combined
