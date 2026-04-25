"""Verdict 2.0 best_fit (WTP 가설) tests.

WTP 가설:
  best_fit 1 장의 insight + improvement 를 unlock 전 풀 공개해
  결제율을 끌어올린다. preview.best_fit_* 3 필드 + full_content.best_fit_photo_index
  추가에 대한 일관성 / fallback / Hard Rules / backward compat 검증.

커버리지:
  - LLM 응답에 best_fit_photo_index 포함 → preview/full 양쪽 sync + insight/improvement 노출
  - best_fit_photo_index = None → preview slot 비활성, 기존 동작 보존
  - 기존 v2 verdict row (best_fit 컬럼 없음) → backward compat 정상
  - Hard Rules: best_fit_insight 에 verdict 단어 → HR1 차단 → 재시도
  - 일관성 보장: full.best_fit_photo_index 와 photo_insights 매핑
  - preview-only best_fit 표기 시 full 으로 sync
  - 잘못된 (out-of-range) index → 모두 None 으로 정리
"""
from __future__ import annotations

import json
import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schemas.verdict_v2 import (
    FullContent,
    PreviewContent,
    VerdictV2Result,
)
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
        "height": "165_170",
    },
    "ig_feed_cache": {"scope": "skipped"},
}

SAMPLE_PHOTOS_3 = [
    {"url": f"https://example.com/p{i}.jpg"} for i in range(3)
]


def _make_response(
    n: int,
    *,
    full_best_fit_index: int | None,
    preview_best_fit_index: int | None = None,
    preview_best_fit_insight: str | None = None,
    preview_best_fit_improvement: str | None = None,
) -> dict:
    """N 장 사진 + best_fit 명시 옵션 응답 fixture."""
    photo_insights = [
        {
            "photo_index": i,
            "insight": f"{i+1}번 사진은 쿨뮤트 톤과 맞는 구도입니다.",
            "improvement": f"{i+1}번은 측광 활용 시 더 자연스러워집니다.",
        }
        for i in range(n)
    ]
    preview: dict = {
        "hook_line": "추구미와 피드 분위기가 일치합니다",
        "reason_summary": (
            "쿨뮤트 톤이 유저 추구 방향과 일치합니다. "
            "다만 1장이 무드 변수로 작용합니다."
        ),
    }
    if preview_best_fit_index is not None:
        preview["best_fit_photo_index"] = preview_best_fit_index
    if preview_best_fit_insight is not None:
        preview["best_fit_insight"] = preview_best_fit_insight
    if preview_best_fit_improvement is not None:
        preview["best_fit_improvement"] = preview_best_fit_improvement

    full_content: dict = {
        "verdict": (
            "전반적으로 유저 추구 방향과 사진 분위기가 일치합니다. "
            "쿨뮤트 톤이 일관되게 유지됩니다. 채도는 낮게 관리된 편입니다."
        ),
        "photo_insights": photo_insights,
        "recommendation": {
            "style_direction": "쿨뮤트 방향 유지",
            "next_action": "다음 촬영 시 측광 시도",
            "why": "추구미와 일치 강화를 위해서입니다",
        },
        "numbers": {
            "photo_count": n,
            "dominant_tone": "쿨뮤트",
            "dominant_tone_pct": 68,
            "alignment_with_profile": "일치",
        },
    }
    if full_best_fit_index is not None:
        full_content["best_fit_photo_index"] = full_best_fit_index

    return {"preview": preview, "full_content": full_content}


def _mock_response(text: str) -> MagicMock:
    content = MagicMock()
    content.type = "text"
    content.text = text
    resp = MagicMock()
    resp.content = [content]
    return resp


def _install_mock_client(monkeypatch, responses: list):
    call_count = {"n": 0}

    def _fake(*args, **kwargs):
        idx = min(call_count["n"], len(responses) - 1)
        call_count["n"] += 1
        item = responses[idx]
        if isinstance(item, Exception):
            raise item
        text = item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)
        return _mock_response(text)

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = _fake
    monkeypatch.setattr(verdict_v2, "_get_client", lambda: mock_client)
    return mock_client


