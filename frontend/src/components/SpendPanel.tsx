import { useEffect, useState } from "react";
import { useJobStream } from "../hooks/useJobStream";

async function startSpend(
  maxUpgradeAttempts: number,
  continueUpgrade: boolean
): Promise<string> {
  const res = await fetch("/api/workflows/spend", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      max_upgrade_attempts: maxUpgradeAttempts,
      continue_upgrade: continueUpgrade,
    }),
  });
  if (res.status === 409) throw new ConflictError();
  if (!res.ok) throw new Error("failed to start spend");
  const data = (await res.json()) as { job_id: string };
  return data.job_id;
}

async function cancelSpend(jobId: string): Promise<void> {
  await fetch(`/api/workflows/${jobId}/cancel`, { method: "POST" });
}

class ConflictError extends Error {}

export function SpendPanel() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [conflict, setConflict] = useState(false);
  const [maxAttempts, setMaxAttempts] = useState<string>("");
  const [continueUpgrade, setContinueUpgrade] = useState(false);
  const stream = useJobStream(jobId);

  useEffect(() => {
    fetch("/api/settings")
      .then((r) => r.json())
      .then((data: { last_count_result: { fail_count: number } | null }) => {
        if (data.last_count_result != null) {
          setMaxAttempts(String(data.last_count_result.fail_count));
        }
      })
      .catch(() => {});
  }, []);

  async function handleStart() {
    const attempts = parseInt(maxAttempts, 10);
    if (isNaN(attempts) || attempts <= 0) return;
    setConflict(false);
    try {
      const id = await startSpend(attempts, continueUpgrade);
      setJobId(id);
    } catch (e) {
      if (e instanceof ConflictError) setConflict(true);
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center gap-4">
        <label className="flex items-center gap-2 text-sm">
          <span>Max attempts</span>
          <input
            id="spend-max-attempts"
            aria-label="Max attempts"
            type="number"
            min={1}
            value={maxAttempts}
            onChange={(e) => setMaxAttempts(e.target.value)}
            disabled={stream.status === "running"}
            className="w-20 bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm"
          />
        </label>
        <label className="flex items-center gap-2 text-sm select-none">
          <input
            type="checkbox"
            aria-label="Continue upgrade"
            checked={continueUpgrade}
            onChange={(e) => setContinueUpgrade(e.target.checked)}
            disabled={stream.status === "running"}
            className="accent-blue-500"
          />
          Continue upgrade
        </label>
        <button
          onClick={handleStart}
          disabled={stream.status === "running" || !maxAttempts}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded font-medium"
        >
          {stream.status === "running" ? "Spending…" : "Start Spend"}
        </button>
        {jobId && stream.status === "running" && (
          <button
            onClick={() => { void cancelSpend(jobId); }}
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
            {stream.result.upgrade_count as number} upgrade(s),{" "}
            {stream.result.attempt_count as number} attempts,{" "}
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
