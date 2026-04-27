"""SiaWriter — 페르소나 B 공통 출력 레이어.

CLAUDE.md §4.7 정의 + 본인 확정 2026-04-24 Best Shot 품질 강화:
  - "정세현" 하드코딩 제거 — user_name 동적 주입
  - Haiku 4.5 실 호출 (HaikuSiaWriter)
  - A-17/A-20/markdown validator wrap (sia_validators_v4)
  - 다양성 강제 — sibling_comments 로 중복 회피

Protocol 은 기존 caller 호환성을 위해 user_name / sibling_comments
kwargs 를 Optional 로 추가.
"""
from __future__ import annotations

import base64
import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Optional, Protocol, runtime_checkable

from schemas.aspiration import MatchedTrendView
from schemas.user_taste import UserTasteProfile
from services.coordinate_system import GapVector
from services.sia_validators_v4 import (
    check_a17_commerce,
    check_a18_length,
    check_a20_abstract_praise,
    check_markdown_markup,
)


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Protocol
# ─────────────────────────────────────────────

@runtime_checkable
class SiaWriter(Protocol):
    """페르소나 B (친근 비서) 출력 생성 인터페이스.

    모든 메서드는 CLAUDE.md §6.2 어미 규칙 준수:
      허용: ~가봐요? / ~이신 것 같은데 / ~으시죠? / ~이시잖아요 / ~이에요 / ~습니다
      금지: ~네요(?) / ~군요 / ~같아요 / ~같습니다 / ~것 같 / ~수 있습니다 / ~더라구요

    A-17 영업 어휘 / A-20 추상 칭찬어 / 마크다운 강조 금지.
    생성 실패 시 fallback 은 각 구현체가 처리 (예외 raise 지양).
    """

    def generate_comment_for_photo(
        self,
        *,
        photo_url: str,
        photo_context: dict,
        profile: UserTasteProfile,
        persona_hint: Optional[str] = None,
        user_name: Optional[str] = None,
        sibling_comments: Optional[list[str]] = None,
    ) -> str:
        """사진 1장에 대한 Sia 한 줄 해석. 1-2 문장, 80자 이내 지향."""
        ...

    def generate_overall_message(
        self,
        *,
        profile: UserTasteProfile,
        context: dict,
        user_name: Optional[str] = None,
    ) -> str:
        """리포트 전체를 감싸는 Sia 종합 멘트. 2-4 문장."""
        ...

    def render_boundary_message(
        self,
        *,
        profile: UserTasteProfile,
        public_count: int,
        locked_count: int,
        user_name: Optional[str] = None,
    ) -> str:
        """PI 공개/잠금 경계 카피."""
        ...

    def generate_aspiration_overall(
        self,
        *,
        profile: UserTasteProfile,
        gap_vector: GapVector,
        target_display_name: str,
        target_analysis_snapshot: Optional[dict] = None,
        user_analysis_snapshot: Optional[dict] = None,
        matched_trends: Optional[list] = None,
        user_name: Optional[str] = None,
        photo_pairs: Optional[list[dict]] = None,
    ) -> dict:
        """추구미 비교 narrative 생성 — JSON dict 반환 (Phase J5).

        Phase J6 ux: user_analysis_snapshot 추가 — 본인 IgFeedAnalysis dump.
        prompt 안 [본인 분석 신호] 블록으로 도출 근거 풀어쓰기 컨텍스트 제공.

        반환 키:
          overall_message / gap_summary / action_hints
          raw_haiku_response (휘발 방지)
          matched_trends_used
        """
        ...

    def generate_pi_overall(
        self,
        *,
        profile: UserTasteProfile,
        components: dict,
        user_name: Optional[str] = None,
    ) -> str:
        """PI 9 컴포넌트 조립 결과 → 종합 메시지 한 단락 (Phase I STEP 8).

        톤: 리포트체 (~있어요/~세요). Sia 친밀체와 Verdict 정중체와 분리.
        Hard Rules: A-17 / A-20 / markdown / 톤 어미 / 길이 350자.
        """
        ...

    def generate_trend_card_narrative(
        self,
        *,
        trend: MatchedTrendView,
        profile: UserTasteProfile,
        gap_vector: Optional[GapVector] = None,
        user_name: Optional[str] = None,
    ) -> str:
        """KB 트렌드 → 유저 결 + 갭에 맞춘 1-2 문장 narrative (Phase J6).

        원본 detailed_guide 가 [score: ...] 메타 + 미디어 인용 등 raw 형식이라
        직출 부적합. profile + gap + trend 컨텍스트로 personalized narrative.
        실패 시 _sanitize_trend_guide() fallback (raw 메타만 제거).
        """
        ...


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

_FALLBACK_COMMENT = "이 장은 차분하게 담겼어요"
_FALLBACK_OVERALL = "피드에서 드러난 결을 따라 골랐어요"
_GENERIC_NAME = "이분"                          # user_name 없을 때 마지막 폴백


def _collect_violations(text: str) -> list[str]:
    """A-17 / A-20 / markdown hard reject 대상 통합."""
    out: list[str] = []
    out.extend(check_a17_commerce(text))
    out.extend(check_a20_abstract_praise(text))
    out.extend(check_markdown_markup(text))
    return out


# ─────────────────────────────────────────────
#  Trend card guide sanitization (Phase J6)
#
#  KB YAML detailed_guide 첫 줄 [score: ±X / 라벨] 메타 프리픽스 제거.
#  의도: KB 는 LLM 컨텍스트로 score 메타 보존, 사용자 화면엔 노출 차단.
#  LLM personalize fallback 에서도 사용 — graceful degrade 보장.
# ─────────────────────────────────────────────

_TREND_SCORE_PREFIX = re.compile(r"^\s*\[score:[^\]]*\]\s*\n?", re.MULTILINE)


def _sanitize_trend_guide(text: str) -> str:
    """KB detailed_guide 의 [score: ±X / 라벨] 메타 프리픽스 제거.

    LLM personalize 실패 시 graceful fallback 으로 사용. 화면엔 raw 메타
    절대 노출 안 됨을 보장.
    """
    if not text:
        return ""
    return _TREND_SCORE_PREFIX.sub("", text).strip()


def _name_honorific(user_name: Optional[str]) -> str:
    """user_name 을 호명형으로 변환. 빈 문자열이면 '이분'."""
    name = (user_name or "").strip()
    if not name:
        return _GENERIC_NAME
    # 이미 '님' 붙어있으면 그대로
    if name.endswith("님"):
        return name
    return f"{name}님"


# ─────────────────────────────────────────────
#  Aspiration 전용 헬퍼 (Phase J5 — vault 5/5 풀 활용)
# ─────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_aspiration_system_prompt() -> str:
    """prompts/haiku_aspiration/base.md 로딩 (1회 캐시)."""
    path = (
        Path(__file__).resolve().parent.parent
        / "prompts" / "haiku_aspiration" / "base.md"
    )
    return path.read_text(encoding="utf-8")


