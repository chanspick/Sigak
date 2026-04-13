// 티어 타입 정의
export interface Tier {
  id: "standard" | "full";
  name: string;
  sub: string;
  price: number;
  originalPrice?: number;
  desc: string;
  badge?: string;
}
