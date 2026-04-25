"""Sia 재대화 vault read 주입 — 5 unit cases (spec v1.2 §3-A).

services/sia_prompts_v4.py:
  - _build_context(...) 에 vault_history / user_phrases 주입 루트 검증
  - _format_vault_history_block(history, phrases) 분기 커버

회귀 가드:
  - 첫 진입 유저 (vault None / 모든 list 빈 / phrases 빈) → 섹션 부재 (회귀 0)
  - 다른 4 기능 read-back 코드 무영향 — 본 파일은 prompts_v4 단위 검증만 담당
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schemas.sia_state import (
    ConversationState,
    MsgType,
)
from schemas.user_history import (
    AspirationHistoryEntry,
    BestShotHistoryEntry,
    UserHistory,
    VerdictHistoryEntry,
)
from services.sia_prompts_v4 import (
    _format_vault_history_block,
    load_haiku_prompt,
)


# ─────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────

def _blank_state(*, user_id: str = "u-vault", user_name: str = "만재") -> ConversationState:
    return ConversationState(
        session_id="sess-vault",
        user_id=user_id,
        user_name=user_name,
    )


_VAULT_HEADER = "## 본인 누적 데이터 (재대화 시)"


# ─────────────────────────────────────────────
#  Case 1 — vault history 비어있음 → 섹션 부재
# ─────────────────────────────────────────────

class TestEmptyVaultHistoryNoInjection:
    def test_empty_history_object_returns_empty_block(self):
        # 빈 UserHistory + phrases None → 빈 string
        out = _format_vault_history_block(UserHistory(), None)
        assert out == ""

    def test_none_history_and_no_phrases_returns_empty_block(self):
        out = _format_vault_history_block(None, None)
        assert out == ""

    def test_load_haiku_prompt_no_vault_no_section(self):
        # 회귀 가드 — 기존 호출부 (vault_history 인자 없음) 와 동일 출력
        s = _blank_state()
        prompt = load_haiku_prompt(MsgType.OBSERVATION, s)
        assert _VAULT_HEADER not in prompt

    def test_load_haiku_prompt_empty_history_no_section(self):
        # 명시적으로 빈 history 전달 — phrases 도 빈 → 첫 진입 유저 케이스
        s = _blank_state()
        prompt = load_haiku_prompt(
            MsgType.OBSERVATION, s,
            vault_history=UserHistory(),
            user_phrases=[],
        )
        assert _VAULT_HEADER not in prompt


# ─────────────────────────────────────────────
#  Case 2 — Best Shot 1건만 추가
# ─────────────────────────────────────────────

class TestBestShotOnlyInjection:
    def test_best_shot_one_entry_renders_count_and_overall(self):
        history = UserHistory(
            best_shot_sessions=[
                BestShotHistoryEntry(
                    session_id="bs1",
                    overall_message="피드 톤이 따뜻한 쪽으로 좁혀집니다. 두 번째 사진의 채도가 일관됩니다.",
                ),
            ],
        )
        block = _format_vault_history_block(history, None)
        assert "Best Shot 1회" in block
        assert "피드 추천 0회" in block
        assert "추구미 분석 0회" in block
        # 첫 문장만 노출
        assert "피드 톤이 따뜻한 쪽으로 좁혀집니다" in block
        assert "두 번째 사진의 채도가 일관됩니다" not in block

    def test_best_shot_via_load_haiku_prompt(self):
        s = _blank_state()
        history = UserHistory(
            best_shot_sessions=[
                BestShotHistoryEntry(
                    session_id="bs1",
                    overall_message="고르신 사진 톤이 그쪽으로 가시는가봐요.",
                ),
            ],
        )
        prompt = load_haiku_prompt(
            MsgType.OBSERVATION, s,
            vault_history=history,
        )
        assert _VAULT_HEADER in prompt
        assert "Best Shot 1회" in prompt
        assert "고르신 사진 톤이 그쪽으로 가시는가봐요" in prompt


# ─────────────────────────────────────────────
#  Case 3 — 4 기능 모두 1건씩 + phrases 3개
# ─────────────────────────────────────────────

class TestAllFourCategoriesInjection:
    def test_all_four_categories_with_phrases(self):
        history = UserHistory(
            best_shot_sessions=[
                BestShotHistoryEntry(
                    session_id="bs1",
                    overall_message="Best Shot 종합 한 줄.",
                ),
            ],
            verdict_sessions=[
                VerdictHistoryEntry(
                    session_id="v1",
                    recommendation={
                        "style_direction": "쿨뮤트 유지하면서 채도 살짝 올리기.",
                        "next_action": "후속",
                        "why": "이유",
                    },
                ),
            ],
            aspiration_analyses=[
                AspirationHistoryEntry(
                    analysis_id="a1",
                    source="instagram",
                    gap_narrative="shape 축에서 0.18 차이가 있어요.",
                ),
            ],
        )
        phrases = ["편안한 인상", "거리감 있는", "정돈된 느낌"]
        block = _format_vault_history_block(history, phrases)

        # 카운트
        assert "Best Shot 1회" in block
        assert "피드 추천 1회" in block
        assert "추구미 분석 1회" in block

        # 각 1줄
        assert "쿨뮤트 유지하면서 채도 살짝 올리기" in block
        assert "Best Shot 종합 한 줄" in block
        assert "shape 축에서 0.18 차이가 있어요" in block

        # 자주 쓰는 표현 3개
        assert "편안한 인상" in block
        assert "거리감 있는" in block
        assert "정돈된 느낌" in block


# ─────────────────────────────────────────────
#  Case 4 — phrases 5개 → 상위 3개만
# ─────────────────────────────────────────────

class TestUserPhrasesTopThreeOnly:
    def test_five_phrases_only_first_three_rendered(self):
        history = UserHistory(
            best_shot_sessions=[BestShotHistoryEntry(session_id="bs1")],
        )
        phrases = ["첫째", "둘째", "셋째", "넷째", "다섯째"]
        block = _format_vault_history_block(history, phrases)

        assert "\"첫째\"" in block
        assert "\"둘째\"" in block
        assert "\"셋째\"" in block
        assert "\"넷째\"" not in block
        assert "\"다섯째\"" not in block

    def test_phrases_only_with_no_history_still_renders_section(self):
        # phrases 만 있어도 섹션 트리거. 카운트 0 이지만 phrases 노출.
        block = _format_vault_history_block(UserHistory(), ["원어1"])
        assert "본인 자주 쓰는 표현" in block
        assert "원어1" in block


# ─────────────────────────────────────────────
#  Case 5 — 매우 긴 overall_message 첫 문장 100자 truncate
# ─────────────────────────────────────────────

class TestLongMessageTruncation:
    def test_500char_single_sentence_truncated_to_100(self):
        # 마침표 없는 500자 단일 문자열 (= "한 문장") → 첫 문장 100자 truncate
        long_msg = "가" * 500
        history = UserHistory(
            best_shot_sessions=[
                BestShotHistoryEntry(
                    session_id="bs-long",
                    overall_message=long_msg,
                ),
            ],
        )
        block = _format_vault_history_block(history, None)
        # 추출된 한 줄을 찾아서 길이 확인
        target_line = next(
            (ln for ln in block.split("\n") if ln.startswith("- 최신 Best Shot 종합:")),
            "",
        )
        assert target_line, "Best Shot 종합 라인 없음"
        # prefix '- 최신 Best Shot 종합: ' 길이 = 16
        prefix = "- 최신 Best Shot 종합: "
        body = target_line[len(prefix):]
        assert len(body) <= 100
        # 100자 truncate 시 끝 ellipsis
        assert body.endswith("…")

    def test_phrase_30char_truncate(self):
        # 30자 초과 phrase 는 잘림
        history = UserHistory(
            best_shot_sessions=[BestShotHistoryEntry(session_id="bs1")],
        )
        long_phrase = "가" * 50    # 50자
        block = _format_vault_history_block(history, [long_phrase])
        # phrase 라인 추출
        phrase_line = next(
            (ln for ln in block.split("\n") if ln.startswith("- 본인 자주 쓰는 표현:")),
            "",
        )
        assert phrase_line, "본인 자주 쓰는 표현 라인 없음"
        # 30자 + ellipsis (한자 29자 + …) 형태 — quoted "..."
        assert "…" in phrase_line
        # 50자 원본은 그대로 노출되지 않아야 함
        assert long_phrase not in phrase_line

    def test_total_block_within_500_chars(self):
        # 모든 카테고리 + 긴 메시지 + 3 phrases — 총 블록 ≤ 500자
        long_msg = "가" * 200
        history = UserHistory(
            best_shot_sessions=[BestShotHistoryEntry(
                session_id="bs1", overall_message=long_msg,
            )],
            verdict_sessions=[VerdictHistoryEntry(
                session_id="v1",
                recommendation={"style_direction": "나" * 200, "next_action": "x", "why": "y"},
            )],
            aspiration_analyses=[AspirationHistoryEntry(
                analysis_id="a1", gap_narrative="다" * 200,
            )],
        )
        phrases = ["라" * 50, "마" * 50, "바" * 50]
        block = _format_vault_history_block(history, phrases)
        assert len(block) <= 500, f"block 길이 {len(block)} > 500"
