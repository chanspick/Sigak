"""Sia LLM client — Claude Haiku 4.5 per-turn responses (v2 Priority 1 D3).

System prompt: design doc §4-1 완전체. Hard Rules 5건 자동 검증 (REQ-SIA-002a).
Retry: 1회 (prompt cache miss 등 transient 장애). 2회 실패 시 generic fallback.

This module does NOT manage Redis session — caller (routes/sia.py) loads session,
invokes build_messages + call_haiku, then writes back to session.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional

import anthropic

from config import get_settings
from services.sia_validators import SiaValidationError, validate_sia_output


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  System Prompt Template (design doc §4-1)
# ─────────────────────────────────────────────

SIA_SYSTEM_TEMPLATE = """당신은 SIGAK 의 AI 미감 분석가 "Sia" 입니다.

[역할]
- 유저의 미감 추구미와 라이프스타일 맥락을 대화로 파악한다.
- 분석가이다. 관찰자가 아닌 진단자. 데이터에 근거해 단정적으로 서술한다.
- 4지선다 질문을 기본으로, 핵심 필드만 예외적으로 주관식을 허용한다.

[Hard Rules — 위반 시 응답 생성 실패로 간주]
1. "Verdict" 단어 사용 금지. 유저 노출은 "피드 분석" 만 사용한다.
2. "판정" 단어 사용 금지.
3. 마크다운 문법 금지: **bold**, *italic*, ## 헤더, > 인용, ``` 백틱.
4. 리스트 불릿은 "- " 만 허용. "*" / "•" / 숫자 외 스타일 금지.
5. 이모지 절대 금지.

[말투 규칙]
- 서술형 정중체 필수 — "~합니다" / "~습니다" / "~있습니다" / "~인 분입니다"
- 경향 진술 어미 — "~하는 경향이 있습니다" / "~할 가능성이 높습니다"
- 유저 단정문 — "{RESOLVED_NAME_OR_EMPTY}은/는 X 인 분입니다" (질문 X, 확인 X)
- 금지 어미: "~네요", "~같아요", "~거든요", "~이더라고요", "~시더라고요"
- 금지 평가: "좋아 보입니다", "잘 어울립니다", "멋집니다"
- 금지 표현: "본인도 그렇게 생각하세요?", "맞으신가요?", "어떠세요?" 류 확인 요청
- 시적 비유 금지: "봄바람 같은", "햇살처럼"
- 한 턴 2-3 문장 이내 (오프닝만 4 문장 허용)
- 문장당 35자 이내 (한자/라틴 1자로 카운트)

[구조 규칙]
- 턴 구조: 관찰 → 데이터 숫자 → 해석 → 4지선다 질문
- 데이터 숫자는 반드시 실제 수치에서 뽑는다 (아래 [숫자 사용 규칙] 참고)
- em-dash(—) 는 관찰과 데이터 사이 연결에 사용 가능
- 4지선다 선택지는 서로 배타적이고 구체적 상황/감정/맥락 포함

[질문 방식 — 4지선다 중심]
- 기본: 4지선다 + 상황 맥락
- 주관식 허용 필드 (핵심 2개만):
    desired_image (추구미)        — 20자 이내 권장
    current_concerns (현재 고민)  — 30자 이내 권장
- 주관식은 유저가 이미 4지선다로 방향 잡은 후 심화 단계에서 요청

[숫자 사용 규칙 — 신뢰 생명선]
- 구체 숫자 (38장, 68%, 1.4배 등) 는 반드시 실제 데이터에서 뽑는다.
- 데이터 소스:
    1. IG_FEED_SUMMARY.post_count / follower_count
    2. IG_FEED_SUMMARY.current_style_mood 비율 (있을 때만)
    3. 대화 중 유저 선택 통계 (턴 4 이상에서)
- 추정/조작 숫자 금지. 데이터 없으면 숫자 자체 생략.

[유저 호칭 확정]
{NAME_RESOLUTION_RESULT}

[현재까지 추출된 필드]
{COLLECTED_FIELDS_JSON}

[아직 못 채운 필드]
{MISSING_FIELDS_LIST}

[IG 피드 요약]
{IG_FEED_SUMMARY}

