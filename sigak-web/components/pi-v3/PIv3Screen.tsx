/**
 * PIv3Screen — 시각이 본 당신 v3 결과 화면 (Phase I PI-D).
 *
 * 모드:
 *   preview : 혼합 iii visibility (cover/celeb 풀 + 4 teaser + 3 lock)
 *   full    : 모든 sections.visibility = "full"
 *
 * paywall:
 *   preview 모드에서 sections 끝에 paywall 카드 노출.
 *     - 토큰 충분 → "결제 없이 풀 PI 받기" (원래 무료 첫 PI 흐름은 폐기, 50토큰 차감)
 *     - 토큰 부족 → "충전하고 풀 PI 받기" → /tokens/purchase
 *
 * 9 컴포넌트 (3-3-3 구조):
 *   raw 3:   cover / celeb_reference / face_structure
 *   vault 3: type_reference / gap_analysis / skin_analysis
 *   trend 3: coordinate_map / hair_recommendation / action_plan
 */

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError } from "@/lib/api/fetch";
import { unlockPIv3 } from "@/lib/api/pi";
import type {
  PIv3Report,
  PIv3Section,
  PIv3SectionId,
} from "@/lib/api/pi";

interface PIv3ScreenProps {
  report: PIv3Report;
  onUnlocked?: (reportId: string) => void;
}

const SECTION_LABELS: Record<PIv3SectionId, string> = {
  cover: "커버",
  celeb_reference: "셀럽 레퍼런스",
  face_structure: "얼굴 구조",
  type_reference: "타입 매칭",
  gap_analysis: "갭 분석",
  skin_analysis: "피부 분석",
  coordinate_map: "좌표 지도",
  hair_recommendation: "헤어 제안",
  action_plan: "실행 가이드",
};

const SECTION_BUCKETS: Record<PIv3SectionId, "raw" | "vault" | "trend"> = {
  cover: "raw",
  celeb_reference: "raw",
  face_structure: "raw",
  type_reference: "vault",
  gap_analysis: "vault",
  skin_analysis: "vault",
  coordinate_map: "trend",
  hair_recommendation: "trend",
  action_plan: "trend",
};

export function PIv3Screen({ report, onUnlocked }: PIv3ScreenProps) {
  const router = useRouter();
  const [unlocking, setUnlocking] = useState(false);
  const [unlockError, setUnlockError] = useState<string | null>(null);

  const isPreview = report.is_preview;
  const balance = report.token_balance ?? 0;
  const cost = report.unlock_cost_tokens;
  const insufficient = balance < cost;

  async function handleUnlock() {
    if (unlocking) return;
    if (insufficient) {
      router.push("/tokens/purchase?intent=pi_unlock");
      return;
    }
    setUnlocking(true);
    setUnlockError(null);
    try {
      const res = await unlockPIv3();
      if (onUnlocked) {
        onUnlocked(res.report_id);
      } else {
        router.replace(`/pi/${encodeURIComponent(res.report_id)}`);
      }
    } catch (e) {
      if (e instanceof ApiError && e.status === 402) {
        router.push("/tokens/purchase?intent=pi_unlock");
        return;
      }
      if (e instanceof ApiError && e.status === 401) {
        router.replace("/");
        return;
      }
      setUnlockError(
        e instanceof Error ? e.message : "PI 해제에 실패했어요.",
      );
    } finally {
      setUnlocking(false);
    }
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        background: "var(--color-paper)",
        color: "var(--color-ink)",
      }}
    >
      <header
        style={{
          padding: "32px 28px 12px",
          borderBottom: "1px solid rgba(0,0,0,0.06)",
        }}
      >
        <span
          className="font-sans uppercase"
          style={{
            fontSize: 10,
            fontWeight: 600,
            letterSpacing: "1.6px",
            opacity: 0.4,
          }}
        >
          {isPreview ? "PREVIEW · v" + report.version : "v" + report.version}
        </span>
        <h1
          className="font-serif"
          style={{
            marginTop: 8,
            fontSize: 24,
            fontWeight: 400,
            letterSpacing: "-0.01em",
          }}
        >
          시각이 본 당신
        </h1>
      </header>

      <section style={{ padding: "8px 0 20px" }}>
        {report.sections.map((section) => (
          <SectionBlock key={section.section_id} section={section} />
        ))}
      </section>

      {isPreview && (
        <PreviewPaywall
          balance={balance}
          cost={cost}
          insufficient={insufficient}
          unlocking={unlocking}
          error={unlockError}
          onUnlock={handleUnlock}
        />
      )}
    </main>
  );
}

// ─────────────────────────────────────────────
//  Section block — visibility 분기 + bucket 라벨
// ─────────────────────────────────────────────

