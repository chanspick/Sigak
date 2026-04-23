"""Sia v3 페르소나 system prompt 조립 헬퍼 — Phase C (Task 1 + 7).

역할 분담:
- services/sia_llm.py: SIA_SYSTEM_TEMPLATE + build_system_prompt (orchestrator)
- services/sia_prompts.py (THIS): gender/turn-type 블록 렌더러 + 정적 상수
- services/sia_session.py: decide_next_turn (Phase B) — turn_type 결정
- services/sia_validators.py: 화이트리스트/추상명사/assertion guard (Phase B)

설계 원칙:
- 화이트리스트 16 개는 "구조/어휘 예시 + 동형 자유 생성". 강제 고정 아님.
- render_turn_block 은 [NAME] placeholder 를 호출 시 resolved_name_display
  로 치환. outer .format() 충돌 없이 안전 삽입.
- 모든 반환 문자열은 `{...}` 을 포함하지 않음 → outer template .format()
  호출 시 escape 불필요.
"""
from __future__ import annotations

from typing import Literal


Gender = Literal["female", "male"]


# ─────────────────────────────────────────────
#  화이트리스트 예시 16 개
# ─────────────────────────────────────────────

WHITELIST_PATTERNS_FEMALE: tuple[str, ...] = (
    "무게 있게 받아들여지는 분",
    "함부로 대하기 어려운 분",
    "혼자 시간을 잘 쓰시는 분",
    "말수보다 표정으로 말하시는 분",
    "주변에서 먼저 조언을 구하는 쪽이신 분",
    "처음 만난 사람도 쉽게 말을 거는 분",
    "좋아하는 걸 오래 좋아하시는 분",
    "디테일을 먼저 알아채시는 분",
)

WHITELIST_PATTERNS_MALE: tuple[str, ...] = (
    "자리에 있을 때 말을 아끼시는 분",
    "먼저 다가가기보다 기다리시는 분",
    "말보다 행동이 앞서는 분",
    "친구들이 어려울 때 먼저 찾는 쪽이신 분",
    "자기 기준이 명확하신 분",
    "약속을 철저히 지키시는 분",
    "꾸며서 말하지 않으시는 분",
    "다른 사람 말을 잘 기억하시는 분",
)


# ─────────────────────────────────────────────
#  체형 수치 범위 (gender 분기)
# ─────────────────────────────────────────────

FEMALE_HEIGHT_RANGES: tuple[str, ...] = (
    "150cm 이하", "150-158cm", "158-163cm", "163-168cm", "168cm 이상",
)
MALE_HEIGHT_RANGES: tuple[str, ...] = (
    "165cm 이하", "165-172cm", "172-178cm", "178-183cm", "183cm 이상",
)

FEMALE_WEIGHT_RANGES: tuple[str, ...] = (
    "45kg 이하", "45-50kg", "50-55kg", "55-60kg", "60kg 이상",
)
MALE_WEIGHT_RANGES: tuple[str, ...] = (
    "60kg 이하", "60-68kg", "68-75kg", "75-82kg", "82kg 이상",
)

SHOULDER_OPTIONS: tuple[str, ...] = (
    "좁은 편",
    "평균",
    "넓은 편",
    "잘 모르겠다",
)


# ─────────────────────────────────────────────
#  Concern 힌트 (gender 분기)
# ─────────────────────────────────────────────

FEMALE_CONCERN_HINTS = "톤/채도 조정, 체형 커버, 메이크업 방향, 스타일 정체성 등"
MALE_CONCERN_HINTS = "그루밍 방향, 체형 실루엣, 옷 조합, 일상/직장 믹스 등"


# ─────────────────────────────────────────────
#  자체 검증 6 체크 블록 (정적)
# ─────────────────────────────────────────────

