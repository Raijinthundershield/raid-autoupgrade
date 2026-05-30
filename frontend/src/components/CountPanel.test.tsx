import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CountPanel } from "./CountPanel";

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

describe("CountPanel", () => {
  beforeEach(() => {
    sockets.length = 0;
    vi.stubGlobal("WebSocket", _WebSocketStub);
  });
  afterEach(() => vi.unstubAllGlobals());

  // ---------------------------------------------------------------------------
  // Idle: the boxes are always visible, showing 0 / 0 / — placeholders
  // ---------------------------------------------------------------------------

  it("renders Fails / Frames / Progress Bar State boxes with placeholders before any run", () => {
    render(<CountPanel adapterIds={null} />);

    const fails = screen.getByText("Fails").closest(".stat-card") as HTMLElement;
    const frames = screen.getByText("Frames").closest(".stat-card") as HTMLElement;
    const bar = screen.getByText("Progress Bar State").closest(".stat-card") as HTMLElement;

    expect(within(fails).getByText("0")).toBeInTheDocument();
    expect(within(frames).getByText("0")).toBeInTheDocument();
    expect(within(bar).getByText("—")).toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Live: progress events streaming in update Fails / Frames / Bar state
  // ---------------------------------------------------------------------------

  it("updates the boxes live as progress events stream in", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ job_id: "job-1" }),
      })
    );

    render(<CountPanel adapterIds={null} />);
    await userEvent.click(screen.getByRole("button", { name: /start count/i }));

    await waitFor(() => expect(sockets).toHaveLength(1));
    sockets[0].emit({ type: "progress", fail_count: 3, frames: 90, state: "FAIL" });

    const fails = screen.getByText("Fails").closest(".stat-card") as HTMLElement;
    const frames = screen.getByText("Frames").closest(".stat-card") as HTMLElement;
    const bar = screen.getByText("Progress Bar State").closest(".stat-card") as HTMLElement;
    expect(within(fails).getByText("3")).toBeInTheDocument();
    expect(within(frames).getByText("90")).toBeInTheDocument();
    expect(within(bar).getByText("FAIL")).toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Running-state UI: lights up the moment a run starts, before any progress
  // ---------------------------------------------------------------------------

  it("shows the running UI (Counting…, Stop, disabled debug) once a run starts", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ job_id: "job-1" }),
      })
    );

    render(<CountPanel adapterIds={null} />);
    await userEvent.click(screen.getByRole("button", { name: /start count/i }));

    // No progress event has streamed yet — the running UI is driven purely by
    // the start transition.
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /counting…/i })).toBeInTheDocument()
    );
    expect(screen.getByRole("button", { name: /stop/i })).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /debug capture/i })).toBeDisabled();
  });

  // ---------------------------------------------------------------------------
  // Reset: starting a second run clears the prior run's boxes and log lines
  // ---------------------------------------------------------------------------

  it("resets boxes to placeholders and clears logs when a new run starts", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ job_id: "job-1" }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ job_id: "job-2" }),
        })
    );

    render(<CountPanel adapterIds={null} />);

    // First run: stream some progress and a log line.
    await userEvent.click(screen.getByRole("button", { name: /start count/i }));
    await waitFor(() => expect(sockets).toHaveLength(1));
    sockets[0].emit({ type: "progress", fail_count: 4, frames: 100, state: "FAIL" });
    sockets[0].emit({ type: "log", level: "INFO", msg: "first run line", ts: 1 });
    sockets[0].emit({ type: "done", result: { fail_count: 4, stop_reason: "x" } });
    expect(screen.getByText("first run line")).toBeInTheDocument();

    // Second run begins with a fresh jobId.
    await userEvent.click(screen.getByRole("button", { name: /start count/i }));
    await waitFor(() => expect(sockets).toHaveLength(2));

    const fails = screen.getByText("Fails").closest(".stat-card") as HTMLElement;
    const frames = screen.getByText("Frames").closest(".stat-card") as HTMLElement;
    expect(within(fails).getByText("0")).toBeInTheDocument();
    expect(within(frames).getByText("0")).toBeInTheDocument();
    expect(screen.queryByText("first run line")).not.toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Behavior 8: passes selected adapters to POST /api/workflows/count
  // ---------------------------------------------------------------------------

  it("passes adapterIds prop to POST /api/workflows/count body", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ job_id: "job-1" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<CountPanel adapterIds={["1", "3"]} />);
    await userEvent.click(screen.getByRole("button", { name: /start count/i }));

    const postCall = fetchMock.mock.calls.find(
      ([url, init]) => url.includes("/api/workflows/count") && init?.method === "POST"
    );
    expect(postCall).toBeDefined();
    const body = JSON.parse(postCall![1].body as string);
    expect(body.adapter_ids).toEqual(["1", "3"]);
  });
});
