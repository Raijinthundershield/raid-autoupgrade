import { useEffect, useState } from "react";
import { useJobStream } from "../hooks/useJobStream";
import { StatCard } from "./StatCard";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

async function startSpend(maxUpgradeAttempts: number, continueUpgrade: boolean): Promise<string> {
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
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 text-sm">
          <Label htmlFor="spend-max-attempts">Max attempts</Label>
          <Input
            id="spend-max-attempts"
            aria-label="Max attempts"
            type="number"
            min={1}
            value={maxAttempts}
            onChange={(e) => setMaxAttempts(e.target.value)}
            disabled={stream.status === "running"}
            className="w-20"
          />
        </div>

        <div className="flex items-center gap-2">
          <Checkbox
            id="spend-continue-upgrade"
            aria-label="Continue upgrade"
            checked={continueUpgrade}
            onCheckedChange={(v) => setContinueUpgrade(v === true)}
            disabled={stream.status === "running"}
          />
          <Label htmlFor="spend-continue-upgrade" className="text-sm select-none cursor-pointer">
            Continue upgrade
          </Label>
        </div>

        <Button
          onClick={handleStart}
          disabled={stream.status === "running" || !maxAttempts}
        >
          {stream.status === "running" ? "Spending…" : "Start Spend"}
        </Button>

        {jobId && stream.status === "running" && (
          <Button variant="destructive" onClick={() => { void cancelSpend(jobId); }}>
            Stop
          </Button>
        )}

        {conflict && <span className="conflict-badge">workflow already running</span>}
      </div>

      {stream.status !== "idle" && (
        <div className="flex gap-3">
          <StatCard label="Fails" value={stream.failCount} />
          <StatCard label="Frames" value={stream.frames} />
          <StatCard label="Bar state" value={stream.barState ?? "—"} />
        </div>
      )}

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
          {stream.result.upgrade_count as number} upgrade(s),{" "}
          {stream.result.attempt_count as number} attempts, stop reason: {stream.result.stop_reason as string}
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
