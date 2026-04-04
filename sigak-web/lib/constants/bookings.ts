import type { TimeSlot, BookingsMap } from "@/lib/types/booking";

// 전체 시간 슬롯 (09:00~18:00, 1시간 단위)
export const ALL_SLOTS: string[] = [
  "09:00", "10:00", "11:00", "12:00", "13:00",
  "14:00", "15:00", "16:00", "17:00", "18:00",
];

// 티어 목록
const T3: Array<TimeSlot["tier"]> = ["basic", "creator", "wedding"];

// 하루 전체 슬롯 생성 (30개 = 10시간 x 3티어)
const fullDay = (): TimeSlot[] =>
  ALL_SLOTS.flatMap((time) => T3.map((tier) => ({ time, tier })));

// 예약 데이터 헬퍼
const bk = (arr: [string, TimeSlot["tier"]][]): TimeSlot[] =>
  arr.map(([time, tier]) => ({ time, tier }));

// 예약 데이터 (landing.jsx에서 추출)
export const BOOKINGS: BookingsMap = {
  // 1주차
  "2026-04-10": bk([
    ["10:00", "basic"], ["10:00", "creator"], ["11:00", "basic"],
    ["14:00", "wedding"], ["15:00", "basic"], ["15:00", "creator"],
    ["16:00", "wedding"], ["17:00", "basic"], ["17:00", "creator"],
    ["18:00", "wedding"],
  ]),
  "2026-04-11": fullDay(),
  "2026-04-12": fullDay(),
  "2026-04-13": bk([
    ["11:00", "basic"], ["14:00", "creator"], ["14:00", "wedding"],
  ]),
  "2026-04-14": bk([
    ["10:00", "wedding"], ["15:00", "basic"], ["15:00", "creator"],
    ["16:00", "wedding"],
  ]),
  "2026-04-15": bk([
    ["14:00", "basic"], ["14:00", "creator"], ["17:00", "wedding"],
  ]),
  "2026-04-16": bk([
    ["15:00", "creator"], ["16:00", "wedding"], ["16:00", "basic"],
    ["18:00", "creator"],
  ]),
  // 2주차
  "2026-04-17": bk([
    ["09:00", "basic"], ["09:00", "creator"], ["10:00", "wedding"],
    ["10:00", "basic"], ["11:00", "creator"], ["14:00", "basic"],
    ["14:00", "wedding"], ["15:00", "creator"], ["16:00", "basic"],
    ["16:00", "wedding"], ["17:00", "creator"], ["18:00", "wedding"],
  ]),
  "2026-04-18": fullDay(),
  "2026-04-19": fullDay(),
  "2026-04-20": bk([
    ["10:00", "basic"], ["10:00", "creator"], ["14:00", "wedding"],
    ["15:00", "basic"],
  ]),
  "2026-04-21": bk([
    ["11:00", "wedding"], ["11:00", "creator"], ["16:00", "basic"],
  ]),
  "2026-04-22": bk([
    ["14:00", "creator"], ["14:00", "wedding"],
  ]),
  "2026-04-23": bk([
    ["10:00", "basic"], ["15:00", "wedding"], ["15:00", "creator"],
  ]),
  // 3주차
  "2026-04-24": bk([
    ["10:00", "wedding"], ["10:00", "basic"], ["11:00", "creator"],
    ["11:00", "wedding"], ["13:00", "basic"], ["14:00", "creator"],
    ["14:00", "wedding"], ["15:00", "basic"], ["16:00", "creator"],
    ["17:00", "wedding"], ["17:00", "basic"], ["18:00", "creator"],
  ]),
  "2026-04-25": fullDay(),
  "2026-04-26": fullDay(),
  "2026-04-27": bk([
    ["11:00", "creator"], ["14:00", "basic"], ["14:00", "wedding"],
    ["15:00", "creator"],
  ]),
  "2026-04-28": bk([
    ["10:00", "basic"], ["10:00", "wedding"], ["16:00", "creator"],
  ]),
  "2026-04-29": bk([
    ["14:00", "wedding"], ["15:00", "basic"], ["15:00", "creator"],
  ]),
  "2026-04-30": bk([
    ["10:00", "creator"], ["11:00", "wedding"], ["11:00", "basic"],
    ["15:00", "creator"],
  ]),
};

// 전체 슬롯 수 (21일 x 10시간 x 3티어)
export const TOTAL_SLOTS = 21 * 10 * 3; // 630

// 전체 예약 목록
const allBookings = Object.values(BOOKINGS).flat();

// 전체 예약 수
export const totalBooked = allBookings.length;

// 잔여 슬롯 수
export const totalRemain = TOTAL_SLOTS - totalBooked;

// 티어별 예약 수
export const bookedByTier = (tierId: string): number =>
  allBookings.filter((b) => b.tier === tierId).length;
