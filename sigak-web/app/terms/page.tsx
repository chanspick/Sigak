import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

// SIGAK MVP v2.0 (2026-04-20) 약관/개인정보처리방침.
// 토큰 기반 BM + verdict + 블러 해제 구조 반영. 레거시 TIER(Standard/Full/Celebrity) 전면 제거.

export const metadata: Metadata = {
  title: "이용약관 및 개인정보처리방침 — SIGAK",
  description: "SIGAK 서비스 이용약관 및 개인정보처리방침 v2.0",
};

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-paper text-ink">
      {/* 헤더 */}
      <nav className="sticky top-0 z-[100] flex h-[60px] items-center justify-between bg-ink px-5 text-paper md:px-[var(--spacing-page-x)]">
        <Link
          href="/"
          className="font-display no-underline"
          style={{ fontSize: 13, fontWeight: 500, letterSpacing: "0.32em", color: "var(--color-paper)" }}
        >
          SIGAK
        </Link>
        <div className="flex items-center gap-5">
          <a
            href="#privacy"
            className="font-sans no-underline opacity-70 transition-opacity hover:opacity-100"
            style={{ fontSize: 11, color: "var(--color-paper)", letterSpacing: "0.1em" }}
          >
            개인정보
          </a>
          <a
            href="#tos"
            className="font-sans no-underline opacity-70 transition-opacity hover:opacity-100"
            style={{ fontSize: 11, color: "var(--color-paper)", letterSpacing: "0.1em" }}
          >
            이용약관
          </a>
        </div>
      </nav>

      <article className="mx-auto max-w-2xl px-5 py-12 md:px-[var(--spacing-page-x)]">
        <h1 className="font-serif mb-2" style={{ fontSize: 26, fontWeight: 700, letterSpacing: "-0.01em" }}>
          개인정보처리방침 및 이용약관
        </h1>
        <p className="mb-10 text-mute" style={{ fontSize: 12, letterSpacing: "-0.005em" }}>
          시행일: 2026년 4월 20일 · 버전 v2.0 · 주식회사 시각
        </p>

        {/* ── 1. 개인정보처리방침 ── */}
        <Section id="privacy" title="1. 개인정보처리방침" />

        <H3>제1조 (개인정보의 수집 및 이용 목적)</H3>
        <P>
          주식회사 시각(이하 &ldquo;회사&rdquo;)이 운영하는 SIGAK(이하 &ldquo;서비스&rdquo;)은 다음의 목적을 위하여 개인정보를 처리합니다. 처리하고 있는 개인정보는 다음의 목적 이외의 용도로는 이용되지 않으며, 이용 목적이 변경되는 경우에는 별도의 동의를 받는 등 필요한 조치를 이행합니다.
        </P>
        <Ul items={[
          "서비스 제공: 사진 분석, 판정 결과 생성, 추구미 기반 개인화된 추천 제공",
          "회원 관리: 회원 식별, 가입 의사 확인, 본인 확인, 부정 이용 방지",
          "결제 처리: 토큰 팩 구매에 따른 결제 대금 처리, 환불 처리",
          "서비스 개선: 비식별화·익명화된 데이터를 활용한 알고리즘 고도화 및 품질 개선",
          "고객 문의 대응: 이용자 식별, 문의 사항 확인, 처리 결과 통보",
        ]} />

        <H3>제2조 (수집하는 개인정보의 항목)</H3>
        <h4 className="mb-2 mt-5 font-sans" style={{ fontSize: 13, fontWeight: 500 }}>2.1 필수 수집 항목</h4>
        <P><strong>회원 가입 시 (카카오 로그인 연동)</strong></P>
        <Ul items={[
          "카카오 회원번호, 닉네임, 프로필 이미지, 이메일",
        ]} />
        <P><strong>서비스 이용 시</strong></P>
        <Ul items={[
          "온보딩 설문 응답 데이터 (키, 몸무게, 어깨 너비, 목 길이, 얼굴 고민, 추구 스타일 키워드, 원하는 이미지, 자기 인식, 현재 고민, 메이크업 수준)",
        ]} />

        <h4 className="mb-2 mt-5 font-sans" style={{ fontSize: 13, fontWeight: 500 }}>2.2 민감정보 수집 항목 (별도 동의)</h4>
        <Ul items={[
          "얼굴 사진: 이용자가 서비스 이용을 위해 직접 업로드한 사진",
          "생체 특징 정보: 얼굴 사진으로부터 도출되는 얼굴 랜드마크, 3축 좌표(Shape·Volume·Age), 8-type 분류 결과",
        ]} />
        <P>민감정보는 이용자의 별도 동의를 받아 수집하며, 서비스의 핵심 기능인 사진 판정·분석 목적으로만 사용됩니다.</P>

        <h4 className="mb-2 mt-5 font-sans" style={{ fontSize: 13, fontWeight: 500 }}>2.3 결제 시 수집 항목</h4>
        <Ul items={[
          "결제 수단 정보는 토스페이먼츠가 직접 처리하며, 회사는 결제 승인 결과만 수신합니다.",
          "회사가 보관하는 결제 관련 정보: 주문번호, 결제 금액, 결제 일시, 토큰 적립 내역",
        ]} />

        <h4 className="mb-2 mt-5 font-sans" style={{ fontSize: 13, fontWeight: 500 }}>2.4 자동 수집 항목</h4>
        <Ul items={["접속 IP, 쿠키, 서비스 이용 기록, 기기 정보, 접속 로그"]} />

        <H3>제3조 (개인정보의 보유 및 이용 기간)</H3>
        <P>
          이용자의 개인정보는 원칙적으로 수집·이용 목적이 달성되면 지체 없이 파기합니다. 다만 다음 경우 해당 기간까지 보관합니다.
        </P>
        <Table
          headers={["항목", "보유 기간", "근거"]}
          rows={[
            ["회원 정보", "회원 탈퇴 시까지", "서비스 제공"],
            ["얼굴 사진 및 생체 특징 정보", "회원 탈퇴 또는 이용자 삭제 요청 시까지", "타임라인·트렌드 분석 기능 제공"],
            ["온보딩 설문 응답", "회원 탈퇴 시까지", "서비스 제공"],
            ["판정(verdict) 결과 및 이력", "회원 탈퇴 시까지", "이용자 이력 관리"],
            ["결제 기록", "5년", "전자상거래 등에서의 소비자보호에 관한 법률"],
            ["불만 또는 분쟁처리 기록", "3년", "전자상거래 등에서의 소비자보호에 관한 법률"],
            ["접속 로그", "3개월", "통신비밀보호법"],
          ]}
        />
        <P>
          <strong>사진 영구 보관 안내</strong>: 이용자가 업로드한 사진 원본은 타임라인·트렌드 변화 추적 기능 제공을 위해 회원 탈퇴 시까지 안전하게 저장됩니다. 이용자는 언제든지 개별 사진 또는 전체 사진 삭제를 요청할 수 있습니다.
        </P>

        <H3>제4조 (개인정보의 파기 절차 및 방법)</H3>
        <Ol items={[
          "이용자의 개인정보는 목적 달성, 회원 탈퇴, 또는 삭제 요청 시 지체 없이 파기됩니다.",
          "전자적 파일 형태로 저장된 개인정보는 기록을 재생할 수 없는 기술적 방법을 사용하여 삭제합니다.",
          "얼굴 사진 등 민감정보 파일은 복구 불가능한 방식으로 영구 삭제됩니다.",
          "관련 법령에 따라 보존이 필요한 정보는 별도의 DB로 옮겨 법정 보유 기간 동안 보관 후 파기합니다.",
        ]} />

        <H3>제5조 (개인정보의 제3자 제공)</H3>
        <P>회사는 이용자의 개인정보를 제3자에게 제공하지 않습니다. 다만, 다음 각 호의 경우는 예외로 합니다.</P>
        <Ol items={[
          "이용자가 사전에 동의한 경우",
          "법령의 규정에 의거하거나, 수사 목적으로 법령에 정해진 절차와 방법에 따라 수사기관의 요구가 있는 경우",
        ]} />

        <H3>제6조 (개인정보 처리 위탁 및 국외 이전)</H3>
        <h4 className="mb-2 mt-5 font-sans" style={{ fontSize: 13, fontWeight: 500 }}>6.1 처리 위탁 현황</h4>
        <Table
          headers={["수탁자", "위탁 업무", "소재지"]}
          rows={[
            ["카카오 주식회사", "카카오 로그인 인증", "대한민국"],
            ["토스페이먼츠 주식회사", "결제 처리", "대한민국"],
            ["Railway Inc.", "클라우드 서버 운영, 데이터베이스 호스팅", "미국"],
            ["Vercel Inc.", "프론트엔드 서비스 호스팅", "미국"],
            ["Anthropic PBC", "AI 분석 엔진 (자연어 해석 생성)", "미국"],
          ]}
        />
        <h4 className="mb-2 mt-5 font-sans" style={{ fontSize: 13, fontWeight: 500 }}>6.2 국외 이전 고지</h4>
        <P>회사는 서비스 제공을 위해 다음과 같이 개인정보를 국외로 이전합니다.</P>

        <P><strong>Railway Inc. (서버 운영)</strong></P>
        <Ul items={[
          "이전 국가: 미국",
          "이전 항목: 서비스 이용 과정에서 수집되는 모든 개인정보",
          "이전 목적: 클라우드 서버 운영 및 데이터베이스 호스팅",
          "이전 방법: 네트워크를 통한 전송",
          "보유 기간: 위탁 계약 종료 시 또는 이용자 삭제 요청 시 즉시 파기",
        ]} />

        <P><strong>Vercel Inc. (프론트엔드 호스팅)</strong></P>
        <Ul items={[
          "이전 국가: 미국",
          "이전 항목: 접속 IP, 쿠키, 접속 로그",
          "이전 목적: 웹 서비스 배포 및 운영",
          "이전 방법: 네트워크를 통한 전송",
          "보유 기간: 위탁 계약 종료 시까지",
        ]} />

        <P><strong>Anthropic PBC (AI 분석)</strong></P>
        <Ul items={[
          "이전 국가: 미국",
          "이전 항목: 얼굴 분석 결과 수치 데이터(3축 좌표, 얼굴 랜드마크 특징), 온보딩 설문 응답 일부",
          "이전 목적: AI 기반 자연어 해석 생성 (판정 이유, 리포트 문장 생성)",
          "이전 방법: API 호출을 통한 네트워크 전송",
          "보유 기간: API 호출 완료 후 즉시 삭제 (Anthropic 정책상 캐시되지 않음)",
        ]} />

        <P>회사는 국외 이전 시 이용자의 개인정보가 안전하게 보호되도록 수탁자에게 관련 법령에 따른 보호 조치를 요구합니다.</P>

        <H3>제7조 (데이터 활용 및 통계)</H3>
        <P>회사는 수집된 분석 데이터를 <strong>비식별화·익명화</strong>하여 다음 목적으로 활용할 수 있습니다.</P>
        <Ul items={[
          "서비스 품질 개선 및 알고리즘 고도화",
          "집계 통계 분석 (개인 식별 불가능한 형태)",
          "학술·연구 목적의 데이터셋 구성",
        ]} />
        <P>비식별화된 통계 데이터는 특정 개인을 식별할 수 없는 형태로만 활용되며, 원본 얼굴 사진은 통계 또는 외부 공유 목적으로 사용되지 않습니다.</P>

        <H3>제8조 (이용자의 권리)</H3>
        <Ol items={[
          "이용자는 언제든지 자신의 개인정보에 대해 열람, 정정, 삭제, 처리 정지, 이동을 요구할 수 있습니다.",
          "권리 행사는 서비스 내 프로필 설정 또는 고객센터(partner@sigak.asia)를 통해 가능합니다. 요청 접수 후 지체 없이 조치합니다.",
          "이용자가 개인정보의 삭제를 요청한 경우, 회사는 해당 개인정보를 지체 없이 파기합니다.",
        ]} />
        <P>개인정보 처리로 인한 피해는 다음 기관에 상담·신고할 수 있습니다.</P>
        <Ul items={[
          "개인정보분쟁조정위원회: 1833-6972 (www.kopico.go.kr)",
          "개인정보침해신고센터: 118 (privacy.kisa.or.kr)",
          "대검찰청 사이버수사과: 1301 (www.spo.go.kr)",
          "경찰청 사이버수사국: 182 (ecrm.police.go.kr)",
        ]} />

        <H3>제9조 (쿠키의 사용)</H3>
        <Ol items={[
          "회사는 이용자의 서비스 이용 편의를 위해 쿠키(Cookie)를 사용합니다.",
          "쿠키는 로그인 세션 유지, 서비스 접속 빈도 분석, 맞춤형 서비스 제공 등의 목적으로 사용됩니다.",
          "이용자는 웹 브라우저 설정을 통해 쿠키 저장을 거부할 수 있으며, 이 경우 일부 서비스 이용이 제한될 수 있습니다.",
        ]} />

        <H3>제10조 (개인정보 보호책임자)</H3>
        <Table
          headers={["항목", "내용"]}
          rows={[
            ["성명", "조찬형"],
            ["직위", "대표이사"],
            ["이메일", "partner@sigak.asia"],
          ]}
        />

        <H3>제11조 (개인정보의 안전성 확보 조치)</H3>
        <P>회사는 개인정보 보호를 위해 다음과 같은 조치를 취하고 있습니다.</P>
        <Ol items={[
          "관리적 조치: 내부관리계획 수립·시행, 전담 인력 지정",
          "기술적 조치: 개인정보처리시스템 접근 권한 관리, 접근 통제 시스템 설치, 암호화 전송(HTTPS)",
          "물리적 조치: 전산실, 자료보관실 등의 접근 통제",
        ]} />

        <H3>제12조 (개인정보처리방침의 변경)</H3>
        <P>본 개인정보처리방침은 법령, 정책 또는 보안 기술의 변경에 따라 내용의 추가·삭제·수정이 있을 경우 시행일 최소 7일 전부터 서비스를 통해 고지합니다.</P>

        <Hr />

        {/* ── 2. 이용약관 ── */}
        <Section id="tos" title="2. 이용약관" />

        <H3>제1조 (목적)</H3>
        <P>본 약관은 주식회사 시각(이하 &ldquo;회사&rdquo;)이 운영하는 SIGAK(이하 &ldquo;서비스&rdquo;)의 이용 조건 및 절차, 회사와 이용자의 권리·의무·책임 사항을 규정함을 목적으로 합니다.</P>

        <H3>제2조 (용어의 정의)</H3>
        <Table
          headers={["용어", "정의"]}
          rows={[
            ["서비스", "회사가 제공하는 SIGAK 웹·모바일 애플리케이션 및 관련 부가 서비스"],
            ["이용자", "본 약관에 따라 서비스를 이용하는 회원"],
            ["판정(Verdict)", "이용자가 업로드한 사진을 분석하여 가장 적합한 1장(GOLD)과 부가 순위(SILVER, BRONZE)를 반환하는 분석 결과"],
            ["토큰", "서비스 내 유료 기능 이용을 위해 이용자가 구매하는 가상의 결제 수단. 1 토큰 = 100원"],
            ["토큰 팩", "Starter (100 토큰/10,000원), Regular (280 토큰/25,000원), Pro (600 토큰/50,000원)"],
            ["블러 해제", "50 토큰을 소비하여 판정 결과의 전체 내용(SILVER, BRONZE 사진 및 상세 분석)을 열람하는 행위"],
          ]}
        />

        <H3>제3조 (약관의 효력 및 변경)</H3>
        <Ol items={[
          "본 약관은 서비스를 이용하고자 하는 모든 이용자에 대하여 그 효력을 발생합니다.",
          "회사는 관련 법령을 위배하지 않는 범위에서 본 약관을 개정할 수 있습니다.",
          "약관 개정 시 적용 일자와 개정 사유를 명시하여 적용 일자 7일 전부터 서비스 내에서 공지합니다.",
        ]} />

        <H3>제4조 (회원 가입)</H3>
        <Ol items={[
          "본 서비스는 만 14세 이상의 이용자를 대상으로 합니다. 만 14세 미만의 아동은 가입이 불가능합니다.",
          "회원 가입은 카카오 로그인을 통해 이루어집니다.",
          "가입 시 이용자는 본 약관, 개인정보 수집·이용 동의, 민감정보(얼굴 생체 특징) 수집·이용 동의에 각각 동의하여야 합니다.",
        ]} />
        <P>회사는 다음 경우 가입 신청을 거절하거나 사후에 이용 계약을 해지할 수 있습니다.</P>
        <Ul items={[
          "실명이 아니거나 타인의 명의를 이용한 경우",
          "허위 정보를 기재하거나 필수 정보를 기재하지 않은 경우",
          "만 14세 미만임이 확인된 경우",
        ]} />

        <H3>제5조 (서비스의 내용)</H3>
        <P>회사는 이용자에게 다음 서비스를 제공합니다.</P>
        <Ol items={[
          "판정(Verdict) 기능: 이용자가 업로드한 사진(3~10장)을 분석하여 가장 적합한 1장(GOLD)과 추가 순위(SILVER, BRONZE)를 제공합니다. GOLD 결과와 짧은 해석은 무료로 제공됩니다.",
          "블러 해제 기능(유료): 50 토큰 소비 시 SILVER·BRONZE 사진과 전체 상세 분석을 열람할 수 있습니다.",
          "추가 분석 기능(유료, 향후 제공 예정): 판정별 상세 추론(reasoning unlock), 월간 리포트, 시즌별 심화 분석 등",
        ]} />

        <H3>제6조 (토큰 및 결제)</H3>
        <h4 className="mb-2 mt-5 font-sans" style={{ fontSize: 13, fontWeight: 500 }}>6.1 토큰 팩 가격</h4>
        <Table
          headers={["팩", "가격", "토큰 수", "토큰당 단가"]}
          rows={[
            ["Starter", "10,000원", "100 토큰", "100원"],
            ["Regular", "25,000원", "280 토큰", "약 89원 (12% 할인)"],
            ["Pro", "50,000원", "600 토큰", "약 83원 (17% 할인)"],
          ]}
        />
        <h4 className="mb-2 mt-5 font-sans" style={{ fontSize: 13, fontWeight: 500 }}>6.2 결제 수단</h4>
        <P>결제는 토스페이먼츠를 통해 처리되며, 신용카드, 카카오페이, 네이버페이 등 토스페이먼츠가 지원하는 결제 수단을 이용할 수 있습니다.</P>
        <h4 className="mb-2 mt-5 font-sans" style={{ fontSize: 13, fontWeight: 500 }}>6.3 토큰 소비 단가 (참고)</h4>
        <Table
          headers={["기능", "소비 토큰", "환산 금액"]}
          rows={[
            ["블러 해제 (1회 판정당)", "50 토큰", "5,000원"],
            ["추론 언락 (1 verdict당)", "5 토큰", "500원"],
            ["월간 리포트", "30 토큰", "3,000원"],
          ]}
        />

        <H3>제7조 (환불 정책)</H3>
        <h4 className="mb-2 mt-5 font-sans" style={{ fontSize: 13, fontWeight: 500 }}>7.1 토큰 환불</h4>
        <Ol items={[
          "이용자는 토큰 구매 후 구매일로부터 7일 이내이면서 구매한 토큰을 전혀 소비하지 않은 경우에 한하여 환불을 요청할 수 있습니다.",
          "환불 조건을 모두 충족하는 경우, 회사는 결제 금액 전액을 환불합니다.",
          "환불 요청은 고객센터(partner@sigak.asia)를 통해 접수하며, 요청 접수 후 영업일 기준 7일 이내에 처리합니다.",
          "환불은 결제 시 사용한 수단으로 이루어집니다.",
        ]} />
        <h4 className="mb-2 mt-5 font-sans" style={{ fontSize: 13, fontWeight: 500 }}>7.2 환불 불가 사유</h4>
        <P>다음 경우 환불이 제한됩니다.</P>
        <Ol items={[
          "구매한 토큰 중 일부라도 소비한 경우",
          "구매일로부터 7일이 경과한 경우",
          "이미 환불 처리가 완료된 건에 대한 중복 요청",
        ]} />
        <h4 className="mb-2 mt-5 font-sans" style={{ fontSize: 13, fontWeight: 500 }}>7.3 청약 철회권 예외</h4>
        <P>「전자상거래 등에서의 소비자보호에 관한 법률」 제17조 제2항 제5호에 따라, 이미 소비된 디지털 콘텐츠(사용된 토큰)에 대해서는 청약 철회가 제한됩니다.</P>

        <H3>제8조 (이용자의 의무)</H3>
        <P>이용자는 다음 행위를 하여서는 안 됩니다.</P>
        <Ul items={[
          "타인의 사진을 무단으로 업로드하는 행위",
          "미성년자 또는 제3자의 얼굴이 포함된 사진을 본인 동의 없이 업로드하는 행위",
          "음란물, 폭력적·불법적 콘텐츠를 업로드하는 행위",
          "서비스의 정상적 운영을 방해하는 행위",
          "타인의 개인정보를 부정하게 수집·이용하는 행위",
          "자동화된 수단(봇, 스크립트)을 이용한 서비스 이용",
        ]} />
        <P>이용자는 본인 계정의 보안 관리에 대한 책임을 집니다. 계정 정보 유출로 인한 피해는 이용자의 귀책 사유에 해당합니다.</P>

        <H3>제9조 (서비스의 변경 및 중단)</H3>
        <Ol items={[
          "회사는 서비스의 내용, 가격, 기능, 운영 정책 등을 변경할 수 있습니다.",
          "변경 시 사전 고지하며, 중대한 변경의 경우 적용일 최소 7일 전 공지합니다.",
        ]} />
        <P>회사는 다음 경우 서비스 제공을 일시적으로 중단할 수 있습니다.</P>
        <Ul items={[
          "시스템 점검, 증설, 교체 등의 사유",
          "천재지변, 전시·사변, 전력 공급 중단 등 불가항력적 사유",
          "제휴 서비스(카카오, 토스페이먼츠, Anthropic 등) 제공 중단",
        ]} />

        <H3>제10조 (면책 조항)</H3>
        <P>회사는 다음 사유로 인한 손해에 대해 책임을 지지 않습니다.</P>
        <Ul items={[
          "천재지변 또는 이에 준하는 불가항력 상황",
          "이용자의 귀책 사유로 발생한 서비스 이용 장애",
          "이용자가 제공한 정보의 부정확성으로 인한 결과",
          "제휴 서비스(카카오, 토스, Anthropic 등)의 장애",
        ]} />
        <P>본 서비스의 판정 결과는 AI 분석에 기반한 <strong>참고 정보</strong>이며, 미의 절대 기준이 아닙니다. 결과의 활용에 대한 최종 판단과 책임은 이용자 본인에게 있습니다. 회사는 판정 결과의 주관적 만족도, 사회적 반응, 타인의 평가에 대해 책임지지 않습니다.</P>

        <H3>제11조 (회원 탈퇴)</H3>
        <Ol items={[
          "이용자는 언제든지 서비스 내 프로필 설정을 통해 탈퇴할 수 있습니다.",
          "탈퇴 시 이용자의 개인정보는 본 처리방침 제3조에 따라 지체 없이 파기됩니다(단, 법정 보유 기간에 해당하는 정보 제외).",
          "탈퇴 시 보유하고 있던 토큰은 환불되지 않으며, 환불 조건을 충족하는 미사용 토큰에 한해 제7조에 따라 환불 요청이 가능합니다.",
        ]} />

        <H3>제12조 (준거법 및 재판관할)</H3>
        <Ol items={[
          "본 약관과 서비스 이용에 관한 분쟁은 대한민국 법률을 준거법으로 합니다.",
          "분쟁이 발생한 경우 민사소송법상 관할 법원에 제기합니다.",
        ]} />

        <H3>제13조 (분쟁 해결)</H3>
        <Ol items={[
          "이용자와 회사 간 분쟁은 당사자 간 협의로 해결함을 원칙으로 합니다.",
          "협의로 해결되지 않는 경우 다음 기관을 통해 해결할 수 있습니다.",
        ]} />
        <Ul items={[
          "소비자분쟁조정위원회: 1372 (www.kca.go.kr)",
          "전자문서·전자거래분쟁조정위원회: 02-2141-5714 (www.ecmc.or.kr)",
        ]} />

        <Hr />

        {/* ── 3. 회사 정보 ── */}
        <Section id="company" title="3. 회사 정보" />
        <Table
          headers={["항목", "내용"]}
          rows={[
            ["회사명", "주식회사 시각"],
            ["서비스명", "SIGAK"],
            ["대표자", "조찬형"],
            ["개인정보 보호책임자", "조찬형 (partner@sigak.asia)"],
            ["고객센터 이메일", "partner@sigak.asia"],
            ["서비스 URL", "https://sigak.asia"],
          ]}
        />

        <Hr />

        <Section id="addendum" title="4. 부칙" />
        <P>본 약관 및 개인정보처리방침은 2026년 4월 20일부터 시행됩니다.</P>

        <p className="mt-12 text-mute" style={{ fontSize: 11, letterSpacing: "-0.005em" }}>
          시행일: 2026년 4월 20일 · 최종 개정일: 2026년 4월 20일
        </p>
      </article>

      <SiteFooter />
    </div>
  );
}

