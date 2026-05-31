import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LabelPanel } from "./LabelPanel";

// Two sessions; the backend returns them most-recent-first and addresses each
// by its id (its path relative to the debug root). Each session's frames are
// keyed by its id so a test can prove which one loaded.
const SESSIONS = [
  { id: "count/20260531_130000_000", kind: "count", name: "20260531_130000_000", frame_count: 2 },
  {
    id: "spend/upgrade_1/20260531_120000_000",
    kind: "spend",
    name: "20260531_120000_000",
    frame_count: 1,
  },
];

const COUNT_FRAMES = {
  frames: [
    { frame_number: 0, detected_state: "standby", roi_file: "f0_roi.png", screenshot_file: "f0_shot.png" },
    { frame_number: 1, detected_state: "fail", roi_file: "f1_roi.png", screenshot_file: "f1_shot.png" },
  ],
};

const SPEND_FRAMES = {
  frames: [
    { frame_number: 0, detected_state: "connection_error", roi_file: "s0_roi.png", screenshot_file: "s0_shot.png" },
  ],
};

function makeFetch(sessions: unknown = SESSIONS) {
  return vi.fn((url: string, _init?: RequestInit) => {
    let body: unknown = {};
    if (url.includes("/api/debug/frames") && url.includes("session=count")) {
      body = COUNT_FRAMES;
    } else if (url.includes("/api/debug/frames") && url.includes("session=spend")) {
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

    // The most recent session's two frames each render a label control.
    await screen.findByRole("combobox", { name: /label for frame 0/i });
    expect(
      screen.getByRole("combobox", { name: /label for frame 1/i })
    ).toBeInTheDocument();

    // Each frame shows its ROI and full screenshot, served from the image endpoint
    // with the session id and filename as query params.
    const roi = screen.getByAltText(/roi.*frame 0/i) as HTMLImageElement;
    expect(roi.src).toContain("/api/debug/image?");
    expect(roi.src).toContain("session=count%2F20260531_130000_000");
    expect(roi.src).toContain("file=f0_roi.png");
  });

  // ---------------------------------------------------------------------------
  // Selecting an older session loads that session's frames.
  // ---------------------------------------------------------------------------

  it("loads an older session's frames when it is selected", async () => {
    vi.stubGlobal("fetch", makeFetch());
    renderPanel();
    await screen.findByRole("combobox", { name: /label for frame 0/i });

    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Session" }),
      "spend/upgrade_1/20260531_120000_000"
    );

    // The spend session has a single frame, pre-filled with its detector guess.
    const frame0 = (await screen.findByRole("combobox", {
      name: /label for frame 0/i,
    })) as HTMLSelectElement;
    await waitFor(() => expect(frame0.value).toBe("connection_error"));
    expect(
      screen.queryByRole("combobox", { name: /label for frame 1/i })
    ).not.toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Each frame's label control is pre-filled with the detector's guess, so
  // correcting a wrong label is a one-click change rather than a fresh pick.
  // ---------------------------------------------------------------------------

  it("pre-fills each frame's label control with the detector's guess", async () => {
    vi.stubGlobal("fetch", makeFetch());
    renderPanel();

    const frame0 = (await screen.findByRole("combobox", {
      name: /label for frame 0/i,
    })) as HTMLSelectElement;
    expect(frame0.value).toBe("standby");

    const frame1 = screen.getByRole("combobox", {
      name: /label for frame 1/i,
    }) as HTMLSelectElement;
    expect(frame1.value).toBe("fail");
  });

  // ---------------------------------------------------------------------------
  // A relabel persists to the session, so a later view shows the correction
  // (carried on the frame as `user_label`) while the original guess is kept.
  // ---------------------------------------------------------------------------

  it("shows the persisted corrected label, not the detector guess, on load", async () => {
    const fetchMock = vi.fn((url: string) => {
      let body: unknown = {};
      if (url.includes("/api/debug/frames")) {
        body = {
          frames: [
            {
              frame_number: 0,
              detected_state: "standby",
              user_label: "fail",
              roi_file: "r.png",
              screenshot_file: "s.png",
            },
          ],
        };
      } else if (url.includes("/api/debug/sessions")) {
        body = { sessions: SESSIONS };
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(body) });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderPanel();

    const sel = (await screen.findByRole("combobox", {
      name: /label for frame 0/i,
    })) as HTMLSelectElement;
    expect(sel.value).toBe("fail");
    // The detector's original guess stays visible alongside the correction.
    expect(screen.getByText(/guess:\s*standby/i)).toBeInTheDocument();
  });

  it("persists a relabel to the session as soon as it changes", async () => {
    const fetchMock = makeFetch();
    vi.stubGlobal("fetch", fetchMock);
    renderPanel();

    await userEvent.selectOptions(
      await screen.findByRole("combobox", { name: /label for frame 0/i }),
      "progress"
    );

    await waitFor(() => {
      const call = fetchMock.mock.calls.find((args) =>
        args[0].includes("/api/debug/labels")
      );
      expect(call).toBeTruthy();
      const body = JSON.parse(call![1]!.body as string);
      expect(body).toMatchObject({
        session: "count/20260531_130000_000",
        frame_number: 0,
        label: "progress",
      });
    });
  });

  // ---------------------------------------------------------------------------
  // Export posts only the frames the reviewer ticked, each with its (possibly
  // corrected) label. Checkboxes are off by default, so nothing exports by
  // accident — the reviewer opts each keeper in.
  // ---------------------------------------------------------------------------

  it("exports only the checked frames with their chosen labels", async () => {
    const fetchMock = makeFetch();
    vi.stubGlobal("fetch", fetchMock);
    renderPanel();

    // Off by default: no frame is selected for export.
    const frame1Checkbox = await screen.findByRole("checkbox", {
      name: /export frame 1/i,
    });
    expect(frame1Checkbox).not.toBeChecked();

    // Correct frame 1's label, tick it, and leave frame 0 unchecked.
    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: /label for frame 1/i }),
      "progress"
    );
    await userEvent.click(frame1Checkbox);
    await userEvent.click(screen.getByRole("button", { name: /export/i }));

    // Only the ticked frame is posted, carrying its corrected label.
    await waitFor(() => {
      const call = fetchMock.mock.calls.find((args) =>
        args[0].includes("/api/debug/export")
      );
      expect(call).toBeTruthy();
      const body = JSON.parse(call![1]!.body as string);
      expect(body.session).toBe("count/20260531_130000_000");
      expect(body.labels).toEqual([{ frame_number: 1, label: "progress" }]);
    });
  });

  // ---------------------------------------------------------------------------
  // After exporting, the written filenames are shown so the reviewer knows
  // which {png, json} pairs to copy into test/fixtures/images/.
  // ---------------------------------------------------------------------------

  it("shows the written sample filenames after exporting", async () => {
    const fetchMock = vi.fn((url: string) => {
      let body: unknown = {};
      if (url.includes("/api/debug/export")) {
        body = { exported: ["fail_640x360_1.png"] };
      } else if (url.includes("/api/debug/frames")) {
        body = COUNT_FRAMES;
      } else if (url.includes("/api/debug/sessions")) {
        body = { sessions: SESSIONS };
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(body) });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderPanel();

    await userEvent.click(
      await screen.findByRole("checkbox", { name: /export frame 0/i })
    );
    await userEvent.click(screen.getByRole("button", { name: /export/i }));

    await screen.findByText(/fail_640x360_1\.png/);
  });

  // ---------------------------------------------------------------------------
  // The reviewer needs to know the export fired and where the files landed, so
  // the folder path is shown after a successful export.
  // ---------------------------------------------------------------------------

  it("shows the export folder path after exporting", async () => {
    const folder = "C:/raid/debug/count/count/20260531_130000_000";
    const fetchMock = vi.fn((url: string) => {
      let body: unknown = {};
      if (url.includes("/api/debug/export")) {
        body = { exported: ["fail_640x360_1.png"], directory: folder };
      } else if (url.includes("/api/debug/frames")) {
        body = COUNT_FRAMES;
      } else if (url.includes("/api/debug/sessions")) {
        body = { sessions: SESSIONS };
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(body) });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderPanel();

    await userEvent.click(
      await screen.findByRole("checkbox", { name: /export frame 0/i })
    );
    await userEvent.click(screen.getByRole("button", { name: /export/i }));

    await screen.findByText(folder);
  });

  it("copies the export folder path to the clipboard", async () => {
    const folder = "C:/raid/debug/count/count/20260531_130000_000";
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText },
      configurable: true,
    });
    const fetchMock = vi.fn((url: string) => {
      let body: unknown = {};
      if (url.includes("/api/debug/export")) {
        body = { exported: ["fail_640x360_1.png"], directory: folder };
      } else if (url.includes("/api/debug/frames")) {
        body = COUNT_FRAMES;
      } else if (url.includes("/api/debug/sessions")) {
        body = { sessions: SESSIONS };
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(body) });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderPanel();

    await userEvent.click(
      await screen.findByRole("checkbox", { name: /export frame 0/i })
    );
    await userEvent.click(screen.getByRole("button", { name: /export/i }));
    await screen.findByText(folder);

    await userEvent.click(screen.getByRole("button", { name: /copy path/i }));
    expect(writeText).toHaveBeenCalledWith(folder);
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
