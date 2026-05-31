import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { StatusHeader } from "./components/StatusHeader";
import { CalibrationBanner } from "./components/CalibrationBanner";
import { CountPanel } from "./components/CountPanel";
import { SpendPanel } from "./components/SpendPanel";
import { NetworkPanel } from "./components/NetworkPanel";
import { ProgressBarStateCard } from "./components/ProgressBarStateCard";
import { RegionPanel } from "./components/RegionPanel";
import { LabelPanel } from "./components/LabelPanel";
import { useJobStream, type JobPhase } from "./hooks/useJobStream";

type Tab = "run" | "calibration" | "label";

const TAB_LABELS: Record<Tab, string> = {
  run: "Run",
  calibration: "Calibration",
  label: "Label",
};

async function fetchDebugEnabled(): Promise<boolean> {
  const res = await fetch("/api/debug/status");
  if (!res.ok) return false;
  return (await res.json()).enabled === true;
}

// Numbered phase header above a Run-tab panel (a Session reads Count → Spend).
function PhaseHeader({ num, title }: { num: string; title: string }) {
  return (
    <>
      <div className="phase-row">
        <span className="phase-num">{num}</span>
        <span className="phase-title">{title}</span>
      </div>
      <div className="phase-rule" />
    </>
  );
}

async function cancelJob(jobId: string): Promise<void> {
  await fetch(`/api/workflows/${jobId}/cancel`, { method: "POST" });
}

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>("run");
  const [adapterIds, setAdapterIds] = useState<string[]>([]);

  // The debug-only Label tab is shown only when the app was launched with
  // --debug (the backend reports it). Without it, the tab and its data are absent.
  const { data: debugEnabled } = useQuery({
    queryKey: ["debug-enabled"],
    queryFn: fetchDebugEnabled,
  });
  const tabs: Tab[] = debugEnabled ? ["run", "calibration", "label"] : ["run", "calibration"];

  // The Run tab owns the single active job and the one shared stream (ADR-0002).
  const [job, setJob] = useState<{ id: string; phase: JobPhase } | null>(null);
  const stream = useJobStream(job?.id ?? null, job?.phase ?? "count");
  const running = stream.status === "running";

  function handleStop() {
    if (job) void cancelJob(job.id);
  }

  return (
    <div className="min-h-screen flex flex-col">
      <StatusHeader />
      <nav role="tablist" className="flex border-b border-[var(--t-border)] px-6">
        {tabs.map((tab) => (
          <button
            key={tab}
            role="tab"
            aria-selected={activeTab === tab}
            onClick={() => setActiveTab(tab)}
            className={[
              "px-4 py-2 text-sm font-medium uppercase tracking-widest transition-colors",
              activeTab === tab
                ? "border-b-2 border-[var(--t-accent)] text-[var(--t-text)]"
                : "text-[var(--t-muted)] hover:text-[var(--t-text)]",
            ].join(" ")}
          >
            {TAB_LABELS[tab]}
          </button>
        ))}
      </nav>
      <main className="flex-1">
        {activeTab === "run" && (
          <div role="tabpanel" aria-label="Run" className="flex gap-6 p-6">
            <div className="flex flex-col flex-1 gap-6 min-w-0">
              <CalibrationBanner onNavigateToCalibration={() => setActiveTab("calibration")} />
              <div>
                <PhaseHeader num="01" title="Count" />
                <CountPanel
                  adapterIds={adapterIds}
                  stream={stream}
                  running={running}
                  onStart={(id) => setJob({ id, phase: "count" })}
                  onStop={handleStop}
                />
              </div>
              <div>
                <PhaseHeader num="02" title="Spend" />
                <SpendPanel
                  stream={stream}
                  running={running}
                  onStart={(id) => setJob({ id, phase: "spend" })}
                  onStop={handleStop}
                />
              </div>
            </div>
            <div className="w-64 shrink-0 flex flex-col gap-6">
              <div>
                <h3 className="sidebar-section">Network</h3>
                <NetworkPanel onSelectionChange={setAdapterIds} />
              </div>
              <ProgressBarStateCard barState={stream.barState} />
            </div>
          </div>
        )}
        {activeTab === "calibration" && (
          <div role="tabpanel" aria-label="Calibration" className="p-6 h-full">
            <RegionPanel />
          </div>
        )}
        {activeTab === "label" && (
          <div role="tabpanel" aria-label="Label" className="p-6 h-full">
            <LabelPanel />
          </div>
        )}
      </main>
    </div>
  );
}
