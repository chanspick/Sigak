// 푸터 컴포넌트
// 가운데 정렬 저작권 텍스트, 위쪽 border

export function Footer() {
  return (
    <footer className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-6 md:py-8 text-center border-t border-black/10">
      <span className="text-[11px] tracking-[1.5px] opacity-30">
        © 2026 시각(SIGAK). ALL RIGHTS RESERVED
      </span>
    </footer>
  );
}
