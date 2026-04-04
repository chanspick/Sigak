// 예약 타입 정의
export interface TimeSlot {
  time: string;
  tier: "basic" | "creator" | "wedding";
}

export interface BookingForm {
  tier: "basic" | "creator" | "wedding";
  date: string;
  time: string;
  name: string;
  phone: string;
  instagram?: string;
}

export type BookingStep = "tier" | "date" | "time" | "form" | "payment";

export type BookingsMap = Record<string, TimeSlot[]>;
