// SIGAK MVP v1.2 — FeedTopBar (2026-04-27 TopBar 통합)
//
// 본인 결정: "상단 뒤로가기 포함된 바를 홈하고 통일".
// FeedTopBar 자체 디자인 폐기 → TopBar 의 단순 wrapper.
// TopBar 가 ← 뒤로 + sigak + 토큰 pill 모두 처리 (홈 정합).

"use client";

import { TopBar } from "./top-bar";

interface FeedTopBarProps {
  backTarget?: string;
  onBack?: () => void;
}

export function FeedTopBar(props: FeedTopBarProps = {}) {
  return <TopBar {...props} />;
}
