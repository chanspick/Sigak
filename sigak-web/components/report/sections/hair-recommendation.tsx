// 헤어 추천 섹션 (full 잠금)
// 파이널폼 v5: p7 TOP 3 조합 + p8~11 심화/AVOID
// AI 레퍼런스 이미지 기반 — 오버레이 없음

import Image from "next/image";
import type { HairRecommendationContent } from "@/lib/types/report";

interface HairRecommendationProps {
  content: HairRecommendationContent;
  locked: boolean;
}

export function HairRecommendation({ content, locked }: HairRecommendationProps) {
  const { cheat_sheet, top_combos, avoid, catalog } = content;
  const hasCombos = top_combos.length > 0;

  return (
    <section className="py-10 border-b border-[var(--color-border)]">
      {/* 섹션 헤더 */}
      <h2 className="text-xs font-semibold tracking-[3px] uppercase text-[var(--color-muted)] mb-6">
        HAIR RECOMMENDATION
      </h2>

      {/* 치트키 — 항상 표시 */}
      {cheat_sheet && (
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-4 mb-8">
          <p className="text-xs font-semibold tracking-[2px] uppercase text-[var(--color-muted)] mb-2">
            치트키
          </p>
          <p className="text-sm font-medium leading-relaxed">{cheat_sheet}</p>
        </div>
      )}

      {/* 상세 내용 — 잠금 시 블러 */}
      <div className={locked ? "select-none" : ""}>
        <div className="relative">
          {/* TOP 3 조합 */}
          {hasCombos && (
            <div className="flex flex-col gap-8 mb-8">
              {top_combos.map((combo) => (
                <div key={combo.rank} className="flex flex-col gap-3">
                  {/* 랭크 + 스코어 */}
                  <div className="flex items-center gap-3">
                    <span className="inline-flex items-center justify-center w-[24px] h-[24px] bg-[var(--color-fg)] text-[var(--color-bg)] text-[13px] font-semibold shrink-0">
                      {combo.rank}
                    </span>
                    <span className="text-sm font-medium">
                      {combo.front?.name_kr ?? ""} × {combo.back?.name_kr ?? ""}
                    </span>
                    {combo.score != null && (
                      <span className="text-xs text-[var(--color-muted)]">
                        {combo.score.toFixed(2)}
                      </span>
                    )}
                    {combo.trend && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-red-500/10 text-red-400">
                        {combo.trend}
                      </span>
                    )}
                  </div>

                  {/* 레퍼런스 이미지 3장 (앞머리 + 뒷머리 정면 + 뒷머리 뒷모습) */}
                  <div className="flex gap-3 overflow-x-auto">
                    {combo.front?.image && (
                      <div className="relative w-[120px] shrink-0 aspect-[3/4] rounded-lg overflow-hidden bg-[var(--color-surface)]">
                        <Image
                          src={combo.front.image}
                          alt={combo.front.name_kr}
                          fill
                          className="object-cover"
                          sizes="120px"
                        />
                        <span className="absolute bottom-1 left-1 text-[10px] bg-black/60 text-white px-1.5 py-0.5 rounded">
                          앞머리
                        </span>
                      </div>
                    )}
                    {combo.back?.image_front && (
                      <div className="relative w-[120px] shrink-0 aspect-[3/4] rounded-lg overflow-hidden bg-[var(--color-surface)]">
                        <Image
                          src={combo.back.image_front}
                          alt={combo.back.name_kr + " 정면"}
                          fill
                          className="object-cover"
                          sizes="120px"
                        />
                        <span className="absolute bottom-1 left-1 text-[10px] bg-black/60 text-white px-1.5 py-0.5 rounded">
                          정면
                        </span>
                      </div>
                    )}
                    {combo.back?.image_rear && (
                      <div className="relative w-[120px] shrink-0 aspect-[3/4] rounded-lg overflow-hidden bg-[var(--color-surface)]">
                        <Image
                          src={combo.back.image_rear}
                          alt={combo.back.name_kr + " 뒷모습"}
                          fill
                          className="object-cover"
                          sizes="120px"
                        />
                        <span className="absolute bottom-1 left-1 text-[10px] bg-black/60 text-white px-1.5 py-0.5 rounded">
                          뒷모습
                        </span>
                      </div>
                    )}
                  </div>

                  {/* WHY + 미용실 지시 */}
                  {combo.why && (
                    <p className="text-sm text-[var(--color-muted)] leading-relaxed">
                      → {combo.why}
                    </p>
                  )}
                  {combo.salon_instruction && (
                    <p className="text-xs text-[var(--color-muted)] leading-relaxed italic">
                      미용실: &ldquo;{combo.salon_instruction}&rdquo;
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* 조합 없을 때: 카탈로그에서 앞머리 전체 표시 */}
          {!hasCombos && catalog.front.length > 0 && (
            <div className="mb-8">
              <p className="text-xs font-semibold tracking-[2px] uppercase text-[var(--color-muted)] mb-3">
                앞머리 스타일
              </p>
              <div className="grid grid-cols-4 gap-2">
                {catalog.front.map((style) => (
                  <div key={style.id} className="flex flex-col gap-1">
                    <div className="relative aspect-[3/4] rounded-lg overflow-hidden bg-[var(--color-surface)]">
                      <Image
                        src={style.image}
                        alt={style.name_kr}
                        fill
                        className="object-cover"
                        sizes="(max-width: 640px) 25vw, 120px"
                      />
                    </div>
                    <span className="text-[11px] text-center text-[var(--color-muted)]">
                      {style.name_kr}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* AVOID */}
          {avoid.length > 0 && (
            <div>
              <p className="text-xs font-semibold tracking-[2px] uppercase text-[var(--color-muted)] mb-3">
                피해야 할 스타일
              </p>
              <ul className="flex flex-col gap-2">
                {avoid.map((av) => (
                  <li key={av.name_kr} className="flex items-start gap-2 text-sm">
                    <span className="text-red-400 shrink-0">✕</span>
                    <span>
                      <strong>{av.name_kr}</strong>
                      {av.reason && (
                        <span className="text-[var(--color-muted)]"> — {av.reason}</span>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* 블러 오버레이 */}
          {locked && (
            <div className="absolute inset-0 blur-overlay blur-fade-out" />
          )}
        </div>
      </div>
    </section>
  );
}
