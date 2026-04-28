"""만재 fixture — 외부 권위 회귀형, 15턴 (세션 #4 v2 §3.2).

프로필: 피드 20장, 본인 얼굴 2장, 베이지/그레이/아이보리 일관.
배경: 퍼스널 컬러 컨설팅 수강 (봄웜 진단).
방어 모드: 외부 권위 회귀 ("컨설팅에서 맞추라고 했어요").

검증 포인트:
- M1 결합 출력 (OPENING + OBSERVATION)
- M7 CONFRONTATION C1 (외부 권위 회귀 돌파)
- DIAGNOSIS 2회 배치 (M12, M14) — sub-rule 충족
- EMPATHY_MIRROR 3회 (20%) — A-3 감정 트리거 3회 강제로 15% 상한 초과 허용
"""
from schemas.sia_state import MsgType

from .schema import AssistantSpec, Fixture, FixtureExpected, FixtureProfile, UserSpec


FIXTURE = Fixture(
    id="manjae",
    name="만재",
    archetype="외부 권위 회귀형",
    session_length=15,
    source="세션 #4 v2 §3.2",
    profile=FixtureProfile(
        handle="만재",
        summary="피드 20장, 본인 얼굴 2장, 베이지/그레이/아이보리 톤 일관",
        defense_mode="외부 권위 회귀 (퍼스널 컬러 컨설팅 수강)",
    ),
    turns=[
        # M1 결합 출력 (OPENING + OBSERVATION 한 메시지)
        AssistantSpec(
            text="만재님 인스타 좀 들여다봤어요. 스무 장 넘게 올리셨는데 만재님 얼굴 나온 건 두 장이더라구요. 원래 본인 잘 안 찍으시는 편이에요?",
            msg_type=MsgType.OPENING_DECLARATION,
            is_first_turn=True,
            is_combined=True,
            secondary_type=MsgType.OBSERVATION,
        ),
        UserSpec(text="아 네네!"),
        # M2 OBSERVATION
        AssistantSpec(
            text="피드 톤도 좀 일관되더라구요. 베이지 그레이 아이보리 이런 색만 거의 쭉이던데 원래 이런 톤 좋아하세요?",
            msg_type=MsgType.OBSERVATION,
        ),
        UserSpec(text="예전에 퍼스널컬러 컨설팅 받았는데 거기서 그런계열의 톤으로 맞추라고 했어요. 그래서 그런쪽 배경을 그나마 주려고 노력해요"),
        # M3 PROBE
        AssistantSpec(
            text="아 컨설팅 받으셨구나. 무슨 톤 나오셨어요?",
            msg_type=MsgType.PROBE,
        ),
        UserSpec(text="봄 웜톤이요"),
        # M4 OBSERVATION + PROBE
        AssistantSpec(
            text="근데 봄웜이면 보통 코랄이나 오렌지 쪽도 잘 붙을 텐데 피드엔 그런 색이 잘 안 보이더라구요. 일부러 빼시는 거예요?",
            msg_type=MsgType.OBSERVATION,
        ),
        UserSpec(text="코랄은 입어보면 좀 튀어서요. 어색하더라구요"),
        # M5 EMPATHY_MIRROR (감정 트리거 "어색")
        AssistantSpec(
            text="아 어색하셨구나. 그럴 수 있어요",
            msg_type=MsgType.EMPATHY_MIRROR,
        ),
        UserSpec(text="네 그래서 베이지 계열이 제일 무난한 것 같아요"),
        # M6 RECOGNITION
        AssistantSpec(
            text="컨설팅에서 봄웜이라고 했는데 실제로 입어봤을 때 코랄은 튀고 베이지가 편하셨다는 거잖아요? 그 감각이 컨설팅 결과보다 실제 만재님 쪽에 더 가까운 느낌 있잖아요?",
            msg_type=MsgType.RECOGNITION,
        ),
        UserSpec(text="음... 그럴 수도 있는데 전문가가 말한거니까요 ㅠㅠ"),
        # M7 CONFRONTATION C1 (외부 권위 회귀 돌파)
        AssistantSpec(
            text="근데 만재님, 봄웜 진단 자체를 의심하는 게 아니라, 봄웜 안에서도 만재님한테 붙는 색은 베이지 쪽이라는 거잖아요? 전문가가 본 큰 카테고리랑 본인이 실제 입어보고 느낀 세부 톤은 다른 레이어 아닐까요?",
            msg_type=MsgType.CONFRONTATION,
            confrontation_block="C1",
        ),
        UserSpec(text="음... 생각해봐야겠어요 그치만 전문가가 말한 것도 아예 틀린건 아닐거고요"),
        # M8 EMPATHY_MIRROR
        AssistantSpec(
            text="아 맞아요 그 부분 바로 뒤집는 건 저도 아니에요",
            msg_type=MsgType.EMPATHY_MIRROR,
        ),
        UserSpec(text="네"),
        # M9 RECOGNITION
        AssistantSpec(
            text="컨설팅에서 본 축은 큰 카테고리고, 만재님이 베이지 쪽으로 수렴하신 건 그 안에서 본인이 실제 시험해본 결과잖아요? 그 두 개가 서로 모순되는 게 아니라 층이 다른 거잖아요?",
            msg_type=MsgType.RECOGNITION,
        ),
        UserSpec(text="그렇게 정리하니까 좀 편하네요"),
        # M10 OBSERVATION
        AssistantSpec(
            text="근데 피드에 만재님 얼굴 들어간 두 장 중 한 장은 실내 조명 아래 찍으신 것 같더라구요. 이건 베이지 톤이 주변에 없는 상황이었던 거예요?",
            msg_type=MsgType.OBSERVATION,
        ),
        UserSpec(text="아 그건 친구가 찍어준거에요 제가 올리고 싶어서 올린 건 아니라서"),
        # M11 PROBE
        AssistantSpec(
            text="그럼 만재님이 직접 본인 나오게 찍으신 건 나머지 한 장이 유일한 거예요?",
            msg_type=MsgType.PROBE,
        ),
        UserSpec(text="네 맞아요"),
        # M12 DIAGNOSIS (1차)
        AssistantSpec(
            text="만재님 피드는 배경이 만재님보다 먼저 자리잡고 있어요. 본인을 드러내는 대신 본인이 편한 톤 안에 본인이 녹아있는 방식으로 피드를 끌고 가세요",
            msg_type=MsgType.DIAGNOSIS,
        ),
        UserSpec(text="어 맞아요 저 저한테 관심이 쏠리는 거 좀 어색해요"),
        # M13 EMPATHY_MIRROR (감정 트리거 "어색")
        AssistantSpec(
            text="아 관심 쏠리는 게 어색하셨구나. 그게 자연스러울 수 있어요",
            msg_type=MsgType.EMPATHY_MIRROR,
        ),
        UserSpec(text="네 ㅎㅎ"),
        # M14 DIAGNOSIS (2차 — sub-rule 충족)
        AssistantSpec(
            text="만재님이 컨설팅에서 받으신 카테고리랑 실제 사용 방식 사이에 본인만의 편집이 들어가 있어요. 외부 기준을 받았지만 거기 머문 게 아니라 본인 쪽으로 끌어오신 거예요",
            msg_type=MsgType.DIAGNOSIS,
        ),
        UserSpec(text="그러네요 그렇게 보니까"),
        # M15 RECOGNITION
        AssistantSpec(
            text="전문가가 준 틀 안에서도 만재님이 직접 고르신 수렴점이 있는 거잖아요? 그게 결국 만재님 스타일의 진짜 축인 느낌 있잖아요?",
            msg_type=MsgType.RECOGNITION,
        ),
    ],
    expected=FixtureExpected(
        # primary_type 기준 카운트. 세션 #4 v2 §3.3 분포 표는 M1 합산/M4 하이브리드 규칙으로
        # OBS 4 / PROBE 2 로 표기되지만, 본 테스트는 primary_type 만 1로 계수.
        type_counts={
            MsgType.OPENING_DECLARATION: 1,
            MsgType.OBSERVATION: 3,   # M2, M4(primary), M10
            MsgType.PROBE: 2,         # M3, M11
            MsgType.EMPATHY_MIRROR: 3,
            MsgType.RECOGNITION: 3,
            MsgType.CONFRONTATION: 1,
            MsgType.DIAGNOSIS: 2,
        },
        empathy_over_15_percent_allowed=True,  # 20% 발생, A-3 트리거 3회 강제
        diagnosis_min_satisfied=True,          # 2/15 = 13.3% ≥ 12%
        recognition_min_satisfied=True,        # 3회 ≥ 2회 하한
    ),
    notes=[
        "M1 결합 출력: OPENING_DECLARATION + OBSERVATION 한 메시지",
        "M5 EMPATHY: '어색' 감정 트리거",
        "M7 CONFRONTATION C1: 외부 권위 회귀 돌파 — 부분 인정 + 레이어 분리 프레임",
        "M12/M14 DIAGNOSIS 2회: sub-rule 12% 하한 충족 (2/15 = 13.3%)",
        "M13 EMPATHY: '어색' 감정 재등장",
        "EMPATHY_MIRROR 20% (3/15) > 15% 가이드 초과 — A-3 트리거 우선으로 허용",
    ],
)
