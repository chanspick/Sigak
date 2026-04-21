---
id: SPEC-ONBOARDING-V2
created: "2026-04-21"
---

# SPEC-ONBOARDING-V2 Acceptance Criteria

## 1. Onboarding Structured Input (Step 0)

- [ ] AC-ONBD-001: Step 0 폼 제출 시 gender (female/male), birth_date (YYYY-MM-DD), ig_handle (optional) 3 필드 수집
- [ ] AC-ONBD-002: gender / birth_date 미입력 시 폼 validation 에러 표시
- [ ] AC-ONBD-003: birth_date 1900-01-01 ~ 오늘 범위 외 입력 시 거부
- [ ] AC-ONBD-004: ig_handle 필드 빈 상태로 제출 가능 (nullable)
- [ ] AC-ONBD-005: 제출 후 users 테이블에 gender/birth_date/ig_handle 저장 확인
- [ ] AC-ONBD-006: 제출 후 user_profiles 테이블 row 생성 확인 (onboarding_completed=false)

## 2. IG Feed Collection (Step 1)

- [ ] AC-IG-001: ig_handle 제출 시 Apify Actor 호출 발생 (로그 확인)
- [ ] AC-IG-002: Apify 성공 시 user_profiles.ig_feed_cache 에 profile_basics + feed_highlights 저장
- [ ] AC-IG-003: Apify 10초 초과 시 ig_fetch_status="failed" 저장 + 토스트 "IG 피드를 못 가져왔어요" 표시
- [ ] AC-IG-004: 비공개 계정 수집 시 scope="public_profile_only" 저장 + profile_picture/bio 만 추출
- [ ] AC-IG-005: IG_ENABLED=false 환경변수 설정 시 Step 0 ig_handle 필드 hidden + Step 1 skip
- [ ] AC-IG-006: ig_fetched_at + 14일 경과한 유저가 서비스 방문 시 백그라운드 refresh 트리거 (로그 확인)
- [ ] AC-IG-007: Apify 실패 시 onboarding flow 중단되지 않음 (Step 2 로 진행)

## 3. Sia Conversational AI (Step 2) — 2026-04-22 persona 재작성 반영

### 3-a. 호칭 폴백 체인
- [ ] AC-SIA-001: 카톡 OAuth name 한글 유저 로그인 시 Sia 첫 메시지에 "[NAME]님" 포함
- [ ] AC-SIA-002: name 없는 유저 로그인 시 Sia 첫 메시지 "어떻게 불러드리면 됩니까?" 포함
- [ ] AC-SIA-003: 애플 로그인 + name 없는 유저가 naming 질문 skip 시 이후 모든 턴 호칭 생략

### 3-b. 톤 규칙 (자동 grep 검증 — test_sia_samples.py)
- [ ] AC-SIA-004: 금지 어미 0건 — "~네요" / "~시더라고요" / "~같아요" / "~이더라고요" / "~거든요" / "~있으세요?" / "~드릴게요"
- [ ] AC-SIA-005: 서술형 정중체 어미 존재 확인 — "~합니다" / "~습니다" / "~있습니다" / "~인 분입니다" 중 1개 이상
- [ ] AC-SIA-006: Sia 응답 한 턴에 2-3 sentences 이내 (오프닝만 4 허용)
- [ ] AC-SIA-007: 문장당 35자 이내 (한/라/숫 1자 카운트)

### 3-c. Hard Rules — 5건 (위반 시 응답 무효)
- [ ] AC-SIA-HR1: "Verdict" / "verdict" 단어 0건 (case-insensitive grep)
- [ ] AC-SIA-HR2: "판정" 단어 0건
- [ ] AC-SIA-HR3: 마크다운 문법 0건 — `**`, `*` (강조), `##`, `>`, 백틱 (3연속)
- [ ] AC-SIA-HR4: 별표 리스트 불릿 0건 (하이픈 `- ` 만 허용)
- [ ] AC-SIA-HR5: 이모지 0건 (Unicode emoji range 전수)

### 3-d. 질문 구조 & 평가 금지
- [ ] AC-SIA-QS1: 4지선다 질문이 기본 구조 (5턴 중 최소 3턴 이상 4지선다)
- [ ] AC-SIA-QS2: 각 선택지에 구체적 상황/감정/맥락 포함 (generic label 금지)
- [ ] AC-SIA-QS3: 주관식 허용 필드는 desired_image / current_concerns 만
- [ ] AC-SIA-EV1: 평가 표현 0건 — "좋아 보입니다" / "잘 어울립니다" / "예뻐 보입니다"
- [ ] AC-SIA-EV2: 확인 요청 0건 — "본인도 그렇게 생각하세요?" / "맞나요?" / "어떠세요?"
- [ ] AC-SIA-EV3: 시적 비유 0건 — "봄바람 같은" / "햇살처럼" / "물결처럼"
- [ ] AC-SIA-EV4: 메이크업 어휘 0건 (메이크업/립스틱/블러셔/아이섀도 등 §1 grep 동일)

