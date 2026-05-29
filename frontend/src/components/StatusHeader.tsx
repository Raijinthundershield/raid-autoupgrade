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
          color: ok ? "oklch(0.93 0.01 285)" : "oklch(0.42 0.03 285)",
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
    <header
      className="flex items-center justify-between px-6 py-3"
      style={{
        background: "oklch(0.085 0.014 290)",
        borderBottom: "1px solid oklch(0.215 0.024 290)",
      }}
    >
      <div className="flex items-center gap-3">
        <div
          style={{
            width: "3px",
            height: "1.4rem",
            background: "oklch(0.72 0.15 68)",
            borderRadius: "2px",
            boxShadow: "0 0 8px oklch(0.72 0.15 68 / 0.5)",
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
          AutoRaid
        </span>
      </div>

      <div className="flex items-center gap-6">
        <StatusBadge label="Raid Window" ok={data?.raid_window_detected ?? false} />
        <StatusBadge label="Network" ok={data?.network_online ?? false} />
      </div>
    </header>
  );
}
