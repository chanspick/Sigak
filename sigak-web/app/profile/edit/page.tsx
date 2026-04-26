// /profile/edit — 본인 정보 수정 (v1: IG 핸들 재설정만)
//
// 운영 단계에서 본인 IG 핸들만 빠르게 갱신 가능. essentials reset (시각
// 재설정) 보다 침습 적음 — Sia 대화 / 좌표 / aspiration history 보존.
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError } from "@/lib/api/fetch";
import { updateIgHandle } from "@/lib/api/onboarding";
import { getCurrentUser, getToken } from "@/lib/auth";
import { PrimaryButton, TopBar } from "@/components/ui/sigak";
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
    const u = getCurrentUser();
    const handle = (u && (u as { ig_handle?: string }).ig_handle) || null;
    setCurrentIg(handle);
    setIgInput(handle || "");
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

      <main className="flex-1" style={{ padding: "24px 28px 120px" }}>
        <header style={{ marginBottom: 28 }}>
          <h1
            className="font-serif"
            style={{
              margin: 0,
              fontSize: 26,
              fontWeight: 400,
              letterSpacing: "-0.01em",
              lineHeight: 1.25,
            }}
          >
            내 정보 수정
          </h1>
          <p
            className="font-sans"
            style={{
              margin: "10px 0 0",
              fontSize: 13,
              lineHeight: 1.6,
              color: "var(--color-mute)",
              letterSpacing: "-0.005em",
            }}
          >
            등록한 인스타그램이 바뀌었거나, 분석 결과가 본인 결과 어긋날 때
            여기서 다시 맞춰주세요.
          </p>
        </header>

        <section style={{ marginBottom: 28 }}>
          <Label>인스타그램 핸들</Label>
          {currentIg && (
            <p
              className="font-sans tabular-nums"
              style={{
                margin: "8px 0 14px",
                fontSize: 12,
                color: "var(--color-mute-2)",
              }}
            >
              현재: @{currentIg}
            </p>
          )}
          <input
            type="text"
            inputMode="url"
            autoComplete="off"
            autoCapitalize="off"
            spellCheck={false}
            placeholder="@yuni 또는 instagram.com/yuni"
            value={igInput}
            onChange={(e) => setIgInput(e.target.value)}
            disabled={saving}
            className="font-sans"
            style={{
              width: "100%",
              padding: "14px 14px",
              fontSize: 15,
              background: "transparent",
              border: "1px solid rgba(0, 0, 0, 0.25)",
              borderRadius: 0,
              color: "var(--color-ink)",
              letterSpacing: "-0.005em",
              opacity: saving ? 0.5 : 1,
            }}
          />
          {normalized && normalized !== (currentIg || "") && (
            <p
              className="font-sans"
              style={{
                margin: "8px 0 0",
                fontSize: 11,
                color: "var(--color-mute-2)",
              }}
            >
              저장하면 @{normalized} 의 피드를 다시 분석해요.
            </p>
          )}
          {!normalized && currentIg && (
            <p
              className="font-sans"
              style={{
                margin: "8px 0 0",
                fontSize: 11,
                color: "var(--color-danger)",
              }}
            >
              저장하면 인스타그램이 빈 상태가 돼요. 추구미 분석은 본인 피드가
              없으면 정확도가 떨어져요.
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
          padding: "12px 28px 24px",
          borderTop: "1px solid rgba(0, 0, 0, 0.08)",
        }}
      >
        <PrimaryButton
          type="button"
          onClick={handleSave}
          disabled={!canSave}
          disabledLabel={
            saving ? "저장 중..." : !dirty ? "변경 사항 없음" : "저장"
          }
        >
          저장
        </PrimaryButton>
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
      className="font-sans uppercase"
      style={{
        display: "block",
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: "1.5px",
        opacity: 0.5,
        color: "var(--color-ink)",
      }}
    >
      {children}
    </span>
  );
}
