# UX.md — SIGAK 소비자 여정 최종본

> 유저가 SIGAK을 처음 발견하는 순간부터 리포트를 공유하는 순간까지.
> 모든 화면, 모든 문구, 모든 감정선을 정의한다.
> 기술 스펙은 CLAUDE.md 참조. 이 문서는 UX만 다룬다.

## 백엔드 리포트 API 응답 구조

```json
{
  "id": "report_abc123",
  "user_name": "홍길동",
  "access_level": "free",
  "sections": [
    { "id": "cover", "locked": false, "content": { "..." } },
    { "id": "executive_summary", "locked": false, "content": { "..." } },
    { "id": "face_structure", "locked": false, "content": { "..." } },
    { "id": "skin_analysis", "locked": true, "unlock_level": "standard",
      "teaser": { "headline": "웜톤 · 밝은 편" } },
    { "id": "coordinate_map", "locked": true, "unlock_level": "standard",
      "teaser": { "headline": "3축 미감 분석 완료" } },
    { "id": "action_plan", "locked": true, "unlock_level": "full",
      "teaser": { "categories": ["메이크업 HIGH", "헤어 HIGH", "스타일링 MEDIUM"] } },
    { "id": "celeb_reference", "locked": true, "unlock_level": "full",
      "teaser": { "headline": "수지와 85% 유사" } },
    { "id": "trend_context", "locked": true, "unlock_level": "full",
      "teaser": null }
  ],
  "paywall": {
    "standard": { "price": 5000, "label": "₩5,000 잠금 해제" },
    "full": { "price": 15000, "label": "+₩15,000 잠금 해제",
              "total_note": "이전 결제 포함 총 ₩20,000" }
  }
}
```

프론트 렌더링 로직:
- locked: false → 전체 렌더링
- locked: true → 블러 티저 + 해당 unlock_level의 마지막 섹션 뒤에 페이월 카드 1개
- 결제 완료 시 access_level 업데이트 → 블러 fade-out → 스크롤 위치 유지

---

## 블러 티저 규칙 요약

원칙: **"답이 있다는 것"은 보여주고, "답 자체"는 가린다.**

| 섹션 | 선명하게 보이는 것 | 블러되는 것 |
|---|---|---|
| 피부톤 | 제목 + "웜톤 · 밝은 편" | 추천 컬러, 주의 컬러, 분석 텍스트 |
| 좌표계 | 제목 + 축 라인/격자/레퍼런스 위치 | 내 점, 추구미 점, 갭 화살표, 수치 |
| 실행가이드 | 카테고리명 + 우선순위(HIGH/MEDIUM) | 구체적 추천 내용 |
| 셀럽 | "수지와 85% 유사" | 유사 이유, 참고 스타일링 |
| 트렌드 | 제목만 | 전부 |

CSS 구현: `backdrop-filter: blur(12px)` + `background: rgba(243,240,235,0.7)` 오버레이.