function SectionBlock({ section }: { section: PIv3Section }) {
  const label = SECTION_LABELS[section.section_id] || section.section_id;
  const bucket = SECTION_BUCKETS[section.section_id];
  const bucketLabel =
    bucket === "raw" ? "RAW" : bucket === "vault" ? "VAULT" : "TREND";

  return (
    <article
      style={{
        padding: "24px 28px",
        borderBottom: "1px solid rgba(0,0,0,0.06)",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: 10,
          marginBottom: 12,
        }}
      >
        <span
          className="font-sans uppercase"
          style={{
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: "1.5px",
            opacity: 0.32,
          }}
        >
          {bucketLabel}
        </span>
        <h2
          className="font-serif"
          style={{
            margin: 0,
            fontSize: 18,
            fontWeight: 500,
            letterSpacing: "-0.005em",
          }}
        >
          {label}
        </h2>
      </div>
      {section.visibility === "full" && (
        <SectionContent content={section.content} sectionId={section.section_id} />
      )}
      {section.visibility === "teaser" && (
        <TeaserContent content={section.content} sectionId={section.section_id} />
      )}
      {section.visibility === "locked" && (
        <LockedContent />
      )}
    </article>
  );
}

// ─────────────────────────────────────────────
//  Visibility 별 렌더
//
//  본 단계에선 minimum viable — 9 컴포넌트 모두 inline placeholder.
//  PI-A/PI-C 가 9 컴포넌트별 schema 정착하면 components/pi-v3/sections/* 로
//  분리 + 카드형 UI 적용 (마케터 검수 영역).
// ─────────────────────────────────────────────

function SectionContent({
  content,
  sectionId,
}: {
  content: Record<string, unknown>;
  sectionId: PIv3SectionId;
}) {
  if (sectionId === "cover") {
    const summary = (content.user_summary as string | undefined) ?? "";
    const needs = (content.needs_statement as string | undefined) ?? "";
    const overall = (content.sia_overall_message as string | undefined) ?? "";
    return (
      <div className="font-serif" style={{ lineHeight: 1.75, fontSize: 15 }}>
        {summary && <p style={{ margin: "0 0 12px" }}>{summary}</p>}
        {needs && <p style={{ margin: "0 0 12px", opacity: 0.85 }}>{needs}</p>}
        {overall && <p style={{ margin: 0, opacity: 0.7 }}>{overall}</p>}
      </div>
    );
  }

  // 사진 리스트가 있는 컴포넌트
  const items = (content.items as Array<Record<string, unknown>> | undefined) ?? [];
  const photos = (content.photos as Array<Record<string, unknown>> | undefined) ?? items;

  if (photos.length > 0) {
    return (
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, 1fr)",
          gap: 8,
        }}
      >
        {photos.map((p, i) => {
          const url = p.stored_url as string | undefined;
          const comment = p.sia_comment as string | undefined;
          return (
            <div key={i} style={{ minWidth: 0 }}>
              {url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={url}
                  alt=""
                  style={{
                    width: "100%",
                    aspectRatio: "1 / 1",
                    objectFit: "cover",
                    background: "rgba(0,0,0,0.04)",
                  }}
                />
              ) : (
                <div
                  style={{
                    width: "100%",
                    aspectRatio: "1 / 1",
                    background: "rgba(0,0,0,0.06)",
                  }}
                />
              )}
              {comment && (
                <p
                  className="font-sans"
                  style={{
                    margin: "6px 0 0",
                    fontSize: 11,
                    lineHeight: 1.55,
                    opacity: 0.65,
                    letterSpacing: "-0.005em",
                  }}
                >
                  {comment}
                </p>
              )}
            </div>
          );
        })}
      </div>
    );
  }

  // 좌표/매칭 등 — JSON 요약 (PI-C 정착 시 component-specific UI 로 대체)
  const keys = Object.keys(content || {}).filter((k) => content[k] != null);
  if (keys.length === 0) {
    return (
      <p
        className="font-sans"
        style={{
          fontSize: 12,
          opacity: 0.5,
          letterSpacing: "-0.005em",
          margin: 0,
        }}
      >
        준비 중
      </p>
    );
  }
  return (
    <ul
      className="font-sans"
      style={{
        margin: 0,
        paddingLeft: 16,
        fontSize: 13,
        lineHeight: 1.7,
        opacity: 0.75,
        letterSpacing: "-0.005em",
      }}
    >
      {keys.slice(0, 6).map((k) => {
        const v = content[k];
        const label =
          typeof v === "string"
            ? v
            : Array.isArray(v)
            ? v.length + "개"
            : typeof v === "object"
            ? "✓"
            : String(v);
        return (
          <li key={k}>
            <span style={{ opacity: 0.5 }}>{k}</span> · {label}
          </li>
        );
      })}
    </ul>
  );
}

