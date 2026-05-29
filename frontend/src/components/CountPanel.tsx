import { useState } from "react";
import { useJobStream } from "../hooks/useJobStream";

async function startCount(adapterIds: string[] | null): Promise<string> {
  const res = await fetch("/api/workflows/count", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ adapter_ids: adapterIds }),
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
  const stream = useJobStream(jobId);

  async function handleStart() {
    setConflict(false);
    try {
      const id = await startCount(adapterIds ?? null);
      setJobId(id);
    } catch (e) {
      if (e instanceof ConflictError) setConflict(true);
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex items-center gap-4">
        <button
          onClick={handleStart}
          disabled={stream.status === "running"}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded font-medium"
        >
          {stream.status === "running" ? "Counting…" : "Start Count"}
        </button>
        {jobId && stream.status === "running" && (
          <button
            onClick={() => { void cancelCount(jobId); }}
            className="px-4 py-2 bg-red-700 hover:bg-red-600 rounded font-medium"
          >
            Stop
          </button>
        )}
        {conflict && (
          <span className="text-yellow-400 text-sm">
            A workflow is already running
          </span>
        )}
      </div>

      {stream.status !== "idle" && (
        <div className="grid grid-cols-3 gap-4 text-sm">
          <Stat label="Fails" value={stream.failCount} />
          <Stat label="Frames" value={stream.frames} />
          <Stat label="Bar state" value={stream.barState ?? "—"} />
        </div>
      )}

      {stream.logs.length > 0 && (
        <div className="bg-gray-900 rounded p-3 font-mono text-xs space-y-0.5 max-h-48 overflow-y-auto">
          {stream.logs.map((entry, i) => (
            <div key={i} className="text-gray-300">
              <span className="text-gray-500">[{entry.level}]</span> {entry.msg}
            </div>
          ))}
        </div>
      )}

      {stream.status === "done" && stream.result && (
        <div className="border border-green-700 rounded p-3 text-sm">
          <span className="font-semibold text-green-400">Done — </span>
          <span>
            {(stream.result.fail_count as number)} fails,{" "}
            stop reason: {stream.result.stop_reason as string}
          </span>
        </div>
      )}

      {stream.status === "error" && (
        <div className="border border-red-700 rounded p-3 text-sm text-red-400">
          <span className="font-semibold">Error: </span>
          {stream.errorMessage}
        </div>
      )}
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-gray-900 rounded p-3">
      <div className="text-gray-500 text-xs uppercase tracking-wide">{label}</div>
      <div className="text-lg font-semibold">{value}</div>
    </div>
  );
}
