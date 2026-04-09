# SIGAK 장기 로드맵 — Phase 7~12

> 전제: 3축 마이그레이션 완료 (migration-3axis.md Phase 0~5)
> 이 문서는 3축 전환 이후 장기 계획만 담는다.

---

## Phase 7: 오버레이 파이프라인 통합 (1~2일)

> overlay_renderer.py v0 → 파이프라인 연결 → 리포트 삽입.

| # | 작업 | 상태 |
|---|------|------|
| 7-1 | face.py에 landmarks_2d_106 저장 추가 | 🔧 |
| 7-2 | main.py에서 리포트 생성 시 오버레이 자동 생성 | 📋 |
| 7-3 | report JSON에 overlay_image_url 포함 | 📋 |
| 7-4 | BeforeAfterOverlay 프론트 삽입 | 📋 |
| 7-5 | ACTION PLAN 섹션에 오버레이 이미지 연결 | 📋 |

---

## Phase 8: 오버레이 고도화 (3~5일)

### v0.5: 추구미 반영 팔레트
- gap vector 방향별 컬러 팔레트 매핑
- ASPIRATION_PALETTES (soft_fresh, sharp_fresh, soft_mature, sharp_mature)

### v1: 풀 오버레이
- blend mode 분기 (highlight → screen, shading → multiply)
- yaw/roll fallback (비정면 대응)
- brow tint 추가
- 컬러 스와치 UI

---

## Phase 9: 스킨톤 고도화 (3~5일)

### 9-1. ROI 확장
- 양 볼 + 이마로 ROI 확장
- 상위/하위 5% 픽셀 트리밍

### 9-2. 동적 컬러 추천
- 유저 피부 LAB → 용도별 색상 공식 (립, 블러셔, 베이스, 포인트)
- 6타입 하드코딩을 baseline으로, 동적 결과와 비교 튜닝

### 9-3. 명도(L*) 축 추가 검토
- 6타입 → 12타입 확장 가능성

---

## Phase 10: 콘텐츠 + UX 개선 (2~3일)

- 설문지 수정 (고민 필드 삭제, placeholder 해요체)
- 랜딩페이지 카피 리뉴얼
- WHY THIS TYPE 고도화
- 리포트 이후 실행 지원 (제품 링크, 단계별 가이드)

---

## Phase 11: 데이터 파이프라인 + 피드백 루프 (지속)

- 피드백 수집 (유형 맞아요? 추천 컬러 어울렸나요?)
- 50명+ 축적 시 OBSERVED_RANGES 재보정
- 가중치 학습 (정답 라벨 100건+)
- 추천 모델 (사진 + 만족도 → 팔레트/액션플랜)

---

## Phase 12: 확장 (장기)

- 남성 파이프라인 분기 (앵커 8개 남성, YAML config 분리)
- z축 트렌드 좌표 (시간에 따른 트렌드 매핑)
- 3D 인터랙티브 시각화 (WebGL/Three.js)
- B2B 캐스팅/브랜드 매칭
- 셀럽 좌표 맵

---

## 타임라인

```
3축 완료 후
    │
    2주 ──→ Phase 7~8 (오버레이)
         ├→ Phase 9 (스킨톤) ← 병렬 가능
         ├→ Phase 10 (콘텐츠) ← 병렬 가능
         │
    1개월 ─→ Phase 11 (피드백 루프 시작)
         │
    3개월 ─→ Phase 12 (확장)
```

---

*이 문서는 migration-3axis.md와 함께 사용합니다.*
*Generated: 2026-04-09*