function TeaserContent({
  content,
  sectionId,
}: {
  content: Record<string, unknown>;
  sectionId: PIv3SectionId;
}) {
  // 첫 한 줄만 노출 + 나머지 blur
  return (
    <div style={{ position: "relative", minHeight: 80 }}>
      <div
        style={{
          filter: "blur(5px)",
          pointerEvents: "none",
          userSelect: "none",
          opacity: 0.7,
        }}
      >
        <SectionContent content={content} sectionId={sectionId} />
      </div>
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          pointerEvents: "none",
        }}
      >
        <span
          className="font-sans uppercase"
          style={{
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: "1.5px",
            background: "rgba(0,0,0,0.7)",
            color: "var(--color-paper)",
            padding: "6px 12px",
          }}
        >
          PREVIEW
        </span>
      </div>
    </div>
  );
}

function LockedContent() {
  return (
    <div
      style={{
        height: 100,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        border: "1px dashed rgba(0,0,0,0.15)",
      }}
    >
      <div
        style={{
          width: 36,
          height: 36,
          borderRadius: "50%",
          background: "rgba(0,0,0,0.7)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <svg width="14" height="16" viewBox="0 0 18 20" aria-hidden>
          <rect
            x="2"
            y="9"
            width="14"
            height="10"
            rx="1.5"
            stroke="#F3F0EB"
            strokeWidth="1.5"
            fill="none"
          />
          <path
            d="M5 9V6a4 4 0 018 0v3"
            stroke="#F3F0EB"
            strokeWidth="1.5"
            strokeLinecap="round"
            fill="none"
          />
        </svg>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
//  Preview paywall — 50 토큰 unlock CTA
// ─────────────────────────────────────────────

function PreviewPaywall({
  balance,
  cost,
  insufficient,
  unlocking,
  error,
  onUnlock,
}: {
  balance: number;
  cost: number;
  insufficient: boolean;
  unlocking: boolean;
  error: string | null;
  onUnlock: () => void;
}) {
  const need = Math.max(0, cost - balance);

  return (
    <section
      style={{
        padding: "32px 28px 60px",
        background: "var(--color-paper)",
      }}
    >
      <div
        style={{
          padding: "24px 22px",
          border: "1px solid rgba(0,0,0,0.12)",
          background: "rgba(0,0,0,0.02)",
        }}
      >
        <div
          className="font-sans uppercase"
          style={{
            fontSize: 10,
            fontWeight: 600,
            letterSpacing: "1.5px",
            opacity: 0.5,
            marginBottom: 10,
          }}
        >
          UNLOCK
        </div>
        <p
          className="font-serif"
          style={{
            margin: 0,
            fontSize: 18,
            lineHeight: 1.55,
            letterSpacing: "-0.01em",
          }}
        >
          잠금 7개 컴포넌트와<br />
          헤어/실행 가이드까지 풀어드릴게요
        </p>
        <div
          className="font-sans"
          style={{
            marginTop: 14,
            fontSize: 12,
            lineHeight: 1.7,
            opacity: 0.6,
            letterSpacing: "-0.005em",
          }}
        >
          보유 {balance}토큰 · 필요 {cost}토큰
          {insufficient && <> · 부족 {need}토큰 (₩{(need * 100).toLocaleString()})</>}
        </div>

        <button
          type="button"
          onClick={onUnlock}
          disabled={unlocking}
          className="font-sans"
          style={{
            marginTop: 18,
            width: "100%",
            height: 54,
            background: unlocking ? "transparent" : "var(--color-ink)",
            color: unlocking ? "var(--color-ink)" : "var(--color-paper)",
            border: unlocking ? "1px solid rgba(0,0,0,0.15)" : "none",
            borderRadius: 0,
            fontSize: 14,
            fontWeight: 600,
            letterSpacing: "0.5px",
            cursor: unlocking ? "default" : "pointer",
            opacity: unlocking ? 0.55 : 1,
          }}
        >
          {unlocking
            ? "해제 중..."
            : insufficient
            ? "충전하고 PI 풀어드리기"
            : `PI 풀어드리기 · ${cost}토큰`}
        </button>
        {error && (
          <p
            className="font-sans"
            role="alert"
            style={{
              marginTop: 10,
              fontSize: 11,
              color: "var(--color-danger)",
              letterSpacing: "-0.005em",
            }}
          >
            {error}
          </p>
        )}
      </div>
    </section>
  );
}
