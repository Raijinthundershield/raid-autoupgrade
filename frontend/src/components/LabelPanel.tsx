import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

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
          {(sessions ?? []).map((s) => (
            <option key={s.id} value={s.id}>
              {s.kind} · {s.name} ({s.frame_count})
            </option>
          ))}
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
              src={imageUrl(active!, f.roi_file)}
              className="h-12"
            />
            <img
              alt={`Screenshot for frame ${f.frame_number}`}
              src={imageUrl(active!, f.screenshot_file)}
              className="h-24"
            />
            <span className="font-mono text-sm">{f.detected_state}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
