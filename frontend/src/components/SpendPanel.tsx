import { useEffect, useState } from "react";
import type { JobStreamState } from "../hooks/useJobStream";
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

class ConflictError extends Error {}

interface Props {
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

export function SpendPanel({ stream, running, onStart, onStop }: Props) {
  const [conflict, setConflict] = useState(false);
  const [maxAttempts, setMaxAttempts] = useState<string>("");
  const [continueUpgrade, setContinueUpgrade] = useState(false);

  // This panel's phase is the active one only when a Spend is the running job.
  const active = stream.phase === "spend";

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

  // When a Count finishes, prefill Max attempts with its fail count so the
  // Session flows Count → Spend without retyping. Fires once per finished
  // Count (result is replaced wholesale on the done event).
  useEffect(() => {
    if (stream.phase === "count" && stream.status === "done" && stream.result) {
      const failCount = stream.result.fail_count;
      if (typeof failCount === "number") setMaxAttempts(String(failCount));
    }
  }, [stream.phase, stream.status, stream.result]);

  async function handleStart() {
    const attempts = parseInt(maxAttempts, 10);
    if (isNaN(attempts) || attempts <= 0) return;
    setConflict(false);
    try {
      const id = await startSpend(attempts, continueUpgrade);
      onStart(id);
    } catch (e) {
      if (e instanceof ConflictError) setConflict(true);
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={handleStart} disabled={running || !maxAttempts}>
          {active && running ? "Spending…" : "Start Spend"}
        </Button>

        {active && running && (
          <Button variant="destructive" onClick={onStop}>
            Stop
          </Button>
        )}

        {conflict && <span className="conflict-badge">workflow already running</span>}
      </div>

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
            disabled={running}
            className="w-20"
          />
        </div>

        <div className="flex items-center gap-2">
          <Checkbox
            id="spend-continue-upgrade"
            aria-label="Continue upgrade"
            checked={continueUpgrade}
            onCheckedChange={(v) => setContinueUpgrade(v === true)}
            disabled={running}
          />
          <Label htmlFor="spend-continue-upgrade" className="text-sm select-none cursor-pointer">
            Continue upgrade
          </Label>
        </div>
      </div>

      <div className="stat-row flex gap-3">
        <StatCard label="Attempts used" value={stream.spend.attemptsUsed} />
        <StatCard label="Remaining" value={stream.spend.remaining} />
        <StatCard label="Upgrades" value={stream.spend.upgrades} />
      </div>

      {active && stream.status === "done" && stream.result && (
        <div className="banner-ok">
          <span className="banner-ok-label">Done — </span>
          {stream.result.upgrade_count as number} upgrade(s),{" "}
          {stream.result.attempt_count as number} attempts, stop reason: {stream.result.stop_reason as string}
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
