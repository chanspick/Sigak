# Sia — UI Kit (Persona B)

Sia is SIGAK's AI 미감 분석가 chat surface. Onboarding ~15 messages. Persona B — 친밀 해요체 ("간파하는 친구"). 100% 주관식. 선택지 UI 일체 없음.

> 2026-04-22 업데이트: 세션 #4 v2 확정 spec 반영. 기존 정세현/정중체/4지선다 버전은 deprecated.

## Files
- `index.html` — full conversation view with sample dialogue (세션 #4 v2 §3.2 샘플 2 "만재" M1–M5), loading dots, 주관식 input dock.

## Key rules

### Tone (Persona B)
- 친밀 해요체. "간파하는 친구" 톤. ㅋ/ㅎ/이모지/마크다운 전부 금지.
- 허용 어미 핵심: `~가봐요?` / `~이시잖아요?` / `~더라구요` / `~에요?` / `~세요?` / `~는가봐요?` / `~느낌 있잖아요?`
- 금지 어미: `~네요` 제외한 정중체 단정 (`~군요` / `~같아요` / `~같습니다` / `~것 같아` / `~수 있습니다` / `~수 있어요`).
- 호명 "{user_name}님" — 한 메시지당 최대 1회. 과잉 호명 금지.

### Bubble structure
- Sia message = 1 문장 per bubble (마침표 단위 분리). `parseSiaMessage` 로 자동 split.
- 한 turn 내 bubble 2–3 개 기본. **M1 만 결합 출력** (OPENING_DECLARATION + OBSERVATION) 으로 3 bubble.
- User bubble = dark navy `#111827`, white text, right-aligned, max 78% width.
- Sia bubble = `#F4F4F5`, black text, left-aligned, rounded with tail corner 4px (왼쪽 하단).
- List items (하이픈) 는 render inside ONE bubble, not split.

### Loading / Input
- Loading = 3 dots in a small Sia bubble, sequential bounce animation.
- Input dock = 하단 sticky. pill-shaped `#F4F4F5` textarea (auto-grow max 4 lines) + round pill 전송 버튼 (텍스트 "보내기", 아이콘 금지).
- 선택지 버튼 / 카드 / 퀵리플라이 / 4지선다 일체 금지. 100% 주관식.

### TopBar
- "Sia" name only, centered, `letter-spacing: 6px`, hairline bottom border.
- progress hairline (JSON 수집률) 은 TopBar 하단 1px line 으로 추가 예정 — UI kit 은 기본 버전 유지.
- 카운트다운은 30초 이하에서만 노출 (노출 위치 미결정).

### A11y
- `<textarea>` aria-label: "Sia에게 답하기"
- 전송 버튼 aria-label: "전송"
- IME composition 중 Enter 전송 차단 필수 (React 구현 참조).

## Reference 구현
- `sigak-web/components/sia/SiaBubble.tsx` / `SiaStream.tsx` / `SiaDots.tsx` / `SiaTopBar.tsx` / `SiaInputDock.tsx`
- 백엔드 MsgType enum (11 → 14 예정): `sigak/schemas/sia_state.py`
