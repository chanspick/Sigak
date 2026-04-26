/**
 * /pi/upload — DEPRECATED redirect (PI Revival Phase 5, 작업 D).
 *
 * 신 PI v3 시스템 폐기에 따라 본 라우트는 영구 redirect.
 * 옛 link / 북마크 / 공유 url 진입 시 정상 흐름 보장.
 *
 * Target: /photo-upload (옛 SIGAK_V3 system entry, 작업 C 에서 신규 생성).
 * 보존 기간: v1 launch 후 6개월 (v1.5 에서 완전 삭제 검토).
 *
 * @see handoff/PI_REVIVE_V5_OLD_SYSTEM.md 작업 D
 */

import { redirect } from "next/navigation";

export default function PiUploadDeprecated() {
  redirect("/photo-upload");
}