[대화 전략]
1. 오프닝: 유저 단정 정의 1문장 + 4지선다 상황 질문
2. 중간 턴: 유저 선택 해석 (데이터 일치/갭) + 다음 4지선다
3. 3-5턴 후 핵심 필드 주관식 심화 (desired_image, current_concerns)
4. 체형 (height/weight/shoulder_width) 대화 후반 (턴 6+)
5. 8 필드 수집 완료 또는 유저 "이만" 의사 → 클로징

[클로징 시 CTA 규칙]
- "시각이 본 나" 한 문장으로 자연 흡수 (별도 섹션/강조 없이)
- 5,000원 + 영구 보관 조건 간결 명시
- CTA 가 억지스러우면 생략하고 그냥 정리 멘트만

[금지 추가]
- LLM 자신을 3인칭으로 지칭 금지
- 사진 요청 금지 (이 단계에선 사진 수집 안 함)
- 메이크업 용어 금지 (립/블러셔/아이섀도 등)
"""


# ─────────────────────────────────────────────
#  Name Resolution Rendering (§0 폴백 체인)
# ─────────────────────────────────────────────

def resolve_name_display(
    *,
    user_name: Optional[str],
    resolved_name: Optional[str],
) -> tuple[str, str]:
    """
    호칭 폴백 체인 §0 규칙:
      1순위: user.name 한글 → "[NAME]님"
      2순위: name 한글 없음 + resolved_name 없음 → 첫 턴에 확인 질문
      3순위: user.name 없음 + resolved_name 없음 → 호칭 생략

    resolved_name 은 2순위 fallback 경로에서 유저 응답으로 획득한 이름.

    Returns:
      (name_display, prompt_instruction)
      name_display: 템플릿 치환용 "[민지]님" / "" / "질문"
      prompt_instruction: SIA_SYSTEM_TEMPLATE 의 {NAME_RESOLUTION_RESULT} 치환 값
    """
    # 1순위
    if user_name and _has_korean(user_name):
        display = f"{user_name}님"
        instruction = f'"{display}" 호칭을 사용한다. 매 응답 첫 등장 시 이 호칭 포함.'
        return display, instruction

    # 2-a: fallback 후 resolved_name 확보됨
    if resolved_name:
        display = f"{resolved_name}님"
        instruction = f'"{display}" 호칭을 사용한다. 매 응답 첫 등장 시 이 호칭 포함.'
        return display, instruction

    # 2-b: 아직 fallback 미진행 (첫 턴)
    if user_name is not None and not _has_korean(user_name):
        instruction = (
            "호칭이 확정되지 않았다. 첫 응답에서 '어떻게 불러드리면 됩니까?' 를 "
            "4지선다 없이 단일 질문으로 묻는다. 이후 턴부터 호칭 적용."
        )
        return "질문", instruction

    # 3순위: 애플 로그인 name 없음
    instruction = (
        "이 유저는 호칭이 없다. 존댓말 유지하되 {NAME}님 형태의 호칭 사용 금지. "
        "주어 생략으로 자연스럽게 서술한다."
    )
    return "", instruction


def _has_korean(s: str) -> bool:
    """한글 음절 또는 한글 자모 1자 이상 포함 여부."""
    return bool(re.search(r"[가-힣ㄱ-ㅎㅏ-ㅣ]", s))


# ─────────────────────────────────────────────
#  Prompt Assembly
# ─────────────────────────────────────────────

def build_system_prompt(
    *,
    user_name: Optional[str],
    resolved_name: Optional[str],
    collected_fields: dict,
    missing_fields: list[str],
    ig_feed_cache: Optional[dict],
) -> str:
    """session_state 로부터 Sia system prompt 완전체 생성."""
    display, instruction = resolve_name_display(
        user_name=user_name, resolved_name=resolved_name,
    )

    ig_summary = _render_ig_summary(ig_feed_cache)
    collected_json = json.dumps(collected_fields or {}, ensure_ascii=False, indent=2)
    missing_str = ", ".join(missing_fields) if missing_fields else "(없음)"

    return SIA_SYSTEM_TEMPLATE.format(
        RESOLVED_NAME_OR_EMPTY=display or "(호칭 생략)",
        NAME_RESOLUTION_RESULT=instruction,
        COLLECTED_FIELDS_JSON=collected_json,
        MISSING_FIELDS_LIST=missing_str,
        IG_FEED_SUMMARY=ig_summary,
    )


def _render_ig_summary(ig_feed_cache: Optional[dict]) -> str:
    """ig_feed_cache dict → LLM-readable summary. None/빈값 시 placeholder."""
    if not ig_feed_cache:
        return "(IG 피드 데이터 없음 — 숫자 사용 금지)"

    scope = ig_feed_cache.get("scope", "unknown")
    if scope == "public_profile_only":
        basics = ig_feed_cache.get("profile_basics", {})
        return (
            f"scope: public_profile_only (비공개 계정)\n"
            f"profile_basics: {json.dumps(basics, ensure_ascii=False)}\n"
            f"피드 수집 불가. 숫자 사용 제한."
        )

    basics = ig_feed_cache.get("profile_basics", {})
    mood = ig_feed_cache.get("current_style_mood") or []
    trajectory = ig_feed_cache.get("style_trajectory") or "(미추출)"
    highlights = ig_feed_cache.get("feed_highlights") or []
    return (
        f"scope: full\n"
        f"profile_basics: {json.dumps(basics, ensure_ascii=False)}\n"
        f"current_style_mood: {json.dumps(mood, ensure_ascii=False)}\n"
        f"style_trajectory: {trajectory}\n"
        f"feed_highlights ({len(highlights)}개):\n"
        + "\n".join(f"- {h}" for h in highlights[:5])
    )


# ─────────────────────────────────────────────
#  Haiku 4.5 Client
# ─────────────────────────────────────────────

_client: Optional[anthropic.Anthropic] = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not configured")
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def reset_client() -> None:
    """테스트 격리 용."""
    global _client
    _client = None


def call_sia_turn(
    *,
    system_prompt: str,
    messages_history: list[dict],
    max_tokens: int = 512,
) -> str:
    """Haiku 4.5 에 1 턴 질의. 응답 텍스트 반환.

    Args:
        system_prompt: build_system_prompt() 결과
        messages_history: [{"role": "user"|"assistant", "content": str}, ...]
            Claude API 포맷. session 의 messages 에서 ts 제거하고 전달.
        max_tokens: Haiku 응답 토큰 상한. 기본 512 (한 턴 3-4 문장 + 4지선다 충분).

    Raises:
        SiaValidationError: Hard Rules 위반 응답. caller 가 retry/fallback 결정.
        anthropic.APIError: 네트워크/API 오류.
    """
    settings = get_settings()
    client = _get_client()

    response = client.messages.create(
        model=settings.anthropic_model_haiku,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=messages_history,
    )

    # Claude response content 는 블록 리스트
    if not response.content:
        raise SiaValidationError("empty Haiku response")

    text_blocks = [b.text for b in response.content if b.type == "text"]
    if not text_blocks:
        raise SiaValidationError("no text block in Haiku response")

    text = "\n".join(text_blocks).strip()

    # Hard Rules 사전 검증 — 위반 시 caller 가 retry
    validate_sia_output(text)
    return text


def call_sia_turn_with_retry(
    *,
    system_prompt: str,
    messages_history: list[dict],
    max_retries: int = 1,
) -> str:
    """검증 실패 시 최대 N회 재시도. 모두 실패하면 generic fallback.

    Generic fallback: "정리에 문제가 있어 잠시만 기다려 주십시오."
    유저 경험 차선책. 운영 로그 남김.
    """
    last_error: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            return call_sia_turn(
                system_prompt=system_prompt,
                messages_history=messages_history,
            )
        except SiaValidationError as e:
            last_error = e
            logger.warning(
                "Sia output validation failed (attempt %d): %s",
                attempt + 1, e,
            )
            continue
        except anthropic.APIError as e:
            last_error = e
            logger.warning("Haiku API error (attempt %d): %s", attempt + 1, e)
            continue

    logger.error("Sia all retries failed: %s", last_error)
    # 운영 알림 + 유저 generic message
    return "정리에 문제가 있어 잠시만 기다려 주십시오."
