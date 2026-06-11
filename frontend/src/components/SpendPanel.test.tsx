import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SpendPanel } from "./SpendPanel";
import { initialJobStreamState, type JobStreamState } from "../hooks/useJobStream";

// The Run tab owns the stream now; SpendPanel reads it from a prop. SpendPanel
// keeps two network collaborators: GET /api/settings (max-attempts prefill) and
// POST /api/workflows/spend. Tests mock at that boundary and assert on output.

function streamWith(overrides: Partial<JobStreamState> = {}): JobStreamState {
  return { ...initialJobStreamState, ...overrides };
}

function noop() {}

function stubSettings(last_count_result: { fail_count: number } | null = null) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ selected_adapters: [], last_count_result }),
    })
  );
}

describe("SpendPanel", () => {
  beforeEach(() => stubSettings());
  afterEach(() => vi.unstubAllGlobals());

  // ---------------------------------------------------------------------------
  // Reads its Spend slice from the injected stream; no Progress Bar State box.
  // ---------------------------------------------------------------------------

  it("renders Attempts used / Remaining / Upgrades from the stream's spend slice", async () => {
    render(
      <SpendPanel
        stream={streamWith({ spend: { attemptsUsed: 3, remaining: 7, upgrades: 1 } })}
        running={false}
        onStart={noop}
        onStop={noop}
      />
    );
    await waitFor(() => screen.getByLabelText(/max attempts/i));

    expect(within(screen.getByText("Attempts used").closest(".stat-card")!).getByText("3")).toBeInTheDocument();
    expect(within(screen.getByText("Remaining").closest(".stat-card")!).getByText("7")).toBeInTheDocument();
    expect(within(screen.getByText("Upgrades").closest(".stat-card")!).getByText("1")).toBeInTheDocument();
  });

  it("does not render a Progress Bar State box (it moved to the sidebar)", async () => {
    render(<SpendPanel stream={streamWith()} running={false} onStart={noop} onStop={noop} />);
    await waitFor(() => screen.getByLabelText(/max attempts/i));
    expect(screen.queryByText("Progress Bar State")).not.toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Button-first layout: the primary button precedes its options (matches Count,
  // which already leads with its button), so the two action rows line up.
  // ---------------------------------------------------------------------------

  it("renders the Start Spend button before the Max attempts input", async () => {
    render(<SpendPanel stream={streamWith()} running={false} onStart={noop} onStop={noop} />);
    await waitFor(() => screen.getByLabelText(/max attempts/i));

    const button = screen.getByRole("button", { name: /start spend/i });
    const input = screen.getByLabelText(/max attempts/i);
    expect(button.compareDocumentPosition(input) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  // ---------------------------------------------------------------------------
  // Prefill from the last Count result.
  // ---------------------------------------------------------------------------

  it("pre-fills max attempts from last_count_result.fail_count on mount", async () => {
    stubSettings({ fail_count: 7 });
    render(<SpendPanel stream={streamWith()} running={false} onStart={noop} onStop={noop} />);

    await waitFor(() => {
      const input = screen.getByLabelText(/max attempts/i) as HTMLInputElement;
      expect(input.value).toBe("7");
    });
  });

  it("fills max attempts with the fail count when a Count finishes", async () => {
    const { rerender } = render(
      <SpendPanel stream={streamWith()} running={true} onStart={noop} onStop={noop} />
    );
    await waitFor(() => {
      const input = screen.getByLabelText(/max attempts/i) as HTMLInputElement;
      expect(input.value).toBe("");
    });

    rerender(
      <SpendPanel
        stream={streamWith({ phase: "count", status: "done", result: { fail_count: 12 } })}
        running={false}
        onStart={noop}
        onStop={noop}
      />
    );

    await waitFor(() => {
      const input = screen.getByLabelText(/max attempts/i) as HTMLInputElement;
      expect(input.value).toBe("12");
    });
  });

  it("leaves max attempts empty when last_count_result is null", async () => {
    render(<SpendPanel stream={streamWith()} running={false} onStart={noop} onStop={noop} />);

    await waitFor(() => {
      const input = screen.getByLabelText(/max attempts/i) as HTMLInputElement;
      expect(input.value).toBe("");
    });
  });

  // ---------------------------------------------------------------------------
  // Network seam: Start POSTs the right body and registers the job via onStart.
  // ---------------------------------------------------------------------------

  it("POSTs max_upgrade_attempts and continue_upgrade, and reports job id via onStart", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ selected_adapters: [], last_count_result: null }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ job_id: "spend-1" }),
      });
    vi.stubGlobal("fetch", fetchMock);
    const onStart = vi.fn();

    render(<SpendPanel stream={streamWith()} running={false} onStart={onStart} onStop={noop} />);
    await waitFor(() => screen.getByLabelText(/max attempts/i));

    await userEvent.type(screen.getByLabelText(/max attempts/i), "10");
    await userEvent.click(screen.getByLabelText(/continue to a 2nd upgrade/i));
    await userEvent.click(screen.getByRole("button", { name: /start spend/i }));

    const postCall = fetchMock.mock.calls.find(
      ([url, init]) => url.includes("/api/workflows/spend") && init?.method === "POST"
    );
    expect(postCall).toBeDefined();
    const body = JSON.parse(postCall![1].body as string);
    expect(body.max_upgrade_attempts).toBe(10);
    expect(body.continue_upgrade).toBe(true);
    expect(onStart).toHaveBeenCalledWith("spend-1");
  });

  // ---------------------------------------------------------------------------
  // Shared disable: while ANY job runs, this panel's controls are disabled.
  // ---------------------------------------------------------------------------

  it("disables its controls when a job is running (even another phase's)", async () => {
    // A Count is the active phase, but the Spend panel must still be disabled.
    render(
      <SpendPanel
        stream={streamWith({ status: "running", phase: "count" })}
        running={true}
        onStart={noop}
        onStop={noop}
      />
    );
    await waitFor(() => screen.getByLabelText(/max attempts/i));

    expect(screen.getByRole("button", { name: /start spend/i })).toBeDisabled();
    expect(screen.getByLabelText(/max attempts/i)).toBeDisabled();
    expect(screen.getByLabelText(/continue to a 2nd upgrade/i)).toBeDisabled();
  });

  // ---------------------------------------------------------------------------
  // Running UI for this phase: Spending… + Stop, and Stop cancels via onStop.
  // ---------------------------------------------------------------------------

  // ---------------------------------------------------------------------------
  // Stall warning: STALLED stop reason renders a warning banner, not the
  // normal done banner and not the error banner.
  // ---------------------------------------------------------------------------

  it("shows a stall warning banner when the spend result stop_reason is stalled", async () => {
    render(
      <SpendPanel
        stream={streamWith({
          phase: "spend",
          status: "done",
          result: {
            upgrade_count: 0,
            attempt_count: 3,
            remaining_attempts: 7,
            stop_reason: "stalled",
          },
        })}
        running={false}
        onStart={noop}
        onStop={noop}
      />
    );
    await waitFor(() => screen.getByLabelText(/max attempts/i));

    expect(document.querySelector(".banner-warn")).toBeInTheDocument();
    expect(document.querySelector(".banner-ok")).not.toBeInTheDocument();
  });

  it("shows Spending… and a Stop that cancels when Spend is the running phase", async () => {
    const onStop = vi.fn();
    render(
      <SpendPanel
        stream={streamWith({ status: "running", phase: "spend" })}
        running={true}
        onStart={noop}
        onStop={onStop}
      />
    );
    await waitFor(() => screen.getByLabelText(/max attempts/i));

    expect(screen.getByRole("button", { name: /spending…/i })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /stop/i }));
    expect(onStop).toHaveBeenCalled();
  });
});
