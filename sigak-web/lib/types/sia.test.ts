/**
 * sia.ts — MsgType union + 버킷 + type guard 검증 (Phase H ⑥).
 *
 * 백엔드 enum .value 와 1:1 정합. 확장 3종 (check_in / re_entry / range_disclosure)
 * 의 버킷 배정과 question-forbidden 포함 확인.
 */
import { describe, it, expect } from "vitest";

import {
  COLLECTION_TYPES,
  CONFRONT_TYPES,
  MANAGEMENT_TYPES,
  MSG_TYPES,
  QUESTION_FORBIDDEN_TYPES,
  QUESTION_REQUIRED_TYPES,
  UNDERSTANDING_TYPES,
  WHITESPACE_TYPES,
  isCollectionType,
  isConfrontType,
  isManagementType,
  isMsgType,
  isQuestionForbidden,
  isQuestionRequired,
  isUnderstandingType,
  isWhitespaceType,
} from "./sia";

describe("MsgType union", () => {
  it("MSG_TYPES 는 14 종", () => {
    expect(MSG_TYPES.length).toBe(14);
  });

  it("관리 버킷 3종 (check_in / re_entry / range_disclosure) 포함", () => {
    expect(MSG_TYPES).toContain("check_in");
    expect(MSG_TYPES).toContain("re_entry");
    expect(MSG_TYPES).toContain("range_disclosure");
  });

  it("MSG_TYPES 항목 전부 소문자 + 언더스코어 (백엔드 .value 일치)", () => {
    for (const t of MSG_TYPES) {
      expect(t).toBe(t.toLowerCase());
      expect(/[a-z_]+/.test(t)).toBe(true);
    }
  });
});

describe("버킷 상수", () => {
  it("MANAGEMENT_TYPES 는 정확히 3종", () => {
    expect(MANAGEMENT_TYPES).toEqual(["check_in", "re_entry", "range_disclosure"]);
  });

  it("모든 버킷 합집합이 14종과 동일", () => {
    const unioned = new Set<string>([
      ...COLLECTION_TYPES,
      ...UNDERSTANDING_TYPES,
      ...WHITESPACE_TYPES,
      ...CONFRONT_TYPES,
      ...MANAGEMENT_TYPES,
    ]);
    expect(unioned.size).toBe(14);
    for (const t of MSG_TYPES) {
      expect(unioned.has(t)).toBe(true);
    }
  });

  it("버킷끼리 겹치지 않는다 (disjoint)", () => {
    const buckets = [
      ["collection", COLLECTION_TYPES],
      ["understanding", UNDERSTANDING_TYPES],
      ["whitespace", WHITESPACE_TYPES],
      ["confront", CONFRONT_TYPES],
      ["management", MANAGEMENT_TYPES],
    ] as const;
    for (let i = 0; i < buckets.length; i++) {
      for (let j = i + 1; j < buckets.length; j++) {
        const [, a] = buckets[i];
        const [, b] = buckets[j];
        for (const t of a) {
          expect(b.includes(t)).toBe(false);
        }
      }
    }
  });
});

describe("QUESTION_FORBIDDEN_TYPES 관리 버킷 포함", () => {
  it("3종 전부 질문 금지", () => {
    expect(QUESTION_FORBIDDEN_TYPES).toContain("check_in");
    expect(QUESTION_FORBIDDEN_TYPES).toContain("re_entry");
    expect(QUESTION_FORBIDDEN_TYPES).toContain("range_disclosure");
  });

  it("QUESTION_REQUIRED / FORBIDDEN 은 disjoint + 합집합=14", () => {
    const req = new Set<string>(QUESTION_REQUIRED_TYPES);
    const forb = new Set<string>(QUESTION_FORBIDDEN_TYPES);
    for (const t of req) expect(forb.has(t)).toBe(false);
    const total = new Set<string>([...req, ...forb]);
    expect(total.size).toBe(14);
  });
});

describe("type guards", () => {
  it("isMsgType 는 유효한 문자열만 true", () => {
    expect(isMsgType("observation")).toBe(true);
    expect(isMsgType("check_in")).toBe(true);
    expect(isMsgType("OBSERVATION")).toBe(false); // 대문자 거절
    expect(isMsgType("bogus")).toBe(false);
    expect(isMsgType(null)).toBe(false);
    expect(isMsgType(undefined)).toBe(false);
    expect(isMsgType(42)).toBe(false);
  });

  it("버킷 guard 는 각 버킷 멤버에만 true", () => {
    expect(isCollectionType("observation")).toBe(true);
    expect(isCollectionType("check_in")).toBe(false);

    expect(isUnderstandingType("diagnosis")).toBe(true);
    expect(isUnderstandingType("observation")).toBe(false);

    expect(isWhitespaceType("opening_declaration")).toBe(true);
    expect(isWhitespaceType("probe")).toBe(false);

    expect(isConfrontType("meta_rebuttal")).toBe(true);
    expect(isConfrontType("empathy_mirror")).toBe(false);

    expect(isManagementType("re_entry")).toBe(true);
    expect(isManagementType("observation")).toBe(false);
  });

  it("question guard 는 14 종 전체에 대해 정확", () => {
    for (const t of MSG_TYPES) {
      const req = isQuestionRequired(t);
      const forb = isQuestionForbidden(t);
      // 정확히 한 쪽만 true
      expect(req !== forb).toBe(true);
    }
  });

  it("관리 버킷 3종은 전부 question forbidden", () => {
    for (const t of MANAGEMENT_TYPES) {
      expect(isQuestionForbidden(t)).toBe(true);
      expect(isQuestionRequired(t)).toBe(false);
    }
  });
});
