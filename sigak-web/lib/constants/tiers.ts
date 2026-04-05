import type { Tier } from "@/lib/types/tier";

// 티어 상수 데이터 (landing.jsx에서 추출)
export const TIERS: Tier[] = [
  {
    id: "basic",
    name: "시선",
    nameUp: "시선",
    sub: "나를 읽다",
    price: 5000,
    desc: "이목구비 비율 · 얼굴형 정밀 분석, 피부톤 × 컬러 복합 매칭, 헤어 · 눈썹 · 안경 핏 설계, 트렌드 포지셔닝, 추구미 방향 로드맵, 메이크업 가이드.",
    target: "나를 객관적으로 알고 싶은 분",
  },
  {
    id: "creator",
    name: "시각 Creator",
    nameUp: "시각 CREATOR",
    sub: "화면 속 나를 설계하다",
    price: 200000,
    desc: "시선 전 항목 포함. 내 채널 톤에 맞는 얼굴 · 스타일링 최적화, 썸네일 · 프로필 최적 앵글 설계, 브랜드 미팅 · 면접 시 타겟 이미지로의 갭 분석과 교정.",
    target: "내 콘텐츠와 내 이미지 사이 간극을 줄이고 싶은 분",
  },
  {
    id: "wedding",
    name: "시각 Wedding",
    nameUp: "시각 WEDDING",
    sub: "스드메 전에, 나를 먼저",
    price: 200000,
    desc: "시선 전 항목 포함. 스드메 컨셉 최적화, 얼굴형 맞춤 드레스 라인 · 헤어 · 메이크업 방향, 스튜디오 조명 · 각도 가이드.",
    target: "스드메를 고르는 기준이 필요한 분",
  },
];
