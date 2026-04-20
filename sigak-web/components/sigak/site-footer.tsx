// SIGAK MVP v1.2 — SiteFooter (사업자 정보)
//
// 토스페이먼츠 PG 심사 필수 — 모든 주요 페이지 하단에 사업자 정보 6가지 기재.
// 특히 /tokens/purchase 결제 페이지에 반드시 있어야 함.
//
// 디자인: 새 브랜딩 (흑백+베이지) 톤 유지. 상단 1px 구분선, 옅은 opacity.

import Link from "next/link";

export function SiteFooter() {
  return (
    <footer
      className="font-sans"
      style={{
        padding: "32px 28px 48px",
        borderTop: "1px solid rgba(0, 0, 0, 0.08)",
        color: "var(--color-ink)",
        background: "var(--color-bg)",
      }}
    >
      {/* 상단 링크 */}
      <div
        style={{
          display: "flex",
          gap: 20,
          marginBottom: 20,
          fontSize: 11,
          letterSpacing: "-0.005em",
        }}
      >
        <Link href="/terms" style={{ opacity: 0.6, color: "var(--color-ink)" }}>
          이용약관
        </Link>
        <Link href="/terms#privacy" style={{ opacity: 0.6, color: "var(--color-ink)" }}>
          개인정보처리방침
        </Link>
        <Link href="/refund" style={{ opacity: 0.6, color: "var(--color-ink)" }}>
          환불정책
        </Link>
      </div>

      {/* 사업자 정보 — 토스 PG 심사 필수 6가지 */}
      <div
        style={{
          fontSize: 10,
          lineHeight: 1.8,
          opacity: 0.5,
          letterSpacing: "-0.005em",
        }}
      >
        <div>
          주식회사 시각 | 대표: 조찬형 | 사업자등록번호: 207-87-03690
        </div>
        <div>통신판매업신고번호: 제 2025-서울서대문-1006호</div>
        <div>
          주소: 서울특별시 서대문구 연세로 2나길 61, 1층 코워킹 스페이스
        </div>
        <div>
          <a href="tel:02-6402-0025" style={{ color: "var(--color-ink)" }}>
            02-6402-0025
          </a>
          {" · "}
          <a href="mailto:partner@sigak.asia" style={{ color: "var(--color-ink)" }}>
            partner@sigak.asia
          </a>
        </div>
      </div>

      {/* Copyright */}
      <div
        style={{
          marginTop: 16,
          fontSize: 10,
          opacity: 0.3,
          letterSpacing: "0.05em",
        }}
      >
        © 2026 SIGAK. All rights reserved.
      </div>
    </footer>
  );
}
