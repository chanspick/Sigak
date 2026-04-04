// 날짜 유틸리티

/** YYYY-MM-DD 형식으로 포맷 */
export function formatDate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/** 요일 한글 반환 */
export function getDayName(date: Date): string {
  const days = ["일", "월", "화", "수", "목", "금", "토"];
  return days[date.getDay()];
}

/** 경과 시간 표시 (예: "5분 전", "2시간 전") */
export function getElapsedTime(from: string): string {
  const diff = Date.now() - new Date(from).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "방금 전";
  if (minutes < 60) return `${minutes}분 전`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}시간 전`;
  const days = Math.floor(hours / 24);
  return `${days}일 전`;
}

/** MM.DD (요일) 형식 */
export function formatShortDate(dateStr: string): string {
  const date = new Date(dateStr);
  const m = date.getMonth() + 1;
  const d = date.getDate();
  const day = getDayName(date);
  return `${m}.${d} (${day})`;
}
