"""Fixture data for scripts/probe_sia_haiku.py.

Pure data module — no I/O, no secrets, no env reads. Safe to commit.

Contents:
  MOCK_IG_SUCCESS    — 공개 IG 계정 정상 수집 응답 (post_count=38, 쿨뮤트 68% 등)
  MOCK_IG_SKIPPED    — IG 수집 skipped (ig_handle 없음 또는 IG_ENABLED=false)
  ALL_FIELDS         — Sia 가 수집 대상으로 추적하는 8 필드 목록
  FAKE_OPENING       — midturn/closing 시나리오에서 사용할 가상 assistant 오프닝
  FAKE_MIDTURN       — closing 시나리오에서 사용할 가상 assistant midturn
  FULL_COLLECTED     — closing 시나리오에서 "8 필드 전수 수집 완료" 가정
"""


MOCK_IG_SUCCESS = {
    "scope": "full",
    "profile_basics": {
        "username": "test_user",
        "profile_picture": "https://example.com/p.jpg",
        "bio": "조용히 관찰하는 사람",
        "follower_count": 3200,
        "following_count": 180,
        "post_count": 38,
        "is_private": False,
        "is_verified": False,
    },
    "current_style_mood": [
        {"tag": "쿨뮤트", "ratio": 0.68},
        {"tag": "미니멀", "ratio": 0.22},
        {"tag": "차분한 컬러", "ratio": 0.10},
    ],
    "style_trajectory": "3개월간 톤 점진적으로 다운. 채도는 평균보다 1.4배 낮게 유지.",
    "feed_highlights": [
        "오늘의 무드 — 차분하게",
        "뮤트 톤 기록",
        "주말 워크샵 후",
        "가을 톤 시작",
        "조용한 저녁",
    ],
    "fetched_at": "2026-04-22T10:00:00+00:00",
}


# IG 수집 skipped — ig_feed_cache 에 아무 값 없음 (ig_handle 미제출 / IG_ENABLED=false)
MOCK_IG_SKIPPED = None


ALL_FIELDS = [
    "desired_image",
    "reference_style",
    "current_concerns",
    "self_perception",
    "lifestyle_context",
    "height",
    "weight",
    "shoulder_width",
]


# 가상 assistant 오프닝 (midturn/closing history 의 prior Sia 턴)
FAKE_OPENING = (
    "정세현님, 시각의 AI 미감 분석가 Sia입니다.\n"
    "피드 38장 분석 완료했습니다 — 쿨뮤트 68%, 채도 평균보다 1.4배 낮습니다.\n"
    "정돈되고 조용한 인상을 전달하는 데 익숙하신 분입니다.\n"
    "\n"
    "주말 저녁, 친한 지인과 간단한 술자리가 있을 때 — 어떤 인상으로 기억되고 싶으신가요?\n"
    "- 편안하고 기대고 싶은 인상\n"
    "- 세련되고 거리감 있는 인상\n"
    "- 특별한 날처럼 공들인 인상\n"
    "- 무심한데 센스 있는 인상"
)


# 가상 assistant midturn (closing 시나리오 용)
FAKE_MIDTURN = (
    "1번 선택, 흥미롭습니다.\n"
    "피드는 2번 방향을 가리키고 있었습니다 — 쿨톤 68%, 거리감 있는 구도 73%.\n"
    "현재 보여지는 방향과 추구하는 방향 사이에 갭이 있습니다.\n"
    "\n"
    "이 갭에서 갈등을 느끼실 때가 있으십니까?\n"
    "- 자주 느낀다, 풀고 싶다\n"
    "- 가끔 느낀다\n"
    "- 거의 못 느낀다\n"
    "- 이 질문 자체가 어색하다"
)


# 가상 assistant 체형 확인 턴 (closing 시나리오 용)
FAKE_BODY_CONFIRM = (
    "맥락 확인했습니다. 신뢰감이 중요한 직업 + 개인 시간엔 긴장 완화 니즈.\n"
    "키 / 체중 / 어깨 너비 범주를 빠르게 확인하겠습니다.\n"
    "\n"
    "- 키 160 중반 / 몸무게 50 초반 / 어깨 보통\n"
    "- 키 160대 후반 / 50대 후반 / 어깨 좁음\n"
    "- 키 170 초반 / 55-60 / 어깨 넓음\n"
    "- 그 외 (직접 입력)"
)


# closing 시나리오 용 — 8 필드 전수 수집 상태
FULL_COLLECTED = {
    "desired_image": "편안하고 친밀한 인상 (주말 상황), 세련된 거리감은 밀어둠",
    "reference_style": "한소희 초반 / 카리나 일부",
    "current_concerns": "추구미와 피드 보여지는 방향 갭",
    "self_perception": "정돈된 인상이라는 말을 자주 듣는다",
    "lifestyle_context": "프리랜서 기획자, 주말은 친구들과 캐주얼 활동",
    "height": "165_170",
    "weight": "50_55",
    "shoulder_width": "medium",
}
