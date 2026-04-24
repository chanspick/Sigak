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

import logging
from typing import Optional, Protocol, runtime_checkable

from schemas.user_taste import UserTasteProfile
from services.sia_validators_v4 import (
    check_a17_commerce,
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
    ) -> str:
        """Haiku 호출 → A-17/A-20/markdown 검증 → 위반 시 1회 재시도 → fallback.

        API 키 / 네트워크 / JSON 에러 전부 fallback 으로 수렴. 예외 raise 안 함.
        """
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

            violations = _collect_violations(text)
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
