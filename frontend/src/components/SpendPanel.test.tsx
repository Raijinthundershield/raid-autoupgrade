import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SpendPanel } from "./SpendPanel";

class _WebSocketStub {
  addEventListener() {}
  close() {}
}

describe("SpendPanel", () => {
  beforeEach(() => vi.stubGlobal("WebSocket", _WebSocketStub));
  afterEach(() => vi.unstubAllGlobals());

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
