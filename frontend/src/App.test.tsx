import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

// A WebSocket stub the test can drive: it records every instance so a test can
// reach in and fire onmessage as if the server streamed an event.
const sockets: _WebSocketStub[] = [];

class _WebSocketStub {
  onmessage: ((e: { data: string }) => void) | null = null;
  constructor() {
    sockets.push(this);
  }
  addEventListener() {}
  close() {}
  emit(event: unknown) {
    act(() => this.onmessage?.({ data: JSON.stringify(event) }));
  }
}

const STATUS = { raid_window_detected: false, network_online: false };
const ADAPTERS = [{ id: "1", name: "Wi-Fi", enabled: true }];
const SETTINGS = { selected_adapters: [], last_count_result: null };
const VALID_REGIONS = {
  regions: { upgrade_bar: [0, 0, 10, 10], upgrade_button: [0, 0, 10, 10] },
  window_size_mismatch: false,
};

function makeFetchMock(overrides: Record<string, unknown> = {}) {
  const responses: Record<string, unknown> = {
    "/api/status": STATUS,
    "/api/adapters": ADAPTERS,
    "/api/settings": SETTINGS,
    "/api/regions": VALID_REGIONS,
    "/api/workflows/count": { job_id: "count-job" },
    "/api/workflows/spend": { job_id: "spend-job" },
    ...overrides,
  };
  return vi.fn((url: string, _init: RequestInit) => {
    const key = Object.keys(responses).find((k) => url.includes(k));
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve(key ? responses[key] : {}),
    });
  });
}

function renderApp() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  );
}

function card(label: string): HTMLElement {
  return screen.getByText(label).closest(".stat-card") as HTMLElement;
}