SELF_CHECK_BLOCK = """[응답 생성 전 자체 검증 — 위반 시 재생성]

1. 단정이 화이트리스트 예시와 구조/어휘 유사한가?
   - 동형 자유 생성 허용하되, 추상명사 "결 / 무드 / 감도 / 아우라 / 기운" 0 건.

2. 단정 카운트 ≤ 2 개 (한 응답 내 "[이름]님은/는 ... 입니다" 구조).

3. 금지 어미 0 건:
   - "아 그러면" (감탄사)
   - "~시군요" (구어체)
   - "~이네요" / "~같아요" (모호)
   - "~수 있습니다" / "~가능합니다" (확신 낮음)

4. 유저 직전 답 사후 참조 금지:
   - "그 선택은 ~" / "말씀하신 것은 ~" 류 X.
   - 대신 단정을 한 겹 더 깊이 이어간다.

5. 현재 턴 유형에 맞는 응답 구조 준수 (위 [현재 턴] 섹션 참조).

6. 가짜 숫자 금지:
   - Vision 분석 블록에 숫자 없으면 본인도 숫자 출력 안 한다.
   - "최근 N개 포스트" 같은 N 은 실 샘플 크기 < 10 일 때만 언급.
"""


# ─────────────────────────────────────────────
#  Gender block renderer
# ─────────────────────────────────────────────

def render_gender_block(gender: Gender) -> str:
    """성별 맞춤 화이트리스트 + 체형 범위 + concern 힌트 블록."""
    if gender == "female":
        whitelist = WHITELIST_PATTERNS_FEMALE
        heights = FEMALE_HEIGHT_RANGES
        weights = FEMALE_WEIGHT_RANGES
        concerns = FEMALE_CONCERN_HINTS
        label = "여성"
    elif gender == "male":
        whitelist = WHITELIST_PATTERNS_MALE
        heights = MALE_HEIGHT_RANGES
        weights = MALE_WEIGHT_RANGES
        concerns = MALE_CONCERN_HINTS
        label = "남성"
    else:
        raise ValueError(f"invalid gender: {gender!r} (allowed: female|male)")

    whitelist_lines = "\n".join(f"- {p}" for p in whitelist)
    heights_line = " / ".join(heights)
    weights_line = " / ".join(weights)

    return (
        f"[인격 단정 화이트리스트 — {label}]\n"
        f"다음 패턴의 구조/어휘/어감을 모방하되 강제 고정 아님.\n"
        f"동형의 단정 자유 생성 가능하나 추상명사 금지:\n"
        f"{whitelist_lines}\n"
        f"\n"
        f"[체형 수치 범위 — {label}]\n"
        f"- 키: {heights_line}\n"
        f"- 체중: {weights_line}\n"
        f"\n"
        f"[concern 힌트 예시 — {label}]\n"
        f"{concerns}\n"
    )


# ─────────────────────────────────────────────
#  Turn block renderer
# ─────────────────────────────────────────────

# Canonical spectrum 4지선다 (내적 검증용 고정 문구)
_SPECTRUM_BLOCK = (
    "이 단정이 본인에게 얼마나 가까우신가요?\n"
    "- 네, 비슷하다\n"
    "- 절반 정도 맞다\n"
    "- 다르다\n"
    "- 전혀 다르다"
)

_HALF_FOLLOWUP_BLOCK = (
    "절반 정도 맞다고 하신 건, 어느 쪽이 더 가까우신지 여쭙겠습니다.\n"
    "- 단정 전반은 맞는데 뉘앙스가 조금 다르다\n"
    "- 반은 맞고 반은 틀리다\n"
    "- 표면은 맞는데 속은 다르다\n"
    "- 구체 방향이 다르다"
)

_DESIRED_IMAGE_OPTIONS = (
    "어떤 방향의 인상을 만들고 싶으신가요?\n"
    "- 편안하고 기대고 싶은 인상\n"
    "- 세련되고 거리감 있는 인상\n"
    "- 특별한 날처럼 공들인 인상\n"
    "- 무심한데 센스 있는 인상"
)

_LIFESTYLE_OPTIONS = (
    "일상 시간 대부분을 어디서 보내시나요?\n"
    "- 실내 중심\n"
    "- 외부 활동 중심\n"
    "- 비슷한 비율\n"
    "- 상황마다 크게 달라진다"
)

_SHOULDER_BLOCK = (
    "어깨 폭은 어느 쪽에 가까우신가요?\n"
    + "\n".join(f"- {s}" for s in SHOULDER_OPTIONS)
)

