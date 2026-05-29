import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CalibrationBanner } from "./CalibrationBanner";

function makeFetchMock(regions: unknown, window_size_mismatch: boolean) {
  return vi.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ regions, window_size_mismatch }),
    })
  );
}

const noop = () => {};

describe("CalibrationBanner", () => {
  afterEach(() => vi.unstubAllGlobals());

  // ---------------------------------------------------------------------------
  // Cycle 1 — tracer bullet: renders when regions is null
  // ---------------------------------------------------------------------------

  it("renders when no regions are cached", async () => {
    vi.stubGlobal("fetch", makeFetchMock(null, false));
    render(<CalibrationBanner onNavigateToCalibration={noop} />);
    await screen.findByRole("alert");
  });

  // ---------------------------------------------------------------------------
  // Cycle 2 — renders when window_size_mismatch is true
  // ---------------------------------------------------------------------------

  it("renders when window size has changed", async () => {
    vi.stubGlobal(
      "fetch",
      makeFetchMock({ upgrade_bar: [0, 0, 10, 10], upgrade_button: [0, 0, 10, 10] }, true)
    );
    render(<CalibrationBanner onNavigateToCalibration={noop} />);
    await screen.findByRole("alert");
  });

  // ---------------------------------------------------------------------------
  // Cycle 3 — absent when valid regions exist and no mismatch
  // ---------------------------------------------------------------------------

  it("does not render when regions are valid", async () => {
    vi.stubGlobal(
      "fetch",
      makeFetchMock({ upgrade_bar: [0, 0, 10, 10], upgrade_button: [0, 0, 10, 10] }, false)
    );
    render(<CalibrationBanner onNavigateToCalibration={noop} />);
    // Give async fetch time to resolve
    await new Promise((r) => setTimeout(r, 20));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Cycle 4 — "Go to Calibration" button calls the prop
  // ---------------------------------------------------------------------------

  it("calls onNavigateToCalibration when the go-to button is clicked", async () => {
    vi.stubGlobal("fetch", makeFetchMock(null, false));
    const onNavigate = vi.fn();
    render(<CalibrationBanner onNavigateToCalibration={onNavigate} />);
    await userEvent.click(await screen.findByRole("button", { name: /calibrat/i }));
    expect(onNavigate).toHaveBeenCalledOnce();
  });

  // ---------------------------------------------------------------------------
  // Cycle 5 — dismiss hides the banner
  // ---------------------------------------------------------------------------

  it("hides after the dismiss button is clicked", async () => {
    vi.stubGlobal("fetch", makeFetchMock(null, false));
    render(<CalibrationBanner onNavigateToCalibration={noop} />);
    await screen.findByRole("alert");
    await userEvent.click(screen.getByRole("button", { name: /dismiss/i }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
