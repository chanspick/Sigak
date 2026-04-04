"use client";

// 예약 오버레이 (우측 슬라이드 패널)
// 5단계: 티어 선택 -> 날짜(4월 달력) -> 시간 -> 정보입력 -> 결제

import { useState, useEffect, useCallback } from "react";
import { TIERS } from "@/lib/constants/tiers";
import { ALL_SLOTS, BOOKINGS, bookedByTier } from "@/lib/constants/bookings";
import { isSlotBooked } from "@/lib/utils/booking";
import { getDayName } from "@/lib/utils/date";
import type { Tier } from "@/lib/types/tier";

// 요일 헤더
const DAY_NAMES = ["일", "월", "화", "수", "목", "금", "토"];

// 4월 달력 생성 (앞쪽 빈칸 포함)
function getAprilCalendar(): (number | null)[] {
  const result: (number | null)[] = [];
  const startDay = new Date(2026, 3, 1).getDay();
  for (let i = 0; i < startDay; i++) result.push(null);
  for (let i = 1; i <= 30; i++) result.push(i);
  return result;
}

// 폼 상태 인터페이스
interface FormState {
  name: string;
  phone: string;
  ig: string;
  partnerName: string;
  partnerPhone: string;
}

const INITIAL_FORM: FormState = {
  name: "",
  phone: "",
  ig: "",
  partnerName: "",
  partnerPhone: "",
};

interface BookingOverlayProps {
  open: boolean;
  onClose: () => void;
  initTier: Tier["id"] | null;
}

// 입력 필드 서브 컴포넌트
function FormInput({
  label,
  required,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  required?: boolean;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
}) {
  return (
    <div>
      <label className="block text-[11px] font-semibold tracking-[0.5px] opacity-50 mb-1.5">
        {label}
        {required && <span className="ml-0.5">*</span>}
      </label>
      <input
        className="w-full px-3.5 py-3 text-sm bg-transparent border border-black/[0.12] outline-none transition-[border-color] duration-200 placeholder:opacity-25 focus:border-[var(--color-fg)]"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </div>
  );
}

