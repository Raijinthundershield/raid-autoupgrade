import { useState } from "react";
import type { JobStreamState } from "../hooks/useJobStream";
import { StatCard } from "./StatCard";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";

async function startCount(adapterIds: string[] | null, debug: boolean): Promise<string> {
  const res = await fetch("/api/workflows/count", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ adapter_ids: adapterIds, debug }),
  });
  if (res.status === 409) throw new ConflictError();
  if (!res.ok) throw new Error("failed to start count");
  const data = (await res.json()) as { job_id: string };
  return data.job_id;
}

class ConflictError extends Error {}

interface Props {
  adapterIds?: string[] | null;
  // The single shared run stream, owned by the Run tab (ADR-0002).
  stream: JobStreamState;
  // True while ANY job runs — disables this panel's controls even when the
  // running job is the other phase (makes the 409 path nearly unreachable).
  running: boolean;
  // Register the started job with the Run tab.
  onStart: (jobId: string) => void;
  // Cancel the active job.
  onStop: () => void;
}

export function CountPanel({ adapterIds = null, stream, running, onStart, onStop }: Props) {
  const [conflict, setConflict] = useState(false);
  const [debugCapture, setDebugCapture] = useState(false);

  // This panel's phase is the active one only when a Count is the running job.
  const active = stream.phase === "count";

  async function handleStart() {
    setConflict(false);
    try {
      const id = await startCount(adapterIds ?? null, debugCapture);
      onStart(id);
    } catch (e) {
      if (e instanceof ConflictError) setConflict(true);
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={handleStart} disabled={running}>
          {active && running ? "Counting…" : "Start Count"}
        </Button>

        {active && running && (
          <Button variant="destructive" onClick={onStop}>
            Stop
          </Button>
        )}

        <div className="flex items-center gap-2">
          <Checkbox
            id="count-debug-capture"
            checked={debugCapture}
            onCheckedChange={(v) => setDebugCapture(v === true)}
            disabled={running}
          />
          <Label htmlFor="count-debug-capture" className="text-sm select-none cursor-pointer">
            Debug capture
          </Label>
        </div>

        {conflict && <span className="conflict-badge">workflow already running</span>}
      </div>

      <div className="flex gap-3">
        <StatCard label="Fails" value={stream.count.failCount} />
        <StatCard label="Frames" value={stream.count.frames} />
      </div>

      {active && stream.logs.length > 0 && (
        <div className="log-console">
          {stream.logs.map((entry, i) => (
            <div key={i}>
              <span className="log-level">[{entry.level}]</span>{" "}
              <span className="log-msg">{entry.msg}</span>
            </div>
          ))}
        </div>
      )}

      {active && stream.status === "done" && stream.result && (
        <div className="banner-ok">
          <span className="banner-ok-label">Done — </span>
          {(stream.result.fail_count as number)} fails, stop reason: {stream.result.stop_reason as string}
        </div>
      )}

      {active && stream.status === "error" && (
        <div className="banner-err">
          <strong>Error: </strong>{stream.errorMessage}
        </div>
      )}
    </section>
  );
}
