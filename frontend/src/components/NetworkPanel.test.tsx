import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NetworkPanel } from "./NetworkPanel";

function makeFetch(responses: Record<string, unknown>) {
  return vi.fn((url: string) => {
    const key = Object.keys(responses).find((k) => url.includes(k));
    if (!key) return Promise.reject(new Error(`unmocked fetch: ${url}`));
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve(responses[key]),
    });
  });
}

const ADAPTERS = [
  { id: "1", name: "Wi-Fi", enabled: true },
  { id: "2", name: "Ethernet", enabled: false },
];
const EMPTY_SETTINGS = { selected_adapters: [], last_count_result: null };

describe("NetworkPanel", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      makeFetch({ "/api/adapters": ADAPTERS, "/api/settings": EMPTY_SETTINGS })
    );
  });

  afterEach(() => vi.unstubAllGlobals());

  // ---------------------------------------------------------------------------
  // Behavior 6: renders adapter names fetched from /api/adapters
  // ---------------------------------------------------------------------------

  it("renders adapter names fetched from the server", async () => {
    render(<NetworkPanel onSelectionChange={() => {}} />);

    await screen.findByText("Wi-Fi");
    expect(screen.getByText("Ethernet")).toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Behavior 7: checking an adapter calls PUT /api/settings with updated selection
  // ---------------------------------------------------------------------------

  it("checking an adapter calls PUT /api/settings with updated selection", async () => {
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (url.includes("/api/adapters")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(ADAPTERS) });
      }
      if (url.includes("/api/settings") && (!init || init.method !== "PUT")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(EMPTY_SETTINGS) });
      }
      if (url.includes("/api/settings") && init?.method === "PUT") {
        const body = JSON.parse(init.body as string);
        return Promise.resolve({ ok: true, json: () => Promise.resolve(body) });
      }
      return Promise.reject(new Error(`unmocked: ${url}`));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<NetworkPanel onSelectionChange={() => {}} />);
    await screen.findByText("Wi-Fi");

    const checkbox = screen.getByRole("checkbox", { name: /Wi-Fi/i });
    await userEvent.click(checkbox);

    const putCall = fetchMock.mock.calls.find(
      ([url, init]) => url.includes("/api/settings") && init?.method === "PUT"
    );
    expect(putCall).toBeDefined();
    const body = JSON.parse(putCall![1]!.body as string);
    expect(body.selected_adapters).toContain("1");
  });

  // ---------------------------------------------------------------------------
  // Behavior 8: opaque PNPDeviceID identities round-trip unchanged; the raw,
  // backslash-bearing value is never baked into a DOM id.
  // ---------------------------------------------------------------------------

  it("round-trips an opaque PNPDeviceID and keeps DOM ids free of the raw value", async () => {
    const PNP = "PCI\\VEN_8086&DEV_1539\\3&11583659&0&C8";
    const PNP_ADAPTERS = [{ id: PNP, name: "Intel Ethernet", enabled: true }];

    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (url.includes("/api/adapters")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(PNP_ADAPTERS) });
      }
      if (url.includes("/api/settings") && init?.method === "PUT") {
        const body = JSON.parse(init.body as string);
        return Promise.resolve({ ok: true, json: () => Promise.resolve(body) });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(EMPTY_SETTINGS) });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<NetworkPanel onSelectionChange={() => {}} />);

    // Readable name still labels the row.
    const checkbox = await screen.findByRole("checkbox", { name: "Intel Ethernet" });

    // The DOM id is derived from list position, not the opaque value.
    expect(checkbox.id).not.toContain("\\");

    await userEvent.click(checkbox);

    const putCall = fetchMock.mock.calls.find(
      ([url, init]) => url.includes("/api/settings") && init?.method === "PUT"
    );
    expect(putCall).toBeDefined();
    const body = JSON.parse(putCall![1]!.body as string);
    // The exact opaque id round-trips — selection is keyed on the value, not a
    // munged DOM id.
    expect(body.selected_adapters).toEqual([PNP]);
  });
});
