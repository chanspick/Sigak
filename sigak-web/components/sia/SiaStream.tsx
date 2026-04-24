"use client";

/**
 * SiaStream — 메시지 배열을 버블 시퀀스로 렌더 (D6 정적 포팅 + Phase H UX stagger).
 *
 * 디자인 출처: chat_design/ui_kits/sia/index.html `.stream` / `.turn` / `.turn-gap`
 *
 * Split 로직 (Sia assistant 메시지 전용):
 *   1. 개행 기준 라인 분해
 *   2. "- " 로 시작하는 연속 라인 → list 버블 1 개로 묶음 (newline 보존)
 *   3. 그 외 라인은 마침표/물음표/느낌표 + 공백 기준으로 문장 분할
 *   4. 각 문장 → text 버블 1 개
 *
 * User 메시지는 split 없이 그대로 1 버블 렌더.
 *
 * 간격:
 *   - 버블 간 4px (turn 내부)
 *   - 턴 간 28px (assistant↔user 전환)
 *
 * Stagger reveal (Phase H UX):
 *   - 마운트 이후 새로 도착한 assistant 턴만 순차 공개.
 *   - 각 버블 공개 전 짧은 SiaDots 표시 (DOTS_DURATION) 후 버블 교체.
 *   - 버블 사이 간격 BUBBLE_INTERVAL.
 *   - 마운트 시 이미 존재하던 메시지는 즉시 전부 공개 (페이지 재진입 시 재애니메이션 X).
 *
 * 자동 스크롤:
 *   - 메시지 길이 변화 + pending 변화 + stagger 진행 변화에 모두 반응.
 *   - SSR 안전: useEffect 내부에서만 scrollTo 접근.
 */
import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from "react";

import type { SiaTurn } from "@/lib/types/sia.legacy";

import { SiaBubble } from "./SiaBubble";
import { SiaDots } from "./SiaDots";

export interface SiaStreamProps {
  messages: SiaTurn[];
  /** true 이면 마지막 턴 아래 SiaDots 표시 (assistant 응답 대기 중) */
  pending?: boolean;
}

export interface SiaStreamHandle {
  /** 스크롤 컨테이너를 하단으로 보정. 키보드 올라올 때 외부에서 호출. */
  scrollToBottom: (opts?: { smooth?: boolean }) => void;
}

interface ParsedBubble {
  type: "text" | "list";
  content: string;
}

/**
 * Sia assistant 메시지 content 문자열 → 버블 조각 배열.
 * Exported for unit tests.
 */
export function parseSiaMessage(content: string): ParsedBubble[] {
  const lines = content
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);

  const bubbles: ParsedBubble[] = [];
  let listBuffer: string[] = [];

  const flushList = () => {
    if (listBuffer.length > 0) {
      bubbles.push({ type: "list", content: listBuffer.join("\n") });
      listBuffer = [];
    }
  };

  for (const line of lines) {
    if (line.startsWith("- ")) {
      listBuffer.push(line);
      continue;
    }
    flushList();
    // 한 라인 내 여러 문장 → split
    const sentences = line
      .split(/(?<=[.?!])\s+/)
      .map((s) => s.trim())
      .filter(Boolean);
    for (const s of sentences) {
      bubbles.push({ type: "text", content: s });
    }
  }
  flushList();

  return bubbles;
}

// ─────────────────────────────────────────────
//  Stagger 상수 — 필요 시 여기서만 조정
// ─────────────────────────────────────────────

const DOTS_DURATION_MS = 250;    // 버블 공개 직전 dots 표시 시간
const BUBBLE_INTERVAL_MS = 500;  // 버블 공개 후 다음 dots 까지 간격

type StaggerPhase = "dots" | "bubble";

interface StaggerState {
  /** 대상 assistant 턴의 signature. 바뀌면 새 stagger 시작. */
  sig: string;
  /** 지금까지 공개된 버블 수 (0..bubbles.length) */
  revealed: number;
  /** 현재 단계 — dots 이면 곧 다음 버블 나타남 / bubble 이면 방금 공개됨 */
  phase: StaggerPhase;
}

/** messages 배열에서 마지막 assistant 턴 인덱스. 없으면 -1. */
function findLastAssistantIdx(messages: SiaTurn[]): number {
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role !== "user") return i;
  }
  return -1;
}

/** 턴 signature — 인덱스 + content 로 유일 식별 (re-render 에 안전). */
function turnSignature(idx: number, content: string): string {
  return `${idx}|${content}`;
}

