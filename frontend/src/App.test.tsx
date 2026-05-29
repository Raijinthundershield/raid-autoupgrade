import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

function renderApp() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  );
}

describe("App", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ raid_window_detected: false, network_online: false }),
      })
    );
  });

  afterEach(() => vi.unstubAllGlobals());

  // ---------------------------------------------------------------------------
  // Tracer bullet: StatusHeader always visible
  // ---------------------------------------------------------------------------

  it("renders the StatusHeader on load", () => {
    renderApp();
    expect(screen.getByText("AutoRaid")).toBeInTheDocument();
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
});
