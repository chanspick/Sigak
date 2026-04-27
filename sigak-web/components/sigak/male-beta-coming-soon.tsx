// 남성 v1.1 베타 차단 안내 화면 (2026-04-27)
//
// photo-upload / aspiration 등 male 풀 미정합 영역 진입 시 렌더.
// 에러 모달 톤 X — "준비중" 자연스러운 안내. 마케터 redesign 1815 톤 정합.
//
// 사용 예:
//   <MaleBetaComingSoon featureName="시각 비밀 레포트" />
//   <MaleBetaComingSoon featureName="추구미 분석" />

import Link from "next/link";
import { TopBar } from "@/components/ui/sigak";

interface MaleBetaComingSoonProps {
  /** "시각 비밀 레포트" / "추구미 분석" 등 상품 노출명. */
  featureName: string;
}

export function MaleBetaComingSoon({ featureName }: MaleBetaComingSoonProps) {
  return (
    <main className="min-h-screen bg-[var(--color-bg)]">
      <TopBar />
      <div className="px-6 pt-20 pb-20 text-center flex flex-col items-center">
        <p className="text-xs tracking-[3px] uppercase text-[var(--color-muted)] mb-6">
          COMING SOON
        </p>
        <h1 className="font-[family-name:var(--font-serif)] text-[28px] font-normal leading-tight mb-4">
          준비중입니다
        </h1>
        <p className="text-sm text-[var(--color-muted)] leading-relaxed max-w-[320px] mb-12 break-keep">
          남성 회원님들을 위한 {featureName}는 준비중입니다.
          <br />
          곧 정식으로 공개될 예정이에요.
        </p>
        <Link
          href="/"
          className="inline-block px-8 py-3 text-sm font-medium bg-[var(--color-fg)] text-[var(--color-bg)] transition-opacity duration-200 hover:opacity-85"
        >
          홈으로
        </Link>
      </div>
    </main>
  );
}
