"use client";

// 블러 티저 컴포넌트
// - locked=true: 콘텐츠 위에 blur-overlay 적용
// - 티저 콘텐츠(headline/categories)는 블러 위에 선명하게 표시
// - fade-out: opacity 0 transition 0.6s (blur-fade-out 클래스)

interface BlurTeaserProps {
  locked: boolean;
  children: React.ReactNode;
  teaser?: React.ReactNode;
}

// 조건부 블러 래퍼 - 잠금 시 콘텐츠를 블러 처리하고 티저만 선명 표시
export function BlurTeaser({ locked, children, teaser }: BlurTeaserProps) {
  if (!locked) {
    return <>{children}</>;
  }

  return (
    <div className="relative">
      {/* 실제 콘텐츠 (블러 뒤에 보임) */}
      <div className="select-none">
        {children}
      </div>

      {/* 블러 오버레이 */}
      <div
        className={`absolute inset-0 blur-overlay blur-fade-out transition-opacity duration-300 ${locked ? "opacity-100" : "opacity-0"}`}
      />

      {/* 티저: 블러 위에 선명하게 표시 */}
      {teaser && (
        <div className="absolute inset-0 z-10 flex items-center justify-center pointer-events-none">
          {teaser}
        </div>
      )}
    </div>
  );
}