def _render_taste_profile_slim(profile: UserTasteProfile) -> dict:
    """Verdict v2 _render_taste_profile() 패턴 — 5 필드 + Phase I latest_pi dump.

    Phase I — Backward echo: latest_pi 키 추가. Aspiration / Sia / 다른 sia_writer
    호출 path 모두 자동 carry. 첫 진입 (latest_pi=None) 회귀 0 — None dump.
    상품명 직접 호명 금지는 caller (prompt build) 책임 — 본 dump 는 raw.
    """
    dump = profile.model_dump(mode="json")
    return {
        "current_position": dump.get("current_position"),
        "aspiration_vector": dump.get("aspiration_vector"),
        "conversation_signals": dump.get("conversation_signals"),
        "user_original_phrases": dump.get("user_original_phrases"),
        "latest_pi": dump.get("latest_pi"),
        "strength_score": dump.get("strength_score"),
    }


def _summarize_target_snapshot(snap: Optional[dict]) -> str:
    """target_analysis_snapshot 핵심만 요약 — prompt 길이 폭주 방지."""
    if not snap:
        return "(target Vision 분석 없음 — gap_vector 만으로 narrative)"
    parts: list[str] = []
    for key in (
        "tone_category", "mood", "color_palette",
        "style_consistency", "pose_frequency",
    ):
        v = snap.get(key)
        if v is None:
            continue
        if isinstance(v, float):
            parts.append(f"{key}: {v:.2f}")
        elif isinstance(v, (int, str)):
            parts.append(f"{key}: {str(v)[:80]}")
        else:
            parts.append(f"{key}: {str(v)[:80]}")
    return "\n".join(parts) if parts else "(요약 가능 필드 없음)"


def _summarize_matched_trends(trends: Optional[list]) -> str:
    """matched_trends → 짧은 요약 (트렌드 ID + title + 첫 hint)."""
    if not trends:
        return "(KB 매칭 트렌드 없음)"
    lines: list[str] = []
    for t in trends[:5]:
        if isinstance(t, dict):
            tid = t.get("trend_id") or "(no_id)"
            title = (t.get("title") or "").strip()
            hints = t.get("action_hints") or []
        else:
            tid = getattr(t, "trend_id", None) or "(no_id)"
            title = (getattr(t, "title", None) or "").strip()
            hints = getattr(t, "action_hints", None) or []
        first_hint = (hints[0] if hints else "").strip() if isinstance(hints, list) else ""
        lines.append(f"- [{tid}] {title} | hint: {first_hint}")
    return "\n".join(lines) if lines else "(매칭 정보 추출 실패)"


def _build_aspiration_fallback(
    *,
    honor: str,
    target_display_name: str,
    gap_vector: GapVector,
    profile: UserTasteProfile,
) -> dict:
    """Haiku 실패 시 deterministic fallback — 페르소나 B + A-17/A-20 통과."""
    primary_axis = gap_vector.primary_axis
    overall = (
        f"{honor} 본인 피드와 {target_display_name} 쪽 결을 같이 봤어요. "
        f"{primary_axis} 축에서 가장 큰 갭이 보여요. "
        "지금 데이터로는 여기까지 또렷해요. "
        "조금씩 더 쓰시면 결이 더 잡히실 거예요."
    )
    gap_short = f"{primary_axis} 축에서 갭이 가장 크고 그 결로 한 칸 이동해보시는 거잖아요."
    hints = [
        f"{primary_axis} 쪽 시도 한 컷을 다음 피드에 넣어보세요",
        "추구미 사진의 톤을 한 번 비교해보세요",
        "다음 분석 때 다시 짚어드릴게요",
    ]
    return {
        "overall_message": overall,
        "gap_summary": gap_short,
        "action_hints": hints,
    }


def _parse_aspiration_response(raw: str, fallback: dict) -> dict:
    """Haiku JSON 응답 파싱 — 실패 시 fallback dict copy."""
    if not raw:
        return dict(fallback)
    text = raw.strip()
    # ```json wrapper 제거
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        parsed = json.loads(text)
    except Exception:
        logger.warning(
            "aspiration JSON parse failed — fallback. raw=%r", text[:120],
        )
        return dict(fallback)
    if not isinstance(parsed, dict):
        return dict(fallback)
    overall = str(parsed.get("overall_message") or fallback["overall_message"])
    gap_summary = str(parsed.get("gap_summary") or fallback["gap_summary"])
    raw_hints = parsed.get("action_hints") or fallback["action_hints"]
    if not isinstance(raw_hints, list):
        raw_hints = fallback["action_hints"]
    hints = [str(h).strip() for h in raw_hints if str(h).strip()][:5]
    return {
        "overall_message": overall,
        "gap_summary": gap_summary,
        "action_hints": hints,
    }


def _collect_violations_aspiration(text: str) -> list[str]:
    """Aspiration JSON 응답 검증 — A-17/A-18/A-20/markdown 4종 통합.

    JSON 파싱 후 user-facing 텍스트만 검증.
    A-18 length 는 overall_message 단독 (300자 hard).
    A-17/A-20/markdown 은 overall+gap+hints 합집합 (영업/추상 어디든 0건).
    파싱 실패 시 raw 전체 검증 (A-18 제외 — 길이 폭주 방지).
    """
    try:
        clean = text.strip()
        if clean.startswith("```"):
            lines = clean.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            clean = "\n".join(lines).strip()
        parsed = json.loads(clean)
    except Exception:
        parsed = None

    out: list[str] = []
    if isinstance(parsed, dict):
        overall = str(parsed.get("overall_message") or "")
        gap_summary = str(parsed.get("gap_summary") or "")
        hints_raw = parsed.get("action_hints") or []
        if isinstance(hints_raw, list):
            hints_text = " ".join(str(h) for h in hints_raw if str(h).strip())
        else:
            hints_text = ""
        full_user_facing = "\n".join([overall, gap_summary, hints_text]).strip()
        out.extend(check_a17_commerce(full_user_facing))
        out.extend(check_a20_abstract_praise(full_user_facing))
        out.extend(check_markdown_markup(full_user_facing))
        out.extend(check_a18_length(overall))
    else:
        out.extend(check_a17_commerce(text))
        out.extend(check_a20_abstract_praise(text))
        out.extend(check_markdown_markup(text))
    return out


# ─────────────────────────────────────────────
#  PI 리포트 전용 헬퍼 (Phase I — STEP 8)
# ─────────────────────────────────────────────

_HAIKU_PI_OVERALL_SYSTEM = """당신은 SIGAK PI (시각이 본 당신) 리포트 종합 메시지 생성기.

역할:
  PI 9 컴포넌트 조립 결과를 짧게 종합한 한 단락 (3-4 문장, 200-300자) 을 생성합니다.

톤 (리포트체) — Sia 친밀체와 분리, Verdict 정중체와도 분리:
  허용 어미: ~있어요 / ~세요 / ~예요 / ~보여요 / ~인 편이에요
  금지 (Sia 친밀체): ~잖아요 / ~더라구요 / ~이시잖아요 / ~인가봐요?
  금지 (Verdict 정중체): ~합니다 / ~할 수 있습니다
  금지 (흐림/감탄): ~네요 / ~군요 / ~같아요 / ~것 같

Hard Rules (validator hard reject):
  - 영업 어휘 0건 (가격 / 토큰 / 결제 / 상품명 / "추천해드릴" / "구독" / "리포트로" / "컨설팅")
  - 추상 칭찬어 0건 (매력 / 독특 / 특별 / 흥미 / 인상적 / 센스 / 안목 / 감각이 있)
  - 마크다운 0건 (* / ** / ## / > / 코드블록 / bullet / list / 이모지)

호명: user_name 1-2회. 이름 다음 쉼표(',') 뒤 문장 시작 X.

객관 뷰티 어휘 PI 한정 허용 (얼굴형 / 광대 / 비율 / 피부 톤 / 분석).

다른 기능 직접 호명 금지 — "Verdict v2" / "Best Shot" / "추구미 분석" 어휘 그대로 X.
대신 "지난번" / "이미 보셨던" / "전에 짚어드린" 자연 우회.

출력: 한 단락 텍스트만. JSON / 따옴표 / 설명 / 마크다운 wrapper 없음."""


