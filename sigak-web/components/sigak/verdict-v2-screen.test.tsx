// SIGAK — VerdictV2Screen tests (WTP 가설 — best_fit 1 장 풀 노출)
//
// 검증:
//   1. preview 명시 best_fit 필드 → BestFitCard + BlurredPhotosGrid 노출
//   2. best_fit_photo_index null → 기존 동작 (UnlockSection 만 노출)
//   3. unlock 후 photo_insights 첫 자리에 best_fit 정렬
//   4. 정규식 fallback (legacy v2 row) 동작
//   5. backward compat — best_fit_* 필드 부재해도 기존 화면 유지

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

import { VerdictV2Screen } from "./verdict-v2-screen";
import type {
  PreviewContent,
  FullContent,
  VerdictV2GetResponse,
} from "@/lib/types/verdict_v2";

// ─────────────────────────────────────────────
//  Mocks — Next router + token hook + API client
// ─────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
}));

vi.mock("@/hooks/use-token-balance", () => ({
  useTokenBalance: () => ({
    balance: 100,
    loading: false,
    error: null,
    refetch: vi.fn().mockResolvedValue(undefined),
  }),
}));

vi.mock("@/lib/api/verdicts", () => ({
  unlockVerdictV2: vi.fn(),
}));

vi.mock("@/components/ui/sigak", () => ({
  FeedTopBar: ({ backTarget }: { backTarget: string }) => (
    <div data-testid="feed-top-bar" data-back={backTarget} />
  ),
}));

vi.mock("./site-footer", () => ({
  SiteFooter: () => <div data-testid="site-footer" />,
}));

// ─────────────────────────────────────────────
//  Fixtures
// ─────────────────────────────────────────────

const PHOTOS_3: (string | null)[] = [
  "https://r2.example.com/p0.jpg",
  "https://r2.example.com/p1.jpg",
  "https://r2.example.com/p2.jpg",
];

function makePreview(overrides: Partial<PreviewContent> = {}): PreviewContent {
  return {
    hook_line: "추구미와 일치합니다",
    reason_summary: "쿨뮤트 톤이 유지됩니다.",
    ...overrides,
  };
}

function makeFullContent(overrides: Partial<FullContent> = {}): FullContent {
  return {
    verdict: "전반적으로 일치합니다.",
    photo_insights: [
      {
        photo_index: 0,
        insight: "0번 사진은 안정적인 구도입니다.",
        improvement: "0번 측광 권장.",
      },
      {
        photo_index: 1,
        insight: "1번 사진이 가장 잘 맞는 결입니다.",
        improvement: "1번 채도 유지.",
      },
      {
        photo_index: 2,
        insight: "2번은 하이컨트라스트 톤입니다.",
        improvement: "2번 살짝 낮게.",
      },
    ],
    recommendation: {
      style_direction: "쿨뮤트 유지",
      next_action: "측광 시도",
      why: "일치 강화",
    },
    numbers: {
      photo_count: 3,
      dominant_tone: "쿨뮤트",
      dominant_tone_pct: 68,
      chroma_multiplier: null,
      alignment_with_profile: "일치",
    },
    cta_pi: null,
    ...overrides,
  };
}

function makeGetResponse(
  overrides: Partial<VerdictV2GetResponse> = {},
): VerdictV2GetResponse {
  return {
    verdict_id: "vrd_test",
    version: "v2",
    full_unlocked: false,
    preview: makePreview(),
    full_content: null,
    photo_urls: PHOTOS_3,
    ...overrides,
  };
}

// ─────────────────────────────────────────────
//  Test cases
// ─────────────────────────────────────────────

describe("VerdictV2Screen — WTP best_fit 1장 풀 노출", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("preview에 best_fit 명시 필드가 있으면 BestFitCard + 블러 카드 N-1개 노출", () => {
    const data = makeGetResponse({
      preview: makePreview({
        best_fit_photo_index: 1,
        best_fit_insight: "1번 사진이 가장 잘 맞는 결입니다.",
        best_fit_improvement: "1번 채도 유지.",
      }),
      best_fit_photo_url: PHOTOS_3[1],
    });
    render(<VerdictV2Screen initial={data} />);

    // 섹션 제목 확인
    expect(screen.getByText("이번 업로드의 베스트 1장")).toBeInTheDocument();
    expect(screen.getByText("나머지 2장")).toBeInTheDocument();

    // best_fit 본문 노출
    expect(
      screen.getByText("1번 사진이 가장 잘 맞는 결입니다."),
    ).toBeInTheDocument();
    expect(screen.getByText("1번 채도 유지.")).toBeInTheDocument();

    // 베스트 배지 노출
    expect(screen.getByText("추구미와 가장 가까운 결")).toBeInTheDocument();

    // 인덱스 라벨 (#02) — 1-based padded
    expect(screen.getByText("#02")).toBeInTheDocument();

    // Unlock CTA 도 함께 노출 (잠금 N-1 카드 안내 → 결제 트리거)
    expect(screen.getByText(/전체 분석 열기/)).toBeInTheDocument();
  });

  it("best_fit_photo_index null이면 기존 동작 — UnlockSection만 노출", () => {
    const data = makeGetResponse({
      preview: makePreview({ best_fit_photo_index: null }),
    });
    render(<VerdictV2Screen initial={data} />);

    // BestFitCard 영역 미노출
    expect(
      screen.queryByText("이번 업로드의 베스트 1장"),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/나머지/)).not.toBeInTheDocument();
    expect(
      screen.queryByText("추구미와 가장 가까운 결"),
    ).not.toBeInTheDocument();

    // 기존 UnlockSection 정상 노출
    expect(screen.getByText(/전체 분석 열기/)).toBeInTheDocument();
    expect(screen.getByText(/이 업로드에 대한 전체 분석/)).toBeInTheDocument();
  });

  it("best_fit_* 필드 부재 (legacy preview) → 기존 동작 보존 (backward compat)", () => {
    // 의도적으로 best_fit_photo_index / insight / improvement 모두 미포함
    const data = makeGetResponse({
      preview: { hook_line: "기존 훅", reason_summary: "기존 근거" },
    });
    render(<VerdictV2Screen initial={data} />);

    expect(screen.getByText("기존 훅")).toBeInTheDocument();
    expect(screen.queryByText(/베스트 1장/)).not.toBeInTheDocument();
    expect(screen.getByText(/전체 분석 열기/)).toBeInTheDocument();
  });

  it("best_fit_photo_url 부재해도 카드는 노출 (텍스트 풀 공개 우선)", () => {
    const data = makeGetResponse({
      preview: makePreview({
        best_fit_photo_index: 0,
        best_fit_insight: "0번 사진 텍스트.",
        best_fit_improvement: "개선 텍스트.",
      }),
      // best_fit_photo_url 명시 없음 → photo_urls[0] fallback
      photo_urls: PHOTOS_3,
    });
    render(<VerdictV2Screen initial={data} />);

    expect(screen.getByText("0번 사진 텍스트.")).toBeInTheDocument();
    expect(screen.getByText("개선 텍스트.")).toBeInTheDocument();
  });

  it("photo_urls 가 1장이면 잠금 카드 영역 미노출 (N-1 = 0)", () => {
    const data = makeGetResponse({
      preview: makePreview({
        best_fit_photo_index: 0,
        best_fit_insight: "1장만 있는 케이스.",
        best_fit_improvement: "남은 게 없습니다.",
      }),
      photo_urls: ["https://r2.example.com/only.jpg"],
    });
    render(<VerdictV2Screen initial={data} />);

    expect(screen.getByText("이번 업로드의 베스트 1장")).toBeInTheDocument();
    expect(screen.queryByText(/나머지/)).not.toBeInTheDocument();
  });
});

