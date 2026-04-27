import type { Metadata } from "next";
import type { ReactNode } from "react";

import { SiteFooter } from "@/components/sigak/site-footer";
import { RefundTopNav } from "./refund-top-nav";

// SIGAK MVP v2.1 (2026-04-24) 환불규정.
// v2 BM 3단 구조 반영: 토큰 팩 구매 + 기능별 해제(진단 10/PI 50/변화 무료).
// 레거시 오버뷰/풀/셀럽 티어 구조 전면 삭제.

export const metadata: Metadata = {
  title: "환불규정 및 서비스 이용안내 — SIGAK",
  description: "SIGAK 환불규정, 결제 안내, 서비스 이용 제한 사항",
};

export default function RefundPage() {
  return (
    <div className="min-h-screen bg-paper text-ink">
      <RefundTopNav />

      <article className="mx-auto max-w-2xl px-5 py-12 md:px-[var(--spacing-page-x)]">
        <h1
          className="font-serif mb-2"
          style={{ fontSize: 26, fontWeight: 700, letterSpacing: "-0.01em" }}
        >
          환불규정 및 서비스 이용안내
        </h1>
        <p
          className="mb-10 text-mute"
          style={{ fontSize: 12, letterSpacing: "-0.005em" }}
        >
          시행일: 2026년 4월 24일 · 버전 v2.1 · 주식회사 시각
        </p>

        {/* ── 1. 서비스 안내 ── */}
        <Section title="1. 서비스 안내" />

        <H3>서비스명</H3>
        <P>SIGAK (시각) — AI 기반 이미지 판정 및 Personal Image 분석</P>

        <H3>서비스 제공자</H3>
        <Table
          headers={["항목", "내용"]}
          rows={[
            ["상호", "주식회사 시각"],
            ["대표", "조찬형"],
            ["사업자등록번호", "207-87-03690"],
            ["통신판매업신고번호", "제 2025-서울서대문-1006호"],
            [
              "주소",
              "서울특별시 서대문구 연세로 2나길 61, 1층 코워킹 스페이스",
            ],
            ["전화", "02-6402-0025"],
            ["이메일 / 고객센터", "partner@sigak.asia"],
            ["개인정보 보호책임자", "조찬형 (대표)"],
          ]}
        />

        <H3>서비스 내용 — 토큰 팩</H3>
        <P>
          SIGAK는 토큰을 구매해 개별 기능을 해제하는 방식으로 동작합니다. 1 토큰 = 100원.
        </P>
        <Table
          headers={["팩", "가격 (VAT 포함)", "토큰 수", "토큰당 단가"]}
          rows={[
            ["Starter", "10,000원", "100 토큰", "100원"],
            ["Regular", "25,000원", "280 토큰", "약 89원 (12% 할인)"],
            ["Pro", "50,000원", "600 토큰", "약 83원 (17% 할인)"],
          ]}
        />

        <H3>서비스 내용 — 토큰 소비 단가</H3>
        <Table
          headers={["기능", "소비 토큰", "환산 금액", "특성"]}
          rows={[
            ["진단 해제 (판정 1건당)", "10 토큰", "1,000원", "판정 단위 개별"],
            ["PI 해제", "50 토큰", "5,000원", "이용자당 1회, 영속"],
            ["변화 탭", "무료", "—", "누적 판정 시계열"],
            ["월간 리포트 (향후)", "30 토큰", "3,000원", "시즌별 심화 분석"],
          ]}
        />

        <H3>서비스 제공 형태</H3>
        <Ul
          items={[
            "디지털 콘텐츠 (비배송 상품): 웹 및 모바일 애플리케이션",
            "별도 배송 없음 (로그인 후 즉시 이용)",
          ]}
        />

        <H3>서비스 제공 기간</H3>
        <Ul
          items={[
            "토큰: 구매 즉시 적립, 사용 기한 없음(계정 유지 기간 내)",
            "판정 결과: 계정 탈퇴 시까지 보관 (이용자 개별 삭제 가능)",
            "PI 리포트: 해제 후 영속 열람 (시각 재설정 시에도 재결제 불요)",
          ]}
        />

        {/* ── 2. 결제 안내 ── */}
        <Section title="2. 결제 안내" />

        <H3>결제 수단</H3>
        <Ul
          items={[
            "신용카드 / 체크카드 (토스페이먼츠)",
            "카카오페이, 네이버페이, 토스페이",
            "계좌이체 (토스페이먼츠 지원 시)",
          ]}
        />

        <H3>결제 시점</H3>
        <P>
          토큰 팩 선택 후 즉시 결제. 결제 완료 시점에 토큰이 잔액에 적립됩니다.
          기능 해제(진단 · PI)는 이후 이용자가 직접 소비 시점을 결정합니다.
        </P>

        {/* ── 3. 환불 정책 ── */}
        <Section title="3. 환불 정책" />

        <H3>3-1. 토큰 구매 환불 — 전액 환불</H3>
        <P>다음 <strong>두 조건을 모두 충족</strong>할 때 전액 환불됩니다.</P>
        <Ul
          items={[
            "구매일로부터 7일 이내",
            "구매한 토큰을 단 1 토큰도 소비하지 않은 경우",
          ]}
        />
        <Table
          headers={["환불 사유", "환불 기한", "환불 방법"]}
          rows={[
            [
              "토큰 구매 후 미사용 상태 취소",
              "구매일로부터 7일 이내",
              "원결제수단 취소",
            ],
            [
              "시스템 오류로 결제는 완료됐으나 토큰이 적립되지 않은 경우",
              "사유 발생일로부터 7일 이내",
              "원결제수단 취소 또는 토큰 재적립 중 선택",
            ],
            [
              "서비스 제공자 사정으로 서비스 제공이 불가능한 경우",
              "사유 발생일로부터 30일 이내",
              "잔여 토큰 환산 금액 원결제수단 환불",
            ],
          ]}
        />

        <H3>3-2. 환불 불가</H3>
        <P>
          「전자상거래 등에서의 소비자보호에 관한 법률」 제17조 제2항 제5호에 따라,
          <strong> 이미 소비된 디지털 콘텐츠(사용된 토큰)</strong>에 대해서는 청약 철회 및
          환불이 제한됩니다.
        </P>
        <Ul
          items={[
            "토큰 중 일부라도 기능 해제에 사용된 경우: 해당 구매 건 전체 환불 불가",
            "구매일로부터 7일 경과: 미사용 토큰도 환불 불가",
            "이미 환불 처리가 완료된 건에 대한 중복 요청",
            "이용 제한 조치(이용약관 위반)로 계정이 정지된 경우의 잔여 토큰",
          ]}
        />

        <H3>3-3. 부분 환불</H3>
        <P>
          원칙적으로 토큰 구매 건은 <strong>부분 환불하지 않습니다</strong>. 이미 1
          토큰이라도 소비된 구매 건은 전체가 환불 불가 처리됩니다. 이는 디지털 콘텐츠의
          특성상 "사용 개시" 시점을 전체 구매 단위로 판단하기 때문입니다.
        </P>
        <P>
          단, 위 3-1의 <em>서비스 제공자 사정</em>으로 인한 환불은 잔여 미사용 토큰 비율에
          따라 환산 금액을 환불합니다.
        </P>

        <H3>3-4. 환불 절차</H3>
        <ol
          className="mb-4 list-outside list-decimal space-y-1.5 pl-5"
          style={{ fontSize: 13 }}
        >
          {[
            "환불 신청: partner@sigak.asia 로 이메일 (주문번호, 환불 사유 필수 기재)",
            "접수 확인: 영업일 기준 1일 이내 접수 확인 회신",
            "환불 승인/거절 판단: 영업일 기준 3일 이내",
            "환불 처리: 승인 후 영업일 기준 3~5일 이내 원결제수단으로 취소",
            "카드 결제는 카드사 정책에 따라 취소 반영까지 3~7 영업일 추가 소요 가능",
          ].map((item) => (
            <li
              key={item}
              className="font-sans"
              style={{
                lineHeight: 1.7,
                opacity: 0.82,
                letterSpacing: "-0.005em",
              }}
            >
              {item}
            </li>
          ))}
        </ol>

        {/* ── 4. 서비스 이용 제한 ── */}
        <Section title="4. 서비스 이용 제한" />
        <Ul
          items={[
            "본 서비스는 만 14세 이상의 이용자를 대상으로 합니다.",
            "타인의 사진을 무단으로 업로드하는 행위는 금지됩니다.",
            "미성년자 또는 제3자의 얼굴이 포함된 사진을 본인 동의 없이 업로드하는 행위는 금지됩니다.",
            "음란물, 폭력적·불법적 콘텐츠 업로드는 금지되며, 발견 시 계정이 영구 정지될 수 있습니다.",
            "자동화된 수단(봇, 스크립트)을 이용해 대량 판정을 요청하는 행위는 금지되며, 해당 요청은 취소 및 잔여 토큰 환불 없이 계정 정지 조치됩니다.",
            "서비스 결과물을 상업적으로 재판매하거나 외부 AI 모델의 학습 데이터로 사용하는 행위는 금지됩니다.",
          ]}
        />

        {/* ── 5. 청약철회 고지 ── */}
        <Section title="5. 청약철회 관련 고지" />
        <P>
          「전자상거래 등에서의 소비자보호에 관한 법률」 제17조 제2항 제5호에 따라 디지털
          콘텐츠의 제공이 개시된 경우 청약 철회가 제한됩니다. 본 서비스에서 "제공 개시"는
          <strong> 토큰을 기능(진단 해제 · PI 해제 등)에 소비한 시점</strong>으로
          해석합니다.
        </P>
        <P>
          서비스 내용이 표시·광고와 다르거나 계약 내용과 다르게 이행된 경우에는 해당 사실을
          안 날로부터 30일, 서비스를 제공받은 날로부터 3개월 이내에 청약철회 및 환불이
          가능합니다.
        </P>

        {/* ── 6. 회원 탈퇴 시 토큰 처리 ── */}
        <Section title="6. 회원 탈퇴 시 토큰 처리" />
        <Ul
          items={[
            "회원 탈퇴 시 보유하고 있던 토큰은 환불되지 않습니다.",
            "탈퇴 전 미사용 토큰이 있다면 위 3-1 조건(구매일로부터 7일 이내 + 미사용)을 충족하는 한 환불 요청이 가능합니다.",
            "탈퇴 후에는 3-1 조건 충족 여부와 무관하게 환불이 불가하므로, 환불 필요 시 탈퇴 전에 신청해주세요.",
          ]}
        />

        {/* ── 7. 분쟁 해결 ── */}
        <Section title="7. 분쟁 해결" />
        <P>
          이용자와 회사 간 분쟁은 당사자 간 협의로 해결함을 원칙으로 하며, 협의로 해결되지
          않는 경우 아래 기관을 통해 조정·구제를 신청할 수 있습니다.
        </P>
        <Ul
          items={[
            "한국소비자원 / 소비자분쟁조정위원회: 1372 (www.kca.go.kr)",
            "전자문서·전자거래분쟁조정위원회: 02-2141-5714 (www.ecmc.or.kr)",
            "개인정보분쟁조정위원회: 1833-6972 (www.kopico.go.kr)",
            "개인정보침해신고센터: 118 (privacy.kisa.or.kr)",
          ]}
        />

        <p
          className="mt-12 text-mute"
          style={{ fontSize: 11, letterSpacing: "-0.005em" }}
        >
          시행일: 2026년 4월 24일 · 최종 개정일: 2026년 4월 24일
        </p>
      </article>

      {/* 사업자 정보 (PG 심사 필수) */}
      <SiteFooter />
    </div>
  );
}

