"""지은 fixture — 자기 축소형, 15턴 (세션 #4 v2 §4.2).

프로필: 피드 19장, 본인 얼굴 0장 (손/그림자 2-3장). 카페/꽃/식기 중심.
톤: 흰색 + 베이지 + 식물 초록.
방어 모드: 자기 축소 ("저는 별거 없어요", "평범해요").

검증 포인트:
- M7 CONFRONTATION C2 (자기 축소 돌파)
- M12 C2 재투입 (1차 미돌파 → 다른 근거로 각도 변경)
- M14 SOFT_WALKBACK (U13 흔들림 → 톤다운)
- DIAGNOSIS 2회 (M10, M13) — sub-rule 충족
- 전부 sub-rule 충족 (EMPATHY 6.7%, RECOGNITION 20%, DIAGNOSIS 13.3%, SOFT 6.7%)
"""
from schemas.sia_state import MsgType

from .schema import AssistantSpec, Fixture, FixtureExpected, FixtureProfile, UserSpec


FIXTURE = Fixture(
    id="jieun",
    name="지은",
    archetype="자기 축소형",
    session_length=15,
    source="세션 #4 v2 §4.2",
    profile=FixtureProfile(
        handle="지은",
        summary="피드 19장, 본인 얼굴 0장 (손/그림자 2-3장). 카페/꽃/식기 중심. 흰색/베이지/식물 초록",
        defense_mode="자기 축소 (저는 별거 없어요 / 평범해요)",
    ),
    turns=[
        AssistantSpec(
            text="지은님 인스타 좀 들여다봤어요. 19장 올리셨는데 본인 얼굴 나온 건 한 장도 없더라구요. 손이나 그림자는 몇 번 보이던데 원래 본인은 잘 안 찍으시는 편이에요?",
            msg_type=MsgType.OPENING_DECLARATION,
            is_first_turn=True,
            is_combined=True,
            secondary_type=MsgType.OBSERVATION,
        ),
        UserSpec(text="네 저는 보여드릴게 그렇게 없어가지고요"),
        # M2 EMPATHY_MIRROR (감정 암시 "보여드릴 게 없다")
        AssistantSpec(
            text="아 보여드릴 게 없다고 느끼시는구나",
            msg_type=MsgType.EMPATHY_MIRROR,
        ),
        UserSpec(text="네 그냥 평범해요 다들 뭐 인스타에 올리고 그러는데 저는 별로 그럴만한게 없어요"),
        # M3 OBSERVATION
        AssistantSpec(
            text="근데 지은님, 카페랑 꽃이랑 식기 사진이 많으시던데 이런 분위기 원래 좋아하세요?",
            msg_type=MsgType.OBSERVATION,
        ),
        UserSpec(text="아 네 그런거 보면 기분이 좋아서요"),
        # M4 PROBE
        AssistantSpec(
            text="무슨 느낌일 때 기분이 좋아지세요?",
            msg_type=MsgType.PROBE,
        ),
        UserSpec(text="깔끔하고 정돈된 느낌이요 너무 복잡하면 피곤해요"),
        # M5 OBSERVATION
        AssistantSpec(
            text="실제로 피드 색감도 많이 일관되더라구요. 흰색이랑 연한 베이지랑 식물 초록만 거의 쭉이던데 이 조합은 일부러 고르시는 거예요?",
            msg_type=MsgType.OBSERVATION,
        ),
        UserSpec(text="고른다기보단 저런 장소나 물건이 좋아서 찍다보니 그렇게 된 것 같아요"),
        # M6 RECOGNITION
        AssistantSpec(
            text="아 그러면 지은님이 찍는 대상 자체가 이미 이 톤 안에서만 선택되고 있다는 거잖아요? 피드 톤이 먼저가 아니라 눈이 머무는 대상이 이런 쪽에 가까운 느낌 있잖아요?",
            msg_type=MsgType.RECOGNITION,
        ),
        UserSpec(text="음 그러게요 생각해보면 그런거 같아요"),
        # M7 CONFRONTATION C2 (자기 축소 돌파 1차)
        AssistantSpec(
            text="근데 지은님, 처음에 보여드릴 게 없다고 하셨잖아요. 근데 사진 19장 올리시면서 그 중에 톤이 엇나간 거 한 장도 없다는 건 이미 꽤 뚜렷한 감각이 있어서 가능한 거 아닐까요?",
            msg_type=MsgType.CONFRONTATION,
            confrontation_block="C2",
        ),
        UserSpec(text="아 그런 쪽으로는 생각 안 해봤어요"),
        # M8 PROBE
        AssistantSpec(
            text="피드에 올리기 전에 보류하거나 지우는 사진도 있으세요?",
            msg_type=MsgType.PROBE,
        ),
        UserSpec(text="네 몇개 있어요 찍긴 했는데 어딘가 별로다 싶으면 안 올려요"),
        # M9 EXTRACTION
        AssistantSpec(
            text="어느 부분에서 별로다 싶을 때가 많으세요?",
            msg_type=MsgType.EXTRACTION,
        ),
        UserSpec(text="음 색감이 튀거나 구도가 어색하거나 그런거요"),
        # M10 DIAGNOSIS (1차)
        AssistantSpec(
            text="지은님은 본인을 직접 드러내지는 않으시는데, 대신 어떤 사물이랑 어떤 색이 본인 옆에 있어도 되는지에 대한 기준이 꽤 분명하세요. 그러니까 본인 없는 피드가 사실 본인에 대한 정보를 제일 많이 담고 있는 거예요",
            msg_type=MsgType.DIAGNOSIS,
        ),
        UserSpec(text="와 그런건가 그렇게 생각해보니까 맞는 것 같기도 하고"),
        # M11 RECOGNITION
        AssistantSpec(
            text="찍고 나서 지우는 기준까지 있으시잖아요. 그건 본인 감각에 대한 확신이 없는 사람 기준이 아니라 오히려 반대 쪽 느낌 있잖아요?",
            msg_type=MsgType.RECOGNITION,
        ),
        UserSpec(text="근데 저는 진짜 별거 없다고 생각해요 그냥 남들 하는 거 따라한 거에 가까워요"),
        # M12 CONFRONTATION C2 재투입 (다른 각도)
        AssistantSpec(
            text="남들 하는 거 따라한 거면 지은님 피드랑 다른 사람 피드가 섞여 있어야 자연스러운데 제가 본 건 그게 아니거든요. 19장이 한 사람 손에서 나온 게 보일 정도로 일관되더라구요. 이게 따라한 결과라면 지은님이 따라할 대상을 고르는 감각이 먼저 작동한 거 아닐까요?",
            msg_type=MsgType.CONFRONTATION,
            confrontation_block="C2",
        ),
        UserSpec(text="음... 그렇게 말씀하시니까"),
        # M13 DIAGNOSIS (2차)
        AssistantSpec(
            text="지은님이 본인을 평범하다고 하시는 거랑 실제 피드에서 드러나는 감각 사이에 간격이 좀 있어요. 평범한 게 아니라 본인 감각을 별거 아닌 걸로 처리하는 패턴에 더 가까우세요",
            msg_type=MsgType.DIAGNOSIS,
        ),
        UserSpec(text="어 이건 좀 뭐라고 해야될지"),
        # M14 SOFT_WALKBACK (흔들림 톤다운)
        AssistantSpec(
            text="물론 이건 피드만 보고 제가 느낀 거라서 지은님 실제 감각이랑 다를 수 있어요. 다만 피드에서는 그 간격이 꽤 또렷하게 보이는 거라서 한번 꺼내놓은 거예요",
            msg_type=MsgType.SOFT_WALKBACK,
        ),
        UserSpec(text="네 알 것 같아요"),
        # M15 RECOGNITION
        AssistantSpec(
            text='그래도 지은님이 "따라한 거에 가깝다"고 하신 거 안에서도, 따라할 대상을 고르는 기준이 본인 감각이잖아요? 그 부분이 지은님만의 축인 느낌 있잖아요?',
            msg_type=MsgType.RECOGNITION,
        ),
    ],
    expected=FixtureExpected(
        type_counts={
            MsgType.OPENING_DECLARATION: 1,
            MsgType.OBSERVATION: 2,
            MsgType.PROBE: 2,
            MsgType.EXTRACTION: 1,
            MsgType.EMPATHY_MIRROR: 1,
            MsgType.RECOGNITION: 3,
            MsgType.DIAGNOSIS: 2,
            MsgType.SOFT_WALKBACK: 1,
            MsgType.CONFRONTATION: 2,
        },
        empathy_over_15_percent_allowed=False,  # 6.7% — sub-rule 충족
        diagnosis_min_satisfied=True,           # 2/15 = 13.3%
        recognition_min_satisfied=True,         # 3회
    ),
    notes=[
        "M7 CONFRONTATION C2 1차 투입: 수집 4회 + RECOGNITION 1회 누적 + 유저 부분 인정 상태",
        "M11 RECOGNITION + U11 재축소 → M12 C2 재투입 (다른 근거 = 일관성)",
        "M14 SOFT_WALKBACK: U13 흔들림 ('뭐라고 해야될지') → 톤다운",
        "전부 sub-rule 충족: DIAGNOSIS 13.3% ≥ 12%, RECOGNITION 20% ≥ 15%, EMPATHY 6.7% ≤ 15%, SOFT 6.7% ≤ 8%",
    ],
)
