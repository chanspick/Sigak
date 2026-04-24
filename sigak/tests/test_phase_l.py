"""Phase L — Verdict v2 확장 테스트.

검증 포인트:
- build_verdict_v2 시그니처에 matched_trends / taste_profile 추가됨
- _build_user_message 가 KB + taste_profile 블록 포함
- 기존 호출 (신규 파라미터 None) 도 그대로 동작
- 라우트 verdict_v2 가 KnowledgeMatcher/Vault 예외 발생해도 degrade
"""
from __future__ import annotations

import sys
import os
import json
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services import verdict_v2 as vv2
from services.coordinate_system import VisualCoordinate
from services.knowledge_matcher import match_trends_for_user
from schemas.user_taste import UserTasteProfile


# ─────────────────────────────────────────────
#  _render_matched_trends
# ─────────────────────────────────────────────

def test_render_matched_trends_empty():
    assert "(KB 매칭 없음)" in vv2._render_matched_trends(None)
    assert "(KB 매칭 없음)" in vv2._render_matched_trends([])


def test_render_matched_trends_with_items():
    profile = UserTasteProfile(
        user_id="u1",
        snapshot_at=datetime.now(timezone.utc),
        current_position=VisualCoordinate(shape=0.5, volume=0.5, age=0.3),
    )
    matched = match_trends_for_user(profile, gender="female", season="2026_spring")
    assert len(matched) >= 1
    text = vv2._render_matched_trends(matched)
    # trend_id + title + score 노출
    assert "female_2026_spring_001" in text
    assert "민트" in text
    assert "score=" in text


# ─────────────────────────────────────────────
#  _render_taste_profile
# ─────────────────────────────────────────────

def test_render_taste_profile_none():
    out = vv2._render_taste_profile(None)
    assert "없음" in out


def test_render_taste_profile_model_dump():
    profile = UserTasteProfile(
        user_id="u1",
        snapshot_at=datetime.now(timezone.utc),
        current_position=VisualCoordinate(shape=0.4, volume=0.5, age=0.3),
        strength_score=0.55,
        user_original_phrases=["차분한데 또렷한"],
    )
    out = vv2._render_taste_profile(profile)
    # JSON 렌더, 주요 필드 노출
    assert "current_position" in out
    assert "strength_score" in out
    assert "0.55" in out
    assert "차분한데 또렷한" in out


def test_render_taste_profile_accepts_dict():
    """pydantic 인스턴스 대신 이미 dump 된 dict 도 허용."""
    d = {
        "current_position": {"shape": 0.5, "volume": 0.5, "age": 0.5},
        "strength_score": 0.3,
    }
    out = vv2._render_taste_profile(d)
    assert "0.3" in out


# ─────────────────────────────────────────────
#  _build_user_message — 신규 블록 주입
# ─────────────────────────────────────────────

def _minimal_photo():
    return {"url": "https://cdn.example.com/x.jpg", "index": 0}


def test_build_user_message_without_new_params_still_works():
    """기존 호출 (matched_trends / taste_profile 없음) 에도 동작."""
    blocks = vv2._build_user_message(
        user_profile={"structured_fields": {}, "ig_feed_cache": None},
        photos=[_minimal_photo()],
        trend_data={},
    )
    # text 블록은 마지막 1개
    text = blocks[-1]["text"]
    assert "taste_profile" in text
    assert "matched_trends" in text
    # 신규 블록 자리는 있지만 내용은 '없음'
    assert "없음" in text


def test_build_user_message_injects_trends_and_taste():
    profile = UserTasteProfile(
        user_id="u1",
        snapshot_at=datetime.now(timezone.utc),
        current_position=VisualCoordinate(shape=0.5, volume=0.5, age=0.3),
        strength_score=0.42,
    )
    matched = match_trends_for_user(profile, gender="female", season="2026_spring")
    blocks = vv2._build_user_message(
        user_profile={"structured_fields": {}, "ig_feed_cache": None},
        photos=[_minimal_photo()],
        trend_data={},
        matched_trends=matched,
        taste_profile=profile,
    )
    text = blocks[-1]["text"]
    # taste_profile 필드
    assert "0.42" in text
    # matched_trends 엔트리
    assert "female_2026_spring_001" in text
    # 양쪽 참조 지시문 (Sonnet 에 "matched_trends / taste_profile 참조" 명시)
    assert "matched_trends" in text
    assert "taste_profile" in text


