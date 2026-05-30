import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SpendPanel } from "./SpendPanel";

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

describe("SpendPanel", () => {
  beforeEach(() => {
    sockets.length = 0;
    vi.stubGlobal("WebSocket", _WebSocketStub);
  });
  afterEach(() => vi.unstubAllGlobals());

  // ---------------------------------------------------------------------------
  // Idle: the outcome boxes are always visible, showing 0 / 0 / 0 / — before run
  // ---------------------------------------------------------------------------

  it("renders Attempts used / Remaining / Upgrades / Progress Bar State boxes with placeholders before any run", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({ selected_adapters: [], last_count_result: null }),
      })
    );

    render(<SpendPanel />);
    await waitFor(() => screen.getByLabelText(/max attempts/i));

    const used = screen.getByText("Attempts used").closest(".stat-card") as HTMLElement;
    const remaining = screen.getByText("Remaining").closest(".stat-card") as HTMLElement;
    const upgrades = screen.getByText("Upgrades").closest(".stat-card") as HTMLElement;
    const bar = screen
      .getByText("Progress Bar State")
      .closest(".stat-card") as HTMLElement;

    expect(within(used).getByText("0")).toBeInTheDocument();
    expect(within(remaining).getByText("0")).toBeInTheDocument();
    expect(within(upgrades).getByText("0")).toBeInTheDocument();
    expect(within(bar).getByText("—")).toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Live: streamed progress updates Attempts used / Remaining / Upgrades / Bar
  // ---------------------------------------------------------------------------

  it("updates the outcome boxes live as progress events stream in", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({ selected_adapters: [], last_count_result: null }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ job_id: "spend-1" }),
      });
    vi.stubGlobal("fetch", fetchMock);

    render(<SpendPanel />);
    await waitFor(() => screen.getByLabelText(/max attempts/i));
    await userEvent.type(screen.getByLabelText(/max attempts/i), "10");
    await userEvent.click(screen.getByRole("button", { name: /start spend/i }));

    await waitFor(() => expect(sockets).toHaveLength(1));
    sockets[0].emit({
      type: "progress",
      attempts_used: 3,
      remaining: 7,
      upgrades: 1,
      state: "FAIL",
    });

    const used = screen.getByText("Attempts used").closest(".stat-card") as HTMLElement;
    const remaining = screen.getByText("Remaining").closest(".stat-card") as HTMLElement;
    const upgrades = screen.getByText("Upgrades").closest(".stat-card") as HTMLElement;
    const bar = screen
      .getByText("Progress Bar State")
      .closest(".stat-card") as HTMLElement;
    expect(within(used).getByText("3")).toBeInTheDocument();
    expect(within(remaining).getByText("7")).toBeInTheDocument();
    expect(within(upgrades).getByText("1")).toBeInTheDocument();
    expect(within(bar).getByText("FAIL")).toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Running-state UI: Spending…, Stop, and disabled inputs once a run starts
  // ---------------------------------------------------------------------------

  it("shows the running UI (Spending…, Stop, disabled inputs) once a run starts", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({ selected_adapters: [], last_count_result: null }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ job_id: "spend-1" }),
      });
    vi.stubGlobal("fetch", fetchMock);

    render(<SpendPanel />);
    await waitFor(() => screen.getByLabelText(/max attempts/i));
    await userEvent.type(screen.getByLabelText(/max attempts/i), "10");
    await userEvent.click(screen.getByRole("button", { name: /start spend/i }));

    // Running UI is driven purely by the start transition — no progress yet.
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /spending…/i })).toBeInTheDocument()
    );
    expect(screen.getByRole("button", { name: /stop/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/max attempts/i)).toBeDisabled();
    expect(screen.getByLabelText(/continue upgrade/i)).toBeDisabled();
  });

  // ---------------------------------------------------------------------------
  // Reset: starting a second run clears the prior run's boxes and log lines
  // ---------------------------------------------------------------------------

  it("resets boxes to placeholders and clears logs when a new run starts", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({ selected_adapters: [], last_count_result: null }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ job_id: "spend-1" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ job_id: "spend-2" }),
      });
    vi.stubGlobal("fetch", fetchMock);

    render(<SpendPanel />);
    await waitFor(() => screen.getByLabelText(/max attempts/i));
    await userEvent.type(screen.getByLabelText(/max attempts/i), "10");

    // First run: stream some progress and a log line, then finish.
    await userEvent.click(screen.getByRole("button", { name: /start spend/i }));
    await waitFor(() => expect(sockets).toHaveLength(1));
    sockets[0].emit({
      type: "progress",
      attempts_used: 5,
      remaining: 5,
      upgrades: 2,
      state: "FAIL",
    });
    sockets[0].emit({ type: "log", level: "INFO", msg: "first run line", ts: 1 });
    sockets[0].emit({
      type: "done",
      result: { upgrade_count: 2, attempt_count: 5, stop_reason: "upgraded" },
    });
    expect(screen.getByText("first run line")).toBeInTheDocument();

    // Second run begins with a fresh jobId.
    await userEvent.click(screen.getByRole("button", { name: /start spend/i }));
    await waitFor(() => expect(sockets).toHaveLength(2));

    const used = screen.getByText("Attempts used").closest(".stat-card") as HTMLElement;
    const remaining = screen.getByText("Remaining").closest(".stat-card") as HTMLElement;
    const upgrades = screen.getByText("Upgrades").closest(".stat-card") as HTMLElement;
    expect(within(used).getByText("0")).toBeInTheDocument();
    expect(within(remaining).getByText("0")).toBeInTheDocument();
    expect(within(upgrades).getByText("0")).toBeInTheDocument();
    expect(screen.queryByText("first run line")).not.toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Behavior: on mount, fetches /api/settings and pre-fills max attempts
  // ---------------------------------------------------------------------------

  it("pre-fills max attempts from last_count_result.fail_count on mount", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          selected_adapters: [],
          last_count_result: { fail_count: 7, stop_reason: "max_attempts_reached" },
        }),
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<SpendPanel />);

    await waitFor(() => {
      const input = screen.getByLabelText(/max attempts/i) as HTMLInputElement;
      expect(input.value).toBe("7");
    });
  });

  // ---------------------------------------------------------------------------
  // Behavior: when no last_count_result, max attempts input is empty or 0
  // ---------------------------------------------------------------------------

  it("leaves max attempts empty when last_count_result is null", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({ selected_adapters: [], last_count_result: null }),
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<SpendPanel />);

    await waitFor(() => {
      const input = screen.getByLabelText(/max attempts/i) as HTMLInputElement;
      expect(input.value).toBe("");
    });
  });

  // ---------------------------------------------------------------------------
  // Behavior: Start button POSTs to /api/workflows/spend with correct body
  // ---------------------------------------------------------------------------

  it("POSTs max_upgrade_attempts and continue_upgrade to /api/workflows/spend", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        // GET /api/settings
        ok: true,
        json: () =>
          Promise.resolve({ selected_adapters: [], last_count_result: null }),
      })
      .mockResolvedValueOnce({
        // POST /api/workflows/spend
        ok: true,
        json: () => Promise.resolve({ job_id: "spend-1" }),
      });
    vi.stubGlobal("fetch", fetchMock);

    render(<SpendPanel />);

    // wait for settings fetch to complete
    await waitFor(() => screen.getByLabelText(/max attempts/i));

    const input = screen.getByLabelText(/max attempts/i);
    await userEvent.clear(input);
    await userEvent.type(input, "10");

    const continueCheckbox = screen.getByLabelText(/continue upgrade/i);
    await userEvent.click(continueCheckbox);

    await userEvent.click(screen.getByRole("button", { name: /start spend/i }));

    const postCall = fetchMock.mock.calls.find(
      ([url, init]) =>
        url.includes("/api/workflows/spend") && init?.method === "POST"
    );
    expect(postCall).toBeDefined();
    const body = JSON.parse(postCall![1].body as string);
    expect(body.max_upgrade_attempts).toBe(10);
    expect(body.continue_upgrade).toBe(true);
  });
});
