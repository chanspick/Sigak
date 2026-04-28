"""도윤 fixture — 자기 PR 과잉형, 6턴 (세션 #7 §12.2).

프로필: 피드 32장. 본인 셀카/전신 14장. 운동/카페/맛집 18장.
캡션에 "오늘도 달림 💪", "이 정도면 합격?", "각 잡고 찍었습니다" 류 자기 PR 멘트.
톤: 블루/블랙/그레이 + 가끔 채도 높은 운동복 컬러.
배경: 본인 외모/인상에 자신 있는 편. 진단 들어온 이유 = "더 잘 나오는 법".
평가 요청 적극적.

검증 주 타깃 (세션 #7 신규 룰 대량 도출):
- C6 평가 의존 돌파 (M5) + 분기 가설 검증 (자기개시 풍부 → C6)
- C7 일반화 회피 돌파 (M6) — 자연 발생
- A-12 질문 종결 신규 정보 원칙 (M3, M4 위반 → 재작성으로 정정 + 정의 확정)
- A-13 자기 충만형 라포 prefix (M2 칭찬 prefix, M3 가설 부분 동의 prefix, M5 칭찬 prefix)
- A-15 산출물 가치사슬 정합 원칙 (M4 위반 '운동 종목' → 본인 지적으로 정의)
- A-16 유저 명시 자기인지 존중 (M6 위반 '의식하고 고르신 거예요' → 본인 지적으로 정의)
"""
from schemas.sia_state import MsgType

from .schema import AssistantSpec, Fixture, FixtureExpected, FixtureProfile, UserSpec