// ─────────────────────────────────────────────
//  재사용 컴포넌트
// ─────────────────────────────────────────────

function Section({ id, title }: { id?: string; title: string }) {
  return (
    <h2
      id={id}
      className="mb-6 mt-12 border-b pb-2"
      style={{
        fontSize: 18,
        fontWeight: 700,
        borderColor: "var(--color-border)",
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
          style={{ fontSize: 13, lineHeight: 1.7, opacity: 0.82, letterSpacing: "-0.005em" }}
        >
          {item}
        </li>
      ))}
    </ul>
  );
}

function Ol({ items }: { items: string[] }) {
  return (
    <ol className="mb-4 list-outside list-decimal space-y-1.5 pl-5">
      {items.map((item, i) => (
        <li
          key={`${i}-${item.slice(0, 20)}`}
          className="font-sans"
          style={{ fontSize: 13, lineHeight: 1.7, opacity: 0.82, letterSpacing: "-0.005em" }}
        >
          {item}
        </li>
      ))}
    </ol>
  );
}

function Table({ headers, rows }: { headers: string[]; rows: string[][] }) {
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
                  borderColor: "var(--color-border)",
                  background: "rgba(15,15,14,0.02)",
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
                    borderColor: "var(--color-border)",
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

function Hr() {
  return <hr className="my-10" style={{ borderColor: "var(--color-border)" }} />;
}

function SiteFooter() {
  return (
    <footer
      className="border-t px-5 py-8 md:px-[var(--spacing-page-x)]"
      style={{ borderColor: "var(--color-border)" }}
    >
      <div className="mx-auto max-w-2xl">
        <div className="mb-4 flex flex-wrap gap-x-6 gap-y-1 text-mute" style={{ fontSize: 11 }}>
          <Link href="/terms" className="hover:opacity-70">이용약관</Link>
          <Link href="/refund" className="hover:opacity-70">환불규정</Link>
          <a href="mailto:partner@sigak.asia" className="hover:opacity-70">partner@sigak.asia</a>
        </div>
        <p className="text-mute" style={{ fontSize: 10, lineHeight: 1.8, opacity: 0.5 }}>
          주식회사 시각 | 대표: 조찬형 | partner@sigak.asia
          <br />
          &copy; 2026 SIGAK. All rights reserved.
        </p>
      </div>
    </footer>
  );
}
