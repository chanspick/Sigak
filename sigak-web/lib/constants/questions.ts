import type { InterviewQuestion } from "@/lib/types/dashboard";

// 핵심 인터뷰 질문 (sigak_dashboard.jsx에서 추출)
export const CORE_QUESTIONS: InterviewQuestion[] = [
  {
    key: "self_perception",
    label: "자기 인식",
    placeholder: "주변에서 어떤 이미지라는 말을 자주 들으세요? 본인이 느끼는 이미지도 함께 알려주세요.",
    rows: 3,
  },
  {
    key: "desired_image",
    label: "추구미",
    placeholder: "되고 싶은 이미지를 자유롭게 적어주세요. 예를 들면 '뉴진스 같은데 좀 더 성숙한 느낌'처럼요.",
    rows: 3,
  },
  {
    key: "reference_celebs",
    label: "레퍼런스 셀럽",
    placeholder: "닮았다는 말을 듣는 셀럽이 있다면 적어주세요. 여러 명도 좋습니다. 닮고 싶은 셀럽은 '추구미' 칸에 적어주시면 돼요.",
    rows: 2,
  },
  {
    key: "style_keywords",
    label: "스타일 키워드",
    placeholder: "본인 스타일을 나타내는 키워드는 무엇인가요? (시크, 캐주얼, 모던 등)",
    rows: 2,
  },
  {
    key: "daily_routine",
    label: "일상 루틴",
    placeholder: "평소 메이크업이나 스타일링은 어떻게 되시나요? 생략하는 편이라면 생략한다고 적어주세요.",
    rows: 2,
  },
];

// 웨딩 추가 질문
export const WEDDING_QUESTIONS: InterviewQuestion[] = [
  {
    key: "wedding_concept",
    label: "웨딩 컨셉",
    placeholder: "원하는 웨딩 분위기/컨셉?",
    rows: 2,
  },
  {
    key: "dress_preference",
    label: "드레스 선호",
    placeholder: "드레스 라인 선호? (A라인, 머메이드 등)",
    rows: 2,
  },
];

// 크리에이터 추가 질문
export const CREATOR_QUESTIONS: InterviewQuestion[] = [
  {
    key: "content_style",
    label: "콘텐츠 스타일",
    placeholder: "콘텐츠 장르/분위기?",
    rows: 2,
  },
  {
    key: "target_audience",
    label: "타겟 시청자",
    placeholder: "타겟 시청자층은?",
    rows: 2,
  },
  {
    key: "brand_tone",
    label: "채널 톤",
    placeholder: "채널이 추구하는 톤/이미지?",
    rows: 2,
  },
];