# ─────────────────────────────────────────────
#  Schema-level tests (no LLM)
# ─────────────────────────────────────────────


def test_preview_content_accepts_best_fit_fields():
    """PreviewContent 가 새 best_fit_* 3 필드 수용."""
    pv = PreviewContent.model_validate({
        "hook_line": "훅",
        "reason_summary": "근거",
        "best_fit_photo_index": 0,
        "best_fit_insight": "이 사진은 쿨뮤트 톤과 맞습니다.",
        "best_fit_improvement": "측광 활용 시 더 자연스러워집니다.",
    })
    assert pv.best_fit_photo_index == 0
    assert pv.best_fit_insight == "이 사진은 쿨뮤트 톤과 맞습니다."
    assert pv.best_fit_improvement == "측광 활용 시 더 자연스러워집니다."


def test_preview_content_best_fit_fields_optional():
    """3 필드 모두 부재해도 정상 (backward compat)."""
    pv = PreviewContent.model_validate({
        "hook_line": "훅",
        "reason_summary": "근거",
    })
    assert pv.best_fit_photo_index is None
    assert pv.best_fit_insight is None
    assert pv.best_fit_improvement is None


def test_full_content_accepts_best_fit_photo_index():
    """FullContent 가 best_fit_photo_index Optional 수용."""
    fc = FullContent.model_validate({
        "verdict": "분석 결과.",
        "photo_insights": [],
        "recommendation": {
            "style_direction": "x", "next_action": "y", "why": "z",
        },
        "best_fit_photo_index": 2,
    })
    assert fc.best_fit_photo_index == 2


def test_full_content_best_fit_photo_index_optional():
    """기존 v2 row (best_fit_photo_index 컬럼 없음) backward compat."""
    fc = FullContent.model_validate({
        "verdict": "분석 결과.",
        "photo_insights": [],
        "recommendation": {
            "style_direction": "x", "next_action": "y", "why": "z",
        },
    })
    assert fc.best_fit_photo_index is None


def test_preview_extra_fields_ignored():
    """extra='ignore' 정책 — 미인지 필드도 무시 (forward compat)."""
    pv = PreviewContent.model_validate({
        "hook_line": "훅",
        "reason_summary": "근거",
        "best_fit_photo_index": 1,
        "future_field": "ignored",
    })
    assert pv.best_fit_photo_index == 1


# ─────────────────────────────────────────────
#  _sync_best_fit_fields (post-processing)
# ─────────────────────────────────────────────


def test_sync_full_index_overrides_preview():
    """full.best_fit_photo_index 가 source of truth — preview 덮어쓰기."""
    payload = _make_response(
        3,
        full_best_fit_index=1,
        # preview 에 다른 값 지정 → full 이 이김
        preview_best_fit_index=0,
        preview_best_fit_insight="잘못된 텍스트",
        preview_best_fit_improvement="잘못된 개선",
    )
    result = VerdictV2Result.model_validate(payload)
    verdict_v2._sync_best_fit_fields(result)
    assert result.full_content.best_fit_photo_index == 1
    assert result.preview.best_fit_photo_index == 1
    assert result.preview.best_fit_insight == result.full_content.photo_insights[1].insight
    assert result.preview.best_fit_improvement == result.full_content.photo_insights[1].improvement


def test_sync_preview_only_synced_to_full():
    """full 에 best_fit 누락, preview 만 명시 → full 으로 sync."""
    payload = _make_response(
        3,
        full_best_fit_index=None,
        preview_best_fit_index=2,
    )
    result = VerdictV2Result.model_validate(payload)
    verdict_v2._sync_best_fit_fields(result)
    assert result.full_content.best_fit_photo_index == 2
    assert result.preview.best_fit_photo_index == 2
    assert result.preview.best_fit_insight == result.full_content.photo_insights[2].insight


