import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RegionPanel } from "./RegionPanel";

const CACHED_REGIONS = {
  upgrade_bar: [0, 0, 100, 20] as [number, number, number, number],
  upgrade_button: [0, 100, 50, 30] as [number, number, number, number],
};

function makeFetchMock(
  regionsPayload: { regions: typeof CACHED_REGIONS | null; window_size_mismatch: boolean }
) {
  return vi.fn((url: string) => {
    if (url.includes("/api/regions")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(regionsPayload),
      });
    }
    if (url.includes("/api/screenshot")) {
      return Promise.resolve({
        ok: true,
        blob: () => Promise.resolve(new Blob(["fake"])),
      });
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
  });
}

describe("RegionPanel", () => {
  beforeEach(() => {
    URL.createObjectURL = vi.fn(() => "blob:mock");
  });
  afterEach(() => vi.unstubAllGlobals());

  // ---------------------------------------------------------------------------
  // Cycle 1 — view mode when regions are cached
  // ---------------------------------------------------------------------------

  it("opens in view mode when regions are cached", async () => {
    vi.stubGlobal(
      "fetch",
      makeFetchMock({ regions: CACHED_REGIONS, window_size_mismatch: false })
    );

    render(<RegionPanel />);

    expect(
      await screen.findByRole("button", { name: /recalibrate/i })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /draw upgrade bar/i })
    ).not.toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Cycle 2 — draw mode when no regions cached
  // ---------------------------------------------------------------------------

  it("opens in draw mode when no regions are cached", async () => {
    vi.stubGlobal(
      "fetch",
      makeFetchMock({ regions: null, window_size_mismatch: false })
    );

    render(<RegionPanel />);

    await screen.findByRole("button", { name: /draw upgrade bar/i });
    expect(
      screen.queryByRole("button", { name: /recalibrate/i })
    ).not.toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Cycle 3 — view mode does NOT auto-fetch screenshot on mount
  // ---------------------------------------------------------------------------

  it("does not auto-fetch screenshot when opening in view mode", async () => {
    const fetchMock = makeFetchMock({ regions: CACHED_REGIONS, window_size_mismatch: false });
    vi.stubGlobal("fetch", fetchMock);

    render(<RegionPanel />);
    await screen.findByRole("button", { name: /recalibrate/i });

    const screenshotCalls = fetchMock.mock.calls.filter(([url]: [string]) =>
      url.includes("/api/screenshot")
    );
    expect(screenshotCalls).toHaveLength(0);
  });

  // ---------------------------------------------------------------------------
  // Cycle 4 — Recalibrate transitions to draw mode
  // ---------------------------------------------------------------------------

  it("Recalibrate button transitions to draw mode", async () => {
    vi.stubGlobal(
      "fetch",
      makeFetchMock({ regions: CACHED_REGIONS, window_size_mismatch: false })
    );

    render(<RegionPanel />);

    await userEvent.click(await screen.findByRole("button", { name: /recalibrate/i }));

    expect(
      screen.queryByRole("button", { name: /recalibrate/i })
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /draw upgrade bar/i })
    ).toBeInTheDocument();
  });
});