### 3-e. 유저 정의 단정문
- [ ] AC-SIA-DEF1: 오프닝에 유저 한 문장 정의 포함 — "{NAME}님은 X 인 분입니다" 패턴
- [ ] AC-SIA-DEF2: 정의문은 판정/평가가 아닌 관찰 기반 서술 (예: "정돈된 인상을 전달하는 데 익숙하신 분")

### 3-f. 구체 숫자 근거 (REQ-SIA-002c)
- [ ] AC-SIA-NUM1: 숫자 출현 시 IG_FEED_SUMMARY / vision analysis / session stats 중 하나에서 근거 가능 (코드 레벨 trace 가능성)
- [ ] AC-SIA-NUM2: 데이터 없는 상태 (IG 실패/초기 턴) 에서 숫자 생략 (조작된 숫자 0건)

### 3-g. CTA 자연 흡수 (클로징)
- [ ] AC-SIA-CTA1: 클로징에 "시각이 본 나" 언급 (유저 노출 이름)
- [ ] AC-SIA-CTA2: CTA 분량 1 문장 이내 (별도 섹션/강조 없이 자연 흡수)

### 3-h. 세션 라이프사이클 (기존)
- [ ] AC-SIA-009: Redis 세션 키 `sia:session:{conversation_id}` 생성 + TTL 300s sliding 확인
- [ ] AC-SIA-010: 유저 idle >5분 시 세션 자동 종료 + extraction 트리거
- [ ] AC-SIA-011: turn_count > 50 시 Sia 가 "이제 정리하겠습니다" 제안 (강제 종료 아님)
- [ ] AC-SIA-012: "이만하면 됐어요" 버튼 클릭 시 세션 즉시 종료 + extraction 트리거

### 3-i. 자동 검증 테스트 파일 (D3 deliverable)

- [ ] AC-SIA-TEST: `sigak/tests/test_sia_samples.py` 파일 존재
- [ ] AC-SIA-TEST: 오프닝 / 중간 / 클로징 3 샘플 각각 위 AC-SIA-HR* / EV* / QS* 전수 통과
- [ ] AC-SIA-TEST: 금지 어미 regex + 마크다운 regex + 이모지 regex 공용 유틸로 추출

## 4. Extraction Pipeline

- [ ] AC-EXT-001: 대화 종료 후 Sonnet 4.6 호출 발생 (로그 확인)
- [ ] AC-EXT-002: extraction 결과에 confidence 필드 포함 (각 추출 필드별 0.0-1.0 값)
- [ ] AC-EXT-003: confidence <0.4 필드는 null 저장 + fallback_needed 리스트 추가
- [ ] AC-EXT-004: 필수 필드 (desired_image, height, weight, shoulder_width) 누락 시 Sia fallback 1-2 턴 실행
- [ ] AC-EXT-005: Sonnet 호출 실패 시 1회 재시도 + 실패 시 운영 알림
- [ ] AC-EXT-006: extraction 결과가 conversations.extraction_result 에 저장
- [ ] AC-EXT-007: extraction 결과가 user_profiles.structured_fields 에 merge
- [ ] AC-EXT-008: makeup_level 필드 extraction 결과에 존재하지 않음 (v2 삭제 검증)

## 4-a. SIGAK Naming System (REQ-NAMING-*)

- [ ] AC-NAMING-001: 모든 Sia 응답에 "Verdict" / "verdict" / "판정" 0건 (AC-SIA-HR1/2 와 중복)
- [ ] AC-NAMING-002: Verdict 2.0 API 응답의 `hook_line` / `reason_summary` / `verdict` / `recommendation` 텍스트에 "Verdict" / "판정" 0건
- [ ] AC-NAMING-003: Verdict 2.0 LLM 은 유저 노출 텍스트에서 "피드 분석" 용어 사용
- [ ] AC-NAMING-004: PI unlock 응답에서 유저 노출 제목/설명이 "시각이 본 나"
- [ ] AC-NAMING-005: Monthly 기능 (Priority 2+) 에서 "이달의 시각" 용어 사용
- [ ] AC-NAMING-006: 내부 코드는 기존 naming 유지 (route path `/api/v1/verdicts`, function `build_hair_spec` 등 — git grep 으로 확인)

---

## 5. Verdict 2.0 Preview/Full

- [ ] AC-VERDICT-001: POST /api/v1/verdicts 사진 3-10장 업로드 + 토큰 0 차감
- [ ] AC-VERDICT-002: 응답에 preview.hook_line (≤30 chars) + preview.reason_summary (2-3 문장)
- [ ] AC-VERDICT-003: preview 에 photo_insights 개별 내용 없음 (grep 검증)
- [ ] AC-VERDICT-004: preview 에 recommendation.next_action 구체 내용 없음 (grep 검증)
- [ ] AC-VERDICT-005: POST /api/v1/verdicts/{id}/unlock-full 토큰 10 차감 (idempotency_key=verdict_id)
- [ ] AC-VERDICT-006: 토큰 <10 유저의 unlock-full 시 HTTP 402 반환
- [ ] AC-VERDICT-007: full_unlocked=true 시 full_content 필드 포함 응답
- [ ] AC-VERDICT-008: GET /api/v1/verdicts/{id} 재조회 시 full_unlocked 상태 존중
- [ ] AC-VERDICT-009: 사진 2장 이하 업로드 시 HTTP 400 반환
- [ ] AC-VERDICT-010: 사진 11장 이상 업로드 시 HTTP 400 반환