def _collect_violations_pi_report(text: str) -> list[str]:
    """PI 리포트체 전용 검증 — A-17/A-20/markdown + 톤 어미 + 길이 (350자 hard).

    Sia 친밀체 어미 (~잖아요/~더라구요) + Verdict 정중체 (~합니다) 차단.
    PI 한정 허용 어휘 (분석 / 얼굴형 / 비율) 허용.
    """
    out: list[str] = []
    out.extend(check_a17_commerce(text))
    out.extend(check_a20_abstract_praise(text))
    out.extend(check_markdown_markup(text))

    bad_endings = (
        "잖아요", "더라구요", "이시잖아요", "인가봐요",
        "합니다", "할 수 있습니다", "할 수 있어요",
        "네요.", "네요!", "네요?", "군요", "같아요", "같습니다", "것 같",
    )
    for ending in bad_endings:
        if ending in text:
            out.append(f"PI 톤 위반: '{ending}' 발견")
            break

    if len(text) > 350:
        out.append(f"PI 길이 초과: {len(text)}자 (max 350)")

    return out


def _build_pi_overall_fallback(
    *,
    honor: str,
    components: dict,
) -> str:
    """PI overall Haiku 실패 시 deterministic fallback. 톤 + Hard Rules 통과."""
    cover_content = (
        components.get("cover", {}).get("content", {})
        if isinstance(components.get("cover"), dict) else {}
    )
    type_ref_content = (
        components.get("type_reference", {}).get("content", {})
        if isinstance(components.get("type_reference"), dict) else {}
    )
    gap_content = (
        components.get("gap_analysis", {}).get("content", {})
        if isinstance(components.get("gap_analysis"), dict) else {}
    )

    matched_label = (type_ref_content.get("matched_label") or "").strip()
    primary_direction = (gap_content.get("primary_direction") or "").strip()

    parts: list[str] = []
    honor_part = f"{honor} " if honor else ""
    parts.append(f"{honor_part}정면 분석과 vault 데이터로 정리해드린 결과예요.")
    if matched_label:
        parts.append(f"매칭 결과는 {matched_label} 쪽이 가장 가까웠어요.")
    if primary_direction:
        parts.append(f"방향은 {primary_direction} 쪽으로 또렷하게 보여요.")
    parts.append("조금 더 쓰시면 더 또렷해져요.")

    return " ".join(parts).strip()


# ─────────────────────────────────────────────
#  Stub 구현 — 테스트/오프라인 전용 (Haiku 호출 없음)
# ─────────────────────────────────────────────

class StubSiaWriter:
    """Haiku 호출 없이 템플릿 응답만 반환. 테스트 / 로컬 개발 전용.

    A-17 / A-20 / markdown 위반 없이 유저 이름만 동적으로 치환.
    """

    def generate_comment_for_photo(
        self,
        *,
        photo_url: str,
        photo_context: dict,
        profile: UserTasteProfile,
        persona_hint: Optional[str] = None,
        user_name: Optional[str] = None,
        sibling_comments: Optional[list[str]] = None,
    ) -> str:
        rank = photo_context.get("rank")
        if rank == 1:
            return "이 장이 가장 또렷하게 드러나요"
        return "같은 결 안에서 고른 장이에요"

    def generate_overall_message(
        self,
        *,
        profile: UserTasteProfile,
        context: dict,
        user_name: Optional[str] = None,
    ) -> str:
        honor = _name_honorific(user_name)
        selected = context.get("selected_count", 0)
        uploaded = context.get("uploaded_count", 0)
        return (
            f"{honor} 올려주신 {uploaded}장 중 {selected}장 골랐어요. "
            "피드에서 드러난 결을 따라 골랐어요"
        )

    def render_boundary_message(
        self,
        *,
        profile: UserTasteProfile,
        public_count: int,
        locked_count: int,
        user_name: Optional[str] = None,
    ) -> str:
        honor = _name_honorific(user_name)
        return (
            f"{honor} 시각이 본 건 여기까지 펼쳐드렸어요. "
            f"나머지 {locked_count}장은 더 쓰실수록 정교해져요"
        )

    def generate_aspiration_overall(
        self,
        *,
        profile: UserTasteProfile,
        gap_vector: GapVector,
        target_display_name: str,
        target_analysis_snapshot: Optional[dict] = None,
        user_analysis_snapshot: Optional[dict] = None,
        matched_trends: Optional[list] = None,
        user_name: Optional[str] = None,
        photo_pairs: Optional[list[dict]] = None,
    ) -> dict:
        """Stub — Haiku 미호출. deterministic fallback dict + raw 자리 채움."""
        honor = _name_honorific(user_name)
        fallback = _build_aspiration_fallback(
            honor=honor,
            target_display_name=target_display_name,
            gap_vector=gap_vector,
            profile=profile,
        )
        return {
            **fallback,
            "raw_haiku_response": "",   # stub: Haiku 미호출
            "matched_trends_used": list(matched_trends or []),
        }

    def generate_pi_overall(
        self,
        *,
        profile: UserTasteProfile,
        components: dict,
        user_name: Optional[str] = None,
    ) -> str:
        """Stub — PI overall fallback (Haiku 미호출). 톤 + Hard Rules 통과."""
        honor = _name_honorific(user_name)
        return _build_pi_overall_fallback(honor=honor, components=components)

    def generate_trend_card_narrative(
        self,
        *,
        trend: MatchedTrendView,
        profile: UserTasteProfile,
        gap_vector: Optional[GapVector] = None,
        user_name: Optional[str] = None,
    ) -> str:
        """Stub — KB raw [score: ...] 프리픽스만 제거. LLM 호출 없음.

        deterministic fallback. 테스트 / 로컬 / API 키 미설정 환경 안전.
        """
        sanitized = _sanitize_trend_guide(trend.detailed_guide or "")
        return sanitized or trend.title


# ─────────────────────────────────────────────
#  Haiku 실 호출 구현
# ─────────────────────────────────────────────

