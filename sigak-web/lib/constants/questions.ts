import type { InterviewQuestion } from "@/lib/types/dashboard";

// ─────────────────────────────────────────────
//  STEP 1: 얼굴 & 체형 (스코어링 엔진 입력)
// ─────────────────────────────────────────────

export const FACE_BODY_QUESTIONS: InterviewQuestion[] = [
  {
    key: "height",
    type: "single_select",
    label: "키",
    description: "체형 비율 분석에 활용돼요",
    options: [
      { value: "under_155", label: "155cm 이하" },
      { value: "155_160", label: "155~160cm" },
      { value: "160_165", label: "160~165cm" },
      { value: "165_170", label: "165~170cm" },
      { value: "170_175", label: "170~175cm" },
      { value: "over_175", label: "175cm 이상" },
    ],
  },
  {
    key: "weight",
    type: "single_select",
    label: "체중",
    description: "어깨/목 비율 맥락 파악에 사용돼요",
    options: [
      { value: "under_45", label: "45kg 이하" },
      { value: "45_50", label: "45~50kg" },
      { value: "50_55", label: "50~55kg" },
      { value: "55_60", label: "55~60kg" },
      { value: "60_65", label: "60~65kg" },
      { value: "65_70", label: "65~70kg" },
      { value: "70_80", label: "70~80kg" },
      { value: "over_80", label: "80kg 이상" },
    ],
  },
  {
    key: "face_concerns",
    type: "multi_select",
    label: "얼굴 고민 영역",
    description: "고민되는 부분을 모두 선택해 주세요",
    options: [
      { value: "wide_face", label: "넓은 얼굴" },
      { value: "long_face", label: "긴 얼굴" },
      { value: "short_face", label: "짧은 얼굴" },
      { value: "square_jaw", label: "각진 턱" },
      { value: "prominent_cheekbone", label: "광대" },
      { value: "short_forehead", label: "짧은 이마" },
      { value: "wide_forehead", label: "넓은 이마" },
      { value: "large_nose", label: "코가 큰 편" },
      { value: "mouth_protrusion", label: "돌출입" },
      { value: "long_midface", label: "긴 중안부" },
      { value: "asymmetry", label: "좌우 비대칭" },
      { value: "none", label: "특별한 고민 없음" },
    ],
  },
  {
    key: "neck_length",
    type: "single_select",
    label: "목 길이",
    options: [
      { value: "short", label: "짧은 편" },
      { value: "medium", label: "보통" },
      { value: "long", label: "긴 편" },
    ],
  },
  {
    key: "shoulder_width",
    type: "single_select",
    label: "어깨 너비",
    options: [
      { value: "narrow", label: "좁은 편" },
      { value: "medium", label: "보통" },
      { value: "wide", label: "넓은 편" },
    ],
  },
];

// ─────────────────────────────────────────────
//  STEP 2: 현재 헤어 상태
// ─────────────────────────────────────────────

export const HAIR_STATE_QUESTIONS: InterviewQuestion[] = [
  {
    key: "hair_texture",
    type: "single_select",
    label: "모질",
    options: [
      { value: "straight", label: "직모" },
      { value: "wavy", label: "웨이브" },
      { value: "curly", label: "곱슬" },
    ],
  },
  {
    key: "hair_thickness",
    type: "single_select",
    label: "모발 굵기",
    options: [
      { value: "thin", label: "가는 편" },
      { value: "medium", label: "보통" },
      { value: "thick", label: "굵은 편" },
    ],
  },
  {
    key: "hair_volume",
    type: "single_select",
    label: "숱",
    options: [
      { value: "low", label: "적은 편" },
      { value: "medium", label: "보통" },
      { value: "high", label: "많은 편" },
    ],
  },
  {
    key: "current_length",
    type: "single_select",
    label: "현재 기장",
    options: [
      { value: "short", label: "숏컷" },
      { value: "bob", label: "단발 (턱선)" },
      { value: "medium", label: "중단발 (어깨~쇄골)" },
      { value: "long", label: "긴머리 (쇄골 아래)" },
    ],
  },
  {
    key: "current_bangs",
    type: "single_select",
    label: "현재 앞머리",
    options: [
      { value: "full", label: "풀뱅" },
      { value: "see_through", label: "시스루뱅" },
      { value: "side", label: "사이드뱅 / 가르마" },
      { value: "grown_out", label: "기르는 중" },
      { value: "none", label: "없음" },
    ],
  },
  {
    key: "current_perm",
    type: "single_select",
    label: "현재 펌",
    options: [
      { value: "none", label: "없음 (생머리)" },
      { value: "c_curl", label: "C컬펌" },
      { value: "s_curl", label: "S컬펌" },
      { value: "hippie", label: "히피펌 / 볼드펌" },
      { value: "volume", label: "볼륨펌 / 뿌리펌" },
      { value: "other", label: "기타" },
    ],
  },
  {
    key: "root_volume_experience",
    type: "yes_no",
    label: "뿌리볼륨 경험",
    description: "뿌리볼륨펌이나 매직기 뿌리볼륨을 해본 적 있나요?",
  },
];

