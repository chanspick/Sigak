import type { Metadata } from "next";
import Link from "next/link";

import { SiteFooter } from "@/components/sigak/site-footer";

export const metadata: Metadata = {
  title: "환불규정 및 서비스 이용안내 — SIGAK",
  description: "SIGAK 환불규정, 결제 안내, 서비스 이용 제한 사항",
};

export default function RefundPage() {
  return (
    <div className="min-h-screen bg-[var(--color-bg)] text-[var(--color-fg)]">
      {/* 헤더 */}
      <nav className="sticky top-0 z-[100] flex items-center justify-between px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] h-[60px] bg-[var(--color-fg)] text-[var(--color-bg)]">
        <Link href="/" className="text-[13px] font-semibold tracking-[6px] uppercase no-underline text-[var(--color-bg)]">SIGAK</Link>
        <Link href="/terms" className="text-[11px] font-medium tracking-[1.5px] opacity-70 hover:opacity-100 transition-opacity no-underline text-[var(--color-bg)]">이용약관</Link>
      </nav>

      <article className="max-w-2xl mx-auto px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-12">
        <h1 className="font-[family-name:var(--font-serif)] text-2xl font-bold mb-2">환불규정 및 서비스 이용안내</h1>
        <p className="text-xs text-[var(--color-muted)] mb-10">시행일: 2026년 4월 14일 | 주식회사 시각</p>

        {/* ── 1. 서비스 안내 ── */}
        <Section title="1. 서비스 안내" />

        <H3>서비스명</H3>
        <P>SIGAK (시각) — AI 이목구비 분석 및 퍼스널 스타일링 리포트</P>

        <H3>서비스 제공자</H3>
        <Table headers={["항목", "내용"]} rows={[
          ["상호", "주식회사 시각"],
          ["대표", "조찬형"],
          ["이메일", "partner@sigak.asia"],
          ["개인정보보호 책임자", "조찬형 (대표)"],
        ]} />

        <H3>서비스 내용</H3>
        <Table headers={["서비스", "금액 (VAT 포함)", "제공 내용"]} rows={[
          ["오버뷰 리포트", "₩5,000", "AI 얼굴형 정밀 분석, 피부톤(퍼스널 컬러) 매칭, 3축 미감 좌표, 요약 카드"],
          ["풀 리포트", "₩49,000", "오버뷰 전 항목 + 헤어 TOP 3 추천, 메이크업 가이드, 갭 분석, 미용실 지시문"],
          ["오버뷰 → 풀 업그레이드", "₩44,000", "오버뷰 이용자가 풀 리포트로 업그레이드 시 추가 결제"],
          ["셀러브리티 풀", "₩100,000", "풀 리포트 전 항목 + 상세 프로필, 우선 매칭, 에이전시 푸시"],
        ]} />

        <H3>서비스 제공 형태</H3>
        <Ul items={[
          "디지털 콘텐츠 (비배송 상품): 웹 리포트 형태로 제공",
          "별도 배송 없음 (웹 URL로 즉시 열람)",
        ]} />

        <H3>서비스 제공 기간</H3>
        <Ul items={[
          "분석 소요 시간: 결제 확인 후 최대 24시간 이내 리포트 생성",
          "리포트 열람 기간: 리포트 생성일로부터 1년간 열람 가능",
          "리포트 보관: 생성일로부터 1년 보관 후 자동 파기 (이용자 삭제 요청 시 즉시 파기)",
        ]} />

        {/* ── 2. 결제 안내 ── */}
        <Section title="2. 결제 안내" />

        <H3>결제 수단</H3>
        <Ul items={[
          "신용카드 / 체크카드 (토스페이먼츠)",
          "카카오페이, 토스페이",
          "계좌이체",
        ]} />

        <H3>결제 시점</H3>
        <P>서비스 신청 시 즉시 결제. 결제 완료 후 AI 분석이 시작됩니다.</P>

        {/* ── 3. 환불 정책 ── */}
        <Section title="3. 환불 정책" />

        <H3>3-1. 전액 환불 (100%)</H3>
        <Table headers={["환불 사유", "환불 기한", "환불 방법"]} rows={[
          ["결제 완료 후 AI 분석이 시작되지 않은 경우", "결제일로부터 7일 이내", "원결제수단 취소"],
          ["서비스 제공자의 사정으로 서비스 제공이 불가능한 경우", "사유 발생일로부터 24시간 이내", "원결제수단 취소"],
          ["선착순 인원 초과로 서비스 신청이 불가한 경우", "확인 즉시", "원결제수단 자동 취소"],
          ["결제 완료 후 24시간 이내에 리포트가 제공되지 않은 경우", "미제공 확인 후 24시간 이내", "원결제수단 취소"],
          ["시스템 오류로 리포트가 정상적으로 생성되지 않은 경우", "사유 발생일로부터 7일 이내", "원결제수단 취소"],
        ]} />

        <H3>3-2. 환불 불가</H3>
        <Ul items={[
          "AI 분석이 시작된 이후: 서비스의 특성상 AI 분석 및 리포트 생성 작업이 시작된 이후에는 단순 변심에 의한 환불이 불가합니다. (「전자상거래 등에서의 소비자보호에 관한 법률」 제17조 제2항 제5호: 디지털 콘텐츠의 제공이 개시된 경우)",
          "리포트 열람 후: 리포트 URL에 접속하여 내용을 확인한 이후에는 환불이 불가합니다.",
          "업그레이드 결제 후: 오버뷰에서 풀 리포트로 업그레이드 후 풀 리포트 콘텐츠가 제공된 경우 추가 결제분에 대한 환불이 불가합니다.",
        ]} />

        <H3>3-3. 부분 환불</H3>
        <Table headers={["상황", "환불 내용"]} rows={[
          ["오버뷰(₩5,000) 결제 후 분석 시작 전 취소", "₩5,000 전액 환불"],
          ["풀 리포트(₩49,000) 결제 후 분석 시작 전 취소", "₩49,000 전액 환불"],
          ["풀 리포트 결제 후 오버뷰만 제공, 나머지 미제공 시", "₩44,000 환불 (오버뷰 비용 ₩5,000 차감)"],
          ["업그레이드(₩44,000) 결제 후 분석 결과 미제공 시", "₩44,000 전액 환불"],
        ]} />

        <H3>3-4. 환불 절차</H3>
        <ol className="list-decimal list-outside pl-5 mb-4 space-y-1.5">
          {[
            "환불 신청: partner@sigak.asia로 환불 요청 (주문번호, 사유 포함)",
            "접수 확인: 영업일 기준 1일 이내 접수 확인 통보",
            "환불 처리: 환불 승인 후 영업일 기준 3~5일 이내 원결제수단으로 환불",
            "카드 결제 환불 시 카드사에 따라 취소 반영까지 3~7 영업일 소요 가능",
          ].map((item) => (
            <li key={item} className="text-[13px] leading-[1.7] opacity-80">{item}</li>
          ))}
        </ol>

        {/* ── 4. 서비스 이용 제한 ── */}
        <Section title="4. 서비스 이용 제한" />
        <Ul items={[
          "본 서비스는 만 14세 이상의 이용자를 대상으로 합니다.",
          "타인의 사진을 무단으로 사용하여 분석을 요청하는 행위는 금지됩니다.",
          "서비스 결과물을 상업적으로 재판매하는 행위는 금지됩니다.",
          "비정상적인 방법으로 대량 분석을 요청하는 행위는 금지되며, 해당 요청은 취소 및 환불 처리됩니다.",
        ]} />

        {/* ── 5. 청약철회 관련 고지 ── */}
        <Section title="5. 청약철회 관련 고지" />
        <P>「전자상거래 등에서의 소비자보호에 관한 법률」 제17조에 따라, 디지털 콘텐츠의 제공이 개시된 경우(AI 분석 시작) 청약철회가 제한될 수 있습니다.</P>
        <P>위 사유에 해당하는 경우에도, 서비스 내용이 표시·광고 내용과 다르거나 계약 내용과 다르게 이행된 경우에는 해당 사실을 안 날로부터 30일, 서비스를 제공받은 날로부터 3개월 이내에 청약철회가 가능합니다.</P>

        {/* ── 6. 분쟁 해결 ── */}
        <Section title="6. 분쟁 해결" />
        <Ul items={[
          "한국소비자원: 1372 (www.kca.go.kr)",
          "전자거래분쟁조정위원회: 1661-5714 (www.ecmc.or.kr)",
          "개인정보분쟁조정위원회: 1833-6972 (www.kopico.go.kr)",
          "개인정보침해신고센터: 118 (privacy.kisa.or.kr)",
        ]} />
      </article>

      {/* 사업자 정보 (PG 심사 필수) */}
      <SiteFooter />
    </div>
  );
}

