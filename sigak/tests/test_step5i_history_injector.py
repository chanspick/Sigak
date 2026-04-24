"""STEP 5i 검증 — history_injector.build_history_context.

LLM prompt prepend 용 user_history 요약 빌더의 분기 커버:
  - 빈 history → ""
  - column 없음 → ""
  - full mode 정상 조립
  - 토큰 한도 초과 시 summary mode
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.history_injector import build_history_context


class _Row:
    def __init__(self, user_history):
        self.user_history = user_history


class _Exec:
    def __init__(self, row):
        self._row = row
    def first(self):
        return self._row


class _DB:
    def __init__(self, history_or_exc):
        self._v = history_or_exc
    def execute(self, stmt, params=None):
        if isinstance(self._v, Exception):
            raise self._v
        return _Exec(_Row(self._v))


# ─────────────────────────────────────────────
#  빈 / 에러 경로
# ─────────────────────────────────────────────

def test_empty_history_returns_empty_string():
    db = _DB({})
    out = build_history_context(db, "u1", include=["conversations"])
    assert out == ""


def test_no_row_returns_empty_string():
    class _NullDB:
        def execute(self, stmt, params=None):
            return _Exec(None)
    out = build_history_context(_NullDB(), "u1", include=["conversations"])
    assert out == ""


def test_column_missing_returns_empty_string():
    db = _DB(RuntimeError("column user_history does not exist"))
    out = build_history_context(db, "u1", include=["conversations"])
    assert out == ""


def test_history_not_dict_returns_empty_string():
    db = _DB("unexpected string")
    out = build_history_context(db, "u1", include=["conversations"])
    assert out == ""


# ─────────────────────────────────────────────
#  Full mode rendering
# ─────────────────────────────────────────────

def test_conversations_block_renders():
    history = {
        "conversations": [
            {
                "session_id": "sia_1",
                "started_at": "2026-04-24T10:00:00+00:00",
                "messages": [
                    {"role": "user", "content": "처음 만나네요"},
                    {"role": "assistant", "content": "결이 차분하시잖아요"},
                    {"role": "user", "content": "맞아요"},
                ],
                "ig_snapshot": {
                    "r2_dir": "user_media/u1/ig_snapshots/t1/",
                    "photo_r2_urls": [],
                    "analysis": {"tone_category": "쿨뮤트"},
                },
            },
        ],
    }
    db = _DB(history)
    out = build_history_context(db, "u1", include=["conversations"], max_per_type=1)
    assert "이전 맥락" in out
    assert "Sia 대화 이력" in out
    assert "쿨뮤트" in out
    assert "sia_1" in out or "세션 #1" in out
    # 현재 요청 마커가 붙어 본문이 이어질 자리 잡음
    assert "현재 요청" in out


def test_aspiration_block_renders():
    history = {
        "aspiration_analyses": [
            {
                "analysis_id": "asp_1",
                "target_handle": "yuni",
                "source": "instagram",
                "gap_narrative": "형태 쪽으로 +0.20 이동이 크고 (소프트 → 샤프)",
                "sia_overall_message": "정리 완료",
            },
        ],
    }
    db = _DB(history)
    out = build_history_context(
        db, "u1",
        include=["aspiration_analyses"],
        max_per_type=1,
    )
    assert "추구미 분석 이력" in out
    assert "yuni" in out
    assert "형태 쪽으로" in out


def test_best_shot_block_renders():
    history = {
        "best_shot_sessions": [
            {
                "session_id": "bs_1",
                "uploaded_count": 80,
                "selected": [{"r2_url": "https://r2/a.jpg"}, {"r2_url": "https://r2/b.jpg"}],
                "overall_message": "두 장 골랐어요",
            },
        ],
    }
    db = _DB(history)
    out = build_history_context(db, "u1", include=["best_shot_sessions"])
    assert "Best Shot" in out
    assert "80" in out
    assert "두 장 골랐어요" in out


def test_verdict_block_renders():
    history = {
        "verdict_sessions": [
            {
                "session_id": "vrd_1",
                "photos_r2_urls": ["https://r2/p1", "https://r2/p2", "https://r2/p3"],
                "recommendation": {"top_action": "자연스럽게 유지"},
            },
        ],
    }
    db = _DB(history)
    out = build_history_context(db, "u1", include=["verdict_sessions"])
    assert "피드 추천" in out
    assert "3장" in out
    assert "자연스럽게 유지" in out


# ─────────────────────────────────────────────
#  include 필터 동작
# ─────────────────────────────────────────────

def test_include_filter_skips_other_categories():
    history = {
        "conversations": [{"session_id": "sia_1", "messages": []}],
        "aspiration_analyses": [{"analysis_id": "asp_1", "target_handle": "x"}],
    }
    db = _DB(history)
    out = build_history_context(db, "u1", include=["conversations"])
    assert "Sia 대화 이력" in out
    assert "추구미" not in out


# ─────────────────────────────────────────────
#  Summary mode (토큰 한도 초과)
# ─────────────────────────────────────────────

def test_summary_mode_when_over_token_limit():
    """token_limit 작게 설정 → summary 모드로 압축."""
    long_content = "길어지는 유저 발화 " * 500  # 충분히 큰 메시지
    history = {
        "conversations": [
            {
                "session_id": f"s_{i}",
                "messages": [
                    {"role": "user", "content": long_content},
                    {"role": "assistant", "content": long_content},
                ],
            }
            for i in range(3)
        ],
    }
    db = _DB(history)
    # 매우 낮은 한도
    out = build_history_context(
        db, "u1",
        include=["conversations"],
        max_per_type=3,
        token_limit=100,
    )
    # summary 모드 — "총 N 메시지" 대신 "유저 시작:" 또는 "Sia 마무리:" 라벨
    # 전체 messages dump 는 없음
    assert out != ""
    assert "총 " not in out  # full 모드 artifact 금지
