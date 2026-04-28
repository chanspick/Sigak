"""유저 메시지 정규식 1단 플래그 추출 (Phase H2a).

PHASE_H_DIRECTIVE §3.1. 0.01s 수준 결정적 플래그. 애매 케이스는 Haiku
응답 생성 단계에서 자연 처리.

9 플래그:
  has_concede          — 맞아요 / 사실 / 그렇긴 해요
  has_emotion_word     — 부담 / 어색 / 힘들 / 속상 / ...
  emotion_word_raw     — 첫 히트 어휘 (EMPATHY_MIRROR 원어 반사용)
  has_tt               — ㅜㅜ / ㅠㅠ
  has_explain_req      — 무슨 얘기 / 뭔 소리 / 이해가 안
  has_meta_challenge   — MBTI 같은 거 / AI 가 / 챗봇 이 / 너 뭔데
  has_evidence_doubt   — 어떻게 알 / 근거 없 / 뭘 보고 / 억지
  has_self_disclosure  — 사실 저 / 실은 / 원래 / 제가 요즘
  is_defensive         — 편해서 / 그냥 / 취향 / 잘 안 찍 / 입어보면
"""
from __future__ import annotations

# ─────────────────────────────────────────────
# v4 QUARANTINE (2026-04-28) — 페르소나 C 시대 코드.
# Phase 3 에서 9 flag → 3 flag (has_self_doubt / has_uncertainty / vault_present)
# 으로 재작성. 시그니처 호환을 위해 기존 9 flag 필드는 보존 (default False) 가능.
# 런타임 보호: SIA_V4_MAINTENANCE=true 시 /sia/* 503 응답.
# Archive: sigak/services/_legacy_persona_c/README.md 참조.
# ─────────────────────────────────────────────

import re

from schemas.sia_state import UserMessageFlags


# ─────────────────────────────────────────────
#  Pattern tables (directive §3.1)
# ─────────────────────────────────────────────

_CONCEDE_PATTERNS = [
    re.compile(r"맞(아요|긴 해요|네요|았어요|죠)"),
    re.compile(r"\b사실\b"),
    re.compile(r"그렇(긴 해요|지|네요)"),
]

# 감정 어휘 — 한글 단어 경계가 모호하므로 원어 포함 체크.
# emotion_word_raw 는 첫 히트 어휘 그대로 저장.
_EMOTION_WORDS = (
    "부담", "어색", "힘들", "속상", "짜증", "귀찮",
    "불편", "무섭", "긴장", "답답", "싫", "피곤",
)

_TT_PATTERN = re.compile(r"[ㅜㅠ]{2,}")

_EXPLAIN_REQ_PATTERNS = [
    re.compile(r"무슨\s*얘기"),
    re.compile(r"뭔\s*소리"),
    re.compile(r"무슨\s*말"),
    re.compile(r"뭐라고"),
    re.compile(r"이해가\s*안"),
    re.compile(r"설명"),
]

_META_CHALLENGE_PATTERNS = [
    re.compile(r"\bMBTI\b", re.IGNORECASE),
    re.compile(r"그런\s*거"),
    re.compile(r"AI\s*가"),
    re.compile(r"챗봇\s*이"),
    re.compile(r"너\s*뭔데"),
    re.compile(r"이런\s*거"),
]

_EVIDENCE_DOUBT_PATTERNS = [
    re.compile(r"어떻게\s*알"),
    re.compile(r"근거\s*없"),
    re.compile(r"뭘\s*보고"),
    re.compile(r"억지"),
    re.compile(r"주관적"),
]

_SELF_DISCLOSURE_PATTERNS = [
    re.compile(r"\b사실\s*저"),
    re.compile(r"\b실은\b"),
    re.compile(r"\b원래\b"),
    re.compile(r"제가\s*(요즘|최근|예전)"),
]

_DEFENSIVE_MARKERS = (
    "편해서", "편하", "취향이", "그냥",
    "잘 안 찍", "어쩌다", "원래 이래",
    "입어보면", "부담스러워", "자신이 없",
)


# ─────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────

def extract_flags(text: str) -> UserMessageFlags:
    """유저 메시지 → UserMessageFlags.

    빈 문자열은 flags 전부 false.
    패턴 간 독립 — 여러 flag 동시에 true 가능.
    """
    flags = UserMessageFlags()
    if not text:
        return flags

    # concede
    flags.has_concede = any(p.search(text) for p in _CONCEDE_PATTERNS)

    # emotion word — 첫 히트 어휘 저장
    for word in _EMOTION_WORDS:
        if word in text:
            flags.has_emotion_word = True
            flags.emotion_word_raw = word
            break

    # ㅜㅜ / ㅠㅠ (2자 이상 연속)
    flags.has_tt = bool(_TT_PATTERN.search(text))

    # explain request
    flags.has_explain_req = any(p.search(text) for p in _EXPLAIN_REQ_PATTERNS)

    # meta challenge
    flags.has_meta_challenge = any(p.search(text) for p in _META_CHALLENGE_PATTERNS)

    # evidence doubt
    flags.has_evidence_doubt = any(p.search(text) for p in _EVIDENCE_DOUBT_PATTERNS)

    # self disclosure
    flags.has_self_disclosure = any(p.search(text) for p in _SELF_DISCLOSURE_PATTERNS)

    # defensive
    flags.is_defensive = any(m in text for m in _DEFENSIVE_MARKERS)

    return flags
