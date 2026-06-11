import { useEffect, useState } from "react";
import type { JobStreamState } from "../hooks/useJobStream";
import { StatCard } from "./StatCard";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";

const SCREENSHOT_ENDPOINT = "/api/last-count-screenshot";

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

  // The counted-Target picture. A cache-busting version is bumped whenever a
  // Count starts or finishes so the <img> tracks the live staging frame and
  // then the committed one. `hidden` drops the element on a 404/load failure so
  // a first-time user (no Count yet) sees nothing rather than a broken image.
  const [version, setVersion] = useState(0);
  const [hidden, setHidden] = useState(false);
  const [lightboxOpen, setLightboxOpen] = useState(false);

  // This panel's phase is the active one only when a Count is the running job.
  const active = stream.phase === "count";

  useEffect(() => {
    if (stream.phase === "count" && (stream.status === "running" || stream.status === "done")) {
      setVersion((v) => v + 1);
      setHidden(false); // a fresh Count may have produced a picture; re-attempt
    }
  }, [stream.phase, stream.status]);

  const screenshotSrc = `${SCREENSHOT_ENDPOINT}?v=${version}`;

  async function handleStart() {
    setConflict(false);
    try {
      const id = await startCount(adapterIds ?? null);
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

        {conflict && <span className="conflict-badge">workflow already running</span>}
      </div>

      <div className="stat-row flex gap-3">
        <StatCard label="Fails" value={stream.count.failCount} />
        <StatCard label="Frames" value={stream.count.frames} />
      </div>

      {/* Rendered independent of the active phase so it stays on screen while
          the user runs Spend on the Fodder, as a reference to relocate the
          Target afterwards. No caption — its place under the Count header says
          what it is. Click to enlarge for reading stats. */}
      {!hidden && (
        <button
          type="button"
          onClick={() => setLightboxOpen(true)}
          className="block w-fit rounded border border-[var(--t-border)] overflow-hidden"
        >
          <img
            src={screenshotSrc}
            alt="Counted target"
            onError={() => setHidden(true)}
            className="max-h-48 w-auto"
          />
        </button>
      )}

      <Dialog open={lightboxOpen} onOpenChange={setLightboxOpen}>
        <DialogContent className="max-w-[90vw]" aria-describedby={undefined}>
          <DialogTitle className="sr-only">Counted target</DialogTitle>
          <img src={screenshotSrc} alt="Counted target (enlarged)" className="w-full h-auto" />
        </DialogContent>
      </Dialog>

      {active && stream.status === "done" && stream.result && stream.result.stop_reason === "stalled" && (
        <div className="banner-warn">
          <span className="banner-warn-label">Stalled — </span>
          Detection stopped. The game may be mid-attempt; check it manually before continuing.
        </div>
      )}

      {active && stream.status === "done" && stream.result && stream.result.stop_reason !== "stalled" && (
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
