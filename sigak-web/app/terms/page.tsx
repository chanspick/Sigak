import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "이용약관 및 개인정보처리방침 — SIGAK",
  description: "SIGAK 서비스 이용약관 및 개인정보처리방침",
};

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-[var(--color-bg)] text-[var(--color-fg)]">
      {/* 헤더 */}
      <nav className="sticky top-0 z-[100] flex items-center justify-between px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] h-[60px] bg-[var(--color-fg)] text-[var(--color-bg)]">
        <Link href="/" className="text-[13px] font-semibold tracking-[6px] uppercase no-underline text-[var(--color-bg)]">SIGAK</Link>
        <Link href="/refund" className="text-[11px] font-medium tracking-[1.5px] opacity-70 hover:opacity-100 transition-opacity no-underline text-[var(--color-bg)]">환불규정</Link>
      </nav>

      <article className="max-w-2xl mx-auto px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-12 legal-content">
        <h1 className="font-[family-name:var(--font-serif)] text-2xl font-bold mb-2">개인정보처리방침 및 이용약관</h1>
        <p className="text-xs text-[var(--color-muted)] mb-10">시행일: 2026년 4월 14일 | 주식회사 파이컴퓨터</p>

        {/* ── 개인정보처리방침 ── */}
        <Section title="1. 개인정보처리방침" />

        <H3>제1조 (개인정보의 수집 및 이용 목적)</H3>
        <P>본 서비스(이하 &lsquo;SIGAK&rsquo;)는 다음의 목적을 위하여 개인정보를 처리합니다. 처리하고 있는 개인정보는 다음의 목적 이외의 용도로는 이용되지 않으며, 이용 목적이 변경되는 경우에는 별도의 동의를 받는 등 필요한 조치를 이행할 예정입니다.</P>
        <Ul items={[
          "서비스 제공: 얼굴형 분석, 스타일 추천 결과물 생성 및 발송, 본인 식별.",
          "캐스팅 매칭 서비스: 이용자의 동의 하에 분석 결과를 기반으로 제작사·에이전시·광고주 등과의 매칭 기회 제공.",
          "고객 문의 대응: 이용자 식별, 문의 사항 확인, 사실조사를 위한 연락·통지, 처리 결과 통보.",
          "환불 처리: 서비스 미제공 시 결제 대금 환불 및 본인 확인.",
          "서비스 개선: 비식별화된 통계 데이터를 활용한 알고리즘 고도화 및 품질 개선.",
        ]} />

        <H3>제2조 (수집하는 개인정보의 항목)</H3>
        <Ul items={[
          "필수 항목: 성명, 연락처(휴대폰 번호), 입금자명.",
          "민감정보: 얼굴 사진 및 이로부터 도출되는 생체 특징 정보(얼굴 랜드마크, 얼굴형 분류, 피부톤 분석 결과). 민감정보는 이용자의 별도 동의를 받아 수집하며, 미용 분석 목적으로만 사용됩니다.",
          "서비스 이용 시 수집 항목: 설문 응답(자기 인식, 추구 이미지, 스타일 키워드, 모질/체형 정보 등).",
          "캐스팅 풀 등록 시 추가 수집 항목 (opt-in 동의 시): 얼굴형 분석 결과, 이미지 유형, 3축 좌표, 사진.",
          "서비스 이용 과정에서 자동 생성되는 정보: 접속 로그, 쿠키, 서비스 이용 기록, 접속 IP.",
        ]} />

        <H3>제3조 (개인정보의 보유 및 이용 기간)</H3>
        <P>이용자의 개인정보는 원칙적으로 개인정보의 수집 및 이용 목적이 달성되면 지체 없이 파기합니다.</P>
        <Ul items={[
          "리포트 관련 데이터: 리포트 생성일로부터 1년간 보관 후 파기. 이용자 삭제 요청 시 즉시 파기.",
          "얼굴 사진 원본: AI 분석 완료 후 즉시 삭제. 분석 결과(수치 데이터)만 리포트에 보관.",
          "캐스팅 풀 등록 데이터: 이용자가 등록 해제를 요청할 때까지 보관. 해제 요청 시 즉시 파기.",
          "결제 관련 데이터: 전자상거래 등에서의 소비자보호에 관한 법률에 따라 5년간 보관.",
          "접속 로그: 통신비밀보호법에 따라 3개월간 보관.",
        ]} />

        <H3>제4조 (개인정보의 파기 절차 및 방법)</H3>
        <P>이용자의 개인정보는 목적 달성 후 별도의 DB 또는 서류함으로 옮겨져 내부 방침 및 기타 관련 법령에 따라 일정 기간 저장된 후 파기됩니다. 전자적 파일 형태의 정보는 기록을 재생할 수 없는 기술적 방법을 사용하여 삭제합니다.</P>

        <H3>제5조 (개인정보의 제3자 제공)</H3>
        <P>SIGAK은 이용자의 별도 동의 없이 개인정보를 제3자에게 제공하지 않습니다. 다만, 이용자가 캐스팅 매칭 서비스에 동의한 경우 아래와 같이 제3자에게 정보를 제공할 수 있습니다.</P>
        <Table headers={["항목", "내용"]} rows={[
          ["제공받는 자", "캐스팅 디렉터, 제작사, 광고 에이전시, 매니지먼트사 등 SIGAK과 제휴한 업체"],
          ["제공 항목", "얼굴형 분석 결과, 이미지 유형, 3축 좌표, 사진(동의한 사진에 한함)"],
          ["제공 목적", "캐스팅·오디션·모델 매칭·광고 출연 등 업무 연결"],
          ["보유 기간", "제공 목적 달성 시까지 (최대 1년). 이용자 철회 요청 시 즉시 파기."],
        ]} />
        <P>이용자는 제3자 제공에 대한 동의를 언제든지 철회할 수 있으며, SIGAK은 매칭 파트너에게 이용자의 실명 및 연락처를 직접 제공하지 않습니다.</P>

        <H3>제6조 (개인정보 처리 위탁 및 국외 이전)</H3>
        <Table headers={["수탁자", "위탁 업무", "소재지"]} rows={[
          ["Railway Inc.", "클라우드 서버 운영 및 데이터 저장", "미국"],
          ["솔라피(Solapi) 등", "카카오톡 알림톡·문자 발송", "대한민국"],
          ["토스페이먼츠", "결제 처리", "대한민국"],
        ]} />

        <H3>제7조 (데이터 활용 및 통계)</H3>
        <P>SIGAK은 수집된 분석 데이터를 비식별화·익명화하여 서비스 품질 개선, 업계 트렌드 통계 리포트 발행, 학술 연구 목적의 데이터셋 구성에 활용할 수 있습니다.</P>

        <H3>제8조 (이용자의 권리)</H3>
        <P>이용자는 언제든지 자신의 개인정보에 대해 열람, 정정, 삭제, 처리 정지를 요청할 수 있습니다. 요청은 partner@sigak.asia를 통해 가능합니다.</P>
        <Ul items={[
          "개인정보분쟁조정위원회: 1833-6972 (www.kopico.go.kr)",
          "개인정보침해신고센터: 118 (privacy.kisa.or.kr)",
        ]} />

        <H3>제9조 (쿠키의 사용)</H3>
        <P>SIGAK은 이용자의 서비스 이용 편의를 위해 쿠키(Cookie)를 사용합니다. 이용자는 웹 브라우저 설정을 통해 쿠키의 저장을 거부하거나 삭제할 수 있습니다.</P>

        <H3>제10조 (개인정보보호 책임자)</H3>
        <Table headers={["항목", "내용"]} rows={[
          ["성명", "최진규"],
          ["직위", "대표"],
          ["연락처", "partner@sigak.asia"],
        ]} />

        <Hr />

        {/* ── 이용약관 ── */}
        <Section title="2. 이용약관" />

        <H3>제1조 (목적)</H3>
        <P>본 약관은 SIGAK팀(이하 &lsquo;팀&rsquo;)이 운영하는 서비스의 이용 조건 및 절차, 팀과 이용자의 권리, 의무 및 책임 사항을 규정함을 목적으로 합니다.</P>

        <H3>제2조 (서비스의 제공 및 변경)</H3>
        <P>본 서비스는 정식 런칭 초기 단계의 서비스로, 안정적인 운영을 위해 선착순 50인 한정으로 서비스를 제공합니다. 팀은 서비스의 내용, 가격, 제공 방식 등을 변경할 수 있으며, 변경 시 사전에 고지합니다. 본 서비스는 만 14세 이상의 이용자를 대상으로 합니다.</P>

        <H3>제3조 (서비스 티어 및 이용 금액)</H3>
        <Table headers={["티어", "금액", "포함 내용"]} rows={[
          ["오버뷰 (Standard)", "₩5,000", "얼굴형 분석, 피부톤 매칭, 3축 좌표, 요약 카드"],
          ["풀 리포트 (Full)", "₩49,000", "오버뷰 전 항목 + 헤어 추천, 메이크업 가이드, 갭 분석, 미용실 지시문"],
          ["셀러브리티 풀", "₩100,000", "풀 리포트 전 항목 + 상세 프로필, 우선 매칭, 에이전시 푸시"],
        ]} />

        <H3>제4조 (캐스팅 매칭 서비스)</H3>
        <P>SIGAK은 이용자의 동의 하에 분석 결과 및 이미지 유형 데이터를 기반으로 매칭 파트너와 이용자를 연결합니다. SIGAK은 매칭 기회를 제공하는 중개 역할만을 수행하며, 매칭 이후의 계약·이행·분쟁에 대해 책임을 지지 않습니다. 이용자는 캐스팅 풀 등록을 언제든지 해제할 수 있습니다.</P>

        <H3>제5조 (매칭 파트너의 의무)</H3>
        <P>매칭 파트너는 SIGAK을 통해 제공받은 이용자 정보를 매칭 목적 외의 용도로 사용할 수 없으며, 매칭이 성사되지 않은 이용자의 정보는 제공일로부터 30일 이내에 파기하여야 합니다.</P>

        <H3>제6조 (환불 정책)</H3>
        <P>상세 환불 정책은 <Link href="/refund" className="underline">환불규정 페이지</Link>를 참고하세요.</P>

        <H3>제7조 (책임의 한계)</H3>
        <P>본 서비스는 분석 데이터에 기반한 참고 정보를 제공하는 것이며, 결과의 활용에 대한 최종 판단과 책임은 이용자 본인에게 있습니다. 캐스팅 매칭 서비스는 기회 제공의 성격이며, 매칭 성사를 보장하지 않습니다.</P>
      </article>

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

function Hr() {
  return <hr className="my-10 border-[var(--color-border)]" />;
}

function SiteFooter() {
  return (
    <footer className="border-t border-[var(--color-border)] px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-8">
      <div className="max-w-2xl mx-auto">
        <div className="flex flex-wrap gap-x-6 gap-y-1 text-[11px] opacity-40 mb-4">
          <Link href="/terms" className="hover:opacity-70">이용약관</Link>
          <Link href="/refund" className="hover:opacity-70">환불규정</Link>
          <a href="mailto:partner@sigak.asia" className="hover:opacity-70">partner@sigak.asia</a>
        </div>
        <p className="text-[10px] leading-[1.8] opacity-30">
          주식회사 파이컴퓨터 | 대표: 최진규 | partner@sigak.asia<br />
          &copy; 2026 SIGAK. All rights reserved.
        </p>
      </div>
    </footer>
  );
}