FIXTURE = Fixture(
    id="doyoon",
    name="도윤",
    archetype="자기 PR 과잉형",
    session_length=6,
    source="세션 #7 §12.2",
    profile=FixtureProfile(
        handle="도윤",
        summary="피드 32장. 본인 셀카/전신 14장. 블루/블랙/그레이 무채색 톤. 자기 PR 캡션 다수",
        defense_mode="자기 PR 과잉 + 평가 요청 적극 + 일반화 회피",
    ),
    turns=[
        AssistantSpec(
            text='도윤님 피드 한번 훑어봤어요. 본인 사진이 열네 장이나 되는데 캡션에 "이 정도면 합격?" 같은 본인 평가 묻는 멘트가 꽤 자주 보이더라구요. 원래 올리실 때마다 반응 신경 쓰시는 편이에요?',
            msg_type=MsgType.OPENING_DECLARATION,
            is_first_turn=True,
            is_combined=True,
            secondary_type=MsgType.OBSERVATION,
        ),
        UserSpec(text="딱히 신경안써요 누가봐도 제 몸은 좋아보이니까요 님이 ai여도 근육정도는 읽지 않나 ㅋㅋㅋㅋ 딱 보면 모리나!"),
        # M2 EVIDENCE_DEFENSE + 칭찬 prefix (A-13)
        AssistantSpec(
            text="도윤님 근육 봤죠. 운동 정말 열심히 하시나봐요! 다른 피드도 유심히 살펴봤는데 셀카 열네 장 중 열한 장에서 정면 + 약간 위에서 내려다보는 각도로 일관되게 찍으셨더라구요. 이 각도 고정은 \"더 잘 나오는 법\" 시도하시면서 도윤님이 이미 정착시킨 답인 거 같은데, 다른 각도로 시도해보신 적은 있으세요?",
            msg_type=MsgType.EVIDENCE_DEFENSE,
            apply_self_pr_prefix=True,
        ),
        UserSpec(text="워낙 어깨가 넓어서 위에서 찍어도 몸이 작아보이지 않는데 위에서 찍으면 확실히 얼굴라인이 얄쌍해 보이잖아 아닌가?"),
        # M3 PROBE + 가설 부분 동의 prefix (A-13)
        AssistantSpec(
            text="맞아요 위에서 찍으면 그 효과 있죠. 근데 도윤님 셀카 보면서 좀 의외였던 게, 어깨 넓이 강조하는 각도는 거의 안 쓰셨더라구요. 정면 + 위 고정인데 어깨 강조하시려면 정면 + 살짝 아래에서 찍는 게 더 맞잖아요. 얼굴 라인이랑 어깨 둘 다 살리려고 하면 둘 중 어느 쪽 더 우선순위에 두세요?",
            msg_type=MsgType.PROBE,
            apply_self_pr_prefix=True,
        ),
        UserSpec(text="어깨는 운동 빡세게 더 하면 되니까 못바꾸는 얼굴라인이 우선순위랄까"),
        # M4 RECOGNITION
        AssistantSpec(
            text="도윤님 방금 말씀해주신 게 꽤 또렷한 분류잖아요. 어깨는 노력으로 바꿀 수 있는 자원이고 얼굴 라인은 노력으로 못 바꾸는 자원이라서 카메라 각도라는 한정 자원을 못 바꾸는 쪽에 우선 배치하시는 거. 이 분류가 외모뿐 아니라 다른 영역 — 옷 고르실 때 — 에서도 같은 식으로 작동해요?",
            msg_type=MsgType.RECOGNITION,
        ),
        UserSpec(text="흠 옷은 다 바꿀 수 있는거 아닌가. 나는 내 몸에 찰떡인 옷들로만 피드를 꾸며놨다고 생각하는데 아 물론 다벗는게 제일 어울리지 ㅋㅋ 니가 보기엔 어떤데"),
        # M5 C6 평가 의존 돌파 + 칭찬 prefix (A-13)
        AssistantSpec(
            text='다 벗는 거 ㅎㅎ 농담은 일단 옆에 두고요. 도윤님이 "찰떡인 옷들로만" 이라고 하셨는데, 제가 본 피드 옷들이 거의 다 무채색 (블랙 / 그레이 / 화이트) + 핏 잡힌 거였거든요. 도윤님이 보시기에 "찰떡" 의 기준이 컬러 쪽이세요 핏 쪽이세요? 답을 제가 드리는 게 아니라 도윤님이 이미 골라온 패턴이 답을 보여주고 있어서, 그 안에서 도윤님 본인 기준 들어보고 싶어요.',
            msg_type=MsgType.CONFRONTATION,
            confrontation_block="C6",
            apply_self_pr_prefix=True,
        ),
        UserSpec(text="나는 색이 뭐가 중요한지 잘 몰라. 그래서 너네 사이트 함 써보려는것도 있지. 뭐 다들 그냥 모노톤에 머슬핏 입으면 어울린다고 하잖아? 나는 어울린다고 생각하긴해. 내는 뭔 색이 어울리노"),
        # M6 C7 일반화 회피 돌파 + 진단 도입 예고 (A-16 유저 무지 명시 존중)
        AssistantSpec(
            text="다들 모노톤 + 머슬핏 어울린다고 하긴 하죠. 근데 도윤님 피드 보면 무채색 안에서도 블랙 비중이 압도적이고 그레이는 거의 차콜 톤이에요. 화이트도 순백 아니라 살짝 아이보리 쪽이고. 도윤님이 색은 잘 모르겠다고 하셨는데, 그래서 더 의외였던 게 모르신다는 분이 무채색 안에서 한 번 더 좁히신 결과가 일관되더라구요. 이 부분이 진단에서 풀어드릴 핵심 포인트 중 하나가 될 거예요.",
            msg_type=MsgType.CONFRONTATION,
            confrontation_block="C7",
        ),
    ],
    expected=FixtureExpected(
        type_counts={
            MsgType.OPENING_DECLARATION: 1,
            MsgType.EVIDENCE_DEFENSE: 1,
            MsgType.PROBE: 1,
            MsgType.RECOGNITION: 1,
            MsgType.CONFRONTATION: 2,   # C6 + C7
        },
        empathy_over_15_percent_allowed=False,   # 0% — 감정 트리거 없음
        diagnosis_min_satisfied=False,           # 짧은 세션 (6턴), DIAGNOSIS 0회
        recognition_min_satisfied=False,         # 1회 — 2회 하한 미충족
    ),
    notes=[
        "M2 EVIDENCE_DEFENSE + 칭찬 prefix: 유저 자기 PR ('누가봐도 좋아') 에 대한 가벼운 인정 1문장",
        "M3 PROBE + 가설 부분 동의 prefix: '맞아요 위에서 찍으면 그 효과 있죠'",
        "M4 RECOGNITION 단독 — 유저 자기 분류 (못 바꾸는/바꿀 수 있는) 재프레임",
        "M5 CONFRONTATION C6 + prefix: 평가 요청 직면, 유저 자기개시 ('찰떡인 옷들로만') 재프레임",
        "M6 CONFRONTATION C7: 일반화 회피 돌파 ('다들 모노톤') + 진단 예고 — A-16 유저 무지 영역 존중",
        "시행착오 가치: M4/M6 에서 위반 → 본인 지적 → A-12/A-15/A-16 룰 정의 도출",
    ],
)