def test_sync_both_none_clears_slots():
    """둘 다 None → 모두 None 으로 정리."""
    payload = _make_response(3, full_best_fit_index=None)
    result = VerdictV2Result.model_validate(payload)
    verdict_v2._sync_best_fit_fields(result)
    assert result.full_content.best_fit_photo_index is None
    assert result.preview.best_fit_photo_index is None
    assert result.preview.best_fit_insight is None
    assert result.preview.best_fit_improvement is None


def test_sync_out_of_range_index_clears():
    """photo_insights 길이 초과 인덱스 → None 으로 정리 (안전)."""
    payload = _make_response(3, full_best_fit_index=5)  # only 3 insights
    result = VerdictV2Result.model_validate(payload)
    verdict_v2._sync_best_fit_fields(result)
    assert result.full_content.best_fit_photo_index is None
    assert result.preview.best_fit_photo_index is None


def test_sync_zero_index_valid():
    """index=0 도 유효 (boundary)."""
    payload = _make_response(3, full_best_fit_index=0)
    result = VerdictV2Result.model_validate(payload)
    verdict_v2._sync_best_fit_fields(result)
    assert result.full_content.best_fit_photo_index == 0
    assert result.preview.best_fit_photo_index == 0


# ─────────────────────────────────────────────
#  build_verdict_v2 — end-to-end with mocked Sonnet
# ─────────────────────────────────────────────


def test_build_with_best_fit_index_propagates(monkeypatch):
    """LLM 이 best_fit_photo_index 명시 → preview / full 양쪽 채워짐."""
    payload = _make_response(3, full_best_fit_index=1)
    _install_mock_client(monkeypatch, [payload])
    result = verdict_v2.build_verdict_v2(
        user_profile=SAMPLE_USER_PROFILE,
        photos=SAMPLE_PHOTOS_3,
    )
    assert result.full_content.best_fit_photo_index == 1
    assert result.preview.best_fit_photo_index == 1
    assert result.preview.best_fit_insight is not None
    assert result.preview.best_fit_improvement is not None
    assert result.preview.best_fit_insight == result.full_content.photo_insights[1].insight


def test_build_without_best_fit_keeps_legacy_behavior(monkeypatch):
    """LLM 이 best_fit_photo_index 안 보냄 → 기존 동작 100% 보존."""
    payload = _make_response(3, full_best_fit_index=None)
    _install_mock_client(monkeypatch, [payload])
    result = verdict_v2.build_verdict_v2(
        user_profile=SAMPLE_USER_PROFILE,
        photos=SAMPLE_PHOTOS_3,
    )
    assert result.full_content.best_fit_photo_index is None
    assert result.preview.best_fit_photo_index is None
    assert result.preview.best_fit_insight is None
    assert result.preview.best_fit_improvement is None
    # hook_line / reason_summary / verdict 정상 노출 — 기존 흐름 보존
    assert result.preview.hook_line == "추구미와 피드 분위기가 일치합니다"
    assert len(result.full_content.photo_insights) == 3


def test_build_inconsistent_preview_overridden_by_full(monkeypatch):
    """LLM 이 preview / full 에 다른 best_fit 텍스트 → full 기준으로 정정."""
    payload = _make_response(
        3,
        full_best_fit_index=2,
        preview_best_fit_insight="LLM 이 잘못 쓴 텍스트",
        preview_best_fit_improvement="잘못된 개선 텍스트",
    )
    _install_mock_client(monkeypatch, [payload])
    result = verdict_v2.build_verdict_v2(
        user_profile=SAMPLE_USER_PROFILE,
        photos=SAMPLE_PHOTOS_3,
    )
    assert result.full_content.best_fit_photo_index == 2
    assert result.preview.best_fit_insight == result.full_content.photo_insights[2].insight
    assert result.preview.best_fit_improvement == result.full_content.photo_insights[2].improvement


