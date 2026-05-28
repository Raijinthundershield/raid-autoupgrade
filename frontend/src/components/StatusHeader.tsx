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

function Indicator({ label, ok }: { label: string; ok: boolean }) {
  return (
    <span className={ok ? "text-green-400 font-semibold" : "text-red-400 font-semibold"}>
      {ok ? "●" : "●"} {label}
    </span>
  );
}

export function StatusHeader() {
  const { data } = useQuery<StatusResponse>({
    queryKey: ["status"],
    queryFn: fetchStatus,
    refetchInterval: 2000,
  });

  return (
    <header className="flex items-center justify-between px-6 py-3 bg-gray-900 border-b border-gray-800">
      <span className="font-bold text-lg tracking-wide">AutoRaid</span>
      <div className="flex gap-6">
        <Indicator label="Raid Window" ok={data?.raid_window_detected ?? false} />
        <Indicator label="Network" ok={data?.network_online ?? false} />
      </div>
    </header>
  );
}
