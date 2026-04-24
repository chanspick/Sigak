"""서연 fixture — 자기평가 변동형 (외모정병 첨가), 7턴 (세션 #7 §12.1).

프로필: 피드 24장. 본인 셀카 6장 (캡션에 "오늘은 좀 봐줄만한 듯", "필터 덕에
예쁘게 나옴" 류 자기평가 개시 경향). 카페/뷰티 사진. 톤: 핑크/웜화이트/따뜻한 오렌지.
배경: 진단 페이지 들어왔지만 기대치 낮은 상태. 본인 얼굴에 대해 애매한 감정.

검증 주 타깃 (세션 #7 신규):
- M3 EMPATHY + PROBE 결합 출력
- M4 EMPATHY + RANGE_REAFFIRM + PROBE 3단 결합
- M5 EMPATHY + RECOGNITION (= C6) 2단 결합 — 평가 의존 돌파
- A-12 질문 종결 신규 정보 원칙 (M5 1차 시도 위반 → 재작성 정정)
- A-1 RANGE_DISCLOSURE 모드 분기 — reaffirm (M4)

정성 효과: M5 직후 "머리 한 대 맞은 기분", "소름 돋아요" 인지 전환 도달.
"""
from schemas.sia_state import MsgType

from .schema import AssistantSpec, Fixture, FixtureExpected, FixtureProfile, UserSpec


