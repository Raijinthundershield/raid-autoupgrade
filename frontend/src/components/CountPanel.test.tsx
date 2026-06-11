import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CountPanel } from "./CountPanel";
import { initialJobStreamState, type JobStreamState } from "../hooks/useJobStream";

// The Run tab owns the stream now; CountPanel reads it from a prop. These tests
// inject a stream and assert on rendered output, and exercise the panel's one
// network collaborator — POST /api/workflows/count — at its seam.

function streamWith(overrides: Partial<JobStreamState> = {}): JobStreamState {
  return { ...initialJobStreamState, ...overrides };
}

function noop() {}

afterEach(() => vi.unstubAllGlobals());

describe("CountPanel", () => {
  // ---------------------------------------------------------------------------
  // Reads its Count slice from the injected stream; no Progress Bar State box.
  // ---------------------------------------------------------------------------

  it("renders Fails / Frames from the stream's count slice", () => {
    render(
      <CountPanel
        stream={streamWith({ count: { failCount: 3, frames: 90 } })}
        running={false}
        onStart={noop}
        onStop={noop}
      />
    );

    expect(within(screen.getByText("Fails").closest(".stat-card")!).getByText("3")).toBeInTheDocument();
    expect(within(screen.getByText("Frames").closest(".stat-card")!).getByText("90")).toBeInTheDocument();
  });

  it("does not render a Progress Bar State box (it moved to the sidebar)", () => {
    render(<CountPanel stream={streamWith()} running={false} onStart={noop} onStop={noop} />);
    expect(screen.queryByText("Progress Bar State")).not.toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Network seam: Start POSTs the right body and registers the job via onStart.
  // ---------------------------------------------------------------------------

  it("POSTs selected adapters and reports the new job id via onStart", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ job_id: "job-1" }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const onStart = vi.fn();

    render(
      <CountPanel adapterIds={["1", "3"]} stream={streamWith()} running={false} onStart={onStart} onStop={noop} />
    );
    await userEvent.click(screen.getByRole("button", { name: /start count/i }));

    const postCall = fetchMock.mock.calls.find(
      ([url, init]) => url.includes("/api/workflows/count") && init?.method === "POST"
    );
    expect(postCall).toBeDefined();
    expect(JSON.parse(postCall![1].body as string).adapter_ids).toEqual(["1", "3"]);
    expect(onStart).toHaveBeenCalledWith("job-1");
  });

  // ---------------------------------------------------------------------------
  // Shared disable: while ANY job runs, this panel's controls are disabled.
  // ---------------------------------------------------------------------------

  it("disables its controls when a job is running (even another phase's)", () => {
    // A Spend is the active phase, but the Count panel must still be disabled.
    render(
      <CountPanel
        stream={streamWith({ status: "running", phase: "spend" })}
        running={true}
        onStart={noop}
        onStop={noop}
      />
    );

    expect(screen.getByRole("button", { name: /start count/i })).toBeDisabled();
  });

  // ---------------------------------------------------------------------------
  // Running UI for this phase: Counting… + Stop, and Stop cancels via onStop.
  // ---------------------------------------------------------------------------

  it("shows Counting… and a Stop that cancels when Count is the running phase", async () => {
    const onStop = vi.fn();
    render(
      <CountPanel
        stream={streamWith({ status: "running", phase: "count" })}
        running={true}
        onStart={noop}
        onStop={onStop}
      />
    );

    expect(screen.getByRole("button", { name: /counting…/i })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /stop/i }));
    expect(onStop).toHaveBeenCalled();
  });

  // ---------------------------------------------------------------------------
  // Counted-Target picture: an <img> at the endpoint whose cache-buster tracks
  // the live/committed state — bumped when a Count finishes so it refreshes to
  // the new Target. (The onError-hide branch isn't asserted: jsdom never fires
  // image load/error events, so a test there would be brittle padding.)
  // ---------------------------------------------------------------------------

  it("targets the screenshot endpoint and bumps the cache-buster after a count-done event", () => {
    const { rerender } = render(
      <CountPanel stream={streamWith()} running={false} onStart={noop} onStop={noop} />
    );

    const before = (screen.getByAltText(/counted target/i) as HTMLImageElement).getAttribute("src");
    expect(before).toContain("/api/last-count-screenshot");

    rerender(
      <CountPanel
        stream={streamWith({ phase: "count", status: "done", result: { fail_count: 5, stop_reason: "x" } })}
        running={false}
        onStart={noop}
        onStop={noop}
      />
    );

    const after = (screen.getByAltText(/counted target/i) as HTMLImageElement).getAttribute("src");
    expect(after).toContain("/api/last-count-screenshot");
    expect(after).not.toEqual(before);
  });

  // ---------------------------------------------------------------------------
  // Stall warning: STALLED stop reason renders a warning banner, not the
  // normal done banner and not the error banner.
  // ---------------------------------------------------------------------------

  it("shows a stall warning banner when the count result stop_reason is stalled", () => {
    render(
      <CountPanel
        stream={streamWith({
          phase: "count",
          status: "done",
          result: { fail_count: 5, stop_reason: "stalled" },
        })}
        running={false}
        onStart={noop}
        onStop={noop}
      />
    );

    expect(document.querySelector(".banner-warn")).toBeInTheDocument();
    expect(document.querySelector(".banner-ok")).not.toBeInTheDocument();
  });

  it("opens a lightbox with the full image when the thumbnail is clicked", async () => {
    render(<CountPanel stream={streamWith()} running={false} onStart={noop} onStop={noop} />);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await userEvent.click(screen.getByAltText(/counted target/i));

    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByRole("img")).toBeInTheDocument();
  });
});