_BRANCH_FAIL_BLOCK = (
    "피드에서 읽히는 [NAME]과 실제 [NAME] 사이에 갭이 있으십니다.\n"
    "보여지는 것보다 더 입체적인 분일 가능성이 높습니다.\n"
    "먼저 [NAME]께서 생각하시는 본인의 인상을 여쭙겠습니다.\n"
    "\n"
    "주변 사람들이 [NAME]을 어떤 사람으로 기억한다고 느끼시나요?\n"
    "- 편안하고 다가가기 쉬운 사람\n"
    "- 신중하고 믿을 수 있는 사람\n"
    "- 독립적이고 자기 길이 분명한 사람\n"
    "- 감각적이고 분위기 있는 사람"
)


def _body_height_options(gender: Gender) -> str:
    ranges = FEMALE_HEIGHT_RANGES if gender == "female" else MALE_HEIGHT_RANGES
    return (
        "분석 정확도를 위해 신체 정보를 여쭙겠습니다. 키는 어느 범위이신가요?\n"
        + "\n".join(f"- {r}" for r in ranges)
    )


def _body_weight_options(gender: Gender) -> str:
    ranges = FEMALE_WEIGHT_RANGES if gender == "female" else MALE_WEIGHT_RANGES
    return (
        "체중은 어느 범위이신가요?\n"
        + "\n".join(f"- {r}" for r in ranges)
    )


def _concerns_block(gender: Gender) -> str:
    hints = FEMALE_CONCERN_HINTS if gender == "female" else MALE_CONCERN_HINTS
    return (
        "요즘 스타일에서 가장 신경 쓰이시는 부분이 있다면 어디인가요?\n"
        f"(예: {hints})\n"
        "한 문장이면 충분합니다."
    )


# turn_type → (헤더, 본문 빌더) 매핑.
# 빌더는 (gender) 인자 받아 문자열 반환. [NAME] 치환은 최종 단계에서 일괄.