_HAIKU_PHOTO_SYSTEM = """당신은 SIGAK 서비스의 Sia — 유저 피드 결을 짚어주는 친근한 비서입니다.

역할:
  유저가 올린 사진 중 선별된 한 장에 대해 1-2 문장 짧은 코멘트를 씁니다.

톤 (페르소나 B 친밀체):
  허용 어미: ~이에요 / ~이시네 / ~인가봐요? / ~이시잖아요 / ~이세요
  금지 어미: ~것 같아요 / ~인 것 같습니다 / ~할 수 있습니다 / ~군요 / ~더라구요

Hard Rules (전수 금지):
  - 영업 어휘: "다음 단계" / "정리해드릴" / "추천해드릴" / "핵심 포인트" /
    "리포트" / "컨설팅" / "구독" / "티어" / "프리미엄" /
    "진단에서" / "진단을" / "진단으로" / 가격 수치 전부
  - 추상 칭찬어: "매력적" / "매력(이/을/있)" / "독특한" / "특별한" /
    "흥미로운" / "인상적" / "센스 있" / "안목" / "감각이 있"
  - 마크다운: `*`, `**`, `##`, `>`, ``` 전부 금지 (순수 텍스트)
  - 이름 다음 ',' 뒤 문장 시작 금지 (자연스럽게 연결)
  - 80자 이내, 1-2 문장

다양성:
  이미 다른 사진 코멘트를 쓴 경우 어미 / 관점 중복 피하세요.
  "같은 결" 반복 금지 — 각 사진 고유 관찰로 진입.

출력: 한 줄 텍스트만. JSON / 따옴표 / 설명 없음."""


_HAIKU_OVERALL_SYSTEM = """당신은 SIGAK 의 Sia — 유저 사진 선별 결과를 종합 정리합니다.

역할:
  여러 장 사진 중 선별한 결과를 2-4 문장으로 정리. 유저 피드의 결 + 골라낸 기준.

톤 (페르소나 B):
  허용 어미: ~이에요 / ~이시네 / ~인가봐요? / ~이시잖아요 / ~이세요
  금지 어미: ~것 같아요 / ~것 같습니다 / ~할 수 있습니다 / ~군요 / ~더라구요

Hard Rules:
  - 영업 어휘 전수 금지 (컨설팅 / 리포트 / 구독 / 추천해드릴 등)
  - 추상 칭찬 금지 (매력 / 독특 / 특별 / 센스 / 감각이 있)
  - 마크다운 금지 (`*`, `**` 등 전부)
  - 200자 이내

유저 호명: 주어진 user_name 만 사용. 예시 이름 금지.

출력: 한 단락 텍스트만. JSON / 따옴표 / 설명 없음."""


_HAIKU_TREND_CARD_SYSTEM = """당신은 SIGAK 의 Sia — 유저 미감 결을 짚어주는 친근한 비서입니다.

역할:
  KB 트렌드 정보 + 유저 taste_profile + gap_vector 를 받아, 이 트렌드가 유저
  결과 어떻게 연결되는지 1-2 문장으로 자연스럽게 풀어 씁니다.

톤 (페르소나 B 친밀체):
  허용 어미: ~이에요 / ~이시네 / ~인가봐요? / ~이시잖아요 / ~이세요
  금지 어미: ~것 같아요 / ~것 같습니다 / ~할 수 있습니다 / ~군요 / ~더라구요

[Hard Rules — 출력 절대 금지]
  - 숫자 일체: 좌표값 (+0.30 등) / score / 백분율 / 연도 외 수치
  - 메타 표기: [score: ±X / 라벨] / 화살표 (→ ↘ ▲) / 이모지 (🔥 등)
  - 미디어 인용 라벨: 'Allure ~' / 'Vogue ~' 등 패션 매거진 명시 인용
  - 내부 좌표 용어 (소비자 ux 가드):
    · 축 이름: shape / volume / age (영문) / 형태 / 부피 / 인상 (한글 그대로)
    · 정성 라벨: 소프트 / 샤프 / 프레시 / 성숙 / 평면 / 입체 / 베이비 / 매추어
    · → "어른스러운" / "산뜻한" / "또렷한" / "부드러운" 등 일상 형용사로 풀어 표현
  - 영업 어휘: "다음 단계" / "정리해드릴" / "추천해드릴" / "핵심 포인트" /
    "리포트" / "컨설팅" / "구독" / "티어" / "프리미엄" / 가격 수치 전부
  - 추상 칭찬어: "매력적" / "독특한" / "특별한" / "흥미로운" / "인상적" /
    "센스 있" / "안목" / "감각이 있"
  - 마크다운: `*`, `**`, `##`, `>`, ``` 전부 (순수 텍스트)
  - KB 가이드 그대로 복사 금지 — 정보를 흡수해 새 narrative 생성

[내용 가이드]
  - "이 트렌드는 ~" 보다 "@호명 결에는 ~" 식 유저 중심 톤
  - 본인 결 (taste_profile) 과 추구미 갭 (gap_vector) 양쪽 맥락 반영
  - 1-2 문장, 50자 ~ 130자 범위 지향
  - 호명 1회만 (있을 때)

출력: 텍스트만. JSON / 따옴표 / 설명 / 인용부호 없음."""


def _fetch_image_for_haiku(
    url: str, *, timeout: float = 8.0,
) -> Optional[tuple[str, str]]:
    """이미지 URL → (base64_str, media_type). 실패 시 None.

    Anthropic Vision 의 image source "base64" 형식 호환. R2 / IG / Pinterest
    CDN 등 외부 URL 어느 것이든 동일 처리. fetch 실패는 caller graceful
    degrade 책임 — image 없이 "사진 보고" system 으로 호출하면 Haiku 가
    "죄송하지만..." 응답할 가능성이 높아, caller 는 즉시 fallback 권장.
    """
    try:
        import httpx
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            ct = (
                resp.headers.get("content-type", "image/jpeg")
                .split(";")[0].strip().lower()
            )
            if not ct.startswith("image/"):
                ct = "image/jpeg"
            data = base64.standard_b64encode(resp.content).decode("ascii")
            return data, ct
    except Exception:
        logger.warning("haiku image fetch failed: %s", url, exc_info=True)
        return None


