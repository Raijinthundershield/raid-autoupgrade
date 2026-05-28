import { describe, expect, it } from "vitest";
import { jobStreamReducer, initialJobStreamState } from "./useJobStream";

// ---------------------------------------------------------------------------
// Behavior 10: progress event → updates failCount, frames, barState
// ---------------------------------------------------------------------------

describe("jobStreamReducer", () => {
  it("progress event updates failCount, frames, and barState", () => {
    const next = jobStreamReducer(initialJobStreamState, {
      type: "progress",
      fail_count: 5,
      frames: 120,
      state: "FAIL",
    });

    expect(next.failCount).toBe(5);
    expect(next.frames).toBe(120);
    expect(next.barState).toBe("FAIL");
  });

  // -------------------------------------------------------------------------
  // Behavior 11: log event appends to logs
  // -------------------------------------------------------------------------

  it("log event appends an entry to logs", () => {
    const next = jobStreamReducer(initialJobStreamState, {
      type: "log",
      level: "INFO",
      msg: "workflow started",
      ts: 1000,
    });

    expect(next.logs).toHaveLength(1);
    expect(next.logs[0]).toEqual({ level: "INFO", msg: "workflow started", ts: 1000 });
  });

  it("successive log events accumulate in order", () => {
    const s1 = jobStreamReducer(initialJobStreamState, {
      type: "log", level: "INFO", msg: "first", ts: 1,
    });
    const s2 = jobStreamReducer(s1, {
      type: "log", level: "DEBUG", msg: "second", ts: 2,
    });

    expect(s2.logs).toHaveLength(2);
    expect(s2.logs[1].msg).toBe("second");
  });

  // -------------------------------------------------------------------------
  // Behavior 12: done event → status "done", result stored
  // -------------------------------------------------------------------------

  it("done event sets status to done and stores result", () => {
    const result = { fail_count: 7, stop_reason: "max_attempts" };
    const next = jobStreamReducer(initialJobStreamState, {
      type: "done",
      result,
    });

    expect(next.status).toBe("done");
    expect(next.result).toEqual(result);
  });
});
