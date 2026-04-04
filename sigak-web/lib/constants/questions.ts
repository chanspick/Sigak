import type { InterviewQuestion } from "@/lib/types/dashboard";

// 핵심 인터뷰 질문 (sigak_dashboard.jsx에서 추출)
export const CORE_QUESTIONS: InterviewQuestion[] = [
  {
    key: "self_perception",
    label: "자기 인식",
    placeholder: '본인이 생각하는 자기 이미지는? (주변에서 뭐라고 하는지도)',
    rows: 3,
  },
  {
    key: "desired_image",
    label: "추구미",
    placeholder: '되고 싶은 이미지? 자유롭게 표현 ("뉴진스 같은데 좀 더 성숙")',
    rows: 3,
  },
  {
    key: "reference_celebs",
    label: "레퍼런스 셀럽",
    placeholder: "닮고 싶은 / 닮았다는 말 듣는 셀럽 (여러 명 OK)",
    rows: 2,
  },
  {
    key: "style_keywords",
    label: "스타일 키워드",
    placeholder: "본인 스타일을 키워드로? (시크, 캐주얼, 모던 등)",
    rows: 2,
  },
  {
    key: "current_concerns",
    label: "현재 고민",
    placeholder: "외모에서 바꾸고 싶은 점은?",
    rows: 3,
  },
  {
    key: "daily_routine",
    label: "일상 루틴",
    placeholder: "평소 메이크업/스타일링 루틴 (안 하면 안 한다고)",
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
