# SIGAK Design System

> 시각 (SIGAK) — AI 퍼스널 이미지 분석 서비스.
> "오늘 한 장." 3~10장 중 가장 나다운 한 장을 AI가 골라드리는 서비스.
> 한국 20-30대 타깃. 모바일 중심 (max-width 440px).

이 디자인 시스템은 **웜 베이지 (#F3F0EB) + 블랙 (#000000) 모노크롬** 브랜드를 중심으로 구성됩니다. 장식은 0, 폰트만 존재하는 분석 툴 미감. 서브 스크린 "Sia" (AI 미감 분석가) 대화 UI 스펙도 포함.

## Sources

- Codebase (local mount): `Sigak/` — Next.js 16 App Router repo (`sigak-web/`) + Python backend (`sigak/`).
- 레퍼런스 UX 문서: `Sigak/UX.md`, `Sigak/sigak-web/README.md`, `Sigak/CLAUDE.md` (MoAI orchestrator rules — 디자인과 무관, 프로젝트 맥락용).
- 실제 토큰 원본: `Sigak/sigak-web/app/globals.css` (MVP v1.2 — 웜 베이지 + 블랙 브랜딩).
- Brand assets: `Sigak/favicons/` (Osiris Eye 로고), `Sigak/sigak-web/public/images/sculptures/`, `.../public/images/types/`.

Figma / Github 링크은 현재 제공되지 않음. 모든 토큰은 codebase에서 직접 추출.

## Products in scope

| Product | Path | Stack | Role |
|---|---|---|---|
| **sigak-web** | `Sigak/sigak-web/` | Next.js 16, React 19, Tailwind v4, TS | 공개 MVP. 카카오 로그인 → 피드 → Verdict 판정 → 리포트 |
| **sigak (backend)** | `Sigak/sigak/` | FastAPI, SQLAlchemy | API + 얼굴/스타일 분석 파이프라인. UI 없음 |
| **Sia 채팅 UI** | (신규 스펙) | — | 4지선다 기반 온보딩 대화 AI. 디자인 스펙만 존재 |

---

## CONTENT FUNDAMENTALS

톤: **서술형 정중체, 시적으로 짧고 단정적인 선언.**

- 문어체 `~합니다 / ~습니다`. `~네요 / ~같아요` 같은 확인 요청은 금지.
- 단문. 마침표 단위 분리. 예: "오늘 한 장." "이 중에서는, 이 한 장." "3~10장 중 가장 나다운 한 장을."
- 1인칭/2인칭은 서비스/AI 관점. 유저 호명은 `정세현님` 풀네임 + 님.
- Sia 자기 소개는 `정세현님, Sia입니다.` 형태.
- 숫자 · 데이터를 주어로 사용 ("피드 38장을 분석했습니다.", "쿨뮤트 68%").
- 마크다운/이모지 **금지**. 유니코드 구분자는 `·` middle dot 하나만 (가격 `₩5,000` 및 날짜 `2026 · 04 · 22`).
- 업리얼 광고 카피 지양. "~드립니다" 권유체도 제한적으로만 ("한 장을 골라드립니다.").
- 버튼 카피는 체언 단독: `시작`, `공유`, `해제 · 10 토큰`, `진단 보기`.
- 마이크로카피는 의미를 다 드러내지 않는 쪽. `3~10장 올려주세요.` 정도. 왜 그래야 하는지는 설명 안 함.
- 에러는 직설적 한 문장: `판정 생성에 실패했습니다. 다시 시도해주세요.`

**Sia 페르소나 (대화 AI):**
- 한 턴을 `마침표 = 버블 경계`로 분리. 긴 서술이 벽처럼 떨어지지 않도록.
- 유저를 정의하는 한 문장 형태: `정세현님은 정돈되고 조용한 인상을 전달하는 데 익숙하신 분입니다`.
- 대부분 턴은 4지선다로 끝남. 가끔 주관식 전환.
- 데이터 근거 붙임: "피드의 촬영 각도와 채도 선택이 이미 그 방향을 가리키고 있었습니다."

**랜딩 카피 실사용 예시 (/):**
- h1: `오늘 한 장.`
- subtitle: `3~10장 중 가장 나다운 한 장을.`
- CTA: `카카오로 시작하기`
- fineprint: `계속 진행하면 이용약관 · 개인정보처리방침에 동의하는 것으로 간주됩니다.`

**Result 카피 실사용 예시 (/verdict/[id]):**
- h1: `시각이 본 당신.`
- meta: `2026 · 04 · 22` (공백 padded middle dot)
- 버튼: `공유`, `진단 보기`, `해제 · 10 토큰`

---

## VISUAL FOUNDATIONS

### Palette — monochrome + warm paper

- **Paper** `#F3F0EB` — 배경 전면. 완전 흰색 아님. 따뜻하고 재질감 있는 베이지.
- **Ink** `#000000` — 텍스트 + 프라이머리 bg (TopBar, PrimaryButton). 순수 블랙.
- **Ink opacities**: `0.04 / 0.06 / 0.10 / 0.15 / 0.30 / 0.40 / 0.55 / 0.85` — 표현되는 depth/emphasis 전부를 opacity 단계로만 다룸. 회색을 섞지 않음.
- **Danger** `#A32D2D` — 에러/삭제 텍스트 전용. 아이콘/보더에는 금지.
- **No accent color.** 브랜드 팔레트는 ink + paper + 에러 하나. Kakao yellow `#FEE500`은 OAuth CTA에만 노출되며 Sia UI에는 절대 들어가지 않음.

### Type

- Display/headline: **Noto Serif KR 400** — h1 34–40px, h2 22–28px, 라인높이 1.2–1.3, tracking `-0.02em`–`-0.01em`.
- UI/Body: **Pretendard Variable 400/600** — body 13px, 버튼 14/600, 라벨 11/600 uppercase tracking 1.5px.
- Mono: `ui-monospace, Menlo, Consolas` (거의 미사용. 토큰/숫자는 serif + tabular-nums 선호).
- **Serif를 숫자 포맷터로 승격**: 잔액, 개수, 가격은 serif + `tabular-nums`. 예: `5 / 10`, `₩5,000`.
- Latin을 섞을 때도 Pretendard가 한국어와 동일 스택 담당 (Inter 대체 안 함).

### Backgrounds

- Full bleed paper (`#F3F0EB`) 한 가지.  **gradient / pattern / texture / 이미지 배경 전부 없음.**
- 데스크톱에서는 body가 440px max-width로 가운데 정렬, 주변은 `#1a1a1a` 어두운 톤 → 폰 프레임 느낌. `box-shadow: 0 0 40px rgba(0,0,0,0.12)`.

### Hairlines, dividers, borders

- 수평 rule = `height: 1px; background: var(--color-ink); opacity: 0.15;` — 페이지 좌우 28px margin 안쪽에서.
- 버튼 테두리 = `1px solid rgba(0,0,0,0.15)` (secondary) / `0.5px solid var(--color-ink)` (selected pill).
- Radius는 **거의 0**. 예외 2개: pill `999px` (PillGroup, 프로필 avatar), avatar. 카드에 둥근 모서리 금지.

### Shadow

- 거의 없음. 예외:
  - Photo kebab 드롭다운 메뉴: `0 4px 12px rgba(0, 0, 0, 0.08)`
  - 데스크톱 폰 프레임 주변: `0 0 40px rgba(0, 0, 0, 0.12)`
- inner shadow / long shadow / 2-tone shadow 금지.

### Corner radii

- 버튼/카드/사진 = 0 (날 것).
- Pill · PillButton = `999px`.
- 아바타 = `50%`.

### Cards

- 카드 개념 자체가 약함. "섹션"은 `padding: 28px 28px 36px` + 아래 hairline rule로만 구분.
- 필요 시 outline 카드: `border: 1px solid rgba(0,0,0,0.15); padding: 24px 22px; background: transparent; border-radius: 0;`. 채워진 카드 없음.

### Motion

- Ease-out 전용 (`ease-out`, `220–260ms`).
- `sigak-fade-in 220ms`, `sigak-slide-in-right 260ms`, `sigak-slide-in-up 240ms`, `sigak-pulse-opacity 900ms`.
- Bounce / spring / scale pop 전부 금지. 호버는 **opacity drop** (0.6~0.9) 또는 색 flip, scale 변환 없음.

### Interaction states

- **Hover**: `opacity: 0.6` 또는 `opacity: 0.9`. 셰이드 어둡게 하지 않고 투명도만.
- **Press**: 별도 처리 거의 없음. Long-press 700ms (verdict 삭제)는 `navigator.vibrate(25)` 햅틱 + 이미지 dim `opacity: 0.4`.
- **Focus**: `::selection` 만 역전 (bg ink / fg paper). focus ring 따로 그리지 않음.
- **Disabled**: 투명 bg + `opacity: 0.3` + ink 텍스트 유지 + `1px solid rgba(0,0,0,0.15)` 테두리.

### Blur / transparency

- 유일하게 blur를 쓰는 곳은 **리포트 페이월 티저**: `backdrop-filter: blur(12px)` + `background: rgba(243,240,235,0.7)` 오버레이.
- Verdict 잠긴 이미지(silver/bronze)는 `filter: blur(10px); transform: scale(1.15)` + 얇은 diagonal hatched background.
- 일반 UI 전반에서는 투명/블러 금지.

### Layout rules

- 모바일 고정 `max-width: 440px` body center. 기본 좌우 `padding: 28px`.
- TopBar **52px 고정**, 검정 bg, paper 텍스트, 중앙 letterspaced `SIGAK` 워드마크 (6px tracking).
- CTA 버튼 **높이 56px**, `border-radius: 0`, full-width, 검정 bg + paper 텍스트.
- 그리드: 피드는 `grid-template-columns: repeat(3, 1fr); gap: 2px;` (인스타 느낌). 업로드는 `gap: 6px`.
- 섹션 아래 가로 hairline 은 옵션이 아니라 리듬 요소.

### Photo treatment

- `object-fit: cover`, aspect-ratio 1/1 (그리드) 또는 4/5 (hero gold).
- 플레이스홀더는 `background: rgba(0,0,0,0.04)`. 스켈레톤 애니메이션 없음.
- 자르기 / 둥근 모서리 없음.

---

## ICONOGRAPHY

SIGAK은 **인라인 `<svg>` 1px stroke 아이콘**을 각 컴포넌트가 직접 그려 씁니다 — 공통 아이콘 폰트나 라이브러리를 두지 않습니다. 이 시스템의 아이콘 원칙:

- **Stroke 1px, 또는 1.5px (back chevron)**. Fill은 거의 사용 안 함.
- `stroke="var(--color-paper)"` 또는 `var(--color-ink)`. 색은 bg에 따라 2개 뿐.
- 크기 micro: 10–20px. `aria-hidden`.
- Stroke linecap/linejoin `round`.
- 모티프는 가는 선 · 십자 plus · 얇은 chevron · 점 3개 dot-pattern. 전부 직접 SVG path로 인라인.

**존재하는 실제 아이콘 (sigak-web 코드 기준):**
- `+` plus (TopBar 우측, 피드 첫 셀, 업로드 placeholder) — 두 1px line 교차.
- Chevron back `M8 1L1 8l7 7` (10x16, stroke 1.5, round).
- Kebab (photo 우상단, 세로 3-dot) — `<circle>` 3개 1.6r, fill paper.
- Close `M1 1l12 12M13 1L1 13` (14x14, stroke 1, round).
- Lock (진단 cta 잠금) — rect + arc stroke 1, fill 없음.
- Kakao 말풍선 logo (OAuth 버튼 한정, currentColor fill).

### Emoji / Unicode chars

- **Emoji 금지.** 모든 UI에서.
- Unicode `·` (middle dot U+00B7) — 유일하게 허용되는 장식 구분자. 가격/날짜/요약에 사용.
- 체크 ✓ / × ✕ 같은 심볼도 인라인 SVG로 대체. `result-screen`의 삭제 버튼 `✕`은 예외 (tiny, 10px).

### 브랜드 자산

- 워드마크: `SIGAK` text, Pretendard 600, **6px letter-spacing**. 로고 이미지 없음. 모든 TopBar에서 동일하게 쓰임.
- Favicon / App icon: `assets/osiris-eye-*` — Osiris 눈 모티프. 로그인 전 / 파비콘 / PWA 아이콘에만 사용. 실제 UI에는 등장하지 않음.

### Decorative imagery

- **조각상 (sculpture) PNG** (`assets/sculpture-*.png`) — 고양이/여우/사슴/올빼미. Report type page 가끔. Full bleed는 아님.
- **Type 레퍼런스 사진** (`assets/type_*.jpg`) — 스타일 유형 예시. 실제 사람 사진이며 그대로 노출.
- **유저 피드 이미지 = 유일한 풀 비주얼 요소.** 장식 일러스트 금지.

### Substitutions / caveats

- `Pretendard Variable` 은 원 repo가 jsdelivr CDN을 로드합니다 (`app/layout.tsx`). 이 디자인 시스템도 CDN을 통해 로드 — 별도 woff2 번들은 안 함. 오프라인 사용이 필요하면 [pretendard releases](https://github.com/orioncactus/pretendard/releases) 에서 다운로드.
- `Noto Serif KR` 은 Google Fonts `display=swap` 로 로드.
- Sia 채팅 UI는 현재 codebase에 구현체가 없는 **스펙 전용 서피스**. 이 시스템에서는 spec을 따른 hi-fi prototype을 `ui_kits/sia/` 에 포함.

---

## Index

| 파일 | 설명 |
|---|---|
| `README.md` | 이 파일 — 브랜드 컨텐츠/비주얼 토대 + 인덱스 |
| `colors_and_type.css` | CSS 변수 + 시맨틱 클래스. 모든 산출물에서 import |
| `SKILL.md` | Agent Skills 메타 (브랜드 skill entrypoint) |
| `assets/` | 로고, Osiris 눈, 조각상 png, type jpg |
| `preview/` | Design System 탭에 표시되는 카드들 |
| `ui_kits/sia/` | Sia 대화 UI (4지선다 중심, 스펙 준수) |
| `ui_kits/sigak-web/` | sigak-web MVP 핵심 화면 재현 (랜딩, 피드, Result) |

---

## Caveats

- Figma 링크 없음. Sia 스펙은 첨부된 텍스트 스펙 + 레퍼런스 이미지 설명만으로 작성.
- Sigak-web 의 report 서비스 화면들은 복잡해 시스템에 포함하지 않음 — UI 킷은 MVP v1.2 의 **메인 플로우**(랜딩 → 피드 → Verdict 판정 → 결과)만 재현.
- 폰트 실파일은 번들하지 않고 CDN 링크 사용. 오프라인 프로덕션 빌드 시 woff2 를 별도 수급 필요.
