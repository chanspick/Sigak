// SIGAK MVP v1.2 — 온보딩 4스텝 구조.
//
// 기존 lib/constants/questions.ts의 한국어 라벨을 재사용하되, v1.2 스펙에 맞춰
// step 분할을 재구성. 백엔드 routes/onboarding.py의 REQUIRED_FIELDS_BY_STEP과
// 필드 구성이 정확히 일치해야 함.
//
// 필수 필드 (source: sigak/routes/onboarding.py):
//   Step 1: height, weight, shoulder_width, neck_length
//   Step 2: face_concerns
//   Step 3: style_image_keywords, desired_image, makeup_level
//   Step 4: self_perception
//
// 선택 필드: reference_celebs(step 3), current_concerns(step 4).
//
// ⚠️ Q5(style_image_keywords 8개 vs 12개)는 브리프에서 미결. 현재 8개 유지.
//    retro/dark/easy/cute 추가 결정되면 options에 추가.

export type QuestionType =
  | "single_select"
  | "multi_select"
  | "text";

export interface Option {
  value: string;
  label: string;
  description?: string;
}

export interface Question {
  key: string;
  type: QuestionType;
  label: string;
  description?: string;
  required: boolean;
  options?: Option[];
  /** multi_select 최대 선택 수. */
  maxSelect?: number;
  /** text 전용 */
  placeholder?: string;
  rows?: number;
  minLength?: number;
  maxLength?: number;
}

export interface OnboardingStep {
  /** 1-indexed. */
  step: 1 | 2 | 3 | 4;
  /** 진행바 위 라벨. */
  shortLabel: string;
  /** 화면 상단 제목. */
  title: string;
  /** 제목 아래 부제 (선택). */
  subtitle?: string;
  questions: Question[];
}

// ─────────────────────────────────────────────
//  Step 1 · 체형
// ─────────────────────────────────────────────

export const STEP_1: OnboardingStep = {
  step: 1,
  shortLabel: "체형",
  title: "체형을 알려주세요",
  subtitle: "비율 분석의 기초가 돼요",
  questions: [
    {
      key: "height",
      type: "single_select",
      label: "키",
      required: true,
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
      required: true,
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
      key: "shoulder_width",
      type: "single_select",
      label: "어깨 너비",
      required: true,
      options: [
        { value: "narrow", label: "좁은 편" },
        { value: "medium", label: "보통" },
        { value: "wide", label: "넓은 편" },
      ],
    },
    {
      key: "neck_length",
      type: "single_select",
      label: "목 길이",
      required: true,
      options: [
        { value: "short", label: "짧은 편" },
        { value: "medium", label: "보통" },
        { value: "long", label: "긴 편" },
      ],
    },
  ],
};

// ─────────────────────────────────────────────
//  Step 2 · 얼굴
// ─────────────────────────────────────────────

export const STEP_2: OnboardingStep = {
  step: 2,
  shortLabel: "얼굴",
  title: "얼굴 고민을 알려주세요",
  subtitle: "모두 선택해도 좋아요",
  questions: [
    {
      key: "face_concerns",
      type: "multi_select",
      label: "얼굴 고민 영역",
      required: true,
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
  ],
};

// ─────────────────────────────────────────────
//  Step 3 · 추구미
// ─────────────────────────────────────────────

export const STEP_3: OnboardingStep = {
  step: 3,
  shortLabel: "추구미",
  title: "되고 싶은 방향을 알려주세요",
  subtitle: "이 답변이 판정의 기준이 됩니다",
  questions: [
    {
      key: "style_image_keywords",
      type: "multi_select",
      label: "끌리는 이미지",
      description: "최대 3개까지 선택해 주세요",
      required: true,
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
      key: "desired_image",
      type: "text",
      label: "추구미",
      description: "되고 싶은 이미지를 자유롭게 적어주세요",
      required: true,
      placeholder: "예: 깔끔하면서 분위기 있는 도시 여자",
      rows: 3,
      minLength: 10,
      maxLength: 300,
    },
    {
      key: "reference_celebs",
      type: "text",
      label: "레퍼런스 인물 (선택)",
      description: "닮았다는 말을 듣거나 닮고 싶은 셀럽",
      required: false,
      placeholder: "예: 김고은, 아이유",
      rows: 2,
      maxLength: 200,
    },
    {
      key: "makeup_level",
      type: "single_select",
      label: "평소 메이크업",
      required: true,
      options: [
        { value: "minimal", label: "거의 안 함", description: "선크림+립 정도" },
        { value: "basic", label: "기본", description: "베이스+눈썹+립" },
        { value: "intermediate", label: "중급", description: "아이라인+블러셔까지" },
        { value: "advanced", label: "풀 메이크업", description: "쉐딩+하이라이트까지" },
      ],
    },
  ],
};

// ─────────────────────────────────────────────
//  Step 4 · 자기 인식
// ─────────────────────────────────────────────

export const STEP_4: OnboardingStep = {
  step: 4,
  shortLabel: "자기 인식",
  title: "마지막, 자기 인식을 알려주세요",
  subtitle: "구체적일수록 판정이 정확해집니다",
  questions: [
    {
      key: "self_perception",
      type: "text",
      label: "주변의 평가",
      description: "주변에서 어떤 이미지라는 말을 자주 들으세요?",
      required: true,
      placeholder: "예: 차분해 보인다, 단단해 보인다",
      rows: 3,
      minLength: 5,
      maxLength: 300,
    },
    {
      key: "current_concerns",
      type: "text",
      label: "지금 고민 (선택)",
      description: "스타일링 관련 고민이 있다면 자유롭게 적어주세요",
      required: false,
      placeholder: "예: 머리가 길어지면 무거워 보여요",
      rows: 3,
      maxLength: 500,
    },
  ],
};

export const ONBOARDING_STEPS: readonly OnboardingStep[] = [
  STEP_1,
  STEP_2,
  STEP_3,
  STEP_4,
] as const;

/** 1-indexed step number → OnboardingStep. 범위 밖이면 null. */
export function getStep(n: number): OnboardingStep | null {
  if (n < 1 || n > 4) return null;
  return ONBOARDING_STEPS[n - 1];
}
