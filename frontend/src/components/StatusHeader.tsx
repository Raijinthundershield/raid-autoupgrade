import { useQuery } from "@tanstack/react-query";

interface StatusResponse {
  raid_window_detected: boolean;
  network_online: boolean;
}

async function fetchStatus(): Promise<StatusResponse> {
  const res = await fetch("/api/status");
  if (!res.ok) throw new Error("status fetch failed");
  return res.json() as Promise<StatusResponse>;
}

function StatusBadge({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <span className={ok ? "dot-online" : "dot-offline"} />
      <span
        style={{
          fontFamily: "'IBM Plex Mono', monospace",
          fontSize: "0.65rem",
          letterSpacing: "0.1em",
          textTransform: "uppercase" as const,
          color: ok ? "var(--t-text)" : "var(--t-muted)",
        }}
      >
        {label}
      </span>
    </div>
  );
}

export function StatusHeader() {
  const { data } = useQuery<StatusResponse>({
    queryKey: ["status"],
    queryFn: fetchStatus,
    refetchInterval: 2000,
  });

  return (
    <header className="app-header flex items-center justify-between px-6 py-3">
      <div className="flex items-center gap-3">
        <div
          style={{
            width: "3px",
            height: "1.4rem",
            background: "var(--t-accent)",
            borderRadius: "2px",
            boxShadow: "0 0 8px color-mix(in srgb, var(--t-accent) 50%, transparent)",
          }}
        />
        <span
          style={{
            fontFamily: "'Rajdhani', sans-serif",
            fontWeight: 700,
            fontSize: "1.1rem",
            letterSpacing: "0.22em",
            textTransform: "uppercase" as const,
            color: "oklch(0.93 0.01 285)",
          }}
        >
          Raid Autoupgrade
        </span>
      </div>

      <div className="flex items-center gap-6">
        <StatusBadge label="Raid Window" ok={data?.raid_window_detected ?? false} />
        <StatusBadge label="Network" ok={data?.network_online ?? false} />
      </div>
    </header>
  );
}
