// /my — IA 정합 (2026-04-26): /profile (마케터 설정) 으로 redirect.
//
// 이전: 다크 헤더 + 히어로 + 2 컬럼 (리포트 + 캐스팅 매칭).
// 변경 이유:
//   1. 메뉴에서 /my 진입점 X (사용자 직접 입력 시만)
//   2. 캐스팅 풀 영역 제거 결정 (PI Revival Phase B-6)
//   3. 리포트 list 는 /vision 또는 /profile 에서 진입 가능
//
// 백엔드 getMyReports / getCastingStatus 는 다른 페이지에서 활용 가능.

import { redirect } from "next/navigation";

export default function MyPage() {
  redirect("/profile");
}
