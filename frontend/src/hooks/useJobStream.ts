import { useEffect, useReducer } from "react";

// ---------------------------------------------------------------------------
// Event types (WS contract)
// ---------------------------------------------------------------------------

type ProgressEvent = {
  type: "progress";
  state: string;
  // Count-only fields.
  fail_count?: number;
  frames?: number;
  // Spend-only outcome fields (optional; absent on Count progress).
  attempts_used?: number;
  remaining?: number;
  upgrades?: number;
};

type DoneEvent = {
  type: "done";
  result: Record<string, unknown>;
};

type ErrorEvent = {
  type: "error";
  error: string;
  message: string;
};

export type JobEvent = ProgressEvent | DoneEvent | ErrorEvent;

// The phase a job belongs to. A Session reads Count → Spend.
export type JobPhase = "count" | "spend";

// A local control action (not part of the WS wire contract): dispatched when a
// new run begins, before the socket opens, to reset stale state. It is
// phase-tagged so it resets only the starting phase's result slice.
type StartAction = { type: "start"; phase: JobPhase };

export type JobAction = JobEvent | StartAction;

// ---------------------------------------------------------------------------
// State
//
// One shared stream is the source of truth for the live run (ADR-0002). It
// splits into a *live* part (status, barState, result, errorMessage, and
// which phase is active) plus *per-phase result slices* that survive across a
// Session: a finished Count's numbers stay on screen while a Spend runs.
// ---------------------------------------------------------------------------

export interface CountSlice {
  failCount: number;
  frames: number;
}

export interface SpendSlice {
  attemptsUsed: number;
  remaining: number;
  upgrades: number;
}

export interface JobStreamState {
  // Live part — replaced wholesale on each start.
  status: "idle" | "running" | "done" | "error";
  phase: JobPhase | null;
  barState: string | null;
  result: Record<string, unknown> | null;
  errorMessage: string | null;
  // Per-phase result slices — each reset only when its own phase starts.
  count: CountSlice;
  spend: SpendSlice;
}

const initialCountSlice: CountSlice = { failCount: 0, frames: 0 };
const initialSpendSlice: SpendSlice = { attemptsUsed: 0, remaining: 0, upgrades: 0 };

export const initialJobStreamState: JobStreamState = {
  status: "idle",
  phase: null,
  barState: null,
  result: null,
  errorMessage: null,
  count: initialCountSlice,
  spend: initialSpendSlice,
};

// ---------------------------------------------------------------------------
// Pure reducer
// ---------------------------------------------------------------------------

export function jobStreamReducer(
  state: JobStreamState,
  event: JobAction
): JobStreamState {
  switch (event.type) {
    case "start":
      // Reset the live part plus only the starting phase's slice; the other
      // phase's numbers stay intact (a Session reads Count → Spend).
      return {
        ...state,
        status: "running",
        phase: event.phase,
        barState: null,
        result: null,
        errorMessage: null,
        count: event.phase === "count" ? initialCountSlice : state.count,
        spend: event.phase === "spend" ? initialSpendSlice : state.spend,
      };
    case "progress":
      // A progress event carries the fields for its phase only; fields the
      // other phase owns are absent and left at their current value.
      return {
        ...state,
        barState: event.state,
        count: {
          failCount: event.fail_count ?? state.count.failCount,
          frames: event.frames ?? state.count.frames,
        },
        spend: {
          attemptsUsed: event.attempts_used ?? state.spend.attemptsUsed,
          remaining: event.remaining ?? state.spend.remaining,
          upgrades: event.upgrades ?? state.spend.upgrades,
        },
      };
    case "done":
      return { ...state, status: "done", result: event.result };
    case "error":
      return { ...state, status: "error", errorMessage: event.message };
  }
}

// ---------------------------------------------------------------------------
// Hook
//
// The Run tab owns the single active jobId and the phase it was started in, and
// passes both here. On a new jobId the stream resets for that phase and opens
// the socket.
// ---------------------------------------------------------------------------

export function useJobStream(
  jobId: string | null,
  phase: JobPhase
): JobStreamState {
  const [state, dispatch] = useReducer(jobStreamReducer, initialJobStreamState);

  useEffect(() => {
    if (!jobId) return;

    // A new run begins: reset the live part and the starting phase's slice and
    // flip to "running" before the socket opens, so the live boxes and
    // run-in-progress UI light up immediately rather than waiting for the first
    // progress event.
    dispatch({ type: "start", phase });

    const ws = new WebSocket(`/ws/workflows/${jobId}`);

    ws.onmessage = (e: MessageEvent) => {
      const event = JSON.parse(e.data as string) as JobEvent;
      dispatch(event);
      if (event.type === "done" || event.type === "error") ws.close();
    };

    return () => {
      ws.close();
    };
  }, [jobId, phase]);

  return state;
}
