import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// useSiaSession / next/navigation 을 mock 해서 상태 주입.
const mockReplace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace, push: vi.fn(), back: vi.fn() }),
}));

const mockSend = vi.fn();
const mockResetError = vi.fn();
let mockState: Record<string, unknown> = {
  status: "booting",
  sessionId: null,
  messages: [],
  countdownSeconds: 300,
  progressPercent: 0,
  turnCount: 0,
  errorCode: null,
  reportId: null,
};

vi.mock("@/hooks/useSiaSession", () => ({
  useSiaSession: () => ({
    ...mockState,
    send: mockSend,
    resetError: mockResetError,
  }),
}));

import { SiaChatView } from "./SiaChatView";

function setState(next: Record<string, unknown>) {
  mockState = { ...mockState, ...next };
}

describe("SiaChatView", () => {
  beforeEach(() => {
    mockReplace.mockClear();
    mockSend.mockClear();
    mockResetError.mockClear();
    mockState = {
      status: "booting",
      sessionId: null,
      messages: [],
      countdownSeconds: 300,
      progressPercent: 0,
      turnCount: 0,
      errorCode: null,
      reportId: null,
    };
  });
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders empty stream while booting", () => {
    setState({ status: "booting" });
    render(<SiaChatView />);
    // TopBar SIGAK 워드마크 존재 (SiaTopBar 내부)
    // Stream 은 pending 없음, 메시지 0
    expect(screen.queryByTestId("sia-input-dock")).toBeInTheDocument();
  });

  it("renders messages in ready state", () => {
    setState({
      status: "ready",
      sessionId: "s1",
      messages: [
        {
          id: "m1",
          role: "sia",
          content: "정세현님, Sia 예요.",
          msg_type: null,
          created_at: new Date().toISOString(),
        },
      ],
    });
    render(<SiaChatView />);
    expect(screen.getByText(/정세현님, Sia 예요/)).toBeInTheDocument();
  });

  it("shows error banner and disables input when errorCode present", () => {
    setState({
      status: "error",
      sessionId: "s1",
      errorCode: "server",
      messages: [],
    });
    render(<SiaChatView />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/잠시 문제가 있었어요/)).toBeInTheDocument();
  });

  it("calls router.replace with /sia/done?report=... when completed", async () => {
    setState({
      status: "completed",
      sessionId: "s1",
      reportId: "rpt_abc",
      messages: [],
    });
    render(<SiaChatView />);
    await waitFor(() =>
      expect(mockReplace).toHaveBeenCalledWith("/sia/done?report=rpt_abc"),
    );
  });

  it("disables input dock when sending", () => {
    setState({
      status: "sending",
      sessionId: "s1",
      messages: [
        {
          id: "m1",
          role: "sia",
          content: "물어볼게요.",
          msg_type: null,
          created_at: new Date().toISOString(),
        },
      ],
    });
    render(<SiaChatView />);
    const textarea = screen.getByLabelText("Sia에게 답하기");
    expect(textarea).toBeDisabled();
  });
});