## 6. PI (Persistent Identity)

- [ ] AC-PI-001: POST /api/v1/pi/unlock 토큰 50 차감 + pi_report 생성
- [ ] AC-PI-002: pi_report 에 9 섹션 포함 (cover, executive_summary, face_structure, skin_analysis, gap_analysis, hair_recommendation, action_plan, type_reference, trend_context)
- [ ] AC-PI-003: PI 입력이 user_profile.structured_fields 기반으로 작동 (onboarding_data 의존 제거)
- [ ] AC-PI-004: PI 재호출 시 기존 pi_report 반환 (idempotent)

## 7. User Profile Management

- [ ] AC-PROFILE-001: user_profiles 테이블에 user_id 당 row 1개 (UNIQUE)
- [ ] AC-PROFILE-002: POST /api/v1/user/refresh-ig 강제 재수집 + ig_fetched_at 갱신
- [ ] AC-PROFILE-003: POST /api/v1/user/restart-conversation 시 기존 conversations archive + 새 row 생성
- [ ] AC-PROFILE-004: restart-conversation 시 토큰 차감 0
- [ ] AC-PROFILE-005: 설정 페이지에서 current_concerns / height / weight / shoulder_width 수동 수정 가능
- [ ] AC-PROFILE-006: 수동 수정 후 다음 Verdict/PI 실행에 반영됨 (caching stale 아님)

## 8. Legacy Migration

- [ ] AC-MIG-001: v1 onboarding_completed=true 유저 로그인 시 대시보드 배너 "Sia와 대화해보기" 노출
- [ ] AC-MIG-002: v1 유저가 배너 클릭 시 새 v2 flow 진입
- [ ] AC-MIG-003: v1 유저가 배너 dismiss 시 기존 v1 경험 유지 (재온보딩 강제 X)
- [ ] AC-MIG-004: v1 users.onboarding_data 는 read-only archive (v2 write 차단)
- [ ] AC-MIG-005: /questionnaire/* 라우트 → /onboarding/basics 302 redirect

## 9. Male Path Compatibility

- [ ] AC-MALE-001: Phase A 7 커밋 (fd77c40~5832a7a) 모두 HEAD 에 존재 (git log 검증)
- [ ] AC-MALE-002: male 유저 시뮬레이션 (테스트 계정 + gender="male") 대화 응답에 메이크업 어휘 0 건
- [ ] AC-MALE-003: user_profiles.structured_fields 에 makeup_level 키 없음 (SELECT 검증)
- [ ] AC-MALE-004: 프론트 start-overlay.tsx disabled:true 유지 (git diff 검증)
- [ ] AC-MALE-005: 남성 일반 유저는 v2 onboarding 접근 시 "준비 중" 안내 (Priority 3 완료 전까지)

## 10. Quality & Telemetry

- [ ] AC-QUAL-001: conversations 테이블에 turn_count / duration / idle_timeouts 메타데이터 저장
- [ ] AC-QUAL-002: extraction 성공 시 confidence 평균 로그 기록
- [ ] AC-QUAL-003: 24시간 abandonment rate >30% 시 운영 알림 트리거 (Q7 QA gate)
- [ ] AC-QUAL-004: confidence <0.4 필드 통계 일일 집계

## E2E Scenarios (통합 검증)

- [ ] E2E-1: 신규 유저 + 카톡 한글 name + IG 성공 → Onboarding 완주 → Verdict → PI 결제 → 9섹션 수신
- [ ] E2E-2: 신규 유저 + name 없음 (2순위 fallback) + IG 미제출 → Sia naming 질문 → 대화 → 완주
- [ ] E2E-3: 신규 유저 + 애플 로그인 (3순위 fallback) → 호칭 생략 대화 → 완주
- [ ] E2E-4: v1 유저 로그인 → "Sia와 대화해보기" 배너 → 재온보딩 수락 → v2 flow 완주
- [ ] E2E-5: v1 유저 로그인 → 배너 dismiss → v1 대시보드 유지
- [ ] E2E-6: Verdict 업로드 → preview 확인 → 10토큰 결제 → full 확인 (동일 verdict_id 에서)
- [ ] E2E-7: 토큰 부족 유저 → Verdict preview 는 받음 → full unlock 시 402 + 충전 안내
- [ ] E2E-8: 남성 테스트 계정 (gender=male 강제) → "준비 중" 안내 (AC-MALE-005 검증)

## Release Gate

- [ ] 모든 유닛 테스트 통과
- [ ] AC-* 체크리스트 >=90% 통과 (E2E 8개 중 최소 6개 통과)
- [ ] Sia 샘플 대화 10건 수동 검수 통과
- [ ] LLM 비용 실측 <$0.10/유저 확인
- [ ] Staging 배포 후 파운더 테스트 계정 통과 (카톡/애플 각 1건)
- [ ] 프로덕션 배포 승인