describe("App", () => {
  beforeEach(() => {
    sockets.length = 0;
    vi.stubGlobal("WebSocket", _WebSocketStub);
    vi.stubGlobal("fetch", makeFetchMock());
  });

  afterEach(() => vi.unstubAllGlobals());

  // ---------------------------------------------------------------------------
  // Tracer bullet: StatusHeader always visible
  // ---------------------------------------------------------------------------

  it("renders the StatusHeader on load", () => {
    renderApp();
    expect(screen.getByText("Raid Autoupgrade")).toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Behavior: Run tab active by default
  // ---------------------------------------------------------------------------

  it("shows Run tab panel by default", () => {
    renderApp();
    expect(screen.getByRole("tabpanel", { name: "Run" })).toBeInTheDocument();
    expect(screen.queryByRole("tabpanel", { name: "Calibration" })).not.toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Behavior: Calibration tab shows calibration content
  // ---------------------------------------------------------------------------

  it("shows Calibration panel when Calibration tab is clicked", async () => {
    renderApp();
    await userEvent.click(screen.getByRole("tab", { name: "Calibration" }));
    expect(screen.getByRole("tabpanel", { name: "Calibration" })).toBeInTheDocument();
    expect(screen.queryByRole("tabpanel", { name: "Run" })).not.toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Behavior: clicking Run tab switches back
  // ---------------------------------------------------------------------------

  it("switches back to Run panel when Run tab is clicked after Calibration", async () => {
    renderApp();
    await userEvent.click(screen.getByRole("tab", { name: "Calibration" }));
    await userEvent.click(screen.getByRole("tab", { name: "Run" }));
    expect(screen.getByRole("tabpanel", { name: "Run" })).toBeInTheDocument();
    expect(screen.queryByRole("tabpanel", { name: "Calibration" })).not.toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Run tab renders both panels
  // ---------------------------------------------------------------------------

  it("Run tab shows a Start Count button", () => {
    renderApp();
    expect(screen.getByRole("button", { name: /start count/i })).toBeInTheDocument();
  });

  it("Run tab shows a Start Spend button", () => {
    renderApp();
    expect(screen.getByRole("button", { name: /start spend/i })).toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Numbered phase headers above each panel — a Session reads Count → Spend.
  // ---------------------------------------------------------------------------

  it("shows numbered phase headers 01 / Count and 02 / Spend above the panels", () => {
    renderApp();

    const count = screen.getByText("Count", { selector: ".phase-title" });
    expect(count).toBeInTheDocument();
    expect(within(count.closest(".phase-row")!).getByText("01")).toBeInTheDocument();

    const spend = screen.getByText("Spend", { selector: ".phase-title" });
    expect(spend).toBeInTheDocument();
    expect(within(spend.closest(".phase-row")!).getByText("02")).toBeInTheDocument();
  });

  it("Run tab shows adapter names from the server", async () => {
    renderApp();
    await screen.findByText("Wi-Fi");
  });

  // ---------------------------------------------------------------------------
  // Adapter selection wires from NetworkPanel to CountPanel
  // ---------------------------------------------------------------------------

  it("pre-selected adapter from settings is included in CountPanel POST body", async () => {
    const fetchMock = makeFetchMock({
      "/api/settings": { selected_adapters: ["1"], last_count_result: null },
    });
    vi.stubGlobal("fetch", fetchMock);

    renderApp();
    await screen.findByText("Wi-Fi"); // wait for NetworkPanel to load and call onSelectionChange

    await userEvent.click(screen.getByRole("button", { name: /start count/i }));

    const postCall = fetchMock.mock.calls.find(
      ([url, init]) => url.includes("/api/workflows/count") && init?.method === "POST"
    );
    expect(postCall).toBeDefined();
    const body = JSON.parse(postCall![1].body as string);
    expect(body.adapter_ids).toEqual(["1"]);
  });

  // ---------------------------------------------------------------------------
  // Calibration tab renders RegionPanel
  // ---------------------------------------------------------------------------

  it("Calibration tab renders RegionPanel in view mode when regions are cached", async () => {
    renderApp();
    await userEvent.click(screen.getByRole("tab", { name: /calibration/i }));
    await screen.findByRole("button", { name: /recalibrate/i });
  });

  // ---------------------------------------------------------------------------
  // CalibrationBanner: Count and Spend stay interactive when shown
  // ---------------------------------------------------------------------------

  it("shows calibration banner and keeps Count/Spend interactive when regions are missing", async () => {
    vi.stubGlobal(
      "fetch",
      makeFetchMock({ "/api/regions": { regions: null, window_size_mismatch: false } })
    );
    renderApp();
    await screen.findByRole("alert");
    expect(screen.getByRole("button", { name: /start count/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /start spend/i })).toBeInTheDocument();
  });

  // ===========================================================================
  // ADR-0002 — one shared run stream + shared Progress Bar State card
  // ===========================================================================

  // ---------------------------------------------------------------------------
  // Phase-tagged start: a finished Count's numbers survive into the Spend that
  // reads from them (a Session reads Count → Spend).
  // ---------------------------------------------------------------------------

  it("keeps a finished Count's Fails/Frames on screen while a Spend runs", async () => {
    renderApp();
    await screen.findByText("Wi-Fi");

    // Run a Count to completion, streaming numbers in.
    await userEvent.click(screen.getByRole("button", { name: /start count/i }));
    await waitFor(() => expect(sockets).toHaveLength(1));
    sockets[0].emit({ type: "progress", fail_count: 47, frames: 200, state: "fail" });
    sockets[0].emit({ type: "done", result: { fail_count: 47, stop_reason: "connection_error" } });
    expect(within(card("Fails")).getByText("47")).toBeInTheDocument();

    // Start a Spend; the Count's numbers must remain visible.
    await userEvent.type(screen.getByLabelText(/max attempts/i), "10");
    await userEvent.click(screen.getByRole("button", { name: /start spend/i }));
    await waitFor(() => expect(sockets).toHaveLength(2));

    expect(within(card("Fails")).getByText("47")).toBeInTheDocument();
    expect(within(card("Frames")).getByText("200")).toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Single-job invariant made visible: while any job runs, BOTH panels' controls
  // are disabled — not just the running phase's.
  // ---------------------------------------------------------------------------

  it("disables both Count and Spend controls while a job runs", async () => {
    renderApp();
    await screen.findByText("Wi-Fi");

    await userEvent.click(screen.getByRole("button", { name: /start count/i }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /counting…/i })).toBeInTheDocument()
    );

    expect(screen.getByRole("button", { name: /counting…/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /start spend/i })).toBeDisabled();
    expect(screen.getByLabelText(/max attempts/i)).toBeDisabled();
    expect(screen.getByRole("checkbox", { name: /continue to a 2nd upgrade/i })).toBeDisabled();
  });

  // ---------------------------------------------------------------------------
  // The shared Progress Bar State card lives once in the sidebar, always
  // visible, showing — when idle.
  // ---------------------------------------------------------------------------

  it("shows exactly one Progress Bar State card, idle (—) before any run", () => {
    renderApp();

    const labels = screen.getAllByText("Progress Bar State");
    expect(labels).toHaveLength(1);

    const cardEl = labels[0].closest(".pbs-card") as HTMLElement;
    expect(within(cardEl).getByText("—")).toBeInTheDocument();
    expect(within(cardEl).getByTestId("pbs-dot")).toHaveAttribute("data-state", "idle");
  });

  it("uses the full label 'Progress Bar State', not the avoided 'Bar State'", () => {
    renderApp();
    expect(screen.getByText("Progress Bar State")).toBeInTheDocument();
    expect(screen.queryByText("Bar State")).not.toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // The card reflects the live state with a state-colored dot.
  // ---------------------------------------------------------------------------

  it("reflects the live Progress Bar State and colors the dot per state", async () => {
    renderApp();
    await screen.findByText("Wi-Fi");

    await userEvent.click(screen.getByRole("button", { name: /start count/i }));
    await waitFor(() => expect(sockets).toHaveLength(1));

    const cardEl = screen.getByText("Progress Bar State").closest(".pbs-card") as HTMLElement;

    sockets[0].emit({ type: "progress", fail_count: 1, frames: 5, state: "progress" });
    expect(within(cardEl).getByText("progress")).toBeInTheDocument();
    expect(within(cardEl).getByTestId("pbs-dot")).toHaveAttribute("data-state", "progress");

    sockets[0].emit({ type: "progress", fail_count: 1, frames: 9, state: "fail" });
    expect(within(cardEl).getByText("fail")).toBeInTheDocument();
    expect(within(cardEl).getByTestId("pbs-dot")).toHaveAttribute("data-state", "fail");

    sockets[0].emit({ type: "progress", fail_count: 1, frames: 9, state: "standby" });
    expect(within(cardEl).getByTestId("pbs-dot")).toHaveAttribute("data-state", "standby");

    sockets[0].emit({ type: "progress", fail_count: 1, frames: 9, state: "connection_error" });
    expect(within(cardEl).getByTestId("pbs-dot")).toHaveAttribute("data-state", "connection_error");
  });

  // ---------------------------------------------------------------------------
  // The sidebar reads as distinct sections: a Network label above the adapters.
  // ---------------------------------------------------------------------------

  it("shows a Network section label above the adapter list", () => {
    renderApp();
    expect(screen.getByRole("heading", { name: "Network" })).toBeInTheDocument();
  });

  // ===========================================================================
  // Debug-only Label tab (#33) — gated on /api/debug/status
  // ===========================================================================

  it("does not show the Label tab when debug is disabled", async () => {
    vi.stubGlobal("fetch", makeFetchMock({ "/api/debug/status": { enabled: false } }));
    renderApp();
    await screen.findByText("Wi-Fi");
    expect(screen.queryByRole("tab", { name: /label/i })).not.toBeInTheDocument();
  });

  it("shows the Label tab when debug is enabled", async () => {
    vi.stubGlobal("fetch", makeFetchMock({ "/api/debug/status": { enabled: true } }));
    renderApp();
    await screen.findByRole("tab", { name: /label/i });
  });

  it("renders the captured session's frames when the Label tab is opened", async () => {
    // Order matters: the specific frames URL must be matched before the generic
    // /api/debug/sessions list URL.
    vi.stubGlobal(
      "fetch",
      makeFetchMock({
        "/api/debug/frames": {
          frames: [
            { frame_number: 0, detected_state: "fail", roi_file: "r.png", screenshot_file: "s.png" },
          ],
        },
        "/api/debug/sessions": {
          sessions: [{ id: "count/sess1", kind: "count", name: "sess1", frame_count: 1 }],
        },
        "/api/debug/status": { enabled: true },
      })
    );
    renderApp();

    await userEvent.click(await screen.findByRole("tab", { name: /label/i }));

    const panel = await screen.findByRole("tabpanel", { name: "Label" });
    expect(within(panel).getByText("fail")).toBeInTheDocument();
    expect(within(panel).getByAltText(/roi.*frame 0/i)).toBeInTheDocument();
  });
});
