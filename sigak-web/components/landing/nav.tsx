// 스티키 내비게이션 바
// 검은 배경, SIGAK 로고 가운데, WORK/ABOUT 왼쪽, 시작 버튼 오른쪽

import Link from "next/link";

interface NavProps {
  onStart: () => void;
}

export function Nav({ onStart }: NavProps) {
  return (
    <nav className="sticky top-0 z-[100] flex items-center justify-between px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] h-[60px] bg-[var(--color-fg)] text-[var(--color-bg)]">
      {/* 왼쪽 링크 - 모바일에서 숨김 */}
      <div className="hidden md:flex items-center gap-7">
        <span className="text-[11px] font-medium tracking-[2.5px] uppercase cursor-pointer opacity-70 transition-opacity duration-200 hover:opacity-100">
          WORK
        </span>
        <span className="text-[11px] font-medium tracking-[2.5px] uppercase cursor-pointer opacity-70 transition-opacity duration-200 hover:opacity-100">
          ABOUT
        </span>
      </div>

      {/* 로고 (가운데) */}
      <span className="text-[13px] font-semibold tracking-[6px] uppercase">
        SIGAK
      </span>

      {/* 오른쪽 시작 버튼 */}
      <div className="flex items-center">
        <Link
          href="/sia"
          className="text-[11px] font-medium tracking-[2.5px] uppercase transition-opacity duration-200 hover:opacity-70 no-underline text-[var(--color-bg)]"
          onClick={(e) => {
            e.preventDefault();
            onStart();
          }}
        >
          지금 시작하기
        </Link>
      </div>
    </nav>
  );
}
