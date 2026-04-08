import type { ReportData } from "@/lib/types/report";

// 리포트 목 데이터 (UX.md API 응답 구조 기반)
// 파이프라인 FaceFeatures + coordinate.py 수치 기반 정량 데이터
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
        face_length_ratio: 1.38,
        jaw_angle: 128.5,
        symmetry_score: 0.924,
        golden_ratio_score: 0.782,
        metrics: [
          {
            key: "jaw_angle",
            label: "턱 각도",
            value: 128.5,
            unit: "\u00B0",
            percentile: 62,
            context: "평균(124\u00B0) 대비 넓은 편 \u2014 부드러운 라인",
            min_value: 110,
            max_value: 150,
            min_label: "날카로운 110\u00B0",
            max_label: "둥근 150\u00B0",
          },
          {
            key: "face_length_ratio",
            label: "얼굴 종횡비",
            value: 1.38,
            unit: "",
            percentile: 55,
            context: "표준 타원형 범위(1.3-1.5)",
            min_value: 1.1,
            max_value: 1.6,
            min_label: "넓은 1.1",
            max_label: "긴 1.6",
          },
          {
            key: "symmetry_score",
            label: "좌우 대칭도",
            value: 0.924,
            unit: "",
            percentile: 78,
            context: "상위 22% \u2014 균형 잡힌 구조",
            min_value: 0.7,
            max_value: 1.0,
            min_label: "비대칭 0.7",
            max_label: "대칭 1.0",
          },
          {
            key: "golden_ratio_score",
            label: "황금비 근접도",
            value: 0.782,
            unit: "",
            percentile: 65,
            context: "조화로운 비율",
            min_value: 0.5,
            max_value: 1.0,
            min_label: "낮음 0.5",
            max_label: "황금비 1.0",
          },
          {
            key: "cheekbone_prominence",
            label: "광대 돌출도",
            value: 0.35,
            unit: "",
            percentile: 45,
            context: "보통 수준",
            min_value: 0,
            max_value: 0.8,
            min_label: "평면 0",
            max_label: "돌출 0.8",
          },
        ],
      },
    },
    {
      id: "skin_analysis",
      locked: true,
      unlock_level: "standard",
      teaser: { headline: "웜톤 \u00B7 밝은 편" },
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
          "턱 각도 128.5\u00B0(상위 38%)와 눈꼬리 기울기 +3.2\u00B0(상위 28%)의 조합이 만드는 인상 \u2014 친근함 위에 세련된 날카로움이 섞인 독특한 밸런스입니다.",
        feature_interpretations: [
          {
            feature: "jaw_angle",
            label: "턱선",
            value: 128.5,
            unit: "\u00B0",
            percentile: 62,
            range_label: "상위 38%의 둥근 턱라인",
            interpretation:
              "128.5\u00B0는 한국 여성 평균(124\u00B0)보다 4.5\u00B0 넓습니다. 이 범위(125-135\u00B0)는 라운드형으로 분류되며, 친근하고 편안한 첫인상에 기여합니다.",
            min_label: "날카로운",
            max_label: "둥근",
          },
          {
            feature: "eye_tilt",
            label: "눈꼬리 기울기",
            value: 3.2,
            unit: "\u00B0",
            percentile: 72,
            range_label: "평균보다 올라간 편",
            interpretation:
              "눈꼬리가 +3.2\u00B0 올라가 있어 평균(1.5\u00B0) 대비 뚜렷한 상향 각도입니다. 둥근 턱(128.5\u00B0)이 주는 부드러움에 세련된 날카로움을 더합니다.",
            min_label: "처진 -5\u00B0",
            max_label: "올라간 +8\u00B0",
          },
          {
            feature: "lip_fullness",
            label: "입술 볼륨",
            value: 0.048,
            unit: "",
            percentile: 55,
            range_label: "중간 볼륨",
            interpretation:
              "입술 높이/얼굴 높이 비율 0.048은 중간 범위입니다. 과하지 않은 자연스러운 볼륨으로, 전체 인상의 균형을 유지합니다.",
            min_label: "얇은",
            max_label: "풍성한",
          },
        ],
        harmony_note:
          "턱 각도(128.5\u00B0)와 눈꼬리 기울기(+3.2\u00B0)의 조합은 전체의 약 15%에서만 나타나는 패턴으로, '부드러운데 날카로운' 인상의 근거입니다.",
        distinctive_points: [
          "턱 128.5\u00B0 + 눈꼬리 +3.2\u00B0 조합",
          "대칭도 상위 22%",
          "황금비 근접도 0.78",
        ],
      },
    },
    {
      id: "gap_analysis",
      locked: true,
      unlock_level: "standard",
      teaser: { headline: "따뜻한 첫사랑 \u2192 부드럽고 성숙" },
      content: {
        current_type: "따뜻한 첫사랑",
        current_type_id: 1,
        aspiration_type: "부드럽고 성숙",
        aspiration_type_id: 5,
        current_coordinates: {
          structure: 0.35,
          impression: -0.22,
          maturity: -0.41,
          intensity: -0.15,
        },
        aspiration_coordinates: {
          structure: 0.28,
          impression: -0.1,
          maturity: 0.38,
          intensity: 0.12,
        },
        gap_magnitude: 0.89,
        gap_difficulty: "중간 난이도",
        gap_summary:
          "4축 거리 0.89 \u2014 주 변화축은 성숙도(delta 0.79)이며, 강도(delta 0.27)가 보조축입니다. 구조와 인상은 거의 유지 가능합니다.",
        direction_items: [
          {
            axis: "maturity",
            label: "성숙도",
            from_score: -0.41,
            to_score: 0.38,
            delta: 0.79,
            from_label: "프레시",
            to_label: "성숙",
            difficulty: "큰 변화",
            recommendation:
              "눈썹 아치를 현재 0.012에서 0.018 수준으로 높이면 성숙도 축에서 약 +0.3 이동 효과. 나머지 +0.49는 립 컬러(웜코랄\u2192로즈)와 헤어 볼륨 변화로 보완 가능합니다.",
          },
          {
            axis: "intensity",
            label: "존재감",
            from_score: -0.15,
            to_score: 0.12,
            delta: 0.27,
            from_label: "내추럴",
            to_label: "미디엄",
            difficulty: "작은 변화",
            recommendation:
              "아이라인 테일 2mm 연장으로 시각적 눈꼬리 각도 +1\u00B0 보정(3.2\u00B0\u2192약 4.2\u00B0). 컨투어링을 코 옆선에 가볍게 추가하면 강도 축 +0.15 정도 이동합니다.",
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
            target_axis: "maturity",
            target_delta: 0.79,
            recommendations: [
              {
                action: "아이브로우 아치 높이기",
                metric: "brow_arch",
                current_value: 0.012,
                target_value: 0.018,
                expected_effect: "성숙도 축 +0.3 이동",
                delta_contribution: 0.3,
              },
              {
                action: "아이라인 테일 2mm 연장",
                metric: "eye_tilt",
                current_value: 3.2,
                target_value: 4.2,
                unit: "\u00B0",
                expected_effect:
                  "강도 축 +0.1 이동, 시각적 눈꼬리 각도 보정",
                delta_contribution: 0.1,
              },
              {
                action: "립 컬러 웜코랄 \u2192 로즈 전환",
                metric: "skin_warmth_score",
                expected_effect:
                  "성숙도 축 +0.2 이동, 쿨톤 방향 미세 조정",
                delta_contribution: 0.2,
              },
            ],
          },
          {
            category: "헤어",
            priority: "HIGH",
            target_axis: "maturity",
            target_delta: 0.79,
            recommendations: [
              {
                action: "C컬 레이어드 \u2192 S컬 볼륨 웨이브",
                expected_effect:
                  "성숙도 축 +0.15 이동, 전체 실루엣 성숙화",
                delta_contribution: 0.15,
              },
              {
                action: "웜브라운 \u2192 다크애쉬브라운 톤다운",
                expected_effect:
                  "강도 축 +0.1, 인상 축 쿨 방향 미세 이동",
                delta_contribution: 0.1,
              },
            ],
          },
          {
            category: "스타일링",
            priority: "MEDIUM",
            target_axis: "intensity",
            target_delta: 0.27,
            recommendations: [
              {
                action: "라운드넥 \u2192 V넥/보트넥 전환",
                expected_effect: "시각적 목선 연장, 성숙 인상 보조",
                delta_contribution: 0.08,
              },
              {
                action: "톤온톤 \u2192 명도 대비 코디(아이보리+차콜)",
                expected_effect: "강도 축 +0.1 이동",
                delta_contribution: 0.1,
              },
            ],
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
        reasons: [
          "부드러운 턱라인 유사",
          "웜톤 피부톤",
          "둥근 눈매와 친근한 인상",
        ],
        styling_tips: [
          "내추럴 웜톤 메이크업 강화",
          "부드러운 웨이브 헤어",
        ],
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
      label: "\u20A95,000 잠금 해제",
      method: "manual",
    },
    full: {
      price: 15000,
      label: "+\u20A915,000 잠금 해제",
      total_note: "이전 결제 포함 총 \u20A920,000",
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
