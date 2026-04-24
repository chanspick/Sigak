"""SiaWriter B3 신 구현 — user_name 주입 + A-17/A-20 wrap + 다양성.

테스트 범위:
  1. StubSiaWriter — 유저 이름 동적, "정세현" 하드코딩 제거 확인
  2. HaikuSiaWriter fallback — API 키 없을 때 StubSiaWriter 경로
  3. HaikuSiaWriter validator wrap — A-17/A-20/markdown 위반 시 재시도
  4. best_shot_engine — user_name / sibling_comments 올바르게 전달
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schemas.user_taste import (
    ConversationSignals,
    UserTasteProfile,
)
from services.sia_writer import (
    HaikuSiaWriter,
    StubSiaWriter,
    _collect_violations,
    _name_honorific,
    get_sia_writer,
    set_sia_writer,
)


# ─────────────────────────────────────────────
#  fixtures
# ─────────────────────────────────────────────

def _make_profile(*, strength: float = 0.5, evidence_count: int = 3) -> UserTasteProfile:
    return UserTasteProfile(
        user_id="u-test",
        snapshot_at=datetime.now(timezone.utc),
        current_position=None,
        aspiration_vector=None,
        preference_evidence=[],
        conversation_signals=ConversationSignals(),
        trajectory=[],
        user_original_phrases=[],
        strength_score=strength,
    )


# ─────────────────────────────────────────────
#  helpers
# ─────────────────────────────────────────────

class TestNameHonorific:
    def test_empty_name_yields_generic(self):
        assert _name_honorific("") == "이분"
        assert _name_honorific(None) == "이분"
        assert _name_honorific("   ") == "이분"

    def test_plain_name_gets_nim_suffix(self):
        assert _name_honorific("진규") == "진규님"
        assert _name_honorific("한") == "한님"

    def test_already_has_nim(self):
        assert _name_honorific("진규님") == "진규님"


class TestCollectViolations:
    def test_clean_text_no_violations(self):
        errs = _collect_violations("이 장이 가장 또렷하게 드러나더라구요")
        assert not errs

    def test_catches_a17(self):
        errs = _collect_violations("다음 단계로 넘어갈게요")
        assert any("A-17" in e for e in errs)

    def test_catches_a20(self):
        errs = _collect_violations("독특한 분이세요")
        assert any("A-20" in e for e in errs)

    def test_catches_markdown(self):
        errs = _collect_violations("**중요** 한 부분")
        assert any("마크다운" in e for e in errs)


# ─────────────────────────────────────────────
#  StubSiaWriter — user_name 동적
# ─────────────────────────────────────────────

class TestStubSiaWriterUserName:
    """기존 "정세현" 하드코딩 제거 확인."""

    def test_overall_no_hardcoded_name(self):
        stub = StubSiaWriter()
        profile = _make_profile()
        text = stub.generate_overall_message(
            profile=profile,
            context={"selected_count": 5, "uploaded_count": 100},
            user_name="진규",
        )
        assert "진규님" in text
        assert "정세현" not in text

    def test_overall_generic_fallback_when_no_name(self):
        stub = StubSiaWriter()
        profile = _make_profile()
        text = stub.generate_overall_message(
            profile=profile,
            context={"selected_count": 5, "uploaded_count": 100},
            user_name=None,
        )
        assert "이분" in text
        assert "정세현" not in text

    def test_boundary_no_hardcoded_name(self):
        stub = StubSiaWriter()
        profile = _make_profile()
        text = stub.render_boundary_message(
            profile=profile,
            public_count=5,
            locked_count=20,
            user_name="진규",
        )
        assert "진규님" in text
        assert "정세현" not in text

    def test_photo_comment_clean_of_violations(self):
        stub = StubSiaWriter()
        profile = _make_profile()
        for rank in [1, 2, 5, 10]:
            text = stub.generate_comment_for_photo(
                photo_url="url",
                photo_context={"rank": rank},
                profile=profile,
                user_name="진규",
            )
            errs = _collect_violations(text)
            assert not errs, f"rank={rank} violations: {errs}"

    def test_overall_clean_of_violations(self):
        stub = StubSiaWriter()
        profile = _make_profile()
        text = stub.generate_overall_message(
            profile=profile,
            context={"selected_count": 5, "uploaded_count": 100},
            user_name="진규",
        )
        errs = _collect_violations(text)
        assert not errs, f"violations: {errs}"

    def test_boundary_clean_of_violations(self):
        stub = StubSiaWriter()
        profile = _make_profile()
        text = stub.render_boundary_message(
            profile=profile, public_count=5, locked_count=20, user_name="진규",
        )
        errs = _collect_violations(text)
        assert not errs, f"violations: {errs}"


# ─────────────────────────────────────────────
#  HaikuSiaWriter — fallback 경로
# ─────────────────────────────────────────────

class TestHaikuWriterFallbackNoApiKey:
    """API 키 없으면 StubSiaWriter fallback."""

    def test_no_api_key_uses_fallback_for_photo(self):
        writer = HaikuSiaWriter()
        profile = _make_profile()
        with patch("config.get_settings") as mock_settings:
            mock_settings.return_value.anthropic_api_key = ""
            text = writer.generate_comment_for_photo(
                photo_url="url",
                photo_context={"rank": 1},
                profile=profile,
                user_name="진규",
            )
        # fallback text is clean
        assert text
        errs = _collect_violations(text)
        assert not errs

    def test_no_api_key_uses_fallback_for_overall(self):
        writer = HaikuSiaWriter()
        profile = _make_profile()
        with patch("config.get_settings") as mock_settings:
            mock_settings.return_value.anthropic_api_key = ""
            text = writer.generate_overall_message(
                profile=profile,
                context={"selected_count": 3, "uploaded_count": 60},
                user_name="진규",
            )
        assert "진규님" in text
        assert "정세현" not in text


class TestHaikuWriterValidatorWrap:
    """Haiku 응답 hard reject 시 재시도 + 최종 fallback."""

    def _make_mock_response(self, text: str) -> MagicMock:
        block = MagicMock()
        block.type = "text"
        block.text = text
        response = MagicMock()
        response.content = [block]
        return response

    def test_clean_response_returned_directly(self):
        writer = HaikuSiaWriter()
        profile = _make_profile()
        clean_text = "이 장은 드러난 결이 또렷하더라구요"

        mock_client = MagicMock()
        mock_client.messages.create.return_value = self._make_mock_response(clean_text)

        with patch("services.sia_llm._get_client", return_value=mock_client), \
             patch("config.get_settings") as mock_settings:
            mock_settings.return_value.anthropic_api_key = "sk-test"
            mock_settings.return_value.anthropic_model_haiku = "claude-haiku-test"
            text = writer.generate_comment_for_photo(
                photo_url="url",
                photo_context={"rank": 1, "rationale": "차분함"},
                profile=profile,
                user_name="진규",
            )
        assert text == clean_text
        # 1회만 호출 (재시도 없음)
        assert mock_client.messages.create.call_count == 1

    def test_retry_on_a17_violation(self):
        writer = HaikuSiaWriter()
        profile = _make_profile()
        bad_text = "다음 단계에서 더 정리해드릴게요"
        good_text = "이 장은 차분하게 드러나더라구요"

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [
            self._make_mock_response(bad_text),
            self._make_mock_response(good_text),
        ]

        with patch("services.sia_llm._get_client", return_value=mock_client), \
             patch("config.get_settings") as mock_settings:
            mock_settings.return_value.anthropic_api_key = "sk-test"
            mock_settings.return_value.anthropic_model_haiku = "claude-haiku-test"
            text = writer.generate_comment_for_photo(
                photo_url="url",
                photo_context={"rank": 1, "rationale": ""},
                profile=profile,
                user_name="진규",
            )
        assert text == good_text
        assert mock_client.messages.create.call_count == 2

    def test_retry_on_a20_violation(self):
        writer = HaikuSiaWriter()
        profile = _make_profile()
        bad_text = "진규님 매력적인 분이세요"
        good_text = "진규님 피드 결 따라 골랐어요"

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [
            self._make_mock_response(bad_text),
            self._make_mock_response(good_text),
        ]

        with patch("services.sia_llm._get_client", return_value=mock_client), \
             patch("config.get_settings") as mock_settings:
            mock_settings.return_value.anthropic_api_key = "sk-test"
            mock_settings.return_value.anthropic_model_haiku = "claude-haiku-test"
            text = writer.generate_overall_message(
                profile=profile,
                context={"selected_count": 3, "uploaded_count": 60},
                user_name="진규",
            )
        assert text == good_text

    def test_fallback_after_exhausting_retries(self):
        """A-17/A-20 반복 위반 시 최종 fallback text."""
        writer = HaikuSiaWriter()
        profile = _make_profile()
        always_bad = "다음 단계로 넘어갈게요. 리포트에서 확인하세요"

        mock_client = MagicMock()
        mock_client.messages.create.return_value = self._make_mock_response(always_bad)

        with patch("services.sia_llm._get_client", return_value=mock_client), \
             patch("config.get_settings") as mock_settings:
            mock_settings.return_value.anthropic_api_key = "sk-test"
            mock_settings.return_value.anthropic_model_haiku = "claude-haiku-test"
            text = writer.generate_comment_for_photo(
                photo_url="url",
                photo_context={"rank": 1},
                profile=profile,
                user_name="진규",
            )
        # fallback 이므로 validator clean
        errs = _collect_violations(text)
        assert not errs
        # 재시도 소진 후 fallback — 총 2회 호출 (최초 + retry 1회)
        assert mock_client.messages.create.call_count == 2

    def test_sibling_comments_passed_to_prompt(self):
        writer = HaikuSiaWriter()
        profile = _make_profile()

        mock_client = MagicMock()
        mock_client.messages.create.return_value = self._make_mock_response("깔끔해요")

        with patch("services.sia_llm._get_client", return_value=mock_client), \
             patch("config.get_settings") as mock_settings:
            mock_settings.return_value.anthropic_api_key = "sk-test"
            mock_settings.return_value.anthropic_model_haiku = "claude-haiku-test"
            writer.generate_comment_for_photo(
                photo_url="url",
                photo_context={"rank": 2},
                profile=profile,
                user_name="진규",
                sibling_comments=[
                    "첫 장은 또렷해요",
                    "두 번째는 차분해요",
                ],
            )
        # Haiku 호출 인자에서 prompt 안에 sibling 포함 확인
        call_args = mock_client.messages.create.call_args
        user_message = call_args.kwargs["messages"][0]["content"]
        assert "첫 장은 또렷해요" in user_message
        assert "두 번째는 차분해요" in user_message


class TestHaikuWriterApiErrorFallback:
    """Haiku API exception 시 fallback text 반환 — raise 안 함."""

    def test_api_exception_returns_fallback(self):
        writer = HaikuSiaWriter()
        profile = _make_profile()

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("api down")

        with patch("services.sia_llm._get_client", return_value=mock_client), \
             patch("config.get_settings") as mock_settings:
            mock_settings.return_value.anthropic_api_key = "sk-test"
            mock_settings.return_value.anthropic_model_haiku = "claude-haiku-test"
            text = writer.generate_comment_for_photo(
                photo_url="url",
                photo_context={"rank": 1},
                profile=profile,
                user_name="진규",
            )
        assert text  # non-empty fallback
        errs = _collect_violations(text)
        assert not errs


# ─────────────────────────────────────────────
#  best_shot_engine — user_name 흐름 검증
# ─────────────────────────────────────────────

class TestEngineUserNameFlow:
    """_materialize_selection 이 user_name / sibling_comments 올바르게 전달."""

    def test_writer_receives_user_name_and_sibling(self, monkeypatch):
        pytest.importorskip("PIL", reason="best_shot_engine requires Pillow")
        from services import best_shot_engine
        from services.best_shot_quality import QualityResult

        captured_calls: list[dict] = []

        class _RecordingWriter(StubSiaWriter):
            def generate_comment_for_photo(self, **kwargs):
                captured_calls.append(dict(kwargs))
                return super().generate_comment_for_photo(**kwargs)

        set_sia_writer(_RecordingWriter())
        try:
            # heuristic_survived 시뮬 (3장)
            survived = [
                (f"photo_{i}.jpg", b"fake_bytes", QualityResult(0.8, 0.8, 0.8, cutoff=0.35))
                for i in range(3)
            ]
            selection_plan = [
                {"rank": 1, "photo_index": 0, "profile_match_score": 0.8,
                 "trend_match_score": 0.7, "associated_trend_id": None, "rationale": "좋음"},
                {"rank": 2, "photo_index": 1, "profile_match_score": 0.75,
                 "trend_match_score": 0.6, "associated_trend_id": None, "rationale": ""},
                {"rank": 3, "photo_index": 2, "profile_match_score": 0.7,
                 "trend_match_score": 0.5, "associated_trend_id": None, "rationale": ""},
            ]
            # R2 put_bytes / public_url 은 monkeypatch
            monkeypatch.setattr(
                "services.r2_client.best_shot_selected_key",
                lambda u, s, p: f"{u}/bs/{s}/{p}",
            )
            monkeypatch.setattr("services.r2_client.put_bytes", lambda *a, **kw: None)
            monkeypatch.setattr("services.r2_client.public_url", lambda k: f"https://cdn/{k}")

            profile = _make_profile()
            results = best_shot_engine._materialize_selection(
                user_id="u-test",
                session_id="sess-1",
                selection_plan=selection_plan,
                heuristic_survived=survived,
                matched_trends=[],
                profile=profile,
                user_name="진규",
            )
        finally:
            set_sia_writer(StubSiaWriter())

        assert len(results) == 3
        assert len(captured_calls) == 3

        # 1st call: sibling_comments 빈 리스트
        assert captured_calls[0]["user_name"] == "진규"
        assert captured_calls[0]["sibling_comments"] == []

        # 2nd call: sibling 1개
        assert captured_calls[1]["user_name"] == "진규"
        assert len(captured_calls[1]["sibling_comments"]) == 1

        # 3rd call: sibling 2개 (첫 + 두번째)
        assert captured_calls[2]["user_name"] == "진규"
        assert len(captured_calls[2]["sibling_comments"]) == 2

    def test_writer_receives_empty_name_fallback(self, monkeypatch):
        """user_name=None 이면 writer 에 None 전달 — generic honorific."""
        pytest.importorskip("PIL", reason="best_shot_engine requires Pillow")
        from services import best_shot_engine
        from services.best_shot_quality import QualityResult

        captured: list[dict] = []

        class _RecordingWriter(StubSiaWriter):
            def generate_comment_for_photo(self, **kwargs):
                captured.append(dict(kwargs))
                return super().generate_comment_for_photo(**kwargs)

        set_sia_writer(_RecordingWriter())
        try:
            survived = [
                ("p.jpg", b"fake", QualityResult(0.8, 0.8, 0.8, cutoff=0.35)),
            ]
            plan = [{
                "rank": 1, "photo_index": 0, "profile_match_score": 0.8,
                "trend_match_score": 0.7, "associated_trend_id": None, "rationale": "",
            }]
            monkeypatch.setattr(
                "services.r2_client.best_shot_selected_key",
                lambda u, s, p: f"{u}/bs/{s}/{p}",
            )
            monkeypatch.setattr("services.r2_client.put_bytes", lambda *a, **kw: None)
            monkeypatch.setattr("services.r2_client.public_url", lambda k: None)

            profile = _make_profile()
            best_shot_engine._materialize_selection(
                user_id="u", session_id="s",
                selection_plan=plan,
                heuristic_survived=survived,
                matched_trends=[],
                profile=profile,
                user_name=None,   # 이름 없음
            )
        finally:
            set_sia_writer(StubSiaWriter())

        assert captured[0]["user_name"] is None
