# Persona C Legacy Archive

페르소나 C "겸손한 경력 디자이너 친구" 시대 (2026-04-27 ~ v4 진입 시점) 코드 격리 archive.

## 격리 사유

베타 6/20 부정 피드백 + FGI 결과:
- A 톤 (AI틱) — `결`, `같아요`, `느낌이 들어요` 등 차단 어휘 미흡
- B 신뢰 (환각) — A-23 보강 필요
- C 깊이 (관통) — 첫 5교환에 단정/진단 발생 (T6 부터 가능해야)
- D 흐름 (매력) — MI 원칙 미반영, change talk 유도 부재

페르소나 C → v4 "미감 비서" 전면 재작성 (2026-04-28).

## 격리 범위

### prompts/haiku_sia/ (8 파일)
- base.md (386줄) — 페르소나 C 본문
- observation.md / recognition.md / diagnosis.md / confrontation.md
- extraction.md / probe.md / empathy_mirror.md

### tests/fixtures/sia_phase_h/ (5 페르소나)
- manjae.py / jieun.py / junho.py / doyoon.py / seoyeon.py
- 14 메시지 타입 라우팅 검증용 fixture

## 보존 (이전 안 함)

### services/ (Phase 3 에서 본문 재작성)
- sia_hardcoded.py — _OPENING_VARIANTS 외 7 pool deprecation 배너만 표기
- sia_decision.py — 14 타입 라우팅, Phase 3 에서 11 turn (T1-T11) 으로 재작성
- sia_validators_v4.py — A-17 / A-23 보존, A-30 / A-34 신설 예정
- sia_flag_extractor.py — 9 flag → 3 flag (has_self_doubt/has_uncertainty/vault_present)

### tests/fixtures/sia_phase_h/ (구조 보존)
- __init__.py — fixture import 제거 + ALL_FIXTURES={} 로 격리
- schema.py — 신규 v4 fixture 작성 시 재사용

## 복구

```bash
# Phase 1 commit hash 로 복귀
git revert <Phase 1 commit hash>

# Maintenance 모드 해제
# .env / Railway dashboard:
SIA_V4_MAINTENANCE=false
```

## v4 진입 후

이 디렉토리는 영구 보존. v4 가 안정화되어도 페르소나 C 시대 의사결정 추적용.

작성: 2026-04-28
