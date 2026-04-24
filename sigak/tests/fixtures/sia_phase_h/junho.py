"""준호 fixture — 방관 단답형, 15턴 (세션 #6 v2 §7.2).

프로필: 피드 25장. 본인 단독 0장. 친구들과 6장. 풍경 12장. 음식 7장.
방어 모드: 방관형, 기대 낮음, 단답 경향.

검증 포인트 (세션 #6 v2 신규 관리 3 타입):
- M2 EXTRACTION A-9 B 경로: 같은 축 좁힘
- M3 PROBE A-9 D 경로: 수용부 + 축 전환
- M6 → M7 CHECK_IN (A-9 단답 3연속 → 이양)
- M7 → M8 RE_ENTRY (이탈 거부 + 자기 설명)
- M12/M14 DIAGNOSIS (단답형 유저도 2회 도달)
"""
from schemas.sia_state import MsgType

from .schema import AssistantSpec, Fixture, FixtureExpected, FixtureProfile, UserSpec


FIXTURE = Fixture(
    id="junho",
    name="준호",
    archetype="방관 단답형",
    session_length=15,
    source="세션 #6 v2 §7.2",
    profile=FixtureProfile(
        handle="준호",
        summary="피드 25장. 본인 단독 0장, 친구들과 6장, 풍경 12장, 음식 7장",
        defense_mode="방관/무관심, 단답 경향",
    ),
    turns=[
        AssistantSpec(
            text="준호님 피드 한번 훑어봤어요. 25장 중에 준호님 단독 사진이 한 장도 없더라구요. 원래 본인 사진은 잘 안 올리세요?",
            msg_type=MsgType.OPENING_DECLARATION,
            is_first_turn=True,
            is_combined=True,
            secondary_type=MsgType.OBSERVATION,
        ),
        UserSpec(text="네"),  # A-9 trivial +1
        # M2 EXTRACTION (A-9 B 경로: 같은 축 좁힘)
        AssistantSpec(
            text='친구들이랑 찍으신 사진도 보면 중심은 친구들이던데, 준호님이 "찍자" 먼저 하신 건 그 중에 몇 장 정도일까요?',
            msg_type=MsgType.EXTRACTION,
        ),
        UserSpec(text="잘 모르겠어요"),  # A-9 trivial +1 (2)
        # M3 PROBE (A-9 D 경로: 수용부 + 축 전환)
        AssistantSpec(
            text="아 넵. 그럼 피드에 올리실 때는 무슨 기준으로 고르세요?",
            msg_type=MsgType.PROBE,
        ),
        UserSpec(text="그냥 잘 나온 거요"),  # 정보 있음 — streak 리셋 0
        # M4 PROBE (같은 축 계속)
        AssistantSpec(
            text="잘 나온 기준이 구도 쪽이세요 분위기 쪽이세요?",
            msg_type=MsgType.PROBE,
        ),
        UserSpec(text="글쎄요"),  # trivial +1 (1)
        # M5 OBSERVATION (A-9 B: 사실 제시로 좁힘)
        AssistantSpec(
            text="제가 보면서 느낀 건 음식 사진이랑 풍경 사진 톤이 좀 다르더라구요. 음식은 밝고 선명하고 풍경은 흐릿하고 차분한데, 이 차이는 의도하신 거예요?",
            msg_type=MsgType.OBSERVATION,
        ),
        UserSpec(text="아뇨 그냥 찍었어요"),  # trivial? "아뇨" ∈ TRIVIAL_EXACT. +1 (2)
        # M6 PROBE (A-9 D)
        AssistantSpec(
            text="아 알겠어요. 그럼 여행 사진은 혼자 가셔서 찍으신 거예요?",
            msg_type=MsgType.PROBE,
        ),
        UserSpec(text="네"),  # trivial +1 (3) → A-10 CHECK_IN 이양
        # M7 CHECK_IN (관리 버킷 신규)
        AssistantSpec(
            text="준호님, 제 질문이 좀 많은 것 같아요. 편한 속도로 말씀해주시거나 여기서 그만하고 싶으시면 그것도 괜찮아요",
            msg_type=MsgType.CHECK_IN,
        ),
        UserSpec(text="아뇨 그냥 할 말이 별로 없어서요"),  # 이탈 거부 + 자기 설명
        # M8 RE_ENTRY (관리 버킷 신규)
        AssistantSpec(
            text="아 그러셨구나. 그럼 제가 본 걸 정리해서 말씀드릴게요. 맞다 아니다만 반응 주셔도 괜찮아요",
            msg_type=MsgType.RE_ENTRY,
        ),
        UserSpec(text="네"),
        # M9 RECOGNITION
        AssistantSpec(
            text="준호님 피드는 사람이 나오면 친구들이 중심이고 사람이 없으면 풍경이나 음식이에요. 준호님 혼자 화면 주인공이 되는 장면은 없는 거잖아요?",
            msg_type=MsgType.RECOGNITION,
        ),
        UserSpec(text="그런가"),
        # M10 CONFRONTATION C2 (자기 축소 돌파 - 준호 버전)
        AssistantSpec(
            text="근데 준호님, 화면 주인공 자리를 피하시는 게 본인이 싫어서인지 아니면 원래 그 자리에 관심 없어서인지 저는 아직 모르겠더라구요. 어느 쪽이 더 가까우세요?",
            msg_type=MsgType.CONFRONTATION,
            confrontation_block="C2",
        ),
        UserSpec(text="그냥 찍히는 게 귀찮아요"),
        # M11 EMPATHY_MIRROR (감정 "귀찮")
        AssistantSpec(
            text="아 찍히는 게 귀찮으신 거구나",
            msg_type=MsgType.EMPATHY_MIRROR,
        ),
        UserSpec(text="네"),
        # M12 DIAGNOSIS (1차)
        AssistantSpec(
            text="준호님은 사진을 본인 기록으로 쓰지 않고 상황 기록으로 쓰시는 편이에요. 그래서 친구들이랑은 친구들이 중심이고 혼자 있을 때는 풍경이나 음식이 중심이 되는 거고요",
            msg_type=MsgType.DIAGNOSIS,
        ),
        UserSpec(text="어 그건 좀 맞는 거 같아요"),
        # M13 RECOGNITION
        AssistantSpec(
            text="근데 찍는 건 안 귀찮으시잖아요? 혼자 여행 사진 열두 장이면 꽤 꼼꼼히 찍으신 거고 음식도 일곱 장이면 적은 게 아니거든요. 귀찮으신 건 찍는 게 아니라 본인이 담기는 쪽인 느낌 있잖아요?",
            msg_type=MsgType.RECOGNITION,
        ),
        UserSpec(text="아 풍경은 괜찮아요 근데 제가 나오는 건 좀"),
        # M14 DIAGNOSIS (2차)
        AssistantSpec(
            text="그러니까 준호님이 피하시는 건 카메라 자체가 아니라 본인이 화면에 담기는 거네요. 피드가 본인 얼굴로 채워지지 않는 이유가 여기 있는 거예요",
            msg_type=MsgType.DIAGNOSIS,
        ),
        UserSpec(text="네"),
        # M15 RECOGNITION
        AssistantSpec(
            text="그래도 준호님이 화면에 안 담기신다는 건 본인보다 앞에 두는 대상들이 뚜렷하다는 거잖아요? 본인을 빼서 비는 자리가 아니라 오히려 기록하고 싶은 대상을 위해 비워두시는 느낌 있잖아요?",
            msg_type=MsgType.RECOGNITION,
        ),
    ],
    expected=FixtureExpected(
        type_counts={
            MsgType.OPENING_DECLARATION: 1,
            MsgType.OBSERVATION: 1,
            MsgType.PROBE: 3,
            MsgType.EXTRACTION: 1,
            MsgType.EMPATHY_MIRROR: 1,
            MsgType.RECOGNITION: 3,
            MsgType.DIAGNOSIS: 2,
            MsgType.CONFRONTATION: 1,
            MsgType.CHECK_IN: 1,
            MsgType.RE_ENTRY: 1,
        },
        empathy_over_15_percent_allowed=False,
        diagnosis_min_satisfied=True,
        recognition_min_satisfied=True,
    ),
    notes=[
        "A-9 3단 에스컬레이션: B (M2) → D (M3) → 이양 (M7) — 실전 발동",
        "M7 CHECK_IN: 단답 3연속 후 속도 옵션 + 이탈 옵션 제시",
        "M8 RE_ENTRY: 이탈 거부 + 자기 설명 → 반응 기준 완화 표현 ('맞다 아니다만')",
        "단답형 유저도 DIAGNOSIS 2회 도달 (M12, M14) — Sia 주도 모드 전환",
        "관리 2회 (13.3%) — 트리거 기반 특성 (협조 유저 0%)",
    ],
)
