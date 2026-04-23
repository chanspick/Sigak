/**
 * SiaDots — Sia 응답 대기 중 3점 바운스 인디케이터 (D6 정적 포팅).
 *
 * 디자인 출처: chat_design/ui_kits/sia/index.html `.dots`
 * - 좌측 정렬, Sia 버블과 동일 배경 (#F4F4F5)
 * - 3개 점 각각 1.3s 바운스 (animation-delay 0s / 0.18s / 0.36s)
 * - keyframe 정의는 app/globals.css `@keyframes sia-dot-bounce`
 */
export function SiaDots() {
  return (
    <div
      className="inline-flex gap-[4px] self-start bg-[var(--color-bubble-ai)] px-[14px] py-[14px] rounded-tl-[16px] rounded-tr-[16px] rounded-br-[16px] rounded-bl-[4px]"
      role="status"
      aria-label="Sia 응답 준비 중"
    >
      <span className="sia-dot h-[5px] w-[5px] rounded-full bg-black/45" />
      <span className="sia-dot sia-dot-2 h-[5px] w-[5px] rounded-full bg-black/45" />
      <span className="sia-dot sia-dot-3 h-[5px] w-[5px] rounded-full bg-black/45" />
    </div>
  );
}
