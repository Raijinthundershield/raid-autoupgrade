import { useState } from "react";
import { useJobStream } from "../hooks/useJobStream";
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

async function cancelCount(jobId: string): Promise<void> {
  await fetch(`/api/workflows/${jobId}/cancel`, { method: "POST" });
}

class ConflictError extends Error {}

interface Props {
  adapterIds?: string[] | null;
}

export function CountPanel({ adapterIds = null }: Props) {
  const [jobId, setJobId] = useState<string | null>(null);
  const [conflict, setConflict] = useState(false);
  const [debugCapture, setDebugCapture] = useState(false);
  const stream = useJobStream(jobId);

  async function handleStart() {
    setConflict(false);
    try {
      const id = await startCount(adapterIds ?? null, debugCapture);
      setJobId(id);
    } catch (e) {
      if (e instanceof ConflictError) setConflict(true);
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={handleStart} disabled={stream.status === "running"}>
          {stream.status === "running" ? "Counting…" : "Start Count"}
        </Button>

        {jobId && stream.status === "running" && (
          <Button variant="destructive" onClick={() => { void cancelCount(jobId); }}>
            Stop
          </Button>
        )}

        <div className="flex items-center gap-2">
          <Checkbox
            id="count-debug-capture"
            checked={debugCapture}
            onCheckedChange={(v) => setDebugCapture(v === true)}
            disabled={stream.status === "running"}
          />
          <Label htmlFor="count-debug-capture" className="text-sm select-none cursor-pointer">
            Debug capture
          </Label>
        </div>

        {conflict && <span className="conflict-badge">workflow already running</span>}
      </div>

      <div className="flex gap-3">
        <StatCard label="Fails" value={stream.failCount} />
        <StatCard label="Frames" value={stream.frames} />
        <StatCard label="Progress Bar State" value={stream.barState ?? "—"} />
      </div>

      {stream.logs.length > 0 && (
        <div className="log-console">
          {stream.logs.map((entry, i) => (
            <div key={i}>
              <span className="log-level">[{entry.level}]</span>{" "}
              <span className="log-msg">{entry.msg}</span>
            </div>
          ))}
        </div>
      )}

      {stream.status === "done" && stream.result && (
        <div className="banner-ok">
          <span className="banner-ok-label">Done — </span>
          {(stream.result.fail_count as number)} fails, stop reason: {stream.result.stop_reason as string}
        </div>
      )}

      {stream.status === "error" && (
        <div className="banner-err">
          <strong>Error: </strong>{stream.errorMessage}
        </div>
      )}
    </section>
  );
}