// ── 재사용 컴포넌트 ──

function Section({ title }: { title: string }) {
  return <h2 className="text-lg font-bold mt-12 mb-6 pb-2 border-b border-[var(--color-border)]">{title}</h2>;
}

function H3({ children }: { children: React.ReactNode }) {
  return <h3 className="text-sm font-bold mt-8 mb-3">{children}</h3>;
}

function P({ children }: { children: React.ReactNode }) {
  return <p className="text-[13px] leading-[1.8] text-[var(--color-fg)] opacity-80 mb-4">{children}</p>;
}

function Ul({ items }: { items: string[] }) {
  return (
    <ul className="list-disc list-outside pl-5 mb-4 space-y-1.5">
      {items.map((item) => (
        <li key={item} className="text-[13px] leading-[1.7] opacity-80">{item}</li>
      ))}
    </ul>
  );
}

function Table({ headers, rows }: { headers: string[]; rows: string[][] }) {
  return (
    <div className="overflow-x-auto mb-4">
      <table className="w-full text-[12px] border-collapse">
        <thead>
          <tr>
            {headers.map((h) => (
              <th key={h} className="text-left font-semibold py-2 px-3 border-b border-[var(--color-border)] bg-black/[0.02]">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {row.map((cell, j) => (
                <td key={j} className="py-2 px-3 border-b border-[var(--color-border)] opacity-80 leading-[1.6]">{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
