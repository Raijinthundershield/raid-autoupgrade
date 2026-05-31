import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LabelPanel } from "./LabelPanel";

// Two sessions; the backend returns them most-recent-first. Each session's
// frames are keyed by its frames URL so a test can prove which one loaded.
const SESSIONS = [
  { kind: "count", name: "20260531_130000_000", frame_count: 2 },
  { kind: "spend", name: "20260531_120000_000", frame_count: 1 },
];

const COUNT_FRAMES = {
  frames: [
    {
      frame_number: 0,
      detected_state: "standby",
      roi_file: "f0_roi.png",
      screenshot_file: "f0_shot.png",
    },
    {
      frame_number: 1,
      detected_state: "fail",
      roi_file: "f1_roi.png",
      screenshot_file: "f1_shot.png",
    },
  ],
};

const SPEND_FRAMES = {
  frames: [
    {
      frame_number: 0,
      detected_state: "connection_error",
      roi_file: "s0_roi.png",
      screenshot_file: "s0_shot.png",
    },
  ],
};

function makeFetch(sessions: unknown = SESSIONS) {
  return vi.fn((url: string) => {
    let body: unknown = {};
    if (url.includes("/api/debug/sessions/count/20260531_130000_000/frames")) {
      body = COUNT_FRAMES;
    } else if (url.includes("/api/debug/sessions/spend/20260531_120000_000/frames")) {
      body = SPEND_FRAMES;
    } else if (url.includes("/api/debug/sessions")) {
      body = { sessions };
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve(body) });
  });
}

function renderPanel() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <LabelPanel />
    </QueryClientProvider>
  );
}

describe("LabelPanel", () => {
  afterEach(() => vi.unstubAllGlobals());

  // ---------------------------------------------------------------------------
  // Tracer: defaults to the most recent session and shows its frame rows —
  // each frame's detector state guess plus its ROI and screenshot images.
  // ---------------------------------------------------------------------------

  it("defaults to the most recent session and renders its frames", async () => {
    vi.stubGlobal("fetch", makeFetch());
    renderPanel();

    // The most recent session's two frames, by their detector state guesses.
    await screen.findByText("standby");
    expect(screen.getByText("fail")).toBeInTheDocument();

    // Each frame shows its ROI and full screenshot, served from the image endpoint.
    const roi = screen.getByAltText(/roi.*frame 0/i) as HTMLImageElement;
    expect(roi.src).toContain(
      "/api/debug/sessions/count/20260531_130000_000/images/f0_roi.png"
    );
    const shot = screen.getByAltText(/screenshot.*frame 0/i) as HTMLImageElement;
    expect(shot.src).toContain(
      "/api/debug/sessions/count/20260531_130000_000/images/f0_shot.png"
    );
  });

  // ---------------------------------------------------------------------------
  // Selecting an older session loads that session's frames.
  // ---------------------------------------------------------------------------

  it("loads an older session's frames when it is selected", async () => {
    vi.stubGlobal("fetch", makeFetch());
    renderPanel();
    await screen.findByText("standby");

    await userEvent.selectOptions(
      screen.getByRole("combobox"),
      "spend/20260531_120000_000"
    );

    await screen.findByText("connection_error");
    expect(screen.queryByText("standby")).not.toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Empty state: no captured sessions yet.
  // ---------------------------------------------------------------------------

  it("shows an empty state when there are no sessions", async () => {
    vi.stubGlobal("fetch", makeFetch([]));
    renderPanel();

    await screen.findByText(/no debug sessions/i);
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });
});
