// 데모 리포트 정적 데이터
// report.json 기반, access_level: "standard", overlay/hair_simulation/paywall/payment_account 제외

import type { ReportData } from "@/lib/types/report";

export const DEMO_REPORT: ReportData = {
  id: "report_abcc2bea",
  user_name: "Dami",
  access_level: "standard",
  pending_level: null,
  sections: [
    {
      id: "cover",
      locked: false,
      content: {
        title: "시각 리포트",
        user_name: "Dami",
        date: "2026-04-15",
        tier: "standard",
      },
    },
    {
      id: "executive_summary",
      locked: false,
      content: {
        summary:
          "현재 부드러운 카리스마 타입이지만 더 발랄하고 어린 느낌으로 변화를 추구하시는군요. 송하영처럼 자연스럽고 사랑스러운 이미지를 만들기 위해 볼 사과존 블러셔와 자연스러운 립 톤이 핵심이에요. 여름 라이트 타입이니 컬러는 쿨톤 베이스의 밝고 부드러운 계열로 잡으세요. 2026 S/S 트렌드인 '도도한 동안'과도 완벽하게 맞아떨어져요.",
      },
    },
    {
      id: "face_structure",
      locked: false,
      content: {
        face_type: "타원형",
        face_length_ratio: 1.347000002861023,
        jaw_angle: 107.8,
        symmetry_label: "대칭 보통 수준",
        golden_ratio_label: "황금비 높은 편",
        metrics: [
          {
            key: "jaw_angle",
            label: "턱 각도",
            value: 107.8,
            unit: "\u00B0",
            percentile: 68,
            context: "평균(102.92\u00B0) 대비 넓은 편 — 부드러운 라인",
            min_value: 85,
            max_value: 125,
            min_label: "날카로운",
            max_label: "둥근",
            show_numeric_value: false,
            context_label: "107.8\u00B0",
          },
          {
            key: "face_length_ratio",
            label: "얼굴 종횡비",
            value: 1.347,
            unit: "",
            percentile: 95,
            context: "표준 타원형 범위(1.3-1.5)",
            min_value: 1.1,
            max_value: 1.35,
            min_label: "넓은",
            max_label: "긴",
            show_numeric_value: false,
            context_label: "매우 높은 편",
          },
          {
            key: "symmetry_score",
            label: "좌우 대칭도",
            value: 0.929,
            unit: "",
            percentile: 55,
            context: "보통 수준",
            min_value: 0.6,
            max_value: 1,
            min_label: "비대칭",
            max_label: "대칭",
            show_numeric_value: false,
            context_label: "보통 수준",
          },
          {
            key: "golden_ratio_score",
            label: "황금비 근접도",
            value: 0.835,
            unit: "",
            percentile: 81,
            context: "조화로운 비율",
            min_value: 0.65,
            max_value: 0.9,
            min_label: "낮음",
            max_label: "황금비",
            show_numeric_value: false,
            context_label: "높은 편",
          },
          {
            key: "cheekbone_prominence",
            label: "광대 돌출도",
            value: 0.611,
            unit: "",
            percentile: 42,
            context: "돌출된 편",
            min_value: 0.4,
            max_value: 0.85,
            min_label: "평면",
            max_label: "돌출",
            show_numeric_value: false,
            context_label: "보통 수준",
          },
        ],
        interpretation_unlock_level: "standard",
        overall_impression:
          "전체적으로 균형 잡힌 타원형 얼굴로, 부드럽고 온화한 인상을 주는 구조예요. 높은 대칭성과 황금비에 근접한 비율로 자연스러운 조화를 이루고 있어요.",
        feature_interpretations: [
          {
            feature: "jaw_angle",
            label: "턱선",
            value: 107.8,
            unit: "\u00B0",
            percentile: 68,
            range_label: "상위 32%",
            interpretation:
              "둥글고 부드러운 턱선으로 친근하고 온화한 인상을 만들어요. 각진 느낌보다는 곡선미가 두드러져서 여성스럽고 부드러운 이미지를 줘요.",
            min_label: "날카로운",
            max_label: "둥근",
            show_numeric_value: false,
            context_label: "107.8\u00B0",
          },
          {
            feature: "cheekbone_prominence",
            label: "광대",
            value: 0.611,
            unit: "",
            percentile: 42,
            range_label: "하위 42%",
            interpretation:
              "적당히 발달한 광대로 얼굴에 입체감을 더해요. 너무 돌출되지 않아서 자연스러우면서도 구조적인 아름다움을 보여줘요.",
            min_label: "평면",
            max_label: "돌출",
            show_numeric_value: false,
            context_label: "보통 수준",
          },
          {
            feature: "eye_tilt",
            label: "눈꼬리 기울기",
            value: 2.75,
            unit: "\u00B0",
            percentile: 56,
            range_label: "상위 44%",
            interpretation:
              "살짝 올라간 눈꼬리로 생동감 있고 매력적인 인상을 연출해요. 처지지 않아서 활기차고 젊은 느낌을 줘요.",
            min_label: "처진",
            max_label: "올라간",
            show_numeric_value: false,
            context_label: "2.8\u00B0",
          },
          {
            feature: "nose_bridge_height",
            label: "코 높이",
            value: 0.494,
            unit: "",
            percentile: 27,
            range_label: "하위 27%",
            interpretation:
              "적당한 높이의 콧대로 자연스럽고 균형 잡힌 옆모습을 만들어요. 과하지 않아서 전체적인 조화를 해치지 않아요.",
            min_label: "낮음",
            max_label: "높음",
            show_numeric_value: false,
            context_label: "다소 낮은 편",
          },
          {
            feature: "symmetry_score",
            label: "대칭도",
            value: 0.929,
            unit: "",
            percentile: 55,
            range_label: "상위 45%",
            interpretation:
              "매우 높은 대칭성으로 안정되고 균형 잡힌 인상을 줘요. 좌우 균형이 잘 맞아서 시각적으로 편안하고 아름다운 인상을 만들어요.",
            min_label: "비대칭",
            max_label: "대칭",
            show_numeric_value: false,
            context_label: "보통 수준",
          },
          {
            feature: "golden_ratio_score",
            label: "황금비",
            value: 0.835,
            unit: "",
            percentile: 81,
            range_label: "상위 19%",
            interpretation:
              "황금비에 가까운 비율로 자연스럽고 조화로운 얼굴 구조를 보여줘요. 각 부위의 크기와 위치가 이상적인 균형을 이루고 있어요.",
            min_label: "낮음",
            max_label: "황금비",
            show_numeric_value: false,
            context_label: "높은 편",
          },
        ],
        harmony_note:
          "부드러운 곡선과 높은 대칭성이 어우러져 자연스럽고 편안한 아름다움을 완성하고 있어요.",
        distinctive_points: [
          "부드러운 타원형 얼굴",
          "높은 대칭도와 균형감",
          "온화하고 친근한 전체 인상",
        ],
      },
    },
    {
      id: "skin_analysis",
      locked: true,
      unlock_level: "standard",
      teaser: {
        headline: "여름 라이트",
      },
      content: {
        tone: "여름 라이트",
        tone_description:
          "밝고 청량한 쿨톤이에요. 부드러운 파스텔 핑크 계열이 자연스럽게 어울려요.",
        hex_sample: "#8E796E",
        best_colors: [
          {
            name: "로즈 핑크",
            hex: "#FF66B2",
            usage: "립",
            why: "쿨한 피부톤을 맑고 화사하게 살려줘요.",
          },
          {
            name: "베이비 핑크",
            hex: "#F4C2C2",
            usage: "립",
            why: "파스텔 톤이 밝은 피부와 자연스럽게 녹아요.",
          },
          {
            name: "라벤더 핑크",
            hex: "#D8A0D8",
            usage: "포인트",
            why: "쿨 언더톤을 살리면서 고급스러운 느낌을 줘요.",
          },
        ],
        okay_colors: [
          {
            name: "쿨 누드",
            hex: "#D2B4A0",
            usage: "베이스",
            why: "무난하고 편안한 데일리 톤이에요.",
          },
          {
            name: "소프트 레드",
            hex: "#C74375",
            usage: "포인트",
            why: "강한 포인트가 필요할 때 쿨 베이스로 활용해요.",
          },
        ],
        avoid_colors: [
          {
            name: "오렌지",
            hex: "#FF8C00",
            why: "따뜻한 색이 쿨한 피부에서 떠요.",
          },
          {
            name: "브릭",
            hex: "#CB4154",
            why: "탁한 웜 계열이 피부를 칙칙하게 만들어요.",
          },
          {
            name: "테라코타",
            hex: "#E2725B",
            why: "흙빛 웜톤이 청량한 피부와 충돌해요.",
          },
        ],
        recommended: [
          {
            name: "로즈 핑크",
            hex: "#FF66B2",
            usage: "립",
            why: "쿨한 피부톤을 맑고 화사하게 살려줘요.",
          },
          {
            name: "베이비 핑크",
            hex: "#F4C2C2",
            usage: "립",
            why: "파스텔 톤이 밝은 피부와 자연스럽게 녹아요.",
          },
          {
            name: "라벤더 핑크",
            hex: "#D8A0D8",
            usage: "포인트",
            why: "쿨 언더톤을 살리면서 고급스러운 느낌을 줘요.",
          },
        ],
        avoid: [
          {
            name: "오렌지",
            hex: "#FF8C00",
            why: "따뜻한 색이 쿨한 피부에서 떠요.",
          },
          {
            name: "브릭",
            hex: "#CB4154",
            why: "탁한 웜 계열이 피부를 칙칙하게 만들어요.",
          },
          {
            name: "테라코타",
            hex: "#E2725B",
            why: "흙빛 웜톤이 청량한 피부와 충돌해요.",
          },
        ],
        avoid_reason: "따뜻한 색이 쿨한 피부에서 떠요.",
        hair_colors: [
          {
            name: "애쉬 블론드",
            hex: "#B8A590",
            why: "쿨한 피부톤에 투명한 느낌을 더해요.",
          },
          {
            name: "라벤더 그레이",
            hex: "#9C8FA3",
            why: "쿨 언더톤을 극대화하는 트렌디한 컬러예요.",
          },
          {
            name: "쿨 베이지 브라운",
            hex: "#A09080",
            why: "자연스러우면서도 칙칙하지 않은 중간 톤이에요.",
          },
        ],
        season: "summer",
        subtype: "light",
        lip_direction:
          "차갑고 밝은 핑크 계열. 부드럽게 한 겹 올리는 느낌으로.",
        cheek_direction: "청량한 핑크빛 혈색. 피부 속 투명감을 살려요.",
        eye_direction: "시원한 톤의 명색. 펄은 실버/핑크 펄.",
        foundation_guide: "13~17호 쿨 (13C, 17C)",
        confidence: 0.13,
        _undertone: "neutral",
        _chroma: 10.9,
        _warmth: 12.1,
        _brightness: 0.519,
      },
    },
    {
      id: "gap_analysis",
      locked: true,
      unlock_level: "standard",
      teaser: {
        headline: "부드러운 카리스마 \u2192 따뜻한 첫사랑",
      },
      content: {
        current_type: "부드러운 카리스마",
        current_type_id: 6,
        aspiration_type: "따뜻한 첫사랑",
        aspiration_type_id: 1,
        aspiration_description:
          "둥근 얼굴형, 부드러운 턱선, 큰 둥근 눈, 도톰한 입술. 작은 이목구비에 어린 비율. 따뜻하고 부드러운 인상.",
        aspiration_features: [
          "둥근 얼굴형",
          "부드러운 턱선",
          "큰 둥근 눈",
          "도톰한 입술",
          "작은 이목구비에 어린 비율",
          "따뜻하고 부드러운 인상",
        ],
        current_coordinates: {
          shape: -0.15,
          volume: 0.18,
          age: 0.34,
        },
        aspiration_coordinates: {
          shape: -0.7,
          volume: -0.6,
          age: -0.7,
        },
        gap_magnitude: 1.41,
        gap_difficulty: "큰 변화",
        gap_summary:
          "가장 큰 변화는 더 발랄한 방향으로 가는 거예요. 그리고 전체적으로 더 은은한 느낌으로요.",
        direction_items: [
          {
            axis: "age",
            label: "무드",
            name_kr: "무드",
            label_low: "발랄한",
            label_high: "성숙한",
            axis_description: "전체적인 분위기의 방향",
            from_score: 0.34,
            to_score: -0.7,
            delta: 1.04,
            from_label: "약간 성숙한",
            to_label: "발랄한 방향으로",
            difficulty: "큰 변화",
            recommendation:
              "무드에서는 어려 보이고 생기 있는 느낌을 더하는 방향이 잘 맞아요.",
          },
          {
            axis: "volume",
            label: "존재감",
            name_kr: "존재감",
            label_low: "은은한",
            label_high: "강렬한",
            axis_description: "이목구비의 선명도",
            from_score: 0.18,
            to_score: -0.6,
            delta: 0.78,
            from_label: "약간 강렬한",
            to_label: "은은한 방향으로",
            difficulty: "큰 변화",
            recommendation:
              "존재감에서는 자연스럽고 힘을 뺀 표현이 포인트예요.",
          },
          {
            axis: "shape",
            label: "골격",
            name_kr: "골격",
            label_low: "부드러운",
            label_high: "또렷한",
            axis_description: "턱선, 광대, 눈매가 만드는 골격의 형태",
            from_score: -0.15,
            to_score: -0.7,
            delta: 0.55,
            from_label: "약간 부드러운",
            to_label: "부드러운 방향으로",
            difficulty: "큰 변화",
            recommendation:
              "골격에서는 윤곽을 둥글고 부드럽게 풀어주는 방향이 핵심이에요.",
          },
        ],
        aesthetic_map: {
          current: {
            x: -0.15,
            y: 0.34,
            size: 0.18,
          },
          aspiration: {
            x: -0.7,
            y: -0.7,
            size: -0.6,
          },
          x_axis: {
            name_kr: "골격",
            low: "부드러운",
            high: "또렷한",
            low_en: "Soft",
            high_en: "Sharp",
            description: "턱선, 광대, 눈매가 만드는 골격의 형태",
          },
          y_axis: {
            name_kr: "무드",
            low: "발랄한",
            high: "성숙한",
            low_en: "Fresh",
            high_en: "Mature",
            description: "전체적인 분위기의 방향",
          },
          size_axis: {
            name_kr: "존재감",
            low: "은은한",
            high: "강렬한",
            low_en: "Subtle",
            high_en: "Bold",
            description: "이목구비의 선명도",
          },
          quadrants: {
            top_left: "Soft Mature",
            top_right: "Sharp Mature",
            bottom_left: "Soft Fresh",
            bottom_right: "Sharp Fresh",
          },
          description:
            "가로축은 골격의 형태, 세로축은 분위기의 방향이에요. 점이 클수록 이목구비 선명도가 높아요.",
        },
        trend: {
          x: 0.09,
          y: -0.13,
          size: 0.07,
        },
      },
    },
    {
      id: "hair_recommendation",
      locked: true,
      unlock_level: "full",
      teaser: {
        headline: "비대칭 사이드뱅 + 중단발 레이어드컷.",
      },
      content: {
        cheat_sheet: "비대칭 사이드뱅 + 중단발 레이어드컷.",
        top_combos: [
          {
            rank: 1,
            score: 0.99,
            front: {
              id: "h-f04",
              name_kr: "비대칭 사이드뱅",
              name_en: "Asymmetric Side Bangs",
              image: "/assets/reference/hair/front/h-f04.jpg",
            },
            back: {
              id: "h-b07",
              name_kr: "중단발 레이어드",
              name_en: "Medium Layered",
              image_front: "/assets/reference/hair/back-front/h-b07.jpg",
              image_rear: "/assets/reference/hair/back-rear/h-b07.jpg",
            },
            why: "비대칭이라 턱 부각 덜함. 레이어드로 하관 가벼움. 비대칭 앞머리 + 가벼운 뒷머리 = 시원하고 세련된 조화.",
            axis_shift: {},
            salon_instruction: "",
            trend: null,
          },
          {
            rank: 2,
            score: 0.8,
            front: {
              id: "h-f04",
              name_kr: "비대칭 사이드뱅",
              name_en: "Asymmetric Side Bangs",
              image: "/assets/reference/hair/front/h-f04.jpg",
            },
            back: {
              id: "h-b02",
              name_kr: "보브단발/레이어드",
              name_en: "Bob Cut / Layered",
              image_front: "/assets/reference/hair/back-front/h-b02.png",
              image_rear: "/assets/reference/hair/back-rear/h-b02.jpg",
            },
            why: "비대칭이라 턱 부각 덜함. 층으로 턱 옆 무게감 감소. 비대칭 앞머리 + 가벼운 뒷머리 = 시원하고 세련된 조화.",
            axis_shift: {},
            salon_instruction: "목 중간보다 길어지지 않도록.",
            trend: null,
          },
          {
            rank: 3,
            score: 0.8,
            front: {
              id: "h-f04",
              name_kr: "비대칭 사이드뱅",
              name_en: "Asymmetric Side Bangs",
              image: "/assets/reference/hair/front/h-f04.jpg",
            },
            back: {
              id: "h-b12",
              name_kr: "긴머리 레이어드펌",
              name_en: "Long Layered Perm",
              image_front: "/assets/reference/hair/back-front/h-b12.jpg",
              image_rear: "/assets/reference/hair/back-rear/h-b12.png",
            },
            why: "비대칭이라 턱 부각 덜함. 레이어드로 턱 아래 무게감 감소. 비대칭 앞머리 + 가벼운 뒷머리 = 시원하고 세련된 조화.",
            axis_shift: {},
            salon_instruction:
              "C컬은 쇄골보다 2-3cm 아래에 레이어드, 목 주변 컬 아주 굵게.",
            trend: null,
          },
        ],
        avoid: [],
        catalog: {
          front: [
            {
              id: "h-f01",
              name_kr: "풀뱅",
              name_en: "Full Bangs",
              image: "/assets/reference/hair/front/h-f01.jpg",
            },
            {
              id: "h-f02",
              name_kr: "시스루뱅",
              name_en: "See-Through Bangs",
              image: "/assets/reference/hair/front/h-f02.jpg",
            },
            {
              id: "h-f03",
              name_kr: "5:5 사이드뱅",
              name_en: "Center-Parted Side Bangs",
              image: "/assets/reference/hair/front/h-f03.jpg",
            },
            {
              id: "h-f04",
              name_kr: "비대칭 사이드뱅",
              name_en: "Asymmetric Side Bangs",
              image: "/assets/reference/hair/front/h-f04.jpg",
            },
            {
              id: "h-f05",
              name_kr: "턱선길이 사이드뱅",
              name_en: "Jaw-Length Side Bangs",
              image: "/assets/reference/hair/front/h-f05.jpg",
            },
            {
              id: "h-f06",
              name_kr: "컬리뱅",
              name_en: "Curly Bangs",
              image: "/assets/reference/hair/front/h-f06.jpg",
            },
            {
              id: "h-f07",
              name_kr: "처피뱅",
              name_en: "Choppy Bangs",
              image: "/assets/reference/hair/front/h-f07.jpg",
            },
            {
              id: "h-f08",
              name_kr: "앞머리없음",
              name_en: "No Bangs",
              image: "/assets/reference/hair/front/h-f08.jpg",
            },
          ],
          back: [
            {
              id: "h-b01",
              name_kr: "숏컷",
              name_en: "Short Pixie Cut",
              image_front: "/assets/reference/hair/back-front/h-b01.jpg",
              image_rear: "/assets/reference/hair/back-rear/h-b01.jpg",
            },
            {
              id: "h-b02",
              name_kr: "보브단발/레이어드",
              name_en: "Bob Cut / Layered",
              image_front: "/assets/reference/hair/back-front/h-b02.png",
              image_rear: "/assets/reference/hair/back-rear/h-b02.jpg",
            },
            {
              id: "h-b03",
              name_kr: "칼단발",
              name_en: "Blunt Bob",
              image_front: "/assets/reference/hair/back-front/h-b03.jpg",
              image_rear: "/assets/reference/hair/back-rear/h-b03.jpg",
            },
            {
              id: "h-b04",
              name_kr: "단발 굵은펌",
              name_en: "Short C-Curl Perm",
              image_front: "/assets/reference/hair/back-front/h-b04.jpg",
              image_rear: "/assets/reference/hair/back-rear/h-b04.jpg",
            },
            {
              id: "h-b05",
              name_kr: "단발 S컬펌",
              name_en: "Short S-Curl Perm",
              image_front: "/assets/reference/hair/back-front/h-b05.jpg",
              image_rear: "/assets/reference/hair/back-rear/h-b05.jpg",
            },
            {
              id: "h-b06",
              name_kr: "일자 중단발",
              name_en: "Medium Straight",
              image_front: "/assets/reference/hair/back-front/h-b06.jpg",
              image_rear: "/assets/reference/hair/back-rear/h-b06.jpg",
            },
            {
              id: "h-b07",
              name_kr: "중단발 레이어드",
              name_en: "Medium Layered",
              image_front: "/assets/reference/hair/back-front/h-b07.jpg",
              image_rear: "/assets/reference/hair/back-rear/h-b07.jpg",
            },
            {
              id: "h-b08",
              name_kr: "중단발 아웃C컬",
              name_en: "Medium Outward C-Curl",
              image_front: "/assets/reference/hair/back-front/h-b08.jpg",
              image_rear: "/assets/reference/hair/back-rear/h-b08.png",
            },
            {
              id: "h-b09",
              name_kr: "중단발펌",
              name_en: "Medium S-Curl Perm",
              image_front: "/assets/reference/hair/back-front/h-b09.jpg",
              image_rear: "/assets/reference/hair/back-rear/h-b09.jpg",
            },
            {
              id: "h-b10",
              name_kr: "긴 생머리",
              name_en: "Long Straight",
              image_front: "/assets/reference/hair/back-front/h-b10.jpg",
              image_rear: "/assets/reference/hair/back-rear/h-b10.jpg",
            },
            {
              id: "h-b11",
              name_kr: "긴머리펌",
              name_en: "Long Wave Perm",
              image_front: "/assets/reference/hair/back-front/h-b11.jpg",
              image_rear: "/assets/reference/hair/back-rear/h-b11.jpg",
            },
            {
              id: "h-b12",
              name_kr: "긴머리 레이어드펌",
              name_en: "Long Layered Perm",
              image_front: "/assets/reference/hair/back-front/h-b12.jpg",
              image_rear: "/assets/reference/hair/back-rear/h-b12.png",
            },
            {
              id: "h-b13",
              name_kr: "히피펌",
              name_en: "Hippie Perm",
              image_front: "/assets/reference/hair/back-front/h-b13.jpg",
              image_rear: "/assets/reference/hair/back-rear/h-b13.jpg",
            },
          ],
        },
      },
    },
    {
      id: "action_plan",
      locked: true,
      unlock_level: "full",
      teaser: {
        categories: ["볼 사과존", "입술", "눈 밑"],
      },
      content: {
        items: [
          {
            category: "볼 사과존",
            priority: "핵심 포인트",
            recommendations: [
              {
                action:
                  "볼 사과 부분에 밝은 톤 블러셔를 발라 어려 보이는 효과를 만들어요. 웃었을 때 가장 볼록한 부분에 집중해서 발라주세요.",
                expected_effect: "더 발랄한 무드으로",
              },
            ],
          },
          {
            category: "입술",
            priority: "핵심 포인트",
            recommendations: [
              {
                action:
                  "부담스럽지 않은 자연스러운 립 톤으로 전체적인 무게감을 덜어내요. 본연의 입술색과 비슷한 톤을 선택하면 됩니다.",
                expected_effect: "더 은은한 존재감으로",
              },
            ],
          },
          {
            category: "눈 밑",
            priority: "추가하면 좋은 포인트",
            recommendations: [
              {
                action:
                  "눈 밑 부분을 밝게 커버해 동안 효과를 극대화해요. 다크서클을 가리는 동시에 전체 얼굴이 환해 보입니다.",
                expected_effect: "더 부드러운 골격으로",
              },
            ],
          },
          {
            category: "전체 베이스",
            priority: "추가하면 좋은 포인트",
            recommendations: [
              {
                action:
                  "전체적으로 매트한 베이스를 만들어 차분하면서도 깔끔한 인상을 연출해요. 과도한 윤기보다는 자연스러운 피부 질감을 살려줍니다.",
                expected_effect: "더 발랄한 느낌으로",
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
      teaser: {
        headline: "'부드러운 카리스마' 유형과 70% 유사",
      },
      content: {
        type_name: "부드러운 카리스마",
        type_id: 6,
        similarity: 70,
        reasons: [
          "얼굴 구조의 주요 특징이 '부드러운 카리스마' 유형 경향과 맞아요.",
          "골격 축에서 또렷한 쪽 경향이 뚜렷해요.",
          "현재 이미지의 비율, 각도, 인상이 이 유형의 전형적 특징과 잘 연결돼요.",
        ],
        styling_tips: [
          "부드러운 카리스마 유형의 장점을 살리면서 변화를 주는 게 포인트예요.",
          "볼과 눈 아래에 생기를 더하면 어려 보이는 효과가 있어요.",
          "특히 볼 사과존, 입술 부분에 집중하면 변화가 빠르게 느껴져요.",
        ],
        runner_ups: [
          {
            type_name: "날카로운 카리스마",
            type_id: 8,
            similarity: 61,
          },
          {
            type_name: "편안한 우아함",
            type_id: 5,
            similarity: 61,
          },
        ],
      },
    },
    {
      id: "trend_context",
      locked: true,
      unlock_level: "full",
      teaser: {
        headline: "2026 S/S \u00B7 트렌드와 다른 방향이에요",
      },
      content: {
        season: "2026_SS",
        season_summary:
          "2026 S/S는 '도도한 동안'과 '이지 시크'가 투톱. 피부는 맑고 얇게, 눈매는 짧지만 선명하게, 베이스는 속광 중심. 과한 커버\u00B7매트\u00B7컨투어는 확실히 빠지고, 건강한 혈색\u00B7자연스러운 텍스처가 새 기준. 퍼스널컬러 규범보다 '오늘 기분에 맞는 무드\u00B7텍스처'가 색 선택의 기준이 되는 시대.",
        trend_direction: {
          shape: 0.09,
          volume: 0.07,
          age: -0.13,
        },
        alignment: "divergent",
        alignment_kr: "트렌드와 다른 방향이에요",
        alignment_description:
          "Dami님의 추구미는 이번 시즌 주류 트렌드와 다른 방향이에요. 그게 오히려 개성이고, 얼굴형에 맞는 게 트렌드보다 항상 우선이에요.",
        matched_mood: {
          id: "healthy_glow",
          label_kr: "헬시 글로우",
          description:
            "글로우 베이스 + 피지컬 치크 + 립밤/시럽 립. 운동하고 난 것 같은 건강한 혈색.",
          keywords: [
            "리얼스킨",
            "속광",
            "건강한 혈색",
            "MLBB",
            "피지컬 글로우",
          ],
          trend_score: 0.8,
        },
        action_trend_tags: [],
        makeup_trends: [
          {
            zone: "eyebrow",
            zone_kr: "눈썹",
            rising: ["자연눈썹/결살/플러피", "소프트 일자"],
            declining: ["진한 블록 일자"],
            summary:
              "2026 눈썹은 '일자냐 아치냐' 싸움이 아니라, 연한 톤 + 자연 결 + 소프트 곡선이 공통분모. 여성조선: '눈썹산을 거의 살리지 않고 수평으로 정돈한 일자 눈썹이 다시 주목. 도톰한 브로 대신 힘을 뺀 실루엣이 얼굴을 부드럽고 미니멀하게 정리.' 보그: '짙고 도톰한 아치형에서 소프트 일자/마농 브로우로 전환'.",
          },
          {
            zone: "eye",
            zone_kr: "아이",
            rising: ["무라인/섀도 음영만", "눈꼬리 생략/짧게"],
            declining: ["두꺼운 젤 라이너"],
            summary:
              "하퍼스바자: '번지듯 은은한 스모키와 수채화처럼 퍼지는 컬러로 눈매 깊이를 만들 것'. 아모레퍼시픽 아티스트: 데일리 기준은 '과하지 않은 자연 속눈썹'. 핵심은 섀도로 깊이만 주고 라인 존재감 최소화.",
          },
          {
            zone: "lip",
            zone_kr: "립",
            rising: ["틴티드 립밤/시럽", "글로시 립 오일/글로스"],
            declining: ["퍽퍽한 풀매트"],
            summary:
              "하퍼스바자: '2026 립 트렌드는 얇은 베이스 위에 더한 투명한 글로시 광. 촉촉하거나 끈적이는 질감이 아닌, 쫀쫀한 광이 핵심.' 형태: 블러 그라데이션과 소프트 풀립이 양축. 오버라인은 입술산\u00B7아랫입술 중앙 1~2mm만 소프트하게. 매트는 벨벳 그라데이션용 서브만.",
          },
          {
            zone: "base",
            zone_kr: "베이스",
            rising: ["세미 리얼 스킨", "속광/글로우"],
            declining: ["풀커버 매트"],
            summary:
              "화해\u00B7하퍼스바자\u00B7헬스조선 공통: '진한 화장은 촌스러워졌고, 지나치게 매트한 베이스보다 자연스럽고 건강한 광이 핵심.' 피부결이 비치는 에어리 광\u00B7세미 글로우 지향. 커버력보다 '광/텍스처 스펙트럼(무광\u2013세미\u2013글로우\u2013웨트)' 중심.",
          },
        ],
      },
    },
  ],
};
