import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CountPanel } from "./CountPanel";


class _WebSocketStub {
  addEventListener() {}
  close() {}
}

describe("CountPanel", () => {
  beforeEach(() => vi.stubGlobal("WebSocket", _WebSocketStub));
  afterEach(() => vi.unstubAllGlobals());

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
