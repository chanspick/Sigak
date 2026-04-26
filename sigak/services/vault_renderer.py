"""vault → LLM-친화 Korean context dump.

Phase A B-1 (PI-REVIVE 2026-04-26): 옛 SubmitRequest dict 변환 대신
양질의 vault 데이터를 한국어 readable context 로 만들어 LLM 에 직접 주입.

dict 변환 우회 → vault 풍부함 손실 0 + 페르소나 B 톤 보존.

호출 path:
  main.run_analysis_legacy → load_vault → render_vault_context →
  pipeline.llm.interpret_interview / generate_report (vault_context kwarg/ctx key)

설계 원칙:
  1. 빈 vault 시 빈 문자열 반환 (caller 가 vault_has_content 별도 검증).
  2. prompt injection 방어 — markdown special char escape (## 행두 등).
  3. 토큰 예산 budget — max_tokens 초과 시 우선순위 truncate.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from schemas.user_history import (
    AspirationHistoryEntry,
    ConversationHistoryEntry,
    HistoryMessage,
)
from services.user_data_vault import UserDataVault


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────

def vault_has_content(vault: Optional[UserDataVault]) -> bool:
    """vault 가 분석 가능한 최소 데이터 보유 여부.

    기준:
      - vault 객체 자체 존재 + Sia 대화 1건 이상 OR
      - structured_fields 에 desired_image / current_concerns 등 핵심 필드 존재 OR
      - aspiration_history 1건 이상
    Sia onboarding 필수 path 가정 — 정상 흐름이면 conversations 1건 이상 보장.
    """
    if vault is None:
        return False

    convs = vault.user_history.conversations
    if convs and any(c.messages for c in convs):
        return True

    sf = vault.structured_fields or {}
    for key in ("desired_image", "desired_image_keywords", "current_concerns",
                "self_perception", "lifestyle_context", "user_original_phrases"):
        v = sf.get(key)
        if v:
            return True

    if vault.user_history.aspiration_analyses:
        return True

    return False


def render_vault_context(
    vault: Optional[UserDataVault],
    max_tokens: int = 3000,
) -> str:
    """vault → Korean readable LLM context.

    Sections (조건부, 데이터 있을 때만):
      ## Sia 대화 (최근 N턴, OBSERVATION/PROBE/EXTRACTION 위주)
      ## 추구미 분석 이력 (총 M건, IG/Pinterest)
      ## 유저 원어 (taste profile)
      ## Sia 추출 structured_fields

    빈 vault 시 빈 문자열 반환 (caller 가 vault_has_content 별도 검증).

    Args:
        vault: UserDataVault (None 허용)
        max_tokens: 글자 수 기준 상한 (한국어 ≈ 1.5-2자/token, 보수적으로 *4)

    Returns:
        조립된 context 문자열. 빈 vault → "".
    """
    if not vault_has_content(vault):
        return ""

    # Section 우선순위 — 가장 중요한 것부터. budget 초과 시 끝부터 자름.
    sections: list[tuple[str, str]] = []  # (section_id, rendered_text)

    sia_section = _render_sia_conversations(vault)
    if sia_section:
        sections.append(("sia_conversations", sia_section))

    phrases_section = _render_user_phrases(vault)
    if phrases_section:
        sections.append(("user_phrases", phrases_section))

    aspiration_section = _render_aspiration_history(vault)
    if aspiration_section:
        sections.append(("aspiration_history", aspiration_section))

    structured_section = _render_structured_fields(vault)
    if structured_section:
        sections.append(("structured_fields", structured_section))

    # 토큰 예산 — 글자 수 *4 이 token 상한 (한국어 보수적). 초과 시 우선순위 낮은 끝부터 drop.
    char_budget = max_tokens * 4
    final_parts: list[str] = []
    used_chars = 0
    for section_id, text in sections:
        if used_chars + len(text) > char_budget:
            # 더 넣으면 초과 — drop. 디버그 로그.
            logger.debug(
                "vault_renderer: budget hit, dropping section=%s (used=%d, would_add=%d, budget=%d)",
                section_id, used_chars, len(text), char_budget,
            )
            continue
        final_parts.append(text)
        used_chars += len(text) + 2  # \n\n separator

    return "\n\n".join(final_parts)


# ─────────────────────────────────────────────
#  Section renderers
# ─────────────────────────────────────────────

# Sia 대화에서 우선 노출할 메시지 타입 — Phase H 4단 리듬 핵심.
_PRIORITY_MSG_TYPES: set[str] = {
    "observation", "interpretation", "diagnosis",
    "probe", "extraction", "confrontation",
    "recognition",  # Phase H 변형 호환
}

_RECENT_TURNS_LIMIT: int = 6   # 최근 N턴 user+sia 쌍
_MAX_MESSAGES_PER_SESSION: int = 10  # 세션당 최대 노출
_MAX_SESSIONS: int = 2  # 최근 세션 N개


def _render_sia_conversations(vault: UserDataVault) -> str:
    """Sia 대화 최근 세션 + 우선 메시지 타입 위주 렌더.

    가장 최근 (head) 세션부터 _MAX_SESSIONS 개. 세션당 최대
    _MAX_MESSAGES_PER_SESSION 메시지. priority msg_type 우선.
    """
    convs = vault.user_history.conversations
    if not convs:
        return ""

    out_lines: list[str] = []
    sessions_to_show = convs[:_MAX_SESSIONS]
    total_msgs = sum(len(c.messages) for c in convs)

    out_lines.append(f"## Sia 대화 (총 {total_msgs}턴, 최근 {len(sessions_to_show)}세션 노출)")

    for sess in sessions_to_show:
        if not sess.messages:
            continue
        ts_label = _fmt_dt(sess.started_at) or "시점 미상"
        out_lines.append("")
        out_lines.append(f"### 세션 {ts_label}")

        # priority msg_type 메시지 + 그 직전 user 메시지를 페어로
        rendered = _render_session_messages(sess)
        out_lines.extend(rendered)

    return "\n".join(out_lines).strip()


def _render_session_messages(sess: ConversationHistoryEntry) -> list[str]:
    """1 세션의 메시지를 user-Sia 페어로 렌더. priority msg_type 우선.

    전략:
      - assistant 메시지 중 priority msg_type 있으면 모두 노출
      - 그 외 일반 메시지는 turn order 보존하여 중요 user 발화 + sia 응답 추출
      - max _MAX_MESSAGES_PER_SESSION 개
    """
    msgs = sess.messages
    out: list[str] = []
    shown = 0

    # 인덱스별 priority 점수 — sia priority msg_type 메시지 + 그 직전 user
    priority_idx: set[int] = set()
    for i, m in enumerate(msgs):
        if m.role == "assistant" and (m.msg_type or "").lower() in _PRIORITY_MSG_TYPES:
            priority_idx.add(i)
            if i > 0 and msgs[i - 1].role == "user":
                priority_idx.add(i - 1)

    # priority 가 너무 적으면 마지막 _RECENT_TURNS_LIMIT*2 개로 fallback
    if len(priority_idx) < 4:
        # 최근 메시지 우선
        recent_count = min(_RECENT_TURNS_LIMIT * 2, len(msgs))
        for i in range(len(msgs) - recent_count, len(msgs)):
            priority_idx.add(i)

    for i, m in enumerate(msgs):
        if shown >= _MAX_MESSAGES_PER_SESSION:
            break
        if i not in priority_idx:
            continue
        rendered = _render_message_line(m)
        if rendered:
            out.append(rendered)
            shown += 1

    return out


def _render_message_line(m: HistoryMessage) -> str:
    """메시지 1건 → 한 줄 (user/Sia + msg_type label + content)."""
    role_label = "유저" if m.role == "user" else "Sia"
    msg_type = (m.msg_type or "").strip()
    content = _sanitize_for_prompt(m.content or "")
    if not content.strip():
        return ""
    if msg_type and m.role == "assistant":
        return f"- {role_label} ({msg_type}): {content}"
    return f"- {role_label}: {content}"


def _render_aspiration_history(vault: UserDataVault) -> str:
    """추구미 분석 이력 — 최근 entries narrative 위주.

    각 entry: 좌표 / gap / Sia narrative. narrative 가 가장 정보 밀도 높음.
    """
    entries = vault.user_history.aspiration_analyses
    if not entries:
        return ""

    out_lines: list[str] = [f"## 추구미 분석 이력 (총 {len(entries)}건)"]

    for entry in entries[:5]:  # 최근 5건
        ts_label = _fmt_dt(entry.created_at) or "시점 미상"
        source_label = "IG" if entry.source == "instagram" else "Pinterest"
        target = (entry.target_handle or "").strip() or "(타겟 미상)"
        out_lines.append("")
        out_lines.append(f"### {ts_label} · {source_label} · {target}")

        # 좌표 정보 (있으면)
        coord_line = _render_aspiration_coords(entry)
        if coord_line:
            out_lines.append(coord_line)

        # narrative — 가장 중요. Sia 톤 보존.
        narr = (entry.gap_narrative or "").strip()
        if narr:
            out_lines.append(f"갭: {_sanitize_for_prompt(narr)}")
        sia_msg = (entry.sia_overall_message or "").strip()
        if sia_msg:
            out_lines.append(f"Sia 종합: {_sanitize_for_prompt(sia_msg)}")

    return "\n".join(out_lines).strip()


def _render_aspiration_coords(entry: AspirationHistoryEntry) -> str:
    """aspiration_vector_snapshot 의 좌표 정보 한 줄 요약."""
    snap = entry.aspiration_vector_snapshot
    if not isinstance(snap, dict):
        return ""

    parts: list[str] = []
    primary_axis = snap.get("primary_axis")
    primary_delta = snap.get("primary_delta")
    if primary_axis and primary_delta is not None:
        try:
            parts.append(f"primary={primary_axis} {float(primary_delta):+.2f}")
        except (TypeError, ValueError):
            pass

    sec_axis = snap.get("secondary_axis")
    sec_delta = snap.get("secondary_delta")
    if sec_axis and sec_delta is not None:
        try:
            parts.append(f"secondary={sec_axis} {float(sec_delta):+.2f}")
        except (TypeError, ValueError):
            pass

    if not parts:
        return ""
    return f"갭 벡터: {', '.join(parts)}"


def _render_user_phrases(vault: UserDataVault) -> str:
    """structured_fields.user_original_phrases 또는 핵심 필드에서 추출한 유저 발화 원어.

    R2 원칙 — 리포트 재활용 키워드. bullet list.
    """
    sf = vault.structured_fields or {}
    phrases: list[str] = []

    raw_phrases = sf.get("user_original_phrases")
    if isinstance(raw_phrases, list):
        for p in raw_phrases:
            if isinstance(p, str) and p.strip():
                phrases.append(p.strip())

    # 보강 — 빈 경우 핵심 자유 텍스트 필드 echo
    if not phrases:
        for key in ("desired_image", "current_concerns", "self_perception",
                    "lifestyle_context", "specific_context"):
            v = sf.get(key)
            if isinstance(v, str) and v.strip():
                phrases.append(v.strip())
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, str) and item.strip():
                        phrases.append(item.strip())

    if not phrases:
        return ""

    # 중복 제거 (순서 보존) + 길이 cap
    seen: set[str] = set()
    unique: list[str] = []
    for p in phrases:
        if p in seen:
            continue
        seen.add(p)
        unique.append(p)
        if len(unique) >= 12:
            break

    out_lines = ["## 유저 원어 (taste profile)"]
    for p in unique:
        out_lines.append(f"- {_sanitize_for_prompt(p)}")
    return "\n".join(out_lines)


def _render_structured_fields(vault: UserDataVault) -> str:
    """Sia 추출 structured_fields 한국어 라벨 + 값.

    user_phrases 와 중복되는 자유 텍스트 필드는 생략. enum / 분류 필드 위주.
    """
    sf = vault.structured_fields or {}
    if not sf:
        return ""

    label_map = [
        ("reference_style", "참고 스타일"),
        ("height", "키"),
        ("weight", "체중"),
        ("shoulder_width", "어깨"),
    ]

    out_lines: list[str] = []
    for key, label in label_map:
        v = sf.get(key)
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        if isinstance(v, list):
            joined = ", ".join(str(x).strip() for x in v if str(x).strip())
            if not joined:
                continue
            out_lines.append(f"- {label}: {_sanitize_for_prompt(joined)}")
        else:
            out_lines.append(f"- {label}: {_sanitize_for_prompt(str(v))}")

    # desired_image_keywords 별도 (list 형식 가능)
    kw = sf.get("desired_image_keywords")
    if isinstance(kw, list) and kw:
        joined = ", ".join(str(x).strip() for x in kw if str(x).strip())
        if joined:
            out_lines.append(f"- 추구 키워드: {_sanitize_for_prompt(joined)}")

    if not out_lines:
        return ""

    return "## Sia 추출 (structured_fields)\n" + "\n".join(out_lines)


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _fmt_dt(dt: Optional[datetime]) -> Optional[str]:
    """datetime → "YYYY-MM-DD HH:MM" 형식."""
    if dt is None:
        return None
    try:
        return dt.strftime("%Y-%m-%d %H:%M")
    except (AttributeError, ValueError):
        return None


def _sanitize_for_prompt(text: str) -> str:
    """user-supplied 텍스트의 markdown 특수 문자 / prompt injection 위험 패턴 escape.

    - 행두 ## / ### → "  ##" (공백 prefix)
    - --- (구분선) → " ---"
    - ``` (코드 블록) → " ``"
    - 개행 다중 → 단일 공백 (LLM 노이즈 절약)
    """
    if not text:
        return ""
    s = text.strip()
    # 개행 정규화 — 메시지 1줄로 압축 (LLM 컨텍스트 가독성)
    s = " ".join(s.split())

    # markdown header injection 차단
    if s.startswith("##"):
        s = " " + s
    if s.startswith("---"):
        s = " " + s
    if s.startswith("```"):
        s = s.replace("```", "``", 1)

    return s
