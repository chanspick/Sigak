/**
 * SiaTopBar — 대화 화면 최상단 워드마크 + 진행도 + 30초 카운트다운 (Phase H ⑤).
 *
 * 합성:
 *   - 상단 52px: 중앙 "Sia" 워드마크 + 우측 SiaCountdown (30초 이하에서만 노출)
 *   - 하단 1px hairline: SiaProgressBar (기존 border-b 대체)
 *
 * 디자인 근거:
 *   - chat_design/ui_kits/sia/index.html 기준 TopBar 52px + hairline border.
 *   - 진행도는 border 자리 그대로 점유 — 디자인 "no extra element" 원칙 준수.
 *   - 카운트다운은 TopBar 내부 우측에 absolute, 중앙 워드마크와 무간섭.
 *
 * Breaking:
 *   - 기존 prop-less 시그니처 → 3-prop 필수. 호출부는 dev preview 1곳 수정됨.
 */
import { SiaCountdown } from "./SiaCountdown";
import { SiaProgressBar } from "./SiaProgressBar";

export interface SiaTopBarProps {
  /** JSON 수집률 0-100 — 하단 hairline. */
  progressPercent: number;
  /** 남은 초 0-300. 30초 이하에서만 우측 카운트다운 노출. */
  remainingSeconds: number;
  /** 0초 도달 시 1회 호출 (SiaCountdown 전달). */
  onExpire?: () => void;
}

export function SiaTopBar({
  progressPercent,
  remainingSeconds,
  onExpire,
}: SiaTopBarProps) {
  return (
    <header
      className="sticky top-0 z-10 flex-shrink-0 bg-[var(--color-paper)]"
      role="banner"
      data-testid="sia-topbar"
    >
      <div className="relative flex h-[52px] items-center justify-center">
        <span
          className="text-[12px] font-semibold"
          style={{ letterSpacing: "6px" }}
        >
          Sia
        </span>
        <div className="absolute right-[20px] top-1/2 -translate-y-1/2">
          <SiaCountdown
            remainingSeconds={remainingSeconds}
            onExpire={onExpire}
          />
        </div>
      </div>
      <SiaProgressBar percent={progressPercent} />
    </header>
  );
}