class HaikuSiaWriter:
    """Haiku 4.5 실 호출 SiaWriter. 생성 후 validator wrap + 1회 재시도.

    실패 3회 (validator hard reject 2회 + API 에러 1회) 시 deterministic fallback.
    API 키 미설정 / 네트워크 에러 시도 StubSiaWriter 대체 경로.
    """

    def __init__(self, fallback: Optional[SiaWriter] = None):
        self._fallback = fallback or StubSiaWriter()

    def generate_comment_for_photo(
        self,
        *,
        photo_url: str,
        photo_context: dict,
        profile: UserTasteProfile,
        persona_hint: Optional[str] = None,
        user_name: Optional[str] = None,
        sibling_comments: Optional[list[str]] = None,
    ) -> str:
        rank = photo_context.get("rank") or 1
        rationale = (photo_context.get("rationale") or "").strip()
        honor = _name_honorific(user_name)

        sibling_block = ""
        if sibling_comments:
            recent = sibling_comments[-5:]
            joined = "\n".join(f"- {c}" for c in recent if c)
            if joined:
                sibling_block = (
                    "\n이미 쓴 코멘트들 (어미/관점 중복 피하기):\n" + joined
                )

        user_prompt = (
            f"[선별 rank] {rank}\n"
            f"[유저 호명] {honor}\n"
            f"[Sonnet rationale] {rationale or '(없음)'}\n"
            f"[profile 요약] "
            f"strength={profile.strength_score:.2f}, "
            f"evidence={len(profile.preference_evidence)}"
            f"{sibling_block}\n\n"
            "위 정보로 이 한 장 사진 코멘트 1-2 문장 씁니다. "
            "유저 호명은 1회만. rank 1 은 가장 좋은 컷이라는 맥락 반영."
        )

        text = self._call_with_retry(
            system=_HAIKU_PHOTO_SYSTEM,
            user_prompt=user_prompt,
            max_tokens=160,
            fallback_text=_FALLBACK_COMMENT,
            image_url=photo_url,
        )
        return text

    def generate_overall_message(
        self,
        *,
        profile: UserTasteProfile,
        context: dict,
        user_name: Optional[str] = None,
    ) -> str:
        honor = _name_honorific(user_name)
        selected = context.get("selected_count", 0)
        uploaded = context.get("uploaded_count", 0)
        product = context.get("product", "best_shot")

        user_prompt = (
            f"[유저 호명] {honor}\n"
            f"[상품] {product}\n"
            f"[업로드] {uploaded}장\n"
            f"[선별] {selected}장\n"
            f"[profile 요약] "
            f"strength={profile.strength_score:.2f}, "
            f"evidence={len(profile.preference_evidence)}\n\n"
            "위 정보로 선별 종합 메시지 2-4 문장 씁니다. "
            "유저 호명 1-2회. 숫자 자연스럽게."
        )

        text = self._call_with_retry(
            system=_HAIKU_OVERALL_SYSTEM,
            user_prompt=user_prompt,
            max_tokens=400,
            fallback_text=self._fallback.generate_overall_message(
                profile=profile, context=context, user_name=user_name,
            ),
        )
        return text

    def render_boundary_message(
        self,
        *,
        profile: UserTasteProfile,
        public_count: int,
        locked_count: int,
        user_name: Optional[str] = None,
    ) -> str:
        # Boundary 는 규칙 강하게 고정된 영역 — Haiku 호출 하지 않고 템플릿.
        return self._fallback.render_boundary_message(
            profile=profile,
            public_count=public_count,
            locked_count=locked_count,
            user_name=user_name,
        )

    def generate_aspiration_overall(
        self,
        *,
        profile: UserTasteProfile,
        gap_vector: GapVector,
        target_display_name: str,
        target_analysis_snapshot: Optional[dict] = None,
        user_analysis_snapshot: Optional[dict] = None,
        matched_trends: Optional[list] = None,
        user_name: Optional[str] = None,
        photo_pairs: Optional[list[dict]] = None,
    ) -> dict:
        """Aspiration 비교 narrative — Haiku 4.5 + 페르소나 B + 5 필드 + JSON.

        Phase J6 ux: user_analysis_snapshot 추가 — 본인 IgFeedAnalysis dump.
        prompt 안 [본인 분석 신호] 블록으로 도출 근거 풀어쓰기 컨텍스트 제공.

        반환 키:
          overall_message / gap_summary / action_hints
          raw_haiku_response (휘발 방지 — 원본 문자열 보존)
          matched_trends_used (활용한 KB 트렌드 list)
        """
        honor = _name_honorific(user_name)
        slim = _render_taste_profile_slim(profile)
        target_summary = _summarize_target_snapshot(target_analysis_snapshot)
        # 동일 헬퍼 — 본인 IgFeedAnalysis 도 같은 키 셋 (tone/pose/consistency 등).
        user_summary = _summarize_target_snapshot(user_analysis_snapshot)
        trends_summary = _summarize_matched_trends(matched_trends)
        gap_n = gap_vector.narrative()
        pair_n = len(photo_pairs or [])

        user_prompt = (
            f"[유저 호명] {honor}\n"
            f"[추구미 대상] {target_display_name}\n\n"
            f"[taste_profile slim — 5 필드]\n"
            f"{json.dumps(slim, ensure_ascii=False, indent=2)}\n\n"
            f"[gap_vector]\n"
            f"  primary: {gap_vector.primary_axis} "
            f"{gap_vector.primary_delta:+.2f}\n"
            f"  secondary: {gap_vector.secondary_axis} "
            f"{gap_vector.secondary_delta:+.2f}\n"
            f"  tertiary: {gap_vector.tertiary_axis} "
            f"{gap_vector.tertiary_delta:+.2f}\n"
            f"  narrative_hint: {gap_n}\n\n"
            f"[본인 사진 분석 신호 — 도출 근거 풀어쓰기 컨텍스트]\n"
            f"{user_summary}\n\n"
            f"[추구미 사진 분석 신호 — 도출 근거 풀어쓰기 컨텍스트]\n"
            f"{target_summary}\n\n"
            f"[matched_trends — KB 매칭]\n{trends_summary}\n\n"
            f"[photo_pairs 수] {pair_n}\n\n"
            "위 정보로 본인 피드 ↔ 추구미 비교 narrative 를 JSON 으로 출력. "
            "본인 / 추구미 양쪽 사진 분석 신호 (톤 / 포즈 / 일관성 / 무드 등) 를 "
            "일상어로 풀어 도출 근거를 narrative 안에 녹여 설득력 확보. "
            "raw 필드명 / 영문 라벨 / 숫자는 컨텍스트로만 활용, 출력 0건. "
            "키: overall_message / gap_summary / action_hints. "
            "JSON 외 텍스트 / 마크다운 wrapper 절대 금지."
        )

        fallback_dict = _build_aspiration_fallback(
            honor=honor,
            target_display_name=target_display_name,
            gap_vector=gap_vector,
            profile=profile,
        )
        fallback_text = json.dumps(fallback_dict, ensure_ascii=False)

        raw = self._call_with_retry(
            system=_load_aspiration_system_prompt(),
            user_prompt=user_prompt,
            max_tokens=600,
            fallback_text=fallback_text,
            validator=_collect_violations_aspiration,
        )

        parsed = _parse_aspiration_response(raw, fallback_dict)
        parsed["raw_haiku_response"] = raw   # 휘발 방지
        parsed["matched_trends_used"] = list(matched_trends or [])
        return parsed

    def generate_pi_overall(
        self,
        *,
        profile: UserTasteProfile,
        components: dict,
        user_name: Optional[str] = None,
    ) -> str:
        """PI overall — Haiku 4.5 + 페르소나 리포트체 + validator 검증 wrap.

        실패 시 deterministic fallback (Stub 동일 결과). raw text R2 영구 보존은
        caller (pi_engine.generate_pi_report_v1) 영역. 본 메서드는 final text 반환.
        """
        honor = _name_honorific(user_name)

        cover_c = (
            components.get("cover", {}).get("content", {})
            if isinstance(components.get("cover"), dict) else {}
        )
        type_c = (
            components.get("type_reference", {}).get("content", {})
            if isinstance(components.get("type_reference"), dict) else {}
        )
        gap_c = (
            components.get("gap_analysis", {}).get("content", {})
            if isinstance(components.get("gap_analysis"), dict) else {}
        )
        action_c = (
            components.get("action_plan", {}).get("content", {})
            if isinstance(components.get("action_plan"), dict) else {}
        )

        user_phrases = profile.user_original_phrases or []
        signals = getattr(profile, "conversation_signals", None)
        signals_dump: Optional[dict] = None
        if signals is not None:
            try:
                signals_dump = (
                    signals.model_dump(mode="json")
                    if hasattr(signals, "model_dump") else dict(signals)
                )
            except Exception:
                signals_dump = None

        prompt_lines = [
            f"[유저 호명] {honor}",
            f"[cover headline] {cover_c.get('headline', '')}",
            f"[cover subhead] {cover_c.get('subhead', '')}",
            f"[matched type] {type_c.get('matched_label', '')} | "
            f"{type_c.get('matched_one_liner', '')}",
            f"[primary axis] {gap_c.get('primary_axis', '')}",
            f"[primary direction] {gap_c.get('primary_direction', '')}",
            f"[primary action] {action_c.get('primary_action', '')}",
            f"[strength_score] {profile.strength_score:.2f}",
        ]
        if user_phrases:
            prompt_lines.append(
                f"[vault user_phrases] "
                f"{json.dumps(user_phrases[:5], ensure_ascii=False)}"
            )
        if signals_dump:
            prompt_lines.append(
                f"[signals 요약] "
                f"{json.dumps(signals_dump, ensure_ascii=False)[:300]}"
            )
        prompt_lines.append(
            "\n위 9 컴포넌트 정리 결과를 PI 리포트 종합 한 단락 "
            "(3-4 문장, 200-300자) 으로 정리합니다. "
            "리포트체 (~있어요/~세요). 호명 1-2회. JSON 아닌 순수 텍스트."
        )

        user_prompt = "\n".join(prompt_lines)
        fallback_text = _build_pi_overall_fallback(
            honor=honor, components=components,
        )

        return self._call_with_retry(
            system=_HAIKU_PI_OVERALL_SYSTEM,
            user_prompt=user_prompt,
            max_tokens=500,
            fallback_text=fallback_text,
            validator=_collect_violations_pi_report,
        )

    def generate_trend_card_narrative(
        self,
        *,
        trend: MatchedTrendView,
        profile: UserTasteProfile,
        gap_vector: Optional[GapVector] = None,
        user_name: Optional[str] = None,
    ) -> str:
        """KB 트렌드 → 유저 결 + 갭 personalized 1-2 문장 narrative.

        분석 시점 1회 호출 → matched_trends_snapshot 동결. 재조회 시 LLM 0건.
        실패 시 _sanitize_trend_guide() fallback ([score: ...] 프리픽스 제거).
        """
        honor = _name_honorific(user_name)
        raw_guide = (trend.detailed_guide or "").strip()
        sanitized_for_context = _sanitize_trend_guide(raw_guide) or raw_guide
        action_hints_str = (
            " / ".join((trend.action_hints or [])[:3]) or "(없음)"
        )
        profile_slim = _render_taste_profile_slim(profile)

        gap_block = ""
        if gap_vector is not None:
            gap_block = (
                "\n[gap_vector — 추구미 이동 방향]\n"
                f"  primary axis: {gap_vector.primary_axis}\n"
                f"  secondary axis: {gap_vector.secondary_axis}\n"
                f"  narrative_hint: {gap_vector.narrative()}\n"
            )

        user_prompt = (
            f"[유저 호명] {honor}\n\n"
            f"[트렌드]\n"
            f"  제목: {trend.title}\n"
            f"  카테고리: {trend.category}\n"
            f"  KB 가이드 (컨텍스트 - 메타/인용/숫자 노출 금지):\n"
            f"{sanitized_for_context}\n"
            f"  action_hints: {action_hints_str}\n\n"
            f"[유저 taste_profile slim]\n"
            f"{json.dumps(profile_slim, ensure_ascii=False, indent=2)}\n"
            f"{gap_block}\n"
            "위 정보로 이 트렌드가 유저 본인 결 + 추구미 갭과 어떻게 연결되는지 "
            "1-2 문장 narrative 씁니다. 호명 1회. KB 가이드 raw 안 [score: ...] / "
            "이모지 / 미디어 인용 / 숫자는 컨텍스트로만 활용하고 출력엔 절대 노출 "
            "금지. 80~130자 범위 지향."
        )

        # Fallback: sanitize 결과 (raw 메타 제거된 KB 텍스트). 그것도 빈값이면 title.
        fallback = sanitized_for_context or trend.title

        return self._call_with_retry(
            system=_HAIKU_TREND_CARD_SYSTEM,
            user_prompt=user_prompt,
            max_tokens=240,
            fallback_text=fallback,
        )

    # ─────────────────────────────────────────────
    #  internal — Haiku 호출 + validator wrap
    # ─────────────────────────────────────────────

    def _call_with_retry(
        self,
        *,
        system: str,
        user_prompt: str,
        max_tokens: int,
        fallback_text: str,
        max_retries: int = 1,
        validator: Optional[Callable[[str], list[str]]] = None,
        image_url: Optional[str] = None,
    ) -> str:
        """Haiku 호출 → validator 검증 → 위반 시 1회 재시도 → fallback.

        validator default: _collect_violations (A-17/A-20/markdown).
        Aspiration 등 다른 영역은 validator 인자로 전용 검증 함수 주입 가능.
        image_url 주어지면 백엔드 fetch + base64 → Vision image block 첨부.
        fetch 실패 시 "사진 보고" system 과 충돌 위험 → 즉시 fallback 반환.
        API 키 / 네트워크 / JSON 에러 전부 fallback 으로 수렴. 예외 raise 안 함.
        """
        _validator = validator or _collect_violations

        try:
            from services.sia_llm import _get_client
            from config import get_settings
        except Exception:
            logger.warning("Haiku writer deps unavailable — fallback")
            return fallback_text

        try:
            settings = get_settings()
            if not getattr(settings, "anthropic_api_key", None):
                return fallback_text
            client = _get_client()
        except Exception:
            logger.warning("Haiku client init failed — fallback", exc_info=True)
            return fallback_text

        # image_url 있으면 Vision input 첨부 — fetch+base64.
        # fetch 실패 = "사진 보고" system 과 충돌 ("죄송하지만 사진..." 응답
        # 위험) → 즉시 fallback 반환. validator 가 못 잡는 형식이라 명시 차단.
        message_content: Any
        if image_url:
            fetched = _fetch_image_for_haiku(image_url)
            if fetched is None:
                logger.info(
                    "image fetch failed → fallback (url=%s)", image_url[:80],
                )
                return fallback_text
            b64_data, media_type = fetched
            message_content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": b64_data,
                    },
                },
                {"type": "text", "text": user_prompt},
            ]
        else:
            message_content = user_prompt

        last_text = ""
        for attempt in range(max_retries + 1):
            try:
                response = client.messages.create(
                    model=settings.anthropic_model_haiku,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": message_content}],
                )
            except Exception:
                logger.warning(
                    "Haiku API error (attempt %d)", attempt + 1, exc_info=True,
                )
                continue

            if not response.content:
                continue
            text_blocks = [b.text for b in response.content if b.type == "text"]
            text = "\n".join(text_blocks).strip()
            if not text:
                continue
            last_text = text

            violations = _validator(text)
            if not violations:
                return text
            logger.warning(
                "SiaWriter hard-reject attempt %d: %s",
                attempt + 1, violations,
            )
        logger.error(
            "SiaWriter all retries failed — fallback. last=%r",
            last_text[:120],
        )
        return fallback_text