# ─────────────────────────────────────────────
#  build_verdict_v2 — 시그니처 확장 경로
# ─────────────────────────────────────────────

def test_build_verdict_v2_accepts_new_kwargs(monkeypatch):
    """신규 kwargs 가 call_sonnet 까지 전달되는지 확인."""
    captured = {}

    def _fake_call_sonnet(user_profile, photos, trend_data,
                          matched_trends=None, taste_profile=None,
                          history_context=None,
                          max_tokens=3000):
        captured["matched_trends"] = matched_trends
        captured["taste_profile"] = taste_profile
        # 최소 유효 Verdict JSON 반환
        return json.dumps({
            "preview": {
                "hook_line": "피드 분석 완료했습니다",
                "reason_summary": "추구미와 사진 분위기가 일치합니다. 추가 정비 여지가 있습니다.",
            },
            "full_content": {
                "verdict": (
                    "정돈된 방향이 피드에 일관되게 드러납니다. "
                    "다만 한 장이 변수로 작용합니다. "
                    "전체 톤은 유지 가치가 있습니다. "
                    "장점을 강화하는 방향이 추천됩니다."
                ),
                "photo_insights": [
                    {
                        "photo_index": 0,
                        "insight": "톤이 일관됩니다.",
                        "improvement": "광원만 살짝 올리면 됩니다.",
                    }
                ],
                "recommendation": {
                    "style_direction": "유지에 무게를 둡니다.",
                    "next_action": "동일 톤 2장 추가합니다.",
                    "why": "근거는 분위기 일관성입니다.",
                },
                "numbers": {
                    "photo_count": 1,
                    "dominant_tone": "쿨뮤트",
                    "dominant_tone_pct": 68,
                    "chroma_multiplier": 1.0,
                    "alignment_with_profile": "일치",
                },
                "cta_pi": {
                    "headline": "피드 분석 너머, 얼굴 단위로 이어집니다",
                    "body": "평소 추구미와 피드 방향의 일치는 확인됐습니다. 시각이 본 나에서 얼굴 비율과 라인이 같은 방향인지 이어서 보실 수 있습니다.",
                    "action_label": "시각이 본 나 열기",
                },
            },
        }, ensure_ascii=False)

    monkeypatch.setattr(vv2, "_call_sonnet", _fake_call_sonnet)

    profile = UserTasteProfile(
        user_id="u1",
        snapshot_at=datetime.now(timezone.utc),
        current_position=VisualCoordinate(shape=0.5, volume=0.5, age=0.3),
    )
    matched = match_trends_for_user(profile, gender="female", season="2026_spring")

    result = vv2.build_verdict_v2(
        user_profile={"structured_fields": {}, "ig_feed_cache": None},
        photos=[_minimal_photo()],
        trend_data=None,
        matched_trends=matched,
        taste_profile=profile,
    )
    # 응답 정상 파싱
    assert result.preview.hook_line
    assert result.full_content.verdict
    # 신규 kwargs 가 _call_sonnet 에 전달됐는지
    assert captured["matched_trends"] is matched
    assert captured["taste_profile"] is profile


def test_build_verdict_v2_backward_compat(monkeypatch):
    """matched_trends / taste_profile 생략해도 기존 경로 그대로 동작."""
    called = {"n": 0}

    def _fake(user_profile, photos, trend_data,
             matched_trends=None, taste_profile=None,
             history_context=None,
             max_tokens=3000):
        called["n"] += 1
        # None 전달 확인
        assert matched_trends is None
        assert taste_profile is None
        return json.dumps({
            "preview": {"hook_line": "a", "reason_summary": "b c d."},
            "full_content": {
                "verdict": "e f g h.",
                "photo_insights": [{"photo_index": 0, "insight": "i", "improvement": "j"}],
                "recommendation": {"style_direction": "k", "next_action": "l", "why": "m"},
                "numbers": {
                    "photo_count": 1, "dominant_tone": "쿨뮤트",
                    "dominant_tone_pct": 50, "chroma_multiplier": 1.0,
                    "alignment_with_profile": "일치",
                },
                "cta_pi": {
                    "headline": "h", "body": "b", "action_label": "a",
                },
            },
        }, ensure_ascii=False)

    monkeypatch.setattr(vv2, "_call_sonnet", _fake)

    result = vv2.build_verdict_v2(
        user_profile={}, photos=[_minimal_photo()], trend_data=None,
    )
    assert called["n"] == 1
    assert result.full_content.verdict
