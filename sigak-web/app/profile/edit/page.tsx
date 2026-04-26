// /profile/edit — 본인 정보 수정 (v1: IG 핸들 재설정만)
//
// 운영 단계에서 본인 IG 핸들만 빠르게 갱신 가능. essentials reset (시각
// 재설정) 보다 침습 적음 — Sia 대화 / 좌표 / aspiration history 보존.
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError } from "@/lib/api/fetch";
import { getMe, updateIgHandle } from "@/lib/api/onboarding";
import { getCurrentUser, getToken } from "@/lib/auth";
import { TopBar } from "@/components/ui/sigak";
import { SiteFooter } from "@/components/sigak/site-footer";

export default function ProfileEditPage() {
  const router = useRouter();

  const [igInput, setIgInput] = useState("");
  const [currentIg, setCurrentIg] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/auth/login?next=/profile/edit");
      return;
    }
    // 1) localStorage 의 ig_handle 즉시 반영 (체감 latency ↓)
    const u = getCurrentUser();
    const localHandle = (u && (u as { ig_handle?: string }).ig_handle) || null;
    if (localHandle) {
      setCurrentIg(localHandle);
      setIgInput(localHandle);
    }
    // 2) backend 에서 정확한 ig_handle 재조회 후 갱신
    (async () => {
      try {
        const me = await getMe();
        const handle = (me as { ig_handle?: string | null }).ig_handle ?? null;
        setCurrentIg(handle);
        setIgInput(handle || "");
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/auth/login");
        }
        // 그 외는 localStorage 값 유지
      }
    })();
  }, [router]);

  const normalized = normalizeIgHandle(igInput);
  const dirty = normalized !== (currentIg || "");
  const canSave = !saving && dirty;

  async function handleSave() {
    if (!canSave) return;
    setError(null);
    setSavedMessage(null);
    setSaving(true);
    try {
      const res = await updateIgHandle({
        ig_handle: normalized || null,
      });
      setCurrentIg(res.ig_handle);
      setIgInput(res.ig_handle || "");
      if (res.ig_fetch_status === "pending") {
        setSavedMessage(
          "새 인스타그램 정보를 가져오고 있어요. 잠시 후 분석에 반영돼요.",
        );
      } else {
        setSavedMessage("인스타그램 핸들을 비웠어요.");
      }
    } catch (e) {
      if (e instanceof ApiError) {
        if (e.status === 401) {
          router.replace("/auth/login");
          return;
        }
        setError(e.message || "저장에 실패했어요.");
      } else {
        setError("연결이 잠깐 끊겼어요. 다시 시도해 주세요.");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="flex min-h-screen flex-col"
      style={{ background: "var(--color-paper)" }}
    >
      <TopBar backTarget="/profile" />

      <main
        className="flex-1"
        style={{ padding: "44px 24px 120px", maxWidth: 480, margin: "0 auto", width: "100%" }}
      >
        <header style={{ marginBottom: 32 }}>
          <h1
            className="font-serif"
            style={{
              margin: 0,
              fontSize: 24,
              fontWeight: 700,
              letterSpacing: "-0.022em",
              lineHeight: 1.42,
              color: "var(--color-ink)",
              wordBreak: "keep-all",
            }}
          >
            내 정보 수정
            <span style={{ color: "var(--color-danger)" }}>.</span>
          </h1>
          <p
            className="font-sans"
            style={{
              margin: "10px 0 0",
              fontSize: 14,
              lineHeight: 1.65,
              color: "var(--color-mute)",
              letterSpacing: "-0.005em",
            }}
          >
            등록한 인스타그램이 바뀌었거나, 분석 결과가 본인과 어긋날 때 여기서 다시 맞춰주세요.
          </p>
        </header>

        <section style={{ marginBottom: 28 }}>
          <Label>INSTAGRAM 핸들</Label>
          {currentIg && (
            <p
              className="tabular-nums"
              style={{
                margin: "6px 0 12px",
                fontFamily: "var(--font-mono)",
                fontSize: 11,
                color: "var(--color-mute-2)",
                letterSpacing: "0.04em",
              }}
            >
              현재: @{currentIg}
            </p>
          )}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              border: "1px solid var(--color-line-strong)",
              borderRadius: 12,
              overflow: "hidden",
              background: "rgba(0, 0, 0, 0.04)",
              opacity: saving ? 0.5 : 1,
              transition: "border-color 0.2s ease, opacity 0.2s ease",
            }}
          >
            <span
              className="font-sans"
              style={{
                padding: "14px 10px 14px 14px",
                fontSize: 15,
                color: "var(--color-mute-2)",
                userSelect: "none",
                flexShrink: 0,
              }}
            >
              @
            </span>
            <input
              type="text"
              inputMode="url"
              autoComplete="off"
              autoCapitalize="off"
              spellCheck={false}
              placeholder="instagram ID"
              value={igInput}
              onChange={(e) => setIgInput(e.target.value)}
              disabled={saving}
              className="font-sans"
              style={{
                flex: 1,
                padding: "14px 14px 14px 0",
                background: "transparent",
                border: "none",
                outline: "none",
                fontSize: 15,
                color: "var(--color-ink)",
                letterSpacing: "-0.005em",
              }}
            />
          </div>
          {normalized && normalized !== (currentIg || "") && (
            <p
              className="font-sans"
              style={{
                margin: "9px 0 0",
                fontSize: 12,
                color: "var(--color-mute)",
                letterSpacing: "-0.005em",
              }}
            >
              저장하면 @{normalized} 의 피드를 다시 분석해요.
            </p>
          )}
          {!normalized && currentIg && (
            <p
              className="font-sans"
              style={{
                margin: "9px 0 0",
                fontSize: 12,
                color: "var(--color-danger)",
                letterSpacing: "-0.005em",
              }}
            >
              저장하면 인스타그램이 빈 상태가 돼요. 추구미 분석은 본인 피드가 없으면 정확도가 떨어져요.
            </p>
          )}
        </section>

        {error && (
          <div
            role="alert"
            style={{
              padding: "14px 16px",
              borderTop: "1px solid var(--color-danger)",
              background: "rgba(163, 45, 45, 0.04)",
              marginBottom: 20,
            }}
          >
            <p
              className="font-sans"
              style={{
                margin: 0,
                fontSize: 13,
                lineHeight: 1.6,
                color: "var(--color-ink)",
                letterSpacing: "-0.005em",
              }}
            >
              {error}
            </p>
          </div>
        )}

        {savedMessage && !error && (
          <div
            role="status"
            style={{
              padding: "14px 16px",
              background: "var(--color-bubble-ai)",
              marginBottom: 20,
            }}
          >
            <p
              className="font-sans"
              style={{
                margin: 0,
                fontSize: 13,
                lineHeight: 1.6,
                color: "var(--color-ink)",
                letterSpacing: "-0.005em",
              }}
            >
              {savedMessage}
            </p>
          </div>
        )}
      </main>

      <div
        style={{
          position: "sticky",
          bottom: 0,
          left: 0,
          right: 0,
          background: "var(--color-paper)",
          padding: "16px 24px 24px",
          borderTop: "1px solid var(--color-line)",
        }}
      >
        <div style={{ maxWidth: 480, margin: "0 auto" }}>
          <button
            type="button"
            onClick={handleSave}
            disabled={!canSave}
            className="font-sans"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: "100%",
              padding: "17px 24px",
              background: canSave ? "var(--color-ink)" : "var(--color-line-strong)",
              color: canSave ? "var(--color-paper)" : "#fff",
              border: "none",
              borderRadius: 100,
              fontSize: 15,
              fontWeight: 600,
              letterSpacing: "-0.012em",
              cursor: canSave ? "pointer" : "not-allowed",
              transition: "all 0.2s ease",
            }}
          >
            {saving ? "저장 중..." : !dirty ? "변경 사항 없음" : "저장"}
          </button>
        </div>
      </div>

      <SiteFooter />
    </div>
  );
}

// ─────────────────────────────────────────────
//  Helpers
// ─────────────────────────────────────────────

function normalizeIgHandle(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return "";
  const urlMatch = trimmed.match(/instagram\.com\/(?:p\/)?([^/?#]+)/i);
  if (urlMatch) {
    return urlMatch[1].replace(/^@/, "").toLowerCase();
  }
  return trimmed.replace(/^@/, "").toLowerCase();
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <span
      className="uppercase"
      style={{
        display: "block",
        fontFamily: "var(--font-mono)",
        fontSize: 10,
        letterSpacing: "0.12em",
        color: "var(--color-mute)",
      }}
    >
      {children}
    </span>
  );
}
