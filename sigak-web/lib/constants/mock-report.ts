import type { ReportData } from "@/lib/types/report";

// 리포트 목 데이터 (UX.md API 응답 구조 기반)
export const MOCK_REPORT: ReportData = {
  id: "report_abc123",
  user_name: "홍길동",
  access_level: "free",
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
      id: "coordinate_map",
      locked: true,
      unlock_level: "standard",
      teaser: { headline: "4축 미감 분석 완료" },
      content: {
        axes: ["클래식-모던", "내추럴-글램", "큐트-시크", "캐주얼-포멀"],
        position: [0.3, 0.6, 0.4, 0.5],
        target: [0.5, 0.7, 0.3, 0.6],
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
      id: "celeb_reference",
      locked: true,
      unlock_level: "full",
      teaser: { headline: "수지와 85% 유사" },
      content: {
        celeb: "수지",
        similarity: 85,
        reasons: ["이목구비 비율 유사", "웜톤 피부톤", "부드러운 인상"],
        styling_tips: ["수지의 내추럴 메이크업 참고", "긴 생머리 스타일"],
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
