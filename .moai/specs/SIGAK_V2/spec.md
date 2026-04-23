# SIGAK 프로덕트 설계 문서 (통합 최종본)

**버전:** v2.0
**작성:** 2026-04-22
**상태:** Week 2 재설계 착수 직전, 확정 사항 51개 반영 완료

**선행 문서:**
- v1.0 SIGAK_MASTER_DOC.md (프로덕트 전체 구조)
- sia_context_handoff.md (마케터 Sia 인격설계서)
- Claude Code 현 코드베이스 조사 리포트

(전문은 CLAUDE.md 참조 — 동일 내용 미러링)

---

## Phase 실행 순서 (Claude Code 위임)

| Phase | 의존성 | 상태 | 실행 가능 |
|---|---|---|---|
| G — 공통 인프라 | 없음 | ready | ✅ 즉시 |
| H — Sia 페르소나 B 전환 | 마케터 인격/CONFRONTATION 5종 | blocked | 외부 대기 |
| I — PI 엔진 | G + H + Knowledge Base 콘텐츠 | blocked | Phase G 후 |
| J — 추구미 분석 | G | chainable | G 후 |
| K — Best Shot | G | chainable | G 후 |
| L — Verdict v2 확장 | G | chainable | G 후 (최소 침습) |
| M — 이달의 시각 스켈레톤 | G | chainable | G 후 |
| N — 프론트 | 본인 주도 | parallel | N/A |
| O — 법적/관리자 | 본인/마케터 | parallel | N/A |
| P — Knowledge Base 콘텐츠 | 본인/마케터 | parallel | N/A |
| Q — QA + Soft Launch | 전부 | final | N/A |

**Critical Path**: G → (J/K/L/M 병렬) → H (마케터 해소 후) → I → Q
