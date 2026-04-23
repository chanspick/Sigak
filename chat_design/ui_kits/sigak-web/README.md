# sigak-web — UI Kit

Pixel recreation of sigak-web MVP v1.2 (ref `Sigak/sigak-web/`). Single-page demo with 4 click-thru tabs.

## Screens
- **Landing** — `/` logged-out state. Centered SIGAK wordmark, "오늘 한 장." h1, Kakao OAuth CTA.
- **Feed** — `/` logged-in. 3-col gap-2 grid. First cell is always `+` upload entry. Source: `components/sigak/verdict-grid.tsx`.
- **Upload** — `/verdict/new`. Serif hero, 사진 / N of 10 counter, 3-col gap-6 upload grid, `시작` full-width primary.
- **Result** — `/verdict/[id]`. Date meta, serif h1 "시각이 본 당신.", 4:5 hero photo, 진단 보기 secondary (10 토큰), serif reading body, `공유` ghost link.

## Components covered
TopBar (2 variants: centered vs. left-aligned with right cluster), PrimaryButton, secondary outline button, Kakao OAuth button, 3-col photo grid, upload dropzone, hairline rule, meta label, serif numeric.