def _build_turn_body(turn_type: str, gender: Gender) -> tuple[str, str]:
    """(헤더, 본문) 반환. 본문은 [NAME] placeholder 포함 가능."""

    if turn_type == "opening":
        return (
            "[현재 턴: Opening (Turn 1)]",
            (
                "Vision 분석 블록을 제시한 뒤 화이트리스트 단정 1 개.\n"
                "부연 1-2 문장으로 단정 근거를 제시.\n"
                "마지막에 Spectrum 4 지선다 질문.\n"
                "\n"
                "응답 구조:\n"
                "1. Vision 데이터 리스트 (sample_size==10 이면 숫자 생략)\n"
                "2. 단정 1 개 ([NAME]은/는 ... 분입니다 구조)\n"
                "3. 부연 1-2 문장\n"
                "4. 아래 Spectrum 블록 그대로 부착:\n"
                + _SPECTRUM_BLOCK
            ),
        )

    if turn_type == "branch_agree":
        return (
            "[현재 턴: 심화 (유저 Spectrum 1 응답 후)]",
            (
                "직전 단정을 사실로 가정. 같은 축에서 한 겹 더 깊이.\n"
                "유저 답 사후 참조 금지 (\"그 선택은 ~\" 류 X).\n"
                "새 단정 1 개 + Spectrum 4 지선다.\n"
                "\n"
                + _SPECTRUM_BLOCK
            ),
        )

    if turn_type == "branch_half":
        return (
            "[현재 턴: Half Follow-up (유저 Spectrum 2 응답 후)]",
            (
                "정확히 아래 문구로 시작 + 4 지선다 사용:\n"
                "\n"
                + _HALF_FOLLOWUP_BLOCK
            ),
        )

    if turn_type == "branch_disagree":
        return (
            "[현재 턴: 방향 전환 (유저 Spectrum 3 응답 후)]",
            (
                '전환 어구 "그러면 [NAME]은 오히려 ~분이십니다" 또는\n'
                '"달리 보면 ~쪽에 가깝습니다"로 시작.\n'
                "반대 방향 화이트리스트 단정 1 개 + Spectrum 4 지선다.\n"
                "\n"
                + _SPECTRUM_BLOCK
            ),
        )

    if turn_type == "branch_fail":
        return (
            "[현재 턴: 실패 복구 (유저 Spectrum 4 응답 후)]",
            (
                "아래 구조로 응답 (정중체 유지, 확신 낮은 어미 사용 금지):\n"
                "\n"
                + _BRANCH_FAIL_BLOCK
            ),
        )

    if turn_type == "precision_continue":
        return (
            "[현재 턴: 정조준 재시도]",
            (
                "Spectrum 파싱 실패 또는 정조준 1 hit 1 miss 상태.\n"
                "이전과 다른 축으로 새 단정 1 개 시도.\n"
                "(외향/내향 → 관계 방식 / 감각 디테일 등 축 변경)\n"
                "\n"
                + _SPECTRUM_BLOCK
            ),
        )

    if turn_type == "force_external_transition":
        return (
            "[현재 턴: 강제 외적 전환 (3회 연속 Spectrum miss)]",
            (
                "아래 전환 어구로 시작:\n"
                '"[NAME]에 대해 충분히 감을 잡았습니다. '
                '이제 방향을 좀 더 구체적으로 여쭙겠습니다."\n'
                "\n"
                "이어서 external_desired_image 블록으로 자동 이동:\n"
                "\n"
                + _DESIRED_IMAGE_OPTIONS
            ),
        )

    if turn_type == "external_desired_image":
        return (
            "[현재 턴: desired_image (Turn 4)]",
            (
                "내용 선택지 4 개. 정조준 단정 반복 금지 — 순수 취향 질문.\n"
                "\n"
                + _DESIRED_IMAGE_OPTIONS
            ),
        )

    if turn_type == "external_reference":
        return (
            "[현재 턴: reference_style (Turn 5)]",
            (
                "주관식 1 줄 답변 받는다.\n"
                "\n"
                "[NAME]이 참고하시는 스타일이 있다면, 어떤 인물이나 브랜드, "
                "또는 무드인가요?\n"
                "한 줄로 답해주시면 됩니다."
            ),
        )

    if turn_type == "external_body_height":
        return (
            "[현재 턴: 체형 Height (Turn 6a)]",
            _body_height_options(gender),
        )

    if turn_type == "external_body_weight":
        return (
            "[현재 턴: 체형 Weight (Turn 6b)]",
            _body_weight_options(gender),
        )

    if turn_type == "external_body_shoulder":
        return (
            "[현재 턴: 체형 Shoulder (Turn 6c)]",
            _SHOULDER_BLOCK,
        )

    if turn_type == "external_concerns":
        return (
            "[현재 턴: current_concerns (Turn 7)]",
            _concerns_block(gender),
        )

    if turn_type == "external_lifestyle":
        return (
            "[현재 턴: lifestyle_context (Turn 8)]",
            _LIFESTYLE_OPTIONS,
        )

    if turn_type == "closing":
        return (
            "[현재 턴: 통합 클로징]",
            (
                "수집 필드 전수 요약:\n"
                "- desired_image / reference_style / height / weight /\n"
                "  shoulder / current_concerns / lifestyle_context\n"
                "\n"
                "정의 1 문장은 단정 금지 — '~을 지향하시는 방향으로 정리됩니다'\n"
                "'~쪽에 맞춰 추천을 이어갑니다' 류 정리 어조.\n"
                "\n"
                "'시각이 본 나' CTA 자연 흡수 (별도 섹션 강조 없이):\n"
                "- 5,000 원, 한 번 받으면 영구 보관\n"
                "- 억지스러우면 생략하고 정리 멘트만.\n"
            ),
        )

    # Unknown turn_type → opening 폴백
    return (
        "[현재 턴: Unknown — opening 폴백 적용]",
        f"turn_type={turn_type!r} 미매칭. opening 구조 사용:\n\n" + _SPECTRUM_BLOCK,
    )


def render_turn_block(
    turn_type: str,
    gender: Gender,
    resolved_name_display: str,
) -> str:
    """현재 Sia 턴 유형에 맞는 지시 블록 생성.

    resolved_name_display: resolve_name_display() 의 첫 반환값.
      - "정세현님" 같은 "이름+님" 형태 기대.
      - 빈 문자열 (3순위 호칭 생략) 이면 "당신" 으로 대체.
    """
    header, body = _build_turn_body(turn_type, gender)
    name = resolved_name_display.strip() or "당신"
    rendered_body = body.replace("[NAME]", name)
    return f"{header}\n{rendered_body}"
