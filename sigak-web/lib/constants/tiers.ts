import type { Tier } from "@/lib/types/tier";

export const TIERS: Tier[] = [
  {
    id: "standard",
    name: "오버뷰",
    sub: "얼굴형 분석 + 요약 카드",
    price: 2900,
    originalPrice: 5000,
    desc: "이목구비 비율, 얼굴형 정밀 분석, 피부톤 매칭, 3축 좌표 포지셔닝. 심화 리포트는 추후 업그레이드 가능.",
  },
  {
    id: "full",
    name: "풀 리포트",
    sub: "헤어 + 메이크업 + 트렌드 + 액션플랜",
    price: 29000,
    originalPrice: 49000,
    desc: "오버뷰 전 항목 포함. 헤어 TOP 3 조합 추천, 메이크업 가이드, 트렌드 포지셔닝, 추구미 갭 분석, 미용실 지시문. 캐스팅 풀 등록 포함 (1년).",
    badge: "추천",
  },
];
