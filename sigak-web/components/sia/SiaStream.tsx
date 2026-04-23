"use client";

/**
 * SiaStream — 메시지 배열을 버블 시퀀스로 렌더 (D6 정적 포팅).
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
 * 자동 스크롤:
 *   - 새 턴 추가 시 하단으로 smooth scroll
 *   - SSR 안전: useEffect 내부에서만 window 접근
 */
import { useEffect, useRef } from "react";

import type { SiaTurn } from "@/lib/types/sia.legacy";

import { SiaBubble } from "./SiaBubble";
import { SiaDots } from "./SiaDots";

export interface SiaStreamProps {
  messages: SiaTurn[];
  /** true 이면 마지막 턴 아래 SiaDots 표시 (assistant 응답 대기 중) */
  pending?: boolean;
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

export function SiaStream({ messages, pending = false }: SiaStreamProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const node = scrollRef.current;
    if (!node) return;
    node.scrollTo({ top: node.scrollHeight, behavior: "smooth" });
  }, [messages.length, pending]);

  return (
    <div
      ref={scrollRef}
      className="flex-1 overflow-y-auto px-[20px] py-[24px]"
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

        const bubbles = parseSiaMessage(turn.content);
        return (
          <div
            key={turnIdx}
            className={`mb-[28px] flex flex-col gap-[4px] ${alignClass}`}
            data-turn-role="sia"
          >
            {bubbles.map((bubble, bubbleIdx) => (
              <SiaBubble
                key={bubbleIdx}
                variant={bubble.type === "list" ? "list" : "sia"}
              >
                {bubble.content}
              </SiaBubble>
            ))}
          </div>
        );
      })}

      {pending && (
        <div
          className="mb-[28px] flex flex-col gap-[4px] items-start"
          data-turn-role="pending"
        >
          <SiaDots />
        </div>
      )}
    </div>
  );
}