# ─────────────────────────────────────────────
#  Default writer registry
# ─────────────────────────────────────────────

_default_writer: SiaWriter = StubSiaWriter()


def get_sia_writer() -> SiaWriter:
    """현재 활성 SiaWriter 반환. 테스트에서 set_sia_writer 로 교체 가능."""
    return _default_writer


def set_sia_writer(writer: SiaWriter) -> None:
    """의존성 주입."""
    global _default_writer
    _default_writer = writer


def use_haiku_writer() -> None:
    """운영 환경 초기화 — 기본 writer 를 HaikuSiaWriter 로 교체."""
    set_sia_writer(HaikuSiaWriter())


# ─────────────────────────────────────────────
#  Sia Finale — SPEC-PI-FINALE-001
#
#  PI 레포트 끝의 종합 마무리. Sonnet 1회 호출 → 6 필드 JSON.
#  Card 1 (headline + lead_paragraph) + Card 2 (4-step) 데이터 소스.
#  페르소나 B 친밀체 + ~이에요 톤. 1000~1500자 총합.
# ─────────────────────────────────────────────


# Sia 친밀체 어미 검증 — finale 은 Sia 1인칭 친밀체 (PI 분석체와 다름)
_FINALE_BAD_ENDINGS = (
    "더라구요",          # CLAUDE.md 4e2b225 폐기
    "네요.", "네요!", "네요?", "네요\n",
    "군요.", "군요!", "군요?", "군요\n",
    "같아요", "같습니다",
    "것 같",
    "수 있습니다", "수 있어요",
)

