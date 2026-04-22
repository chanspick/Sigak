"""Sia LLM 출력 파서 — body / 4지선다 / mode 분리 (v2 Priority 1 D5).

SIA_SYSTEM_TEMPLATE 이 강제하는 출력 구조:
  - 기본: 서술 + 마지막에 "- X" 4줄 (4지선다)
  - 주관식 턴: 서술만, 마지막 4줄 없음
  - 호칭 fallback 첫 턴: 단일 질문, 4지선다 없음 (routes 에서 mode 오버라이드)

이 모듈은 순수 파싱만 담당한다. name_fallback 판정은 호출부(routes) 에서
`is_name_fallback_turn()` 으로 결정하고 파서 결과를 override 한다.

SPEC: SPEC-ONBOARDING-V2 REQ-SIA-002b (4지선다 기본), REQ-SIA-004 (호칭 폴백).
"""
from __future__ import annotations

import re
from typing import Literal

# 공개 타입 — routes.sia / schemas 에서 재사용
ResponseMode = Literal["choices", "freetext", "name_fallback"]


# ─────────────────────────────────────────────
#  한글 감지 (sia_llm._has_korean 과 동일 로직 재구현)
# ─────────────────────────────────────────────

_KOREAN_RE = re.compile(r"[가-힣ㄱ-ㅎㅏ-ㅣ]")


def _has_korean(s: str) -> bool:
    """한글 음절 또는 자모 1자 이상 포함 여부.

    `sia_llm._has_korean` 과 동일하게 동작한다. 순환 import 회피를 위해 로컬 재정의.
    """
    return bool(s) and bool(_KOREAN_RE.search(s))


# ─────────────────────────────────────────────
#  4지선다 파싱
# ─────────────────────────────────────────────

# 마지막 연속 하이픈 블록 — 각 라인은 "- " (하이픈 + 공백) 으로 시작.
# trailing whitespace 는 허용 (.strip() 전에 매치).
_BULLET_LINE_RE = re.compile(r"^-\s+(.+?)\s*$")


def parse_sia_output(text: str) -> tuple[str, list[str], ResponseMode]:
    """Sia LLM 원문에서 (body, choices, mode) 를 분리한다.

    Rules:
      1. 끝에서부터 연속된 "- " 로 시작하는 라인 탐지 (trailing whitespace 무시).
      2. 정확히 4 라인이면 → mode="choices". body 는 그 4 라인 위 텍스트.
         각 choice 는 "- " 제거 + strip().
      3. 3 또는 5+ 라인이면 → mode="freetext". body=text 원본, choices=[].
      4. 4 라인이지만 사이에 공백 라인 있으면 → 연속 아님 → freetext.
      5. 4 라인이 텍스트 중간에 있으면 (뒤에 다른 서술 있음) → freetext.
      6. name_fallback 은 파서가 결정하지 않음 — 호출부(routes) 책임.

    Args:
        text: Sia LLM raw output (Claude Haiku 응답 텍스트, strip 불필요).

    Returns:
        (body, choices, mode):
            - body: 사용자에게 노출할 본문 (choices 블록 제거).
            - choices: 4지선다 선택지 리스트 (mode="choices" 일 때만 길이 4).
            - mode: "choices" | "freetext".
              name_fallback 은 본 파서가 반환하지 않는다.
    """
    if not text or not text.strip():
        return text, [], "freetext"

    # trailing whitespace 만 제거, leading 은 보존
    stripped = text.rstrip()
    lines = stripped.split("\n")

    # 끝에서부터 연속된 bullet 라인 수집
    trailing_bullets: list[str] = []
    idx = len(lines) - 1
    while idx >= 0:
        line = lines[idx]
        # 빈 줄을 만나면 연속 끊김 → stop (rule 4)
        if not line.strip():
            break
        m = _BULLET_LINE_RE.match(line)
        if not m:
            break
        # bullet 매치 — 역순으로 쌓이므로 prepend
        trailing_bullets.insert(0, m.group(1).strip())
        idx -= 1

    # rule 2: 정확히 4 개 → choices 모드
    if len(trailing_bullets) == 4:
        # body 는 bullet 블록 위 텍스트 (idx 가 마지막 non-bullet 라인 위치)
        body_lines = lines[: idx + 1]
        body = "\n".join(body_lines).rstrip()
        return body, trailing_bullets, "choices"

    # rule 3, 4, 5: 4 가 아니면 전부 freetext, 원문 유지
    return text, [], "freetext"


# ─────────────────────────────────────────────
#  name_fallback 판정 (호출부 책임)
# ─────────────────────────────────────────────

def is_name_fallback_turn(
    *,
    user_has_korean_name: bool,
    resolved_name: str | None,
    turn_count: int,
) -> bool:
    """첫 턴 + 한글 이름 없음 + resolved_name 없음 → name_fallback.

    SPEC: REQ-SIA-004 (WHEN user.name is empty or non-Korean → "어떻게 불러드릴까요?").

    Args:
        user_has_korean_name: `user.name` 이 한글 1자 이상 포함하는가.
        resolved_name: Redis `session_state.resolved_name` (fallback 응답 저장 값).
        turn_count: 유저 발화 턴 카운트 (user 메시지 append 전 값).

    Returns:
        True → 이 턴의 응답은 호칭 확인 단일 질문 (4지선다 없음).
    """
    return turn_count == 0 and not user_has_korean_name and not resolved_name