# ─────────────────────────────────────────────
#  Hard Rules — best_fit 텍스트도 검증 대상
# ─────────────────────────────────────────────


def test_hard_rules_block_verdict_word_in_best_fit_insight(monkeypatch):
    """preview.best_fit_insight 에 'verdict' 단어 → HR1 위반 → 재시도 후 실패."""
    bad = _make_response(3, full_best_fit_index=1)
    bad["full_content"]["photo_insights"][1]["insight"] = (
        "이 verdict 결과는 쿨뮤트와 맞습니다."
    )
    _install_mock_client(monkeypatch, [bad, bad])
    with pytest.raises(VerdictV2Error, match="Hard Rules 위반"):
        verdict_v2.build_verdict_v2(
            user_profile=SAMPLE_USER_PROFILE,
            photos=SAMPLE_PHOTOS_3,
            max_retries=1,
        )


def test_hard_rules_block_emoji_in_best_fit_improvement(monkeypatch):
    """photo_insights[idx].improvement 의 이모지 → preview 도 동일 텍스트라 HR5 위반."""
    bad = _make_response(3, full_best_fit_index=0)
    bad["full_content"]["photo_insights"][0]["improvement"] = "측광 활용 좋습니다 😊"
    _install_mock_client(monkeypatch, [bad, bad])
    with pytest.raises(VerdictV2Error):
        verdict_v2.build_verdict_v2(
            user_profile=SAMPLE_USER_PROFILE,
            photos=SAMPLE_PHOTOS_3,
            max_retries=1,
        )


def test_collect_user_facing_text_includes_best_fit():
    """preview.best_fit_insight / improvement 가 HR 검증 대상에 포함."""
    payload = _make_response(3, full_best_fit_index=1)
    result = VerdictV2Result.model_validate(payload)
    verdict_v2._sync_best_fit_fields(result)
    combined = verdict_v2._collect_user_facing_text(result)
    assert result.preview.best_fit_insight in combined
    assert result.preview.best_fit_improvement in combined


def test_collect_user_facing_text_skips_none_best_fit():
    """best_fit_insight/improvement None → 텍스트에서 제외."""
    payload = _make_response(3, full_best_fit_index=None)
    result = VerdictV2Result.model_validate(payload)
    verdict_v2._sync_best_fit_fields(result)
    combined = verdict_v2._collect_user_facing_text(result)
    # hook_line 은 여전히 포함, best_fit_* 는 None 이라 제외
    assert result.preview.hook_line in combined
    # None 이므로 fixture 텍스트만 포함되어야 (insight 는 photo_insights 경로로 포함)
    assert "best_fit" not in combined


# ─────────────────────────────────────────────
#  Backward compat — 기존 v2 row 조회
# ─────────────────────────────────────────────


def test_legacy_preview_row_validates():
    """기존 DB 에 저장된 preview_content (best_fit_* 없음) 조회 정상."""
    legacy = {
        "hook_line": "추구미와 일치합니다",
        "reason_summary": "쿨뮤트 톤이 유지되고 있습니다.",
    }
    pv = PreviewContent.model_validate(legacy)
    assert pv.hook_line == "추구미와 일치합니다"
    assert pv.best_fit_photo_index is None


def test_legacy_full_content_row_validates():
    """기존 DB 에 저장된 full_content (best_fit_photo_index 없음) 조회 정상."""
    legacy = {
        "verdict": "분석 결과입니다.",
        "photo_insights": [
            {"photo_index": 0, "insight": "x", "improvement": "y"},
        ],
        "recommendation": {
            "style_direction": "방향",
            "next_action": "행동",
            "why": "이유",
        },
        "numbers": {},
    }
    fc = FullContent.model_validate(legacy)
    assert fc.verdict == "분석 결과입니다."
    assert fc.best_fit_photo_index is None
    assert fc.cta_pi is None
