/**
 * /best-shot — Best Shot 업로드 + 선별 시작 (Phase K6 프론트).
 *
 * 흐름:
 *   1. 가드 통과 + 토큰 잔액 조회
 *   2. expected_count 입력 + 파일 선택 (50-500장)
 *   3. POST /init  → strength<0.3 시 409 모달 → acknowledge 재호출
 *   4. 배치 업로드 (10장씩) → 진행률 표시
 *   5. POST /run   → LoadingSlides 표시 (응답 동기 대기)
 *   6. 결과 받으면 /best-shot/{id} redirect
 *
 * 백엔드 계약:
 *   - 50장 미만 → 400 too_few_photos → /verdict/new 안내
 *   - 토큰<30 → 402 → /tokens/purchase 안내
 *   - 실패 3종 (cost_cap / engine / unexpected) → 자동 환불 + status="failed"
 */

"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import { useOnboardingGuard } from "@/hooks/use-onboarding-guard";
import { ApiError, api } from "@/lib/api/fetch";
import {
  abortBestShotSession,
  initBestShotSession,
  isStrengthLowWarning,
  isTooFewPhotosError,
  runBestShotSelection,
  uploadBestShotBatch,
} from "@/lib/api/best_shot";
import type { BestShotInitResponse } from "@/lib/types/best_shot";
import { LoadingSlides } from "@/components/sia/LoadingSlides";
import { PrimaryButton, TopBar } from "@/components/ui/sigak";
import { SiteFooter } from "@/components/sigak/site-footer";

const COST_BEST_SHOT = 30;
const MIN_PHOTOS = 50;
const MAX_PHOTOS = 500;
const MAX_FILE_BYTES = 15 * 1024 * 1024;
const ALLOWED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);
const UPLOAD_BATCH_SIZE = 10;

type Stage =
  | "setup"
  | "init_pending"
  | "strength_warn"
  | "uploading"
  | "running"
  | "error";

interface SelectedFile {
  id: string;
  file: File;
  previewUrl: string;
}

