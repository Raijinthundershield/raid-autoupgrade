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

async function exportSamples(
  session: string,
  labels: { frame_number: number; label: string }[]
): Promise<string[]> {
  const res = await fetch("/api/debug/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session, labels }),
  });
  if (!res.ok) return [];
  return (await res.json()).exported ?? [];
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
  const [exported, setExported] = useState<string[]>([]);
  useEffect(() => {
    setLabels({});
    setPicks({});
    setExported([]);
  }, [active]);

  async function handleExport() {
    if (active == null) return;
    const chosen = (frames ?? [])
      .filter((f) => picks[f.frame_number])
      .map((f) => ({
        frame_number: f.frame_number,
        label: labels[f.frame_number] ?? f.detected_state,
      }));
    setExported(await exportSamples(active, chosen));
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
                value={labels[f.frame_number] ?? f.detected_state}
                onChange={(e) =>
                  setLabels((prev) => ({ ...prev, [f.frame_number]: e.target.value }))
                }
                className="bg-transparent border border-[var(--t-border)] rounded px-2 py-1 text-sm font-mono"
              >
                {LABELS.map((label) => (
                  <option key={label} value={label}>
                    {label}
                  </option>
                ))}
              </select>
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

      {exported.length > 0 && (
        <div className="text-sm">
          <p className="text-[var(--t-muted)]">
            Wrote {exported.length} sample{exported.length === 1 ? "" : "s"} into the
            session — copy the {"{png, json}"} pairs into test/fixtures/images/:
          </p>
          <ul className="font-mono list-disc list-inside">
            {exported.map((name) => (
              <li key={name}>{name}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
