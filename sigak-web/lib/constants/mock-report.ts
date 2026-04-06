import type { ReportData } from "@/lib/types/report";

// 리포트 목 데이터 (UX.md API 응답 구조 기반)
export const MOCK_REPORT: ReportData = {
  id: "report_abc123",
  user_name: "홍길동",
  access_level: "full",
  pending_level: null,
  sections: [
    {
      id: "cover",
      locked: false,
      content: {
        title: "시각 리포트",
        user_name: "홍길동",
        date: "2026-04-15",
        tier: "basic",
      },
    },
    {
      id: "executive_summary",
      locked: false,
      content: {
        summary:
          "전반적으로 따뜻하고 부드러운 인상을 가진 얼굴형입니다. 웜톤 베이스에 밝은 피부톤으로, 자연스러운 메이크업이 잘 어울립니다.",
      },
    },
    {
      id: "face_structure",
      locked: false,
      content: {
        face_type: "타원형",
        ratio: "1:1.4",
        features: ["이마 넓이 적정", "턱선 부드러움", "광대 약간 돌출"],
      },
    },
    {
      id: "skin_analysis",
      locked: true,
      unlock_level: "standard",
      teaser: { headline: "웜톤 · 밝은 편" },
      content: {
        tone: "웜톤",
        brightness: "밝은 편",
        recommended_colors: ["코랄", "피치", "웜베이지"],
        avoid_colors: ["블루베이스 핑크", "쿨그레이"],
      },
    },
    {
      id: "face_interpretation",
      locked: true,
      unlock_level: "standard",
      teaser: { headline: "얼굴 구조 심층 분석 완료" },
      content: {
        overall_impression:
          "부드러운 턱라인에 눈꼬리가 살짝 올라간 형태로, 따뜻하면서도 세련된 인상을 줍니다. 전체적인 이목구비 비율이 균형 잡혀 있어 자연스러운 매력이 돋보입니다.",
        feature_interpretations: [
          { feature: "jaw_angle", label: "턱선", interpretation: "부드러운 라운드형 턱선으로, 친근하고 편안한 인상을 줍니다." },
          { feature: "eye_tilt", label: "눈매", interpretation: "눈꼬리가 살짝 올라간 형태로, 세련된 느낌을 더합니다." },
          { feature: "lip_fullness", label: "입술", interpretation: "적당한 볼륨감으로 자연스러운 인상을 완성합니다." },
        ],
        harmony_note: "이목구비 간 비율이 조화로워 다양한 스타일 시도가 가능합니다.",
        distinctive_points: ["부드러운 턱라인", "살짝 올라간 눈꼬리", "균형 잡힌 이마 비율"],
      },
    },
    {
      id: "gap_analysis",
      locked: true,
      unlock_level: "standard",
      teaser: { headline: "따뜻한 첫사랑 → 부드럽고 성숙" },
      content: {
        current_type: "따뜻한 첫사랑",
        current_type_id: 1,
        aspiration_type: "부드럽고 성숙",
        aspiration_type_id: 5,
        gap_summary:
          "현재 따뜻하고 발랄한 인상에서, 좀 더 우아하고 성숙한 분위기로 이동하고 싶어하시는 방향입니다. 기본 인상의 따뜻함은 유지하면서 성숙도만 높이는 전략이 효과적입니다.",
        direction_items: [
          {
            axis: "maturity",
            label: "성숙도",
            from: "프레시",
            to: "성숙",
            recommendation: "아이브로우 각도를 살짝 높이고, 립 컬러를 로즈 계열로 전환하면 자연스럽게 성숙한 느낌을 줄 수 있습니다.",
          },
          {
            axis: "intensity",
            label: "강도",
            from: "내추럴",
            to: "미디엄",
            recommendation: "아이라인을 살짝 연장하고 컨투어링을 가볍게 추가하면 이목구비가 좀 더 또렷해 보입니다.",
          },
        ],
      },
    },
    {
      id: "action_plan",
      locked: true,
      unlock_level: "full",
      teaser: {
        categories: ["메이크업 HIGH", "헤어 HIGH", "스타일링 MEDIUM"],
      },
      content: {
        items: [
          {
            category: "메이크업",
            priority: "HIGH",
            recommendations: ["코랄톤 립 추천", "아이브로우 아치형 조정"],
          },
          {
            category: "헤어",
            priority: "HIGH",
            recommendations: ["레이어드컷 추천", "웜브라운 컬러"],
          },
          {
            category: "스타일링",
            priority: "MEDIUM",
            recommendations: ["니트+와이드팬츠 조합", "톤온톤 코디"],
          },
        ],
      },
    },
    {
      id: "type_reference",
      locked: true,
      unlock_level: "full",
      teaser: { headline: "'따뜻한 첫사랑' 유형과 87% 유사" },
      content: {
        type_name: "따뜻한 첫사랑",
        type_id: 1,
        similarity: 87,
        reasons: ["부드러운 턱라인 유사", "웜톤 피부톤", "둥근 눈매와 친근한 인상"],
        styling_tips: ["내추럴 웜톤 메이크업 강화", "부드러운 웨이브 헤어"],
        runner_ups: [
          { type_name: "부드럽고 성숙", type_id: 5, similarity: 78 },
          { type_name: "강인하고 따뜻", type_id: 6, similarity: 72 },
        ],
      },
    },
    {
      id: "trend_context",
      locked: true,
      unlock_level: "full",
      teaser: null,
      content: {
        trends: [
          {
            title: "2026 S/S 트렌드",
            description: "글로우 스킨, 내추럴 브로우, 소프트 코랄 립",
          },
        ],
      },
    },
  ],
  paywall: {
    standard: {
      price: 5000,
      label: "₩5,000 잠금 해제",
      method: "manual",
    },
    full: {
      price: 15000,
      label: "+₩15,000 잠금 해제",
      total_note: "이전 결제 포함 총 ₩20,000",
      method: "manual",
    },
  },
  payment_account: {
    bank: "카카오뱅크",
    number: "3333-00-0000000",
    holder: "홍한진(시각)",
    kakao_link: "kakaotalk://send?",
  },
};
