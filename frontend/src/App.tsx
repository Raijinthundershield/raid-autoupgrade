import { useState } from "react";
import { CountPanel } from "./components/CountPanel";
import { NetworkPanel } from "./components/NetworkPanel";
import { RegionPanel } from "./components/RegionPanel";
import { SpendPanel } from "./components/SpendPanel";
import { StatusHeader } from "./components/StatusHeader";

function Phase({ num, title, children }: { num: string; title: string; children: React.ReactNode }) {
  return (
    <section>
      <div className="phase-row">
        <span className="phase-num">{num}</span>
        <span className="phase-title">{title}</span>
      </div>
      <div className="phase-rule" />
      {children}
    </section>
  );
}

export default function App() {
  const [adapterIds, setAdapterIds] = useState<string[]>([]);

  return (
    <div className="min-h-screen flex flex-col">
      <StatusHeader />
      <main className="flex-1 px-6 py-8 space-y-10 max-w-2xl mx-auto w-full">
        <Phase num="01" title="Screen Regions">
          <RegionPanel />
        </Phase>
        <Phase num="02" title="Network Adapters">
          <NetworkPanel onSelectionChange={setAdapterIds} />
        </Phase>
        <Phase num="03" title="Count Fails">
          <CountPanel adapterIds={adapterIds.length > 0 ? adapterIds : null} />
        </Phase>
        <Phase num="04" title="Spend Attempts">
          <SpendPanel />
        </Phase>
      </main>
    </div>
  );
}
