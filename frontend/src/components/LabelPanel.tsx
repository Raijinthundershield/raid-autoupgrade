import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";

interface DebugSession {
  id: string;
  kind: string;
  name: string;
  frame_count: number;
}

interface DebugFrame {
  frame_number: number;
  detected_state: string;
  // The reviewer's persisted correction, if any. Absent until relabelled.
  user_label?: string | null;
  roi_file: string;
  screenshot_file: string;
}

async function fetchSessions(): Promise<DebugSession[]> {
  const res = await fetch("/api/debug/sessions");
  if (!res.ok) return [];
  return (await res.json()).sessions ?? [];
}

async function fetchFrames(sessionId: string): Promise<DebugFrame[]> {
  const res = await fetch(`/api/debug/frames?session=${encodeURIComponent(sessionId)}`);
  if (!res.ok) return [];
  return (await res.json()).frames ?? [];
}

function imageUrl(sessionId: string, file: string): string {
  return `/api/debug/image?session=${encodeURIComponent(sessionId)}&file=${encodeURIComponent(file)}`;
}

async function persistLabel(
  session: string,
  frame_number: number,
  label: string
): Promise<void> {
  await fetch("/api/debug/labels", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session, frame_number, label }),
  });
}

interface ExportResult {
  filenames: string[];
  directory: string | null;
}

async function exportSamples(
  session: string,
  labels: { frame_number: number; label: string }[]
): Promise<ExportResult> {
  const res = await fetch("/api/debug/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session, labels }),
  });
  if (!res.ok) return { filenames: [], directory: null };
  const data = await res.json();
  return { filenames: data.exported ?? [], directory: data.directory ?? null };
}

// The labels a reviewer can assign: the four real states plus `unknown` and
// `skip` (a deliberately-ambiguous frame, kept but not asserted by the detector
// test).
const LABELS = ["fail", "progress", "standby", "connection_error", "unknown", "skip"];

export function LabelPanel() {
  const { data: sessions } = useQuery({
    queryKey: ["debug-sessions"],
    queryFn: fetchSessions,
  });

  // Default to the most recent session (the backend lists them recent-first)
  // until the user explicitly picks another.
  const [picked, setPicked] = useState<string | null>(null);
  const active = picked ?? sessions?.[0]?.id ?? null;

  const { data: frames } = useQuery({
    queryKey: ["debug-frames", active],
    queryFn: () => fetchFrames(active!),
    enabled: active != null,
  });

  // Per-frame label overrides; a frame with no override keeps the detector's
  // guess. `picks` is the set of frames ticked for export — off by default, so
  // the reviewer opts each keeper in. Both reset when the session changes.
  const [labels, setLabels] = useState<Record<number, string>>({});
  const [picks, setPicks] = useState<Record<number, boolean>>({});
  const [result, setResult] = useState<ExportResult | null>(null);
  useEffect(() => {
    setLabels({});
    setPicks({});
    setResult(null);
  }, [active]);

  async function handleExport() {
    if (active == null) return;
    const chosen = (frames ?? [])
      .filter((f) => picks[f.frame_number])
      .map((f) => ({
        frame_number: f.frame_number,
        label: labels[f.frame_number] ?? f.user_label ?? f.detected_state,
      }));
    setResult(await exportSamples(active, chosen));
  }

  if (sessions && sessions.length === 0) {
    return <p className="label-empty">No debug sessions captured yet.</p>;
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-4">
        <label className="flex items-center gap-2">
          <span className="sidebar-section">Session</span>
          <select
            aria-label="Session"
            value={active ?? ""}
            onChange={(e) => setPicked(e.target.value)}
            className="bg-transparent border border-[var(--t-border)] rounded px-2 py-1 text-sm"
          >
            {(sessions ?? []).map((s) => (
              <option key={s.id} value={s.id}>
                {s.kind} · {s.name} ({s.frame_count})
              </option>
            ))}
          </select>
        </label>

        <button
          type="button"
          onClick={handleExport}
          className="border border-[var(--t-border)] rounded px-3 py-1 text-sm hover:bg-[var(--t-border)]"
        >
          Export
        </button>

        {result &&
          (result.directory ? (
            <span className="text-sm text-[var(--t-muted)] flex items-center gap-2">
              Wrote {result.filenames.length} sample
              {result.filenames.length === 1 ? "" : "s"} to{" "}
              <span className="font-mono text-[var(--t-text)]">{result.directory}</span>
              <button
                type="button"
                onClick={() => void navigator.clipboard?.writeText(result.directory!)}
                className="border border-[var(--t-border)] rounded px-2 py-0.5 text-xs hover:bg-[var(--t-border)]"
              >
                Copy path
              </button>
            </span>
          ) : (
            <span className="text-sm text-[var(--t-muted)]">Nothing to export.</span>
          ))}
      </div>

      <ul className="flex flex-col gap-3 list-none m-0 p-0">
        {(frames ?? []).map((f) => (
          <li
            key={f.frame_number}
            className="flex items-center gap-4 border-b border-[var(--t-border)] pb-3"
          >
            <img
              alt={`ROI for frame ${f.frame_number}`}
              src={imageUrl(active!, f.roi_file)}
              className="h-12"
            />
            <img
              alt={`Screenshot for frame ${f.frame_number}`}
              src={imageUrl(active!, f.screenshot_file)}
              className="h-24"
            />
            <div className="flex flex-col items-start gap-2">
              <select
                aria-label={`Label for frame ${f.frame_number}`}
                value={labels[f.frame_number] ?? f.user_label ?? f.detected_state}
                onChange={(e) => {
                  const value = e.target.value;
                  setLabels((prev) => ({ ...prev, [f.frame_number]: value }));
                  if (active != null) void persistLabel(active, f.frame_number, value);
                }}
                className="bg-transparent border border-[var(--t-border)] rounded px-2 py-1 text-sm font-mono"
              >
                {LABELS.map((label) => (
                  <option key={label} value={label}>
                    {label}
                  </option>
                ))}
              </select>
              <span className="text-xs text-[var(--t-muted)] font-mono">
                guess: {f.detected_state}
              </span>
              <div className="flex items-center gap-2">
                <Checkbox
                  id={`export-${f.frame_number}`}
                  aria-label={`Export frame ${f.frame_number}`}
                  checked={picks[f.frame_number] ?? false}
                  onCheckedChange={(value) =>
                    setPicks((prev) => ({ ...prev, [f.frame_number]: value === true }))
                  }
                />
                <Label
                  htmlFor={`export-${f.frame_number}`}
                  className="text-sm cursor-pointer"
                >
                  Export
                </Label>
              </div>
            </div>
          </li>
        ))}
      </ul>

      {result && result.filenames.length > 0 && (
        <div className="text-sm">
          <p className="text-[var(--t-muted)]">
            Copy the {"{png, json}"} pairs into test/fixtures/images/:
          </p>
          <ul className="font-mono list-disc list-inside">
            {result.filenames.map((name) => (
              <li key={name}>{name}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