// ─────────────────────────────────────────────
//  STEP 3: 스타일 & 추구미
// ─────────────────────────────────────────────

export const STYLE_QUESTIONS: InterviewQuestion[] = [
  {
    key: "self_perception",
    type: "text",
    label: "주변의 평가",
    placeholder: "주변에서 어떤 이미지라는 말을 자주 들으세요? (5자 이상)",
    rows: 2,
    minLength: 5,
    maxLength: 300,
  },
  {
    key: "desired_image",
    type: "text",
    label: "추구미",
    placeholder: "되고 싶은 이미지를 자유롭게 적어주세요 (10자 이상)",
    description: "이 답변이 리포트의 핵심 방향을 결정해요",
    rows: 2,
    minLength: 10,
    maxLength: 300,
  },
  {
    key: "reference_celebs",
    type: "text",
    label: "레퍼런스",
    placeholder: "닮았다는 말을 듣거나 닮고 싶은 셀럽",
    rows: 2,
    required: false,
    maxLength: 200,
  },
  {
    key: "style_image_keywords",
    type: "multi_select",
    label: "원하는 이미지",
    description: "끌리는 키워드를 최대 3개 선택해 주세요",
    maxSelect: 3,
    options: [
      { value: "lovely", label: "러블리" },
      { value: "innocent", label: "청순" },
      { value: "chic", label: "도도 / 시크" },
      { value: "elegant", label: "우아 / 차분" },
      { value: "unique", label: "개성" },
      { value: "modern", label: "모던 / 미니멀" },
      { value: "natural", label: "내추럴" },
      { value: "sexy", label: "섹시 / 글래머" },
    ],
  },
  {
    key: "makeup_level",
    type: "single_select",
    label: "메이크업 난이도",
    description: "평소 메이크업은 어느 정도?",
    options: [
      { value: "minimal", label: "거의 안 함", description: "선크림+립 정도" },
      { value: "basic", label: "기본", description: "베이스+눈썹+립" },
      { value: "intermediate", label: "중급", description: "아이라인+블러셔까지" },
      { value: "advanced", label: "풀 메이크업", description: "쉐딩+하이라이트까지" },
    ],
  },
  {
    key: "current_concerns",
    type: "text",
    label: "추가 고민",
    placeholder: "스타일링 관련 고민이 있다면 자유롭게 적어주세요",
    description: "구체적으로 적을수록 결과지에 직접 반영돼요!",
    rows: 2,
    required: false,
    maxLength: 500,
  },
];

// ─────────────────────────────────────────────
//  티어별 추가 질문
// ─────────────────────────────────────────────

export const WEDDING_QUESTIONS: InterviewQuestion[] = [
  {
    key: "wedding_concept",
    type: "text",
    label: "웨딩 컨셉",
    placeholder: "원하는 웨딩 분위기/컨셉은?",
    rows: 2,
  },
  {
    key: "dress_preference",
    type: "single_select",
    label: "드레스 선호",
    options: [
      { value: "a_line", label: "A라인" },
      { value: "mermaid", label: "머메이드" },
      { value: "empire", label: "엠파이어" },
      { value: "ball_gown", label: "볼가운" },
      { value: "undecided", label: "미정" },
    ],
  },
];

export const CREATOR_QUESTIONS: InterviewQuestion[] = [
  {
    key: "content_style",
    type: "text",
    label: "콘텐츠 스타일",
    placeholder: "콘텐츠 장르/분위기?",
    rows: 2,
  },
  {
    key: "target_audience",
    type: "text",
    label: "타겟 시청자",
    placeholder: "타겟 시청자층은?",
    rows: 2,
  },
  {
    key: "brand_tone",
    type: "text",
    label: "채널 톤",
    placeholder: "채널이 추구하는 톤/이미지?",
    rows: 2,
  },
];

// ─────────────────────────────────────────────
//  스텝 정의
// ─────────────────────────────────────────────

export interface StepConfig {
  title: string;
  subtitle: string;
  questions: InterviewQuestion[];
}

/** 티어에 따른 전체 스텝 목록 반환 */
export function getSteps(tier: string): StepConfig[] {
  const steps: StepConfig[] = [
    {
      title: "얼굴 & 체형",
      subtitle: "헤어/메이크업 추천의 기초가 됩니다",
      questions: FACE_BODY_QUESTIONS,
    },
    {
      title: "현재 헤어",
      subtitle: "지금 상태를 알아야 정확한 추천이 가능해요",
      questions: HAIR_STATE_QUESTIONS,
    },
    {
      title: "스타일 & 추구미",
      subtitle: "원하는 방향을 알려주세요",
      questions: STYLE_QUESTIONS,
    },
  ];

  // 티어별 추가 스텝
  if (tier === "wedding") {
    steps.push({
      title: "웨딩",
      subtitle: "웨딩 맞춤 추천을 위한 추가 질문",
      questions: WEDDING_QUESTIONS,
    });
  } else if (tier === "creator") {
    steps.push({
      title: "크리에이터",
      subtitle: "채널 맞춤 추천을 위한 추가 질문",
      questions: CREATOR_QUESTIONS,
    });
  }

  return steps;
}