# 데이터 숫자 노출 차단 — "0.42 좌표" 같은 표현 금지
_NUMERIC_LEAK_PATTERNS = [
    re.compile(r"\b0\.\d{2,}"),                # 0.42, 0.123 등
    re.compile(r"\b-0\.\d+"),                  # -0.5 등
    re.compile(r"좌표\s*[0-9.]+"),             # "좌표 0.5"
    re.compile(r"type_\d+"),                   # type_3 같은 내부 ID
    re.compile(r"trend_id|trend_[a-z_0-9]+"),  # trend ID 노출
]


# 폴백 카피 — Sonnet 모든 재시도 실패 시 사용 (페르소나 B + Hard Rules 통과)
FALLBACK_FINALE: dict = {
    "headline": "오늘의 좌표, 시각이 잡아드렸어요.",
    "lead_paragraph": (
        "이번 분석에서 가장 또렷하게 보였던 건 당신 본인의 결이에요. "
        "지금 자리에서 추구하는 쪽으로 옮겨가는 길이 생각보다 가깝게 잡혀요. "
        "조금 더 쓰시면 더 정교해질 거예요. 우선 이번 분석으로 길을 잡아두시면 좋아요."
    ),
    "step_1_observation": (
        "정면 사진과 대화에서 모은 데이터를 같이 봤어요. "
        "골격, 분위기, 인상의 결이 일관되게 한 방향으로 모여 있어요. "
        "본인이 모르고 계셨을 만한 강점이 분명히 있어요."
    ),
    "step_2_interpretation": (
        "이건 약점이 아니라 시그니처예요. "
        "지금의 결을 살리면서 추구하는 인상에 가깝게 다가갈 수 있어요. "
        "출발점이 좋은 편이에요."
    ),
    "step_3_diagnosis": (
        "추구하는 쪽으로 가려면 한 축에 집중하시는 게 효과적이에요. "
        "여러 군데 손대기보다 가장 가까운 거리부터 좁히세요. "
        "다음 분석에서 변화가 분명하게 보일 거예요."
    ),
    "step_4_closing": (
        "오늘 길은 잡혔어요. 이제 한 걸음씩 옮겨가시면 돼요. "
        "다음 번엔 어떤 결이 될지 시각이 또 봐드릴게요."
    ),
}


def _check_finale_persona_b(finale: "SiaFinale") -> list[str]:
    """페르소나 B 친밀체 어미 검증. 위반 1개 이상이면 list 에 사유 적재."""
    out: list[str] = []
    fields = (
        ("headline", finale.headline),
        ("lead_paragraph", finale.lead_paragraph),
        ("step_1_observation", finale.step_1_observation),
        ("step_2_interpretation", finale.step_2_interpretation),
        ("step_3_diagnosis", finale.step_3_diagnosis),
        ("step_4_closing", finale.step_4_closing),
    )
    for name, text in fields:
        for ending in _FINALE_BAD_ENDINGS:
            if ending in text:
                out.append(f"{name}: 금지 어미 '{ending}'")
                break
    return out


def _check_finale_numeric_leak(finale: "SiaFinale") -> list[str]:
    """데이터 숫자/내부 ID 본문 노출 차단."""
    out: list[str] = []
    fields = (
        ("headline", finale.headline),
        ("lead_paragraph", finale.lead_paragraph),
        ("step_1_observation", finale.step_1_observation),
        ("step_2_interpretation", finale.step_2_interpretation),
        ("step_3_diagnosis", finale.step_3_diagnosis),
        ("step_4_closing", finale.step_4_closing),
    )
    for name, text in fields:
        for pattern in _NUMERIC_LEAK_PATTERNS:
            if pattern.search(text):
                out.append(f"{name}: 숫자/ID 노출 ({pattern.pattern})")
                break
    return out


def _strip_json_fence(text: str) -> str:
    """Sonnet 이 ```json ... ``` 래핑하면 제거."""
    t = text.strip()
    if t.startswith("```"):
        lines = t.split("\n")
        if len(lines) > 1:
            lines = lines[1:]
        while lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t


_FINALE_SYSTEM_PROMPT = """당신은 SIGAK 의 미감 분석 페르소나 'Sia' 입니다. 페르소나 B (간파하는 친근 비서).
유저의 PI(개인 시각 정체성) 레포트 마지막에 들어갈 종합 마무리를 작성합니다.

## 톤 규칙 (HARD)
- 허용 어미: ~이에요 / ~이신 것 같은데 / ~으시죠? / ~이시잖아요 / ~습니다
- 금지 어미: ~네요 / ~군요 / ~같아요 / ~같습니다 / ~것 같 / ~수 있습니다 / ~더라구요
- 호칭: '당신' 으로 일관 사용
- 한국어. 영어 표현 최소화 (필요한 고유명사만).

## 컨텐츠 규칙 (HARD)
- 좌표 숫자 (예 "0.42") / 내부 type_id / trend_id 본문에 노출 금지
- 마크다운 (**굵게**, _기울임_, # 헤딩) 금지 — 순수 텍스트
- 영업 어휘 ('지금 구매', '한정 할인', '전문가') 금지
- 추상 칭찬 ('완벽해요', '환상적이에요', '대단해요') 금지
- 데이터에서 추론 가능한 사실만 서술. 거짓 추측 금지.

## 출력 형식 (반드시 6 필드 JSON, 다른 텍스트 X)
```json
{
  "headline": "<8~50자, 시그니처 한 줄. 듣고 싶은 말, 강한 인상>",
  "lead_paragraph": "<150~350자, 핵심 단락. OBSERVATION+INTERPRETATION 융합. 유저 본인 발화 자연 인용 가능>",
  "step_1_observation": "<120~250자, '관찰' — 시각이 본 것. 데이터 근거.>",
  "step_2_interpretation": "<120~250자, '해석' — 그게 의미하는 것. 재프레임/강점.>",
  "step_3_diagnosis": "<150~350자, '진단' — 추구미 가는 길. 핵심 1-2개로 압축.>",
  "step_4_closing": "<80~200자, '다음 한 걸음' — action_plan 1개로 매듭. 격려.>"
}
```

## 결 (마케터 의도)
- 파인 다이닝 디저트. 식사 끝의 인상적인 마무리.
- 듣고 싶은 말 해주는 결. 다정함 + 정교함.
- 단정짓지 않고 짚어주는 톤.
- 1000~1500자 총합. 모바일 1~2화면.
"""


