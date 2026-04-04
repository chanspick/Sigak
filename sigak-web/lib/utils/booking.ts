import type { BookingsMap } from "@/lib/types/booking";
import { formatDate } from "./date";

// 예약 유틸리티

/** 슬롯 예약 여부 확인 */
export function isSlotBooked(
  bookings: BookingsMap,
  date: Date,
  time: string,
  tier: string,
): boolean {
  const key = formatDate(date);
  return bookings[key]?.some((b) => b.time === time && b.tier === tier) ?? false;
}

/** 날짜 매진 여부 (30 슬롯 = 10시간 x 3티어) */
export function isDaySoldOut(bookings: BookingsMap, date: Date): boolean {
  const key = formatDate(date);
  return (bookings[key]?.length ?? 0) >= 30;
}

/** 티어별 예약 수 */
export function getBookedByTier(bookings: BookingsMap, tier: string): number {
  return Object.values(bookings)
    .flat()
    .filter((b) => b.tier === tier).length;
}

/** 전체 예약 수 */
export function getTotalBooked(bookings: BookingsMap): number {
  return Object.values(bookings).flat().length;
}
