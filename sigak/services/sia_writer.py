"""SiaWriter — 페르소나 B 공통 출력 레이어 (Phase G8 인터페이스).

CLAUDE.md §4.7 정의.

현재 Phase G 는 Protocol + 미구현 stub. Phase H (Sia 재설계) / Phase I (PI 엔진)
가 각자 concrete 구현 주입.

인터페이스 사용처:
- Phase I PI 엔진: 사진 25장 각 해석 + 종합 메시지 + boundary_message
- Phase J 추구미 분석: 좌우 쌍 해석 + 종합 메시지
- Phase K Best Shot: 30장 해석 배치
- Phase L Verdict v2: 이미 자체 로직 보유 (재사용 안 해도 됨)
"""
from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from schemas.user_taste import UserTasteProfile


@runtime_checkable
class SiaWriter(Protocol):
    """페르소나 B (간파형 비서) 출력 생성 인터페이스.

    모든 메서드는 CLAUDE.md §6.2 어미 규칙 준수:
      허용: ~가봐요? / ~이신 것 같은데 / ~으시죠? / ~이시잖아요 / ~더라구요 / ~습니다
      금지: ~네요 / ~군요 / ~같아요 / ~같습니다 / ~것 같 / ~수 있습니다

    생성 실패 시 fallback 은 각 구현체가 처리 (예외 raise 지양).
    """

    def generate_comment_for_photo(
        self,
        *,
        photo_url: str,
        photo_context: dict,               # category / rank / extracted_colors 등
        profile: UserTasteProfile,
        persona_hint: Optional[str] = None,
    ) -> str:
        """사진 1장에 대한 Sia 한 줄 해석. 1-2 문장, 60자 이내 지향."""
        ...

    def generate_overall_message(
        self,
        *,
        profile: UserTasteProfile,
        context: dict,                     # 리포트 종류 / 키 포인트 등
    ) -> str:
        """리포트 전체를 감싸는 Sia 의 종합 멘트. 3-5 문장."""
        ...

    def render_boundary_message(
        self,
        *,
        profile: UserTasteProfile,
        public_count: int,
        locked_count: int,
    ) -> str:
        """PI 공개/잠금 경계 카피 — strength_score 반영한 동적 문구.

        CLAUDE.md §7.1 참조:
          "시각이 본 당신은 여기까지 펼쳐드렸어요. 나머지는 정세현님이 더
          쓰실수록 정교해져요. ..."
        """
        ...


# ─────────────────────────────────────────────
#  Stub 구현 — Phase G 동안의 placeholder
# ─────────────────────────────────────────────

class StubSiaWriter:
    """Phase H 이전 사용되는 최소 구현. Haiku 호출 없이 템플릿 응답만."""

    def generate_comment_for_photo(
        self,
        *,
        photo_url: str,
        photo_context: dict,
        profile: UserTasteProfile,
        persona_hint: Optional[str] = None,
    ) -> str:
        # Stub — Phase H/I 에서 실 Haiku 호출로 대체.
        category = photo_context.get("category", "signature")
        return f"이 사진은 {category} 카테고리로 정세현님의 결이 드러나는 장면입니다."

    def generate_overall_message(
        self,
        *,
        profile: UserTasteProfile,
        context: dict,
    ) -> str:
        evidence = len(profile.preference_evidence)
        strength = profile.strength_score
        return (
            f"피드 {evidence}장을 같이 살펴봤습니다. "
            f"지금까지 수집된 정보로 정세현님의 방향이 어느 정도 보이시죠?"
            f" (데이터 풍부도 {strength:.0%})"
        )

    def render_boundary_message(
        self,
        *,
        profile: UserTasteProfile,
        public_count: int,
        locked_count: int,
    ) -> str:
        evidence = len(profile.preference_evidence)
        return (
            f"시각이 본 당신은 여기까지 펼쳐드렸어요.\n\n"
            f"나머지 {locked_count}장은 정세현님이 더 쓰실수록 정교해져요. "
            f"추구미 알려주시고, 피드 추천 받으실 때마다 저(Sia)가 더 잘 알게 돼요.\n\n"
            f"지금 정세현님 정보: 피드 {evidence}장, 데이터 풍부도 "
            f"{profile.strength_score:.0%}."
        )


# 기본 writer — Phase H/I 에서 concrete 구현으로 교체.
_default_writer: SiaWriter = StubSiaWriter()


def get_sia_writer() -> SiaWriter:
    """현재 활성 SiaWriter 반환. 테스트에서 set_sia_writer 로 교체 가능."""
    return _default_writer


def set_sia_writer(writer: SiaWriter) -> None:
    """의존성 주입 — 테스트/실 구현 교체."""
    global _default_writer
    _default_writer = writer
