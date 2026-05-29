import { useEffect, useReducer } from "react";

// ---------------------------------------------------------------------------
// Event types (WS contract)
// ---------------------------------------------------------------------------

type ProgressEvent = {
  type: "progress";
  fail_count: number;
  frames: number;
  state: string;
};

type LogEvent = {
  type: "log";
  level: string;
  msg: string;
  ts: number;
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

export type JobEvent = ProgressEvent | LogEvent | DoneEvent | ErrorEvent;

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

export interface JobStreamState {
  status: "idle" | "running" | "done" | "error";
  failCount: number;
  frames: number;
  barState: string | null;
  logs: Array<{ level: string; msg: string; ts: number }>;
  result: Record<string, unknown> | null;
  errorMessage: string | null;
}

export const initialJobStreamState: JobStreamState = {
  status: "idle",
  failCount: 0,
  frames: 0,
  barState: null,
  logs: [],
  result: null,
  errorMessage: null,
};

// ---------------------------------------------------------------------------
// Pure reducer (exported so tests can call it directly)
// ---------------------------------------------------------------------------

export function jobStreamReducer(
  state: JobStreamState,
  event: JobEvent
): JobStreamState {
  switch (event.type) {
    case "progress":
      return {
        ...state,
        failCount: event.fail_count,
        frames: event.frames,
        barState: event.state,
      };
    case "log":
      return {
        ...state,
        logs: [
          ...state.logs,
          { level: event.level, msg: event.msg, ts: event.ts },
        ],
      };
    case "done":
      return { ...state, status: "done", result: event.result };
    case "error":
      return { ...state, status: "error", errorMessage: event.message };
  }
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useJobStream(jobId: string | null): JobStreamState {
  const [state, dispatch] = useReducer(jobStreamReducer, initialJobStreamState);

  useEffect(() => {
    if (!jobId) return;

    const ws = new WebSocket(`/ws/workflows/${jobId}`);

    ws.onmessage = (e: MessageEvent) => {
      const event = JSON.parse(e.data as string) as JobEvent;
      dispatch(event);
      if (event.type === "done" || event.type === "error") ws.close();
    };

    return () => {
      ws.close();
    };
  }, [jobId]);

  return state;
}
