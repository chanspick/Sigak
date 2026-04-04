// 티어 타입 정의
export interface Tier {
  id: "basic" | "creator" | "wedding";
  name: string;
  nameUp: string;
  sub: string;
  price: number;
  desc: string;
  target: string;
}
