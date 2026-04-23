/**
 * /dev/sia-preview — Sia 컴포넌트 정적 시각 검증 페이지 (D6).
 *
 * 목적: 업데이트된 Sia 톤 원칙 (간결, 14턴 목표, 10개 default 숫자 생략)
 *       을 반영한 목업 대화로 시각 검증.
 *
 * 원칙:
 *   - 한 턴당 버블 2-3개 (오프닝만 최대 5)
 *   - 한 턴당 질문 1개
 *   - 샘플 크기 == 10 이면 숫자 생략
 *   - 데이터 조각은 여러 턴에 걸쳐 조금씩 공개
 *
 * 주의: API 호출 0건. D7 에서 실 API 연결.
 */
"use client";

import { SiaInputDock, SiaStream, SiaTopBar } from "@/components/sia";
import type { SiaTurn } from "@/lib/types/sia.legacy";

const MOCK_MESSAGES: SiaTurn[] = [
  // 턴 1 — 오프닝: 인사 + 짧은 정의 + 질문 하나
  {
    role: "sia",
    content: [
      "정세현님, Sia 입니다.",
      "피드를 살펴봤습니다.",
      "정세현님은 정돈된 인상을 전달하는 데 익숙하신 분입니다.",
      "하나만 먼저 확인하겠습니다.",
      "주말 저녁, 가까운 지인과의 자리에서 어떤 인상으로 기억되고 싶으신가요?",
    ].join("\n"),
  },

  // 턴 2 — 유저 선택
  { role: "user", content: "세련되고 거리감 있는 인상" },

  // 턴 3 — 짧은 해석 + 데이터 조각 한 개 공개 + 다음 질문
  {
    role: "sia",
    content: [
      "그 선택은 피드가 가리키던 방향과 같습니다.",
      "촬영 각도와 채도가 이미 같은 결을 띠고 있었습니다.",
      "다음 하나 여쭙겠습니다.",
      "평소 새로운 스타일을 시도할 때 더 가까운 쪽은 어느 쪽인가요?",
    ].join("\n"),
  },

  // 턴 4 — 유저 선택
  { role: "user", content: "검증된 안정감을 먼저" },

  // 턴 5 — 관찰 + 데이터 조각 (채도) 공개 + 질문
  {
    role: "sia",
    content: [
      "그 답이 피드의 일관성과 맞닿아 있습니다.",
      "최근 피드에는 단색 의상 비중이 73% 입니다.",
      "그런데 채도가 있는 의상일 때 좋아요 수가 평균 1.4 배 높습니다.",
      "이 데이터를 본 첫 반응은 어느 쪽에 가까우신가요?",
    ].join("\n"),
  },

  // 턴 6 — 유저 선택
  { role: "user", content: "의외다, 내가 감을 놓쳤나" },

  // 턴 7 — 해석만 짧게 + 주관식으로 자연 전환
  {
    role: "sia",
    content: [
      "그 반응이 미감 감수성을 보여줍니다.",
      "데이터를 즉각 자기 점검으로 연결하는 태도입니다.",
      "요즘 스타일에서 가장 바꾸고 싶은 부분이 있다면 어디인가요?",
      "한 문장이면 충분합니다.",
    ].join("\n"),
  },
];

export default function SiaPreviewPage() {
  const handleSend = async (text: string) => {
    // dev preview — 실 API 호출 없이 콘솔만 남김
    // eslint-disable-next-line no-console
    console.log("[dev preview] onSend:", text);
    await new Promise((resolve) => setTimeout(resolve, 400));
  };

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-[440px] flex-col bg-[var(--color-paper)]">
      <SiaTopBar progressPercent={45} remainingSeconds={27} />
      <SiaStream messages={MOCK_MESSAGES} pending />
      <SiaInputDock onSend={handleSend} />
    </main>
  );
}
