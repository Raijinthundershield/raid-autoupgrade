import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

interface DebugSession {
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

// A session is addressed by "{kind}/{name}", which is also its URL path under
// /api/debug/sessions/.
function sessionKey(s: DebugSession): string {
  return `${s.kind}/${s.name}`;
}

async function fetchSessions(): Promise<DebugSession[]> {
  const res = await fetch("/api/debug/sessions");
  if (!res.ok) return [];
  return (await res.json()).sessions ?? [];
}

async function fetchFrames(sessionKey: string): Promise<DebugFrame[]> {
  const res = await fetch(`/api/debug/sessions/${sessionKey}/frames`);
  if (!res.ok) return [];
  return (await res.json()).frames ?? [];
}

export function LabelPanel() {
  const { data: sessions } = useQuery({
    queryKey: ["debug-sessions"],
    queryFn: fetchSessions,
  });

  // Default to the most recent session (the backend lists them recent-first)
  // until the user explicitly picks another.
  const [picked, setPicked] = useState<string | null>(null);
  const active = picked ?? (sessions && sessions[0] ? sessionKey(sessions[0]) : null);

  const { data: frames } = useQuery({
    queryKey: ["debug-frames", active],
    queryFn: () => fetchFrames(active!),
    enabled: active != null,
  });

  if (sessions && sessions.length === 0) {
    return <p className="label-empty">No debug sessions captured yet.</p>;
  }

  return (
    <div className="flex flex-col gap-4">
      <label className="flex items-center gap-2">
        <span className="sidebar-section">Session</span>
        <select
          aria-label="Session"
          value={active ?? ""}
          onChange={(e) => setPicked(e.target.value)}
          className="bg-transparent border border-[var(--t-border)] rounded px-2 py-1 text-sm"
        >
          {(sessions ?? []).map((s) => {
            const key = sessionKey(s);
            return (
              <option key={key} value={key}>
                {s.kind} · {s.name} ({s.frame_count})
              </option>
            );
          })}
        </select>
      </label>

      <ul className="flex flex-col gap-3 list-none m-0 p-0">
        {(frames ?? []).map((f) => (
          <li
            key={f.frame_number}
            className="flex items-center gap-4 border-b border-[var(--t-border)] pb-3"
          >
            <img
              alt={`ROI for frame ${f.frame_number}`}
              src={`/api/debug/sessions/${active}/images/${f.roi_file}`}
              className="h-12"
            />
            <img
              alt={`Screenshot for frame ${f.frame_number}`}
              src={`/api/debug/sessions/${active}/images/${f.screenshot_file}`}
              className="h-24"
            />
            <span className="font-mono text-sm">{f.detected_state}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