export const SiaStream = forwardRef<SiaStreamHandle, SiaStreamProps>(
  function SiaStream({ messages, pending = false }, handleRef) {
    const scrollRef = useRef<HTMLDivElement | null>(null);

    // 하단 스크롤 헬퍼 — 여러 effect 에서 재사용.
    const scrollToBottom = (smooth = true) => {
      const node = scrollRef.current;
      if (!node) return;
      node.scrollTo({
        top: node.scrollHeight,
        behavior: smooth ? "smooth" : "auto",
      });
    };

    // 외부 (SiaChatView) 가 input focus 시 호출할 수 있도록 expose.
    useImperativeHandle(
      handleRef,
      () => ({
        scrollToBottom: (opts) => scrollToBottom(opts?.smooth !== false),
      }),
      [],
    );

    // visualViewport resize — 모바일 키보드 open/close 시 자동 재정렬.
    // iOS/Android 공통 지원. 일부 데스크톱 브라우저는 visualViewport=null 이라
    // 조건부 리스너만 등록. 120ms 지연 = 키보드 애니메이션 완료 대기.
    useEffect(() => {
      if (typeof window === "undefined") return;
      const vv = window.visualViewport;
      if (!vv) return;
      const onResize = () => {
        window.setTimeout(() => scrollToBottom(true), 120);
      };
      vv.addEventListener("resize", onResize);
      return () => vv.removeEventListener("resize", onResize);
    }, []);

  // ── 마지막 assistant 턴 식별 + 버블 파싱 ──
  const lastSiaIdx = useMemo(() => findLastAssistantIdx(messages), [messages]);
  const lastSiaSig = useMemo(() => {
    if (lastSiaIdx < 0) return "";
    return turnSignature(lastSiaIdx, messages[lastSiaIdx].content);
  }, [lastSiaIdx, messages]);

  const parsedLatest = useMemo<ParsedBubble[]>(() => {
    if (lastSiaIdx < 0) return [];
    return parseSiaMessage(messages[lastSiaIdx].content);
  }, [lastSiaIdx, messages]);

  // ── 초기 마운트에 이미 있던 메시지는 즉시 전부 공개 ──
  const [stagger, setStagger] = useState<StaggerState>(() => {
    if (lastSiaIdx < 0) {
      return { sig: "", revealed: 0, phase: "bubble" };
    }
    const bubbleCount = parseSiaMessage(messages[lastSiaIdx].content).length;
    return {
      sig: turnSignature(lastSiaIdx, messages[lastSiaIdx].content),
      revealed: bubbleCount,
      phase: "bubble",
    };
  });

  // ── 새 assistant 턴 도착 감지 → stagger 재시작 ──
  useEffect(() => {
    if (!lastSiaSig) return;
    if (lastSiaSig === stagger.sig) return;
    setStagger({ sig: lastSiaSig, revealed: 0, phase: "dots" });
  }, [lastSiaSig, stagger.sig]);

  // ── 타임아웃 기반 순차 공개 ──
  useEffect(() => {
    if (stagger.sig !== lastSiaSig) return;
    // 완료 조건: bubble 단계 + 전부 공개됨
    if (
      stagger.phase === "bubble" &&
      stagger.revealed >= parsedLatest.length
    ) {
      return;
    }

    const delay =
      stagger.phase === "dots" ? DOTS_DURATION_MS : BUBBLE_INTERVAL_MS;

    const timer = window.setTimeout(() => {
      setStagger((prev) => {
        if (prev.sig !== lastSiaSig) return prev; // stale guard
        if (prev.phase === "dots") {
          return { ...prev, phase: "bubble", revealed: prev.revealed + 1 };
        }
        // bubble → dots (다음 버블 대기). 단 이미 끝이면 멈춤.
        if (prev.revealed >= parsedLatest.length) return prev;
        return { ...prev, phase: "dots" };
      });
    }, delay);

    return () => window.clearTimeout(timer);
  }, [stagger, parsedLatest.length, lastSiaSig]);

  // ── 자동 스크롤 — messages 길이 + pending + stagger 진행에 반응 ──
  useEffect(() => {
    const node = scrollRef.current;
    if (!node) return;
    node.scrollTo({ top: node.scrollHeight, behavior: "smooth" });
  }, [messages.length, pending, stagger.revealed, stagger.phase]);

  const staggerActive = stagger.sig === lastSiaSig;
  const staggerInProgress =
    staggerActive && stagger.revealed < parsedLatest.length;

  return (
    <div
      ref={scrollRef}
      className="flex-1 overflow-y-auto min-h-0 px-[20px] py-[24px]"
      data-testid="sia-stream"
    >
      {messages.map((turn, turnIdx) => {
        const isUser = turn.role === "user";
        const alignClass = isUser ? "items-end" : "items-start";

        if (isUser) {
          return (
            <div
              key={turnIdx}
              className={`mb-[28px] flex flex-col gap-[4px] ${alignClass}`}
              data-turn-role="user"
            >
              <SiaBubble variant="user">{turn.content}</SiaBubble>
            </div>
          );
        }

        // Assistant 턴 — stagger 대상 여부에 따라 slice 결정
        const isStaggerTarget = staggerActive && turnIdx === lastSiaIdx;
        const allBubbles = isStaggerTarget
          ? parsedLatest
          : parseSiaMessage(turn.content);
        const visibleCount = isStaggerTarget ? stagger.revealed : allBubbles.length;
        const visibleBubbles = allBubbles.slice(0, visibleCount);

        // stagger 진행 중이고 dots 단계 + 아직 공개할 버블 남음 → 턴 하단에 dots
        const showStaggerDots =
          isStaggerTarget &&
          stagger.phase === "dots" &&
          stagger.revealed < parsedLatest.length;

        return (
          <div
            key={turnIdx}
            className={`mb-[28px] flex flex-col gap-[4px] ${alignClass}`}
            data-turn-role="sia"
          >
            {visibleBubbles.map((bubble, bubbleIdx) => {
              // 마지막으로 드러난 버블 = 방금 공개됨 → 진입 애니메이션.
              // 그 이전 버블들은 이미 드러나 있었으므로 애니메이션 재생 X.
              const isJustRevealed =
                isStaggerTarget && bubbleIdx === visibleCount - 1;
              return (
                <SiaBubble
                  key={bubbleIdx}
                  variant={bubble.type === "list" ? "list" : "sia"}
                  animateIn={isJustRevealed}
                >
                  {bubble.content}
                </SiaBubble>
              );
            })}
            {showStaggerDots && <SiaDots />}
          </div>
        );
      })}

      {pending && !staggerInProgress && (
        <div
          className="mb-[28px] flex flex-col gap-[4px] items-start"
          data-turn-role="pending"
        >
          <SiaDots />
        </div>
      )}
    </div>
  );
  },
);