def _build_finale_user_prompt(
    *,
    user_data: dict,
    finale_inputs: dict,
) -> str:
    """8 input 데이터 → user prompt 한국어 자연어 풀어쓰기.

    finale_inputs 키:
      face_structure, skin, type_match, gap_analysis,
      aspiration_history, verdict_history, user_original_phrases, action_plan
    각 값은 dict 또는 list. None 이면 해당 섹션 생략.
    """
    user_name = (user_data or {}).get("name") or "당신"
    gender = (user_data or {}).get("gender") or "미정"

    sections: list[str] = []
    sections.append(f"[유저 기본]\n이름: {user_name}\n성별: {gender}")

    # 1. 얼굴 구조
    face = finale_inputs.get("face_structure")
    if face:
        sections.append("[1. 얼굴 구조]")
        sections.append(json.dumps(face, ensure_ascii=False, indent=2))

    # 2. Skin
    skin = finale_inputs.get("skin")
    if skin:
        sections.append("[2. 피부/스킨]")
        sections.append(json.dumps(skin, ensure_ascii=False, indent=2))

    # 3. Type Match
    type_match = finale_inputs.get("type_match")
    if type_match:
        sections.append("[3. 8-타입 매칭]")
        sections.append(json.dumps(type_match, ensure_ascii=False, indent=2))

    # 4. Gap Analysis
    gap = finale_inputs.get("gap_analysis")
    if gap:
        sections.append("[4. 추구미 갭]")
        sections.append(json.dumps(gap, ensure_ascii=False, indent=2))

    # 5. 누적 추구미
    asp_hist = finale_inputs.get("aspiration_history") or []
    if asp_hist:
        sections.append(f"[5. 누적 추구미 분석 ({len(asp_hist)} 건)]")
        sections.append(json.dumps(asp_hist[:5], ensure_ascii=False, indent=2))

    # 6. Verdict 누적
    vdc = finale_inputs.get("verdict_history") or []
    if vdc:
        sections.append(f"[6. 피드 분석 누적 ({len(vdc)} 건)]")
        sections.append(json.dumps(vdc[:5], ensure_ascii=False, indent=2))

    # 7. Sia 대화 — 유저 본인 발화 (인용 권장)
    phrases = finale_inputs.get("user_original_phrases") or []
    if phrases:
        sections.append("[7. 유저 본인 발화 (Sia 대화에서)]")
        for p in phrases[:8]:
            sections.append(f"- \"{p}\"")
        sections.append(
            "위 발화 중 1개 이하를 lead_paragraph 에 자연스럽게 인용하세요."
        )

    # 8. Action Plan
    action = finale_inputs.get("action_plan")
    if action:
        sections.append("[8. 실행 가이드]")
        sections.append(json.dumps(action, ensure_ascii=False, indent=2))

    sections.append(
        "\n---\n위 8개 데이터를 모두 종합해서 6 필드 JSON 만 응답하세요. "
        "JSON 외 다른 텍스트 (설명, 머리말, 마크다운 코드블록) 금지."
    )

    return "\n\n".join(sections)


def generate_finale(
    *,
    user_data: dict,
    finale_inputs: dict,
    max_retries: int = 2,
) -> dict:
    """Sia Finale 생성 — Sonnet 1회 호출. SPEC-PI-FINALE-001.

    Args:
        user_data: {"name": str, "gender": str}
        finale_inputs: 8 input dict (face_structure, skin, type_match,
            gap_analysis, aspiration_history, verdict_history,
            user_original_phrases, action_plan).
            None/빈 값은 해당 섹션 자동 생략.
        max_retries: 페르소나/JSON 검증 실패 시 동일 프롬프트 재시도 횟수.

    Returns:
        SiaFinale 6 필드 dict + generated_at ISO datetime.
        모든 재시도 실패 시 FALLBACK_FINALE 반환 (예외 raise 안 함).
    """
    # lazy import (config / anthropic 모듈 의존성 우회)
    from datetime import datetime, timezone

    from schemas.sia_finale import SiaFinale

    try:
        import anthropic
        from config import get_settings
        from services.sia_llm import _get_client
    except Exception as e:
        logger.warning("finale deps unavailable — fallback (%s)", e)
        result = dict(FALLBACK_FINALE)
        result["generated_at"] = datetime.now(timezone.utc).isoformat()
        return result

    try:
        settings = get_settings()
        if not getattr(settings, "anthropic_api_key", None):
            logger.warning("ANTHROPIC_API_KEY not configured — finale fallback")
            result = dict(FALLBACK_FINALE)
            result["generated_at"] = datetime.now(timezone.utc).isoformat()
            return result
        client = _get_client()
    except Exception:
        logger.warning("finale client init failed — fallback", exc_info=True)
        result = dict(FALLBACK_FINALE)
        result["generated_at"] = datetime.now(timezone.utc).isoformat()
        return result

    user_prompt = _build_finale_user_prompt(
        user_data=user_data, finale_inputs=finale_inputs,
    )

    last_error: Optional[str] = None
    for attempt in range(max_retries + 1):
        try:
            response = client.messages.create(
                model=settings.anthropic_model_sonnet,
                max_tokens=2048,
                system=_FINALE_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except anthropic.APIError as e:
            logger.warning("finale API error (attempt %d): %s", attempt + 1, e)
            last_error = f"api: {e}"
            continue
        except Exception as e:
            logger.warning("finale unknown error (attempt %d): %s", attempt + 1, e)
            last_error = f"unknown: {e}"
            continue

        if not response.content:
            last_error = "empty response"
            continue
        text_blocks = [b.text for b in response.content if b.type == "text"]
        text = "\n".join(text_blocks).strip()
        if not text:
            last_error = "no text block"
            continue

        text = _strip_json_fence(text)

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning("finale JSON parse fail (attempt %d): %s", attempt + 1, e)
            last_error = f"json: {e}"
            continue

        try:
            finale = SiaFinale(**data)
        except Exception as e:
            logger.warning("finale schema fail (attempt %d): %s", attempt + 1, e)
            last_error = f"schema: {e}"
            continue

        # 페르소나 B 어미 검증
        persona_violations = _check_finale_persona_b(finale)
        if persona_violations:
            logger.warning(
                "finale persona violations (attempt %d): %s",
                attempt + 1, persona_violations,
            )
            last_error = f"persona: {persona_violations}"
            continue

        # 데이터 숫자 노출 검사
        numeric_violations = _check_finale_numeric_leak(finale)
        if numeric_violations:
            logger.warning(
                "finale numeric leak (attempt %d): %s",
                attempt + 1, numeric_violations,
            )
            last_error = f"numeric: {numeric_violations}"
            continue

        # 통과
        result = finale.model_dump()
        result["generated_at"] = datetime.now(timezone.utc).isoformat()
        logger.info(
            "finale generated OK (attempt %d, headline=%r)",
            attempt + 1, finale.headline[:40],
        )
        return result

    logger.error("finale all retries failed — fallback. last=%s", last_error)
    result = dict(FALLBACK_FINALE)
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    return result
