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
  // Spend fields: a progress event carrying attempts_used / remaining /
  // upgrades stores them (Count never sends them).
  // -------------------------------------------------------------------------

  it("progress event stores attempts_used, remaining, and upgrades", () => {
    const next = jobStreamReducer(initialJobStreamState, {
      type: "progress",
      state: "FAIL",
      attempts_used: 6,
      remaining: 4,
      upgrades: 2,
    });

    expect(next.attemptsUsed).toBe(6);
    expect(next.remaining).toBe(4);
    expect(next.upgrades).toBe(2);
    expect(next.barState).toBe("FAIL");
  });

  it("progress event without spend fields leaves them at their defaults", () => {
    const next = jobStreamReducer(initialJobStreamState, {
      type: "progress",
      fail_count: 3,
      frames: 90,
      state: "FAIL",
    });

    expect(next.failCount).toBe(3);
    expect(next.attemptsUsed).toBe(0);
    expect(next.remaining).toBe(0);
    expect(next.upgrades).toBe(0);
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

  // -------------------------------------------------------------------------
  // Behavior 13: error event → status "error", errorMessage set
  // -------------------------------------------------------------------------

  it("error event sets status to error and stores errorMessage", () => {
    const next = jobStreamReducer(initialJobStreamState, {
      type: "error",
      error: "RuntimeError",
      message: "disk full",
    });

    expect(next.status).toBe("error");
    expect(next.errorMessage).toBe("disk full");
  });

  // -------------------------------------------------------------------------
  // start action: fresh running state, clears every stale stream value
  // -------------------------------------------------------------------------

  it("start action resets stale values/logs and sets status to running", () => {
    // A dirty state carrying the previous run's leftovers.
    const dirty = {
      status: "done" as const,
      failCount: 9,
      frames: 300,
      barState: "FAIL",
      logs: [{ level: "INFO", msg: "old line", ts: 1 }],
      result: { fail_count: 9 },
      errorMessage: "boom",
    };

    const next = jobStreamReducer(dirty, { type: "start" });

    expect(next.status).toBe("running");
    expect(next.failCount).toBe(0);
    expect(next.frames).toBe(0);
    expect(next.barState).toBeNull();
    expect(next.logs).toEqual([]);
    expect(next.result).toBeNull();
    expect(next.errorMessage).toBeNull();
  });
});