// ─────────────────────────────────────────────
//  Reusable content components
// ─────────────────────────────────────────────

function Section({ title }: { title: string }) {
  return (
    <h2
      className="mb-6 mt-12 border-b pb-2"
      style={{
        fontSize: 18,
        fontWeight: 700,
        borderColor: "var(--color-line)",
        letterSpacing: "-0.005em",
      }}
    >
      {title}
    </h2>
  );
}

function H3({ children }: { children: ReactNode }) {
  return (
    <h3
      className="mb-3 mt-8 font-sans"
      style={{ fontSize: 14, fontWeight: 700, letterSpacing: "-0.005em" }}
    >
      {children}
    </h3>
  );
}

function P({ children }: { children: ReactNode }) {
  return (
    <p
      className="mb-4 font-sans"
      style={{
        fontSize: 13,
        lineHeight: 1.8,
        opacity: 0.82,
        letterSpacing: "-0.005em",
      }}
    >
      {children}
    </p>
  );
}

function Ul({ items }: { items: string[] }) {
  return (
    <ul className="mb-4 list-outside list-disc space-y-1.5 pl-5">
      {items.map((item) => (
        <li
          key={item}
          className="font-sans"
          style={{
            fontSize: 13,
            lineHeight: 1.7,
            opacity: 0.82,
            letterSpacing: "-0.005em",
          }}
        >
          {item}
        </li>
      ))}
    </ul>
  );
}

function Table({
  headers,
  rows,
}: {
  headers: string[];
  rows: string[][];
}) {
  return (
    <div className="mb-4 overflow-x-auto">
      <table className="w-full border-collapse" style={{ fontSize: 12 }}>
        <thead>
          <tr>
            {headers.map((h) => (
              <th
                key={h}
                className="border-b px-3 py-2 text-left font-sans"
                style={{
                  fontWeight: 600,
                  borderColor: "var(--color-line)",
                  background: "rgba(0, 0, 0, 0.02)",
                  letterSpacing: "-0.005em",
                }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {row.map((cell, j) => (
                <td
                  key={j}
                  className="border-b px-3 py-2 font-sans"
                  style={{
                    borderColor: "var(--color-line)",
                    opacity: 0.82,
                    lineHeight: 1.6,
                    letterSpacing: "-0.005em",
                  }}
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