export function BookingOverlay({ open, onClose, initTier }: BookingOverlayProps) {
  const [tier, setTier] = useState<Tier["id"] | null>(initTier);
  const [day, setDay] = useState<number | null>(null);
  const [time, setTime] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);

  const april = getAprilCalendar();
  const tierObj = TIERS.find((t) => t.id === tier);
  const isWedding = tier === "wedding";

  // 모든 필수 필드가 채워졌는지 확인
  const isFormValid =
    form.name &&
    form.phone &&
    day &&
    time &&
    tier &&
    (!isWedding || (form.partnerName && form.partnerPhone));

  // 오버레이 열림 시 스크롤 잠금
  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  // 결제 처리 (시뮬레이션)
  const handlePay = useCallback(() => {
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      setDone(true);
    }, 1800);
  }, []);

  // 초기화 및 닫기
  const handleReset = useCallback(() => {
    setDone(false);
    setDay(null);
    setTime(null);
    setForm(INITIAL_FORM);
    onClose();
  }, [onClose]);

  // 폼 필드 업데이트 헬퍼
  const updateForm = useCallback(
    (field: keyof FormState) => (value: string) => {
      setForm((prev) => ({ ...prev, [field]: value }));
    },
    [],
  );

  // 슬롯 예약 여부 확인
  const checkSlotBooked = useCallback(
    (dayNum: number, slotTime: string, slotTier: string): boolean => {
      const date = new Date(2026, 3, dayNum);
      return isSlotBooked(BOOKINGS, date, slotTime, slotTier);
    },
    [],
  );

  if (!open) return null;

  // 가격 표시 텍스트
  const priceText = tierObj
    ? "₩" + tierObj.price.toLocaleString() + " 결제하기"
    : "정보를 입력해주세요";

  // 선택된 날짜 텍스트
  const selectedDateText = day
    ? "4월 " + day + "일 (" + getDayName(new Date(2026, 3, day)) + ")"
    : "";

  // 시간 선택 라벨 보조 텍스트
  const timeSubLabel = time
    ? " — 4/" + day + "(" + getDayName(new Date(2026, 3, day ?? 1)) + ") " + time
    : "";

  return (
    <div
      className="fixed inset-0 z-[200] flex justify-end bg-black/50 animate-[fadeIn_0.25s_ease]"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      {/* 패널 */}
      <div className="w-full max-w-[480px] h-full bg-[var(--color-bg)] flex flex-col animate-[slideIn_0.3s_cubic-bezier(0.22,1,0.36,1)]">
        {/* 헤더 */}
        <div className="flex items-center justify-between px-7 py-[18px] border-b border-black/10">
          <span className="text-xs font-semibold tracking-[2px] uppercase">
            예약
          </span>
          <button
            className="bg-transparent border-none text-base cursor-pointer opacity-40 transition-opacity duration-200 hover:opacity-100"
            onClick={onClose}
          >
            ✕
          </button>
        </div>

        {/* 스크롤 영역 */}
        <div className="flex-1 overflow-y-auto px-7 pt-6 pb-10">
          {done ? (
            <div className="py-12 text-center">
              <p className="font-[family-name:var(--font-serif)] text-[22px] font-normal mb-2">
                예약 완료
              </p>
              <p className="text-[13px] opacity-40 mb-7">
                상세 안내는 카카오톡으로 연락드립니다.
              </p>
              <div className="border border-black/10 p-5 text-left mb-6">
                {[
                  ["진단", tierObj?.name ?? ""],
                  ["날짜", selectedDateText],
                  ["시간", time ?? ""],
                  ["이름", form.name],
                ].map(([key, val]) => (
                  <div
                    key={key}
                    className="flex justify-between py-2.5 border-b border-black/[0.06] text-sm last:border-b-0"
                  >
                    <span className="opacity-40">{key}</span>
                    <span className="font-bold">{val}</span>
                  </div>
                ))}
              </div>
              <button
                className="text-[13px] font-semibold px-9 py-3 bg-[var(--color-fg)] text-[var(--color-bg)] border-none cursor-pointer tracking-[1px]"
                onClick={handleReset}
              >
                닫기
              </button>
            </div>
          ) : (
            <>
              {/* 티어 선택 */}
              <div className="mb-7">
                <p className="text-[11px] font-semibold tracking-[1.5px] uppercase opacity-40 mb-3">
                  진단 선택
                </p>
                <div className="flex flex-col md:flex-row gap-2">
                  {TIERS.map((t) => {
                    const isActive = tier === t.id;
                    return (
                      <button
                        key={t.id}
                        onClick={() => {
                          setTier(t.id);
                          setForm((prev) => ({
                            ...prev,
                            partnerName: "",
                            partnerPhone: "",
                          }));
                        }}
                        className={isActive
                          ? "flex-1 py-3.5 px-2 text-center border cursor-pointer transition-all duration-150 border-[var(--color-fg)] bg-[var(--color-fg)] text-[var(--color-bg)]"
                          : "flex-1 py-3.5 px-2 text-center border cursor-pointer transition-all duration-150 border-black/[0.12] bg-transparent hover:border-black/40"
                        }
                      >
                        <span className="block text-xs font-bold tracking-[0.5px] mb-1">
                          {t.name}
                        </span>
                        <span className="block font-[family-name:var(--font-serif)] text-base font-normal">
                          ₩{t.price.toLocaleString()}
                        </span>
                        <span
                          className={isActive
                            ? "block text-[10px] mt-1 opacity-60"
                            : "block text-[10px] mt-1 opacity-40"
                          }
                        >
                          {bookedByTier(t.id)}건 예약됨
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* 달력 */}
              {tier && (
                <div className="mb-7">
                  <p className="text-[11px] font-semibold tracking-[1.5px] uppercase opacity-40 mb-3">
                    날짜 — 2026년 4월
                  </p>
                  {/* 요일 헤더 */}
                  <div className="grid grid-cols-7 text-center mb-1">
                    {DAY_NAMES.map((d) => (
                      <div
                        key={d}
                        className="text-[10px] font-semibold opacity-30 py-1.5"
                      >
                        {d}
                      </div>
                    ))}
                  </div>
                  {/* 날짜 그리드 */}
                  <div className="grid grid-cols-7 gap-0.5">
                    {april.map((dd, i) => {
                      if (dd === null) {
                        return <div key={"empty-" + i} />;
                      }
                      const available = dd >= 10 && dd <= 30;
                      const selected = day === dd;
                      return (
                        <button
                          key={dd}
                          disabled={!available}
                          onClick={() => {
                            setDay(dd);
                            setTime(null);
                          }}
                          className={
                            selected
                              ? "py-2.5 text-[13px] font-bold border-none text-center transition-all duration-150 bg-[var(--color-fg)] text-[var(--color-bg)]"
                              : available
                                ? "py-2.5 text-[13px] font-medium bg-transparent border-none text-center transition-all duration-150 cursor-pointer hover:bg-black/5"
                                : "py-2.5 text-[13px] font-medium bg-transparent border-none text-center opacity-15 cursor-default"
                          }
                        >
                          {dd}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* 시간 선택 */}
              {day && tier && (
                <div className="mb-7">
                  <p className="text-[11px] font-semibold tracking-[1.5px] uppercase opacity-40 mb-3">
                    시간
                    {time && (
                      <span className="font-medium opacity-80 tracking-normal normal-case">
                        {timeSubLabel}
                      </span>
                    )}
                  </p>
                  <div className="grid grid-cols-3 md:grid-cols-5 gap-1.5">
                    {ALL_SLOTS.map((slot) => {
                      const booked = checkSlotBooked(day, slot, tier);
                      const selected = time === slot;
                      return (
                        <button
                          key={slot}
                          disabled={booked}
                          onClick={() => setTime(slot)}
                          className={
                            selected
                              ? "py-[11px] text-[13px] font-medium border transition-all duration-150 bg-[var(--color-fg)] text-[var(--color-bg)] border-[var(--color-fg)]"
                              : booked
                                ? "py-[11px] text-[13px] font-medium bg-transparent border border-black/10 opacity-20 cursor-default"
                                : "py-[11px] text-[13px] font-medium bg-transparent border border-black/10 transition-all duration-150 cursor-pointer hover:border-[var(--color-fg)]"
                          }
                        >
                          {booked ? "마감" : slot}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* 정보 입력 폼 */}
              {time && (
                <div className="mb-7">
                  <p className="text-[11px] font-semibold tracking-[1.5px] uppercase opacity-40 mb-3">
                    정보
                  </p>
                  <div className="flex flex-col gap-3">
                    <FormInput
                      label="이름"
                      required
                      value={form.name}
                      onChange={updateForm("name")}
                      placeholder="홍길동"
                    />
                    <FormInput
                      label="연락처"
                      required
                      value={form.phone}
                      onChange={updateForm("phone")}
                      placeholder="010-0000-0000"
                    />
                    <FormInput
                      label="인스타그램"
                      value={form.ig}
                      onChange={updateForm("ig")}
                      placeholder="@username"
                    />
                    {/* 웨딩 티어: 파트너 정보 추가 */}
                    {isWedding && (
                      <>
                        <FormInput
                          label="파트너 이름"
                          required
                          value={form.partnerName}
                          onChange={updateForm("partnerName")}
                          placeholder="파트너 이름"
                        />
                        <FormInput
                          label="파트너 연락처"
                          required
                          value={form.partnerPhone}
                          onChange={updateForm("partnerPhone")}
                          placeholder="010-0000-0000"
                        />
                      </>
                    )}
                  </div>
                </div>
              )}

              {/* 결제 버튼 */}
              {time && (
                <>
                  <button
                    disabled={!isFormValid || loading}
                    onClick={handlePay}
                    className={isFormValid
                      ? "w-full py-4 mt-6 text-sm font-bold border-none flex items-center justify-center gap-2 transition-all duration-200 bg-[var(--color-fg)] text-[var(--color-bg)] cursor-pointer hover:opacity-85"
                      : "w-full py-4 mt-6 text-sm font-bold border-none flex items-center justify-center gap-2 transition-all duration-200 bg-black/[0.08] text-black/30 cursor-not-allowed"
                    }
                  >
                    {loading ? (
                      <span className="inline-block w-4 h-4 border-2 border-[var(--color-bg)]/30 border-t-[var(--color-bg)] rounded-full animate-spin" />
                    ) : isFormValid ? (
                      priceText
                    ) : (
                      "정보를 입력해주세요"
                    )}
                  </button>
                  <p className="text-center text-[10px] opacity-30 mt-2.5">
                    토스페이먼츠 · 카카오페이 · 네이버페이
                  </p>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
