import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

class _WebSocketStub {
  addEventListener() {}
  close() {}
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
    ...overrides,
  };
  return vi.fn((url: string) => {
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

describe("App", () => {
  beforeEach(() => {
    vi.stubGlobal("WebSocket", _WebSocketStub);
    vi.stubGlobal("fetch", makeFetchMock());
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

  // ---------------------------------------------------------------------------
  // Cycle 1 — Run tab renders CountPanel
  // ---------------------------------------------------------------------------

  it("Run tab shows a Start Count button", () => {
    renderApp();
    expect(screen.getByRole("button", { name: /start count/i })).toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Cycle 2 — Run tab renders SpendPanel
  // ---------------------------------------------------------------------------

  it("Run tab shows a Start Spend button", () => {
    renderApp();
    expect(screen.getByRole("button", { name: /start spend/i })).toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Cycle 3 — Run tab renders NetworkPanel sidebar
  // ---------------------------------------------------------------------------

  it("Run tab shows adapter names from the server", async () => {
    renderApp();
    await screen.findByText("Wi-Fi");
  });

  // ---------------------------------------------------------------------------
  // Cycle 4 — adapter selection wires from NetworkPanel to CountPanel
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
      ([url, init]: [string, RequestInit]) =>
        url.includes("/api/workflows/count") && init?.method === "POST"
    );
    expect(postCall).toBeDefined();
    const body = JSON.parse(postCall![1].body as string);
    expect(body.adapter_ids).toEqual(["1"]);
  });

  // ---------------------------------------------------------------------------
  // Cycle 5 — Calibration tab renders RegionPanel
  // ---------------------------------------------------------------------------

  it("Calibration tab renders RegionPanel in view mode when regions are cached", async () => {
    renderApp();

    await userEvent.click(screen.getByRole("tab", { name: /calibration/i }));

    await screen.findByRole("button", { name: /recalibrate/i });
  });

  // ---------------------------------------------------------------------------
  // Cycle 6 — CalibrationBanner: Count and Spend stay interactive when shown
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
});
