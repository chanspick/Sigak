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

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Optional, Protocol, runtime_checkable

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
      허용: ~가봐요? / ~이신 것 같은데 / ~으시죠? / ~이시잖아요 / ~더라구요 / ~습니다
      금지: ~네요(?) / ~군요 / ~같아요 / ~같습니다 / ~것 같 / ~수 있습니다

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
        matched_trends: Optional[list] = None,
        user_name: Optional[str] = None,
        photo_pairs: Optional[list[dict]] = None,
    ) -> dict:
        """추구미 비교 narrative 생성 — JSON dict 반환 (Phase J5).

        반환 키:
          overall_message / gap_summary / action_hints
          raw_haiku_response (휘발 방지)
          matched_trends_used
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
    """Verdict v2 _render_taste_profile() 패턴 — 5 필드 dump."""
    dump = profile.model_dump(mode="json")
    return {
        "current_position": dump.get("current_position"),
        "aspiration_vector": dump.get("aspiration_vector"),
        "conversation_signals": dump.get("conversation_signals"),
        "user_original_phrases": dump.get("user_original_phrases"),
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
        f"{primary_axis} 축에서 가장 큰 갭이 보이더라구요. "
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
            return "이 장이 가장 또렷하게 드러나더라구요"
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


# ─────────────────────────────────────────────
#  Haiku 실 호출 구현
# ─────────────────────────────────────────────

_HAIKU_PHOTO_SYSTEM = """당신은 SIGAK 서비스의 Sia — 유저 피드 결을 짚어주는 친근한 비서입니다.

역할:
  유저가 올린 사진 중 선별된 한 장에 대해 1-2 문장 짧은 코멘트를 씁니다.

톤 (페르소나 B 친밀체):
  허용 어미: ~더라구요 / ~이시네 / ~인가봐요? / ~이시잖아요 / ~이세요
  금지 어미: ~것 같아요 / ~인 것 같습니다 / ~할 수 있습니다 / ~군요

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
  허용 어미: ~더라구요 / ~이시네 / ~인가봐요? / ~이시잖아요 / ~이세요
  금지 어미: ~것 같아요 / ~것 같습니다 / ~할 수 있습니다 / ~군요

Hard Rules:
  - 영업 어휘 전수 금지 (컨설팅 / 리포트 / 구독 / 추천해드릴 등)
  - 추상 칭찬 금지 (매력 / 독특 / 특별 / 센스 / 감각이 있)
  - 마크다운 금지 (`*`, `**` 등 전부)
  - 200자 이내

유저 호명: 주어진 user_name 만 사용. 예시 이름 금지.

출력: 한 단락 텍스트만. JSON / 따옴표 / 설명 없음."""


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
        matched_trends: Optional[list] = None,
        user_name: Optional[str] = None,
        photo_pairs: Optional[list[dict]] = None,
    ) -> dict:
        """Aspiration 비교 narrative — Haiku 4.5 + 페르소나 B + 5 필드 + JSON.

        반환 키:
          overall_message / gap_summary / action_hints
          raw_haiku_response (휘발 방지 — 원본 문자열 보존)
          matched_trends_used (활용한 KB 트렌드 list)
        """
        honor = _name_honorific(user_name)
        slim = _render_taste_profile_slim(profile)
        target_summary = _summarize_target_snapshot(target_analysis_snapshot)
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
            f"[target_analysis 핵심]\n{target_summary}\n\n"
            f"[matched_trends — KB 매칭]\n{trends_summary}\n\n"
            f"[photo_pairs 수] {pair_n}\n\n"
            "위 정보로 본인 피드 ↔ 추구미 비교 narrative 를 JSON 으로 출력하십시오. "
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
    ) -> str:
        """Haiku 호출 → validator 검증 → 위반 시 1회 재시도 → fallback.

        validator default: _collect_violations (A-17/A-20/markdown).
        Aspiration 등 다른 영역은 validator 인자로 전용 검증 함수 주입 가능.
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

        last_text = ""
        for attempt in range(max_retries + 1):
            try:
                response = client.messages.create(
                    model=settings.anthropic_model_haiku,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user_prompt}],
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
