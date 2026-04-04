# 시각 (Sigak) - AI 이미지 컨설팅 서비스

AI 기반 얼굴 분석 및 스타일 컨설팅 웹 서비스

## 기술 스택

- **프레임워크**: Next.js 16 (App Router)
- **UI**: React 19, TypeScript 5.9+, Tailwind CSS v4
- **패키지 매니저**: pnpm

## 시작하기

```bash
cd sigak-web
pnpm install
pnpm dev
```

[http://localhost:3000](http://localhost:3000)에서 확인할 수 있습니다.

## 라우트 구조

| 라우트 | 설명 |
|--------|------|
| `/` | 랜딩 페이지 (서비스 소개 + "지금 시작하기" CTA) |
| `/start` | 즉시 시작 (티어 선택 + 기본정보 입력) |
| `/questionnaire` | 셀프 질의 폼 (3페이지 멀티스텝) |
| `/questionnaire/complete` | 분석 대기 + 리포트 링크 |
| `/report/[id]` | 리포트 뷰어 (8섹션 + 블러 티저 + 페이월) |

## 프로젝트 구조

```
sigak-web/
├── app/                    # Next.js App Router 라우트
│   ├── page.tsx            # 랜딩 페이지
│   ├── start/              # 즉시 시작 플로우
│   ├── questionnaire/      # 셀프 질의 폼 + 완료
│   └── report/[id]/        # 리포트 뷰어
├── components/
│   ├── landing/            # 랜딩 섹션 (hero, nav, tier 등)
│   ├── start/              # 시작 오버레이
│   ├── questionnaire/      # 질의 폼, 사진 업로드, 분석 로더
│   ├── report/             # 리포트 뷰어 + 8개 섹션
│   └── ui/                 # 공용 UI (button, input, divider 등)
├── lib/
│   ├── api/                # API 클라이언트 (mock)
│   ├── types/              # TypeScript 타입 정의
│   ├── constants/          # 상수 (질문, 티어, mock 데이터)
│   └── utils/              # 유틸리티 (날짜, 리포트, 폴링)
└── public/                 # 정적 파일
```

## 서비스 티어

| 티어 | 가격 | 포함 내용 |
|------|------|-----------|
| 기본 시선 | 50,000원 | 얼굴 분석 + 컬러 매칭 + 메이크업 가이드 |
| 시각 Creator | 200,000원 | 기본 + 썸네일 최적화 + 브랜드 이미지 |
| 시각 Wedding | 200,000원 | 기본 + 웨딩 드레스 가이드 + 스튜디오 앵글 |

## 빌드

```bash
pnpm build    # 프로덕션 빌드
pnpm lint     # ESLint 검사
```