export default function BestShotPage() {
  const router = useRouter();
  const { status: guardStatus } = useOnboardingGuard();

  const [stage, setStage] = useState<Stage>("setup");
  const [balance, setBalance] = useState<number | null>(null);
  const [files, setFiles] = useState<SelectedFile[]>([]);
  const [errorText, setErrorText] = useState<string | null>(null);
  const [errorAction, setErrorAction] = useState<{
    label: string;
    href: string;
  } | null>(null);

  // init / upload 상태
  const [initResponse, setInitResponse] = useState<BestShotInitResponse | null>(
    null,
  );
  const [strengthScore, setStrengthScore] = useState<number | null>(null);
  const [uploadedCount, setUploadedCount] = useState(0);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── 잔액 조회 (가드 통과 후 1회)
  useEffect(() => {
    if (guardStatus !== "ready") return;
    let cancelled = false;
    (async () => {
      try {
        const res = await api.getBalance();
        if (!cancelled) setBalance(res.balance);
      } catch {
        if (!cancelled) setBalance(0);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [guardStatus]);

  // ── 파일 미리보기 URL 정리
  useEffect(() => {
    return () => {
      for (const f of files) URL.revokeObjectURL(f.previewUrl);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── 파일 선택
  function handleFilesPick(picked: FileList | null): void {
    if (!picked || picked.length === 0) return;
    const accepted: SelectedFile[] = [];
    const skipped: string[] = [];

    const room = MAX_PHOTOS - files.length;
    const list = Array.from(picked).slice(0, room);

    for (const file of list) {
      if (!ALLOWED_TYPES.has(file.type)) {
        const isHeic =
          /\.hei[cf]$/i.test(file.name) || file.type.includes("heic") || file.type.includes("heif");
        skipped.push(
          `${file.name} (${isHeic ? "HEIC/HEIF 미지원 — JPG 로 저장 후 올려주세요" : "지원 형식 아님"})`,
        );
        continue;
      }
      if (file.size > MAX_FILE_BYTES) {
        skipped.push(`${file.name} (한 장당 15MB까지)`);
        continue;
      }
      accepted.push({
        id: `${file.name}_${file.size}_${file.lastModified}_${Math.random().toString(36).slice(2, 8)}`,
        file,
        previewUrl: URL.createObjectURL(file),
      });
    }
    setFiles((prev) => [...prev, ...accepted]);
    if (skipped.length > 0) {
      setErrorText(`일부 파일을 건너뛰었어요: ${skipped.slice(0, 3).join(", ")}${skipped.length > 3 ? " 외" : ""}`);
    } else {
      setErrorText(null);
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function handleRemoveFile(id: string): void {
    setFiles((prev) => {
      const target = prev.find((f) => f.id === id);
      if (target) URL.revokeObjectURL(target.previewUrl);
      return prev.filter((f) => f.id !== id);
    });
  }

  function handleRemoveAll(): void {
    for (const f of files) URL.revokeObjectURL(f.previewUrl);
    setFiles([]);
    setErrorText(null);
  }

  // ── 본 분석 시작 (init → upload → run)
  const canStart =
    stage === "setup"
    && files.length >= MIN_PHOTOS
    && files.length <= MAX_PHOTOS
    && balance !== null
    && balance >= COST_BEST_SHOT;

  async function handleStart(acknowledge = false): Promise<void> {
    if (!canStart && !acknowledge) return;
    setErrorText(null);
    setErrorAction(null);
    setStage("init_pending");

    try {
      const init = await initBestShotSession({
        expected_count: files.length,
        acknowledge_strength_warning: acknowledge,
      });
      setInitResponse(init);
      setStrengthScore(init.strength_score);
      await runUploadAndAnalyze(init.session_id);
    } catch (err) {
      handleInitError(err);
    }
  }

  function handleInitError(err: unknown): void {
    if (isTooFewPhotosError(err)) {
      setErrorText(err.body.message);
      setErrorAction({ label: "피드 추천으로 가기", href: err.body.redirect });
      setStage("error");
      return;
    }
    if (isStrengthLowWarning(err)) {
      setStrengthScore(err.body.strength_score);
      setStage("strength_warn");
      return;
    }
    if (err instanceof ApiError) {
      if (err.status === 402) {
        setErrorText("토큰이 부족해요. 30개가 필요합니다.");
        setErrorAction({ label: "토큰 충전하기", href: "/tokens/purchase" });
        setStage("error");
        return;
      }
      if (err.status === 401) {
        router.replace("/auth/login");
        return;
      }
      if (err.status === 409) {
        setErrorText("아직 onboarding이 완료되지 않았어요.");
        setErrorAction({ label: "온보딩으로", href: "/sia" });
        setStage("error");
        return;
      }
      setErrorText(err.message || "세션 시작에 실패했어요. 다시 시도해주세요.");
      setStage("error");
      return;
    }
    setErrorText("연결이 잠깐 끊겼어요. 다시 시도해주세요.");
    setStage("error");
  }

  async function runUploadAndAnalyze(sessionId: string): Promise<void> {
    setStage("uploading");
    setUploadedCount(0);

    try {
      let uploaded = 0;
      for (let i = 0; i < files.length; i += UPLOAD_BATCH_SIZE) {
        const batch = files.slice(i, i + UPLOAD_BATCH_SIZE).map((f) => f.file);
        const ack = await uploadBestShotBatch(sessionId, batch);
        uploaded = ack.uploaded_count;
        setUploadedCount(uploaded);
      }

      if (uploaded < MIN_PHOTOS) {
        setErrorText(
          `업로드된 사진이 ${uploaded}장이에요. 최소 ${MIN_PHOTOS}장 필요합니다.`,
        );
        setStage("error");
        return;
      }

      setStage("running");
      const runRes = await runBestShotSelection(sessionId);
      if (runRes.status === "failed") {
        setErrorText(
          runRes.failure_reason
          || "선별 처리 중 오류가 있었어요. 토큰은 환불됐습니다.",
        );
        setStage("error");
        return;
      }
      router.replace(`/best-shot/${encodeURIComponent(sessionId)}`);
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorText(err.message || "업로드 중 오류가 발생했어요.");
      } else {
        setErrorText("연결이 잠깐 끊겼어요. 다시 시도해주세요.");
      }
      setStage("error");
    }
  }

  async function handleAbort(): Promise<void> {
    if (initResponse?.session_id) {
      try {
        await abortBestShotSession(initResponse.session_id);
      } catch {
        // best-effort
      }
    }
    setStage("setup");
    setInitResponse(null);
    setUploadedCount(0);
    setErrorText(null);
    setErrorAction(null);
  }

  // ── 가드 대기
  if (guardStatus !== "ready") {
    return (
      <div
        style={{ minHeight: "100vh", background: "var(--color-paper)" }}
        aria-hidden
      />
    );
  }

  // ── running 중에는 LoadingSlides 풀스크린
  if (stage === "running") {
    return (
      <LoadingSlides
        onComplete={() => {
          // 응답이 더 빨리 오면 redirect가 이미 발생. 늦으면 그냥 대기 화면.
        }}
      />
    );
  }

  return (
    <div className="flex min-h-screen flex-col" style={{ background: "var(--color-paper)" }}>
      <TopBar backTarget="/" />

      <main className="flex-1" style={{ padding: "24px 24px 120px" }}>
        <Header balance={balance} fileCount={files.length} />

        {stage === "uploading" && (
          <UploadProgress
            uploaded={uploadedCount}
            total={files.length}
            onAbort={handleAbort}
          />
        )}

        {stage !== "uploading" && (
          <>
            <FilePickerCard
              files={files}
              onPick={() => fileInputRef.current?.click()}
              onRemove={handleRemoveFile}
              onRemoveAll={handleRemoveAll}
              disabled={stage === "init_pending"}
            />

            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              multiple
              hidden
              onChange={(e) => handleFilesPick(e.target.files)}
            />

            <FootnoteBlock fileCount={files.length} />
          </>
        )}

        {errorText && (
          <ErrorBanner text={errorText} action={errorAction} onDismiss={() => {
            setErrorText(null);
            setErrorAction(null);
          }} />
        )}
      </main>

      {stage !== "uploading" && (
        <StickyCta
          fileCount={files.length}
          balance={balance}
          stage={stage}
          onStart={() => handleStart(false)}
        />
      )}

      {stage === "strength_warn" && strengthScore !== null && (
        <StrengthWarningModal
          score={strengthScore}
          onCancel={() => {
            setStage("setup");
          }}
          onProceed={() => {
            setStage("setup");
            void handleStart(true);
          }}
        />
      )}

      <SiteFooter />
    </div>
  );
}

// ─────────────────────────────────────────────
//  Sub-views
// ─────────────────────────────────────────────

function Header({ balance, fileCount }: { balance: number | null; fileCount: number }) {
  return (
    <header style={{ marginBottom: 24 }}>
      <h1
        className="font-serif"
        style={{
          margin: 0,
          fontSize: 28,
          fontWeight: 400,
          letterSpacing: "-0.01em",
          lineHeight: 1.25,
        }}
      >
        Best Shot
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
        올리신 사진들 안에서, 한 장만 정성껏 골라요.
      </p>
      <div
        className="font-sans tabular-nums"
        style={{
          marginTop: 18,
          fontSize: 11,
          letterSpacing: "0.05em",
          color: "var(--color-mute-2)",
        }}
      >
        {fileCount > 0 ? `사진 ${fileCount}장 선택됨` : "사진을 선택해 주세요"}
        {balance !== null && (
          <>
            {"  ·  "}토큰 {balance}개 보유
          </>
        )}
      </div>
    </header>
  );
}

function FilePickerCard({
  files,
  onPick,
  onRemove,
  onRemoveAll,
  disabled,
}: {
  files: SelectedFile[];
  onPick: () => void;
  onRemove: (id: string) => void;
  onRemoveAll: () => void;
  disabled: boolean;
}) {
  if (files.length === 0) {
    return (
      <button
        type="button"
        onClick={onPick}
        disabled={disabled}
        className="font-sans"
        style={{
          width: "100%",
          padding: "60px 24px",
          background: "transparent",
          border: "1px dashed rgba(0, 0, 0, 0.25)",
          borderRadius: 0,
          cursor: disabled ? "default" : "pointer",
          color: "var(--color-ink)",
          fontSize: 14,
          letterSpacing: "-0.005em",
          lineHeight: 1.6,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 6,
        }}
      >
        <span style={{ fontWeight: 600 }}>사진 고르기</span>
        <span style={{ fontSize: 12, color: "var(--color-mute)" }}>
          한 번에 50~500장. JPG · PNG · WEBP
        </span>
        <span style={{ fontSize: 11, color: "var(--color-mute-2)" }}>
          iPhone HEIC 은 지원 안 돼요. 아이폰 설정 → 카메라 →
          포맷 → 호환성 우선 으로 바꿔 주세요.
        </span>
      </button>
    );
  }

  return (
    <div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 6,
          marginBottom: 12,
        }}
      >
        {files.slice(0, 60).map((f) => (
          <div
            key={f.id}
            style={{
              position: "relative",
              aspectRatio: "1 / 1",
              background: "rgba(0,0,0,0.06)",
              overflow: "hidden",
            }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={f.previewUrl}
              alt=""
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
                display: "block",
              }}
            />
            <button
              type="button"
              onClick={() => onRemove(f.id)}
              aria-label="이 사진 빼기"
              style={{
                position: "absolute",
                top: 2,
                right: 2,
                width: 20,
                height: 20,
                background: "rgba(0,0,0,0.65)",
                color: "#fff",
                border: "none",
                fontSize: 12,
                lineHeight: 1,
                cursor: "pointer",
              }}
            >
              x
            </button>
          </div>
        ))}
      </div>
      {files.length > 60 && (
        <p
          className="font-sans tabular-nums"
          style={{
            margin: "0 0 12px",
            fontSize: 11,
            color: "var(--color-mute)",
          }}
        >
          썸네일은 60장까지만 보여요. 전체 {files.length}장이 분석됩니다.
        </p>
      )}
      <div style={{ display: "flex", gap: 10 }}>
        <button
          type="button"
          onClick={onPick}
          disabled={disabled}
          className="font-sans"
          style={{
            flex: 1,
            height: 44,
            background: "transparent",
            border: "1px solid rgba(0, 0, 0, 0.25)",
            cursor: disabled ? "default" : "pointer",
            fontSize: 13,
            fontWeight: 600,
            letterSpacing: "0.3px",
          }}
        >
          더 추가
        </button>
        <button
          type="button"
          onClick={onRemoveAll}
          disabled={disabled}
          className="font-sans"
          style={{
            flex: 1,
            height: 44,
            background: "transparent",
            border: "1px solid rgba(0, 0, 0, 0.25)",
            cursor: disabled ? "default" : "pointer",
            fontSize: 13,
            fontWeight: 600,
            letterSpacing: "0.3px",
            color: "var(--color-mute)",
          }}
        >
          전부 빼기
        </button>
      </div>
    </div>
  );
}

function FootnoteBlock({ fileCount }: { fileCount: number }) {
  const fewerThanMin = fileCount > 0 && fileCount < MIN_PHOTOS;
  return (
    <div
      className="font-sans"
      style={{
        marginTop: 28,
        padding: "16px 18px",
        background: "rgba(0, 0, 0, 0.03)",
        fontSize: 12,
        lineHeight: 1.7,
        color: "var(--color-mute)",
        letterSpacing: "-0.005em",
      }}
    >
      <div>Best Shot은 50장부터 가능해요. 30 토큰이 차감됩니다.</div>
      <div>JPG · PNG · WEBP 만 돼요. iPhone 기본 HEIC 은 안 됩니다.</div>
      <div>업로드된 원본은 24시간 후 자동으로 정리돼요.</div>
      {fewerThanMin && (
        <div style={{ marginTop: 8, color: "var(--color-danger)" }}>
          {fileCount}장은 적어요. 50장 미만이면{" "}
          <Link
            href="/verdict/new"
            style={{ color: "var(--color-danger)", textDecoration: "underline" }}
          >
            피드 추천
          </Link>
          이 더 잘 맞아요.
        </div>
      )}
    </div>
  );
}

function StickyCta({
  fileCount,
  balance,
  stage,
  onStart,
}: {
  fileCount: number;
  balance: number | null;
  stage: Stage;
  onStart: () => void;
}) {
  const ready = fileCount >= MIN_PHOTOS && balance !== null && balance >= COST_BEST_SHOT;
  const lowBalance = balance !== null && balance < COST_BEST_SHOT;
  const labelMain = stage === "init_pending" ? "준비 중" : "분석 시작 (30 토큰)";
  const labelDisabled =
    fileCount < MIN_PHOTOS
      ? "사진을 50장 이상 골라 주세요"
      : lowBalance
        ? "토큰이 부족해요"
        : labelMain;

  return (
    <div
      style={{
        position: "sticky",
        bottom: 0,
        left: 0,
        right: 0,
        background: "var(--color-paper)",
        padding: "12px 24px 24px",
        borderTop: "1px solid rgba(0, 0, 0, 0.08)",
      }}
    >
      {lowBalance && (
        <Link
          href="/tokens/purchase"
          className="font-sans"
          style={{
            display: "block",
            textAlign: "center",
            fontSize: 12,
            color: "var(--color-ink)",
            textDecoration: "underline",
            marginBottom: 12,
          }}
        >
          토큰 충전하러 가기
        </Link>
      )}
      <PrimaryButton
        type="button"
        onClick={onStart}
        disabled={!ready || stage === "init_pending"}
        disabledLabel={labelDisabled}
      >
        {labelMain}
      </PrimaryButton>
    </div>
  );
}

function UploadProgress({
  uploaded,
  total,
  onAbort,
}: {
  uploaded: number;
  total: number;
  onAbort: () => void;
}) {
  const percent = total === 0 ? 0 : Math.min(100, Math.round((uploaded / total) * 100));
  return (
    <div style={{ padding: "60px 0" }}>
      <p
        className="font-serif"
        style={{
          margin: 0,
          fontSize: 22,
          fontWeight: 400,
          letterSpacing: "-0.01em",
        }}
      >
        사진을 올리는 중이에요
      </p>
      <p
        className="font-sans tabular-nums"
        style={{
          margin: "10px 0 24px",
          fontSize: 13,
          color: "var(--color-mute)",
        }}
      >
        {uploaded} / {total}장 ({percent}%)
      </p>
      <div
        style={{
          height: 2,
          background: "rgba(0,0,0,0.1)",
          position: "relative",
          marginBottom: 32,
        }}
      >
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            bottom: 0,
            width: `${percent}%`,
            background: "var(--color-ink)",
            transition: "width 220ms ease",
          }}
        />
      </div>
      <button
        type="button"
        onClick={onAbort}
        className="font-sans"
        style={{
          background: "transparent",
          border: "none",
          padding: 0,
          color: "var(--color-mute)",
          fontSize: 12,
          textDecoration: "underline",
          cursor: "pointer",
        }}
      >
        업로드 취소
      </button>
    </div>
  );
}

function ErrorBanner({
  text,
  action,
  onDismiss,
}: {
  text: string;
  action: { label: string; href: string } | null;
  onDismiss: () => void;
}) {
  return (
    <div
      role="alert"
      style={{
        marginTop: 20,
        padding: "14px 16px",
        borderTop: "1px solid var(--color-danger)",
        background: "rgba(163, 45, 45, 0.04)",
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
        {text}
      </p>
      <div style={{ marginTop: 10, display: "flex", gap: 12 }}>
        {action && (
          <Link
            href={action.href}
            className="font-sans"
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: "var(--color-ink)",
              textDecoration: "underline",
            }}
          >
            {action.label}
          </Link>
        )}
        <button
          type="button"
          onClick={onDismiss}
          className="font-sans"
          style={{
            background: "transparent",
            border: "none",
            padding: 0,
            color: "var(--color-mute)",
            fontSize: 13,
            cursor: "pointer",
          }}
        >
          닫기
        </button>
      </div>
    </div>
  );
}

function StrengthWarningModal({
  score,
  onCancel,
  onProceed,
}: {
  score: number;
  onCancel: () => void;
  onProceed: () => void;
}) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.45)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
        zIndex: 50,
      }}
    >
      <div
        style={{
          background: "var(--color-paper)",
          padding: "28px 24px 24px",
          maxWidth: 360,
          width: "100%",
        }}
      >
        <h2
          className="font-serif"
          style={{
            margin: 0,
            fontSize: 20,
            fontWeight: 400,
            letterSpacing: "-0.01em",
          }}
        >
          잠깐만요
        </h2>
        <p
          className="font-sans"
          style={{
            margin: "12px 0 6px",
            fontSize: 13,
            lineHeight: 1.7,
            color: "var(--color-ink)",
            letterSpacing: "-0.005em",
          }}
        >
          아직 모인 정보가 적어서 선별 정확도가 평소보다 낮을 수 있어요.
          (현재 데이터 충실도 {(score * 100).toFixed(0)}%)
        </p>
        <p
          className="font-sans"
          style={{
            margin: "0 0 22px",
            fontSize: 12,
            lineHeight: 1.7,
            color: "var(--color-mute)",
          }}
        >
          시각이 본 당신 또는 추구미 분석을 한두 번 해보고 다시 오시면 더 정확해져요.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <PrimaryButton type="button" onClick={onProceed}>
            그래도 진행하기
          </PrimaryButton>
          <button
            type="button"
            onClick={onCancel}
            className="font-sans"
            style={{
              background: "transparent",
              border: "1px solid rgba(0,0,0,0.25)",
              height: 48,
              fontSize: 13,
              fontWeight: 600,
              letterSpacing: "0.3px",
              cursor: "pointer",
            }}
          >
            나중에 다시
          </button>
        </div>
      </div>
    </div>
  );
}
