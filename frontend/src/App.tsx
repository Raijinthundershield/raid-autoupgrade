import { useState } from "react";
import { StatusHeader } from "./components/StatusHeader";
import { CalibrationBanner } from "./components/CalibrationBanner";
import { CountPanel } from "./components/CountPanel";
import { SpendPanel } from "./components/SpendPanel";
import { NetworkPanel } from "./components/NetworkPanel";
import { RegionPanel } from "./components/RegionPanel";

type Tab = "run" | "calibration";

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>("run");
  const [adapterIds, setAdapterIds] = useState<string[]>([]);

  return (
    <div className="min-h-screen flex flex-col">
      <StatusHeader />
      <nav role="tablist" className="flex border-b border-[var(--t-border)] px-6">
        {(["run", "calibration"] as Tab[]).map((tab) => (
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
            {tab === "run" ? "Run" : "Calibration"}
          </button>
        ))}
      </nav>
      <main className="flex-1">
        {activeTab === "run" && (
          <div role="tabpanel" aria-label="Run" className="flex gap-6 p-6">
            <div className="flex flex-col flex-1 gap-6 min-w-0">
              <CalibrationBanner onNavigateToCalibration={() => setActiveTab("calibration")} />
              <CountPanel adapterIds={adapterIds} />
              <SpendPanel />
            </div>
            <div className="w-64 shrink-0">
              <NetworkPanel onSelectionChange={setAdapterIds} />
            </div>
          </div>
        )}
        {activeTab === "calibration" && (
          <div role="tabpanel" aria-label="Calibration" className="p-6 h-full">
            <RegionPanel />
          </div>
        )}
      </main>
    </div>
  );
}