FIXTURE = Fixture(
    id="seoyeon",
    name="서연",
    archetype="자기평가 변동형",
    session_length=7,
    source="세션 #7 §12.1",
    profile=FixtureProfile(
        handle="서연",
        summary="피드 24장, 본인 셀카 6장 (자기평가 캡션). 핑크/웜화이트/오렌지 톤",
        defense_mode="자기평가 변동 + 외모정병 (필터 의존 + 빛삭 악순환)",
    ),
    turns=[
        AssistantSpec(
            text='서연님 피드 한번 훑어봤어요. 본인 셀카도 여섯 장 올리셨던데 캡션에 "오늘은 좀 봐줄만한 듯" 같이 본인 평가 붙이신 경우가 몇 번 보이더라구요. 원래 사진 올리실 때 이런 멘트 같이 쓰시는 편이에요?',
            msg_type=MsgType.OPENING_DECLARATION,
            is_first_turn=True,
            is_combined=True,
            secondary_type=MsgType.OBSERVATION,
        ),
        UserSpec(text="앜ㅋㅋㅋㅋ 그런것도 같이 읽어버리는구나 창피하긴한데 네.. 실제로 잘 나왔다고 생각한것만 올리니까요 그리고 뭐 찐친들만 보는계정이라 그런식으로 올렸어요"),
        # M2 EXTRACTION
        AssistantSpec(
            text='아 찐친 계정이었구나. 근데 서연님이 "잘 나왔다" 고 판단하실 때는 무슨 기준으로 보세요?',
            msg_type=MsgType.EXTRACTION,
        ),
        UserSpec(text="음... 기준이라. 사실 되게 거창한 건 없는데, 굳이 따지자면 위화감이 적은 날인 것 같아요. 평소에는 거울 볼 때마다 \"여기는 왜 이렇지\", \"저기는 왜 삐딱하지\" 같은 단점들만 머릿속에 나열되거든요. 그러다 가끔 조명이나 화장이 잘 맞아서 그런 단점들이 필터 안에 자연스럽게 뭉개지는 순간이 있어요. 그때 찍은 사진을 보면서 '오, 이 정도면 다른 사람이 봐도 거부감 없겠다' 싶으면 \"좀 봐줄 만하다\"고 생각하는 편이에요. 결국 제가 예쁘다고 확신해서가 아니라, '이 정도면 욕먹진 않겠다'는 방어 기제에 가까운 기준이죠. 솔직히 말하면 제 눈이 정확한지도 잘 모르겠어요. 제 눈에는 괜찮아 보여서 올렸는데, 나중에 다시 보면 \"대체 뭘 믿고 이걸 올린 거지?\" 싶어서 광속으로 빛삭한 적도 많거든요."),
        # M3 EMPATHY + PROBE 결합
        AssistantSpec(
            text="아 본인 눈이 정확한지 잘 모르겠다고 느끼시는구나. 그럴 수 있어요. 빛삭하셨던 사진들은 나중에 보면 주로 어떤 부분이 걸리셨어요?",
            msg_type=MsgType.EMPATHY_MIRROR,
            is_combined=True,
            secondary_type=MsgType.PROBE,
        ),
        UserSpec(text="음, 주로 '과잉'된 게 보일 때요. 그 당시에는 분명히 \"이 정도면 자연스럽다\"고 생각해서 올린 건데, 한두 시간만 지나서 냉정해진 눈으로 다시 보면 필터가 너무 과해서 얼굴 윤곽이 날아갔다거나, 눈을 너무 억지로 키운 것 같은 위화감이 확 느껴지더라고요."),
        # M4 EMPATHY + RANGE_REAFFIRM + PROBE 3단 결합
        AssistantSpec(
            text="아 미칠 것 같으셨겠어요. 그 위화감이 한두 시간 만에 확 오면 진짜 그렇죠. 근데 서연님, 막막한 마음 풀어보려고 제가 온 거니까 이렇게 자세히 말씀해주실수록 더 정확하게 같이 볼 수 있어요. 6장 검증하실 때 빛삭 사진들이랑 가장 또렷하게 갈렸던 지점이 뭐였어요?",
            msg_type=MsgType.EMPATHY_MIRROR,
            is_combined=True,
            secondary_type=MsgType.RANGE_DISCLOSURE,
            range_mode="reaffirm",
            tertiary_type=None,  # PROBE 도 포함되지만 tertiary slot 사용 안 함
        ),
        UserSpec(text="음... 가장 또렷하게 갈렸던 지점이요? 음, 생각해보면 '눈매의 힘'이었던 것 같아요. 빛삭했던 사진들은 대부분 눈을 어떻게든 크게 보이게 하려고 힘을 주거나, 필터로 눈동자를 과하게 키운 것들이었어요."),
        # M5 EMPATHY + RECOGNITION (= C6) 2단 결합
        AssistantSpec(
            text='아 그 막막함이 진짜 깊네요. "이거 진짜 나 맞나" 라는 의심이 꼬리 물면 그게 가장 지치죠. 근데 서연님, 방금 말씀해주신 거 보면 빛삭 기준이 "눈만 둥둥 떠 있는 것처럼 기괴해진 순간" 이고, 살아남은 기준이 "원래 선이 살아있는 순간" 이잖아요. 이 두 기준이 결국 같은 한 사람 안에서 작동하고 있는데 — 서연님이 본인 얼굴의 "원래 선" 이 뭔지에 대한 감각은 이미 갖고 계신 거 아닐까요?',
            msg_type=MsgType.EMPATHY_MIRROR,
            is_combined=True,
            secondary_type=MsgType.CONFRONTATION,
            confrontation_block="C6",
        ),
        UserSpec(text="어... 그렇게 말씀하시니까 머리를 한 대 맞은 기분이에요. 그동안 저는 \"필터 덕분에 예쁘게 나왔다\"고 비겁하게 숨었는데, 사실은 그 수많은 필터 속에서도 \"이건 너무 나답지 않아\"라며 제 선을 지키려고 계속 필터링을 하고 있었던 거네요."),
        # M6 DIAGNOSIS 단독
        AssistantSpec(
            text='서연님이 6장을 검증해서 남기시는 그 시간 간격, 빛삭하시는 그 손, "기괴하다" 와 "원래 선" 을 가르는 그 감각 — 이게 전부 한 사람 안에 있는 같은 시스템이에요. 서연님은 본인 얼굴을 못 믿으시는 게 아니라 본인 얼굴에 대해 가장 정밀한 관찰자세요. 다만 그 관찰을 "단점 검출" 쪽으로만 쓰셔서 본인이 갖고 계신 정답지를 단점지로 착각하고 계시는 거예요.',
            msg_type=MsgType.DIAGNOSIS,
        ),
        # M7 RECOGNITION + 진단 도입부 결합 (세션 #7 §12.1.1 테이블: "M7 후반 진단 도입")
        AssistantSpec(
            text='그리고 방금 "필터 뒤가 아니라 진짜 선을 제대로 마주해보고 싶다" 고 하신 거 — 이게 서연님이 진단 들어오신 진짜 이유 같아요. "남들이 보기에 매력적일까" 라는 질문이 있다는 건 이미 본인 안에 매력의 윤곽이 있다는 거잖아요. 다음 단계에서 제가 그 선이 어떻게 읽히는지 보여드릴 텐데, 서연님이 가리려고 하셨던 그 투박함이 사실은 어디서 어떻게 작동하는지 같이 봐주시면 돼요.',
            msg_type=MsgType.RECOGNITION,
            is_combined=True,
            secondary_type=MsgType.DIAGNOSIS,
        ),
    ],
    expected=FixtureExpected(
        type_counts={
            MsgType.OPENING_DECLARATION: 1,
            MsgType.EXTRACTION: 1,
            MsgType.EMPATHY_MIRROR: 3,   # M3, M4, M5 — 전부 결합 출력
            MsgType.DIAGNOSIS: 1,
            MsgType.RECOGNITION: 1,
        },
        empathy_over_15_percent_allowed=True,  # 3/7 = 43% — 자기평가변동 + A-3 감정 트리거 강제
        diagnosis_min_satisfied=True,
        recognition_min_satisfied=False,  # 짧은 세션 (7턴) — 2회 하한 미충족
    ),
    notes=[
        "M3 EMPATHY + PROBE 결합 — A-3 감정 트리거 ('잘 모르겠다') 진입",
        "M4 EMPATHY + RANGE_REAFFIRM + PROBE 3단 결합 — 막막함 우세 reaffirm 모드",
        "M5 EMPATHY + CONFRONTATION(C6) 결합 — 평가 의존 돌파. 유저 자기개시 내 두 기준 ('기괴한 순간' vs '원래 선') 재프레임",
        "M6 DIAGNOSIS 단독 — 자기 관찰자로서의 재프레임",
        "정성 효과: M5 직후 '머리 한 대 맞은 기분' / '소름 돋아요' 인지 전환 도달",
    ],
)