describe("VerdictV2Screen — unlock 후 best_fit 정렬", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("unlock 후 photo_insights 첫 자리에 best_fit 노출 (명시 필드)", () => {
    const data = makeGetResponse({
      full_unlocked: true,
      preview: makePreview({
        best_fit_photo_index: 1,
        best_fit_insight: "1번이 가장 잘 맞는 결입니다.",
        best_fit_improvement: "1번 채도 유지.",
      }),
      full_content: makeFullContent({ best_fit_photo_index: 1 }),
    });
    render(<VerdictV2Screen initial={data} />);

    // 사진별 해석 섹션의 카드 순서 — best_fit (#02) 가 첫 번째
    const insightCards = screen.getAllByText(/^#0[123]$/);
    // 가장 가까운 결 배지가 1번 카드에만 있어야 함
    expect(screen.getByText("추구미와 가장 가까운 결")).toBeInTheDocument();

    // 첫 번째 카드의 인덱스가 #02 (1-based) 인지 확인
    expect(insightCards[0]).toHaveTextContent("#02");
    expect(insightCards[1]).toHaveTextContent("#01");
    expect(insightCards[2]).toHaveTextContent("#03");
  });

  it("정규식 fallback (best_fit_photo_index null + 텍스트 매칭)", () => {
    const data = makeGetResponse({
      full_unlocked: true,
      preview: makePreview(),  // no explicit best_fit
      full_content: makeFullContent({
        best_fit_photo_index: null,
        // photo_insight[1] 본문에 "가장 잘 맞는" 포함 → 정규식 매칭
      }),
    });
    render(<VerdictV2Screen initial={data} />);

    // 정규식 fallback 결과로도 best_fit 배지 노출
    expect(screen.getByText("추구미와 가장 가까운 결")).toBeInTheDocument();

    // 정렬 확인 — index 1 첫 자리
    const insightCards = screen.getAllByText(/^#0[123]$/);
    expect(insightCards[0]).toHaveTextContent("#02");
  });

  it("best_fit 부재 (명시 + 정규식 둘 다 매칭 X) → 원래 순서 유지", () => {
    const data = makeGetResponse({
      full_unlocked: true,
      preview: makePreview(),
      full_content: makeFullContent({
        best_fit_photo_index: null,
        photo_insights: [
          { photo_index: 0, insight: "0번 평이한 인사이트", improvement: "0개선" },
          { photo_index: 1, insight: "1번 평이한 인사이트", improvement: "1개선" },
          { photo_index: 2, insight: "2번 평이한 인사이트", improvement: "2개선" },
        ],
      }),
    });
    render(<VerdictV2Screen initial={data} />);

    expect(
      screen.queryByText("추구미와 가장 가까운 결"),
    ).not.toBeInTheDocument();

    // 원래 순서 유지 (#01, #02, #03)
    const insightCards = screen.getAllByText(/^#0[123]$/);
    expect(insightCards[0]).toHaveTextContent("#01");
    expect(insightCards[1]).toHaveTextContent("#02");
    expect(insightCards[2]).toHaveTextContent("#03");
  });

  it("preview 명시 + full_content 일치 시 일관성 검증", () => {
    const data = makeGetResponse({
      full_unlocked: true,
      preview: makePreview({
        best_fit_photo_index: 2,
        best_fit_insight: "2번이 best_fit",
        best_fit_improvement: "2번 개선",
      }),
      full_content: makeFullContent({ best_fit_photo_index: 2 }),
    });
    render(<VerdictV2Screen initial={data} />);

    const insightCards = screen.getAllByText(/^#0[123]$/);
    expect(insightCards[0]).toHaveTextContent("#03");
  });
});
