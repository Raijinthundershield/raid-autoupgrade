import { useState } from "react";
import { CountPanel } from "./components/CountPanel";
import { NetworkPanel } from "./components/NetworkPanel";
import { StatusHeader } from "./components/StatusHeader";

export default function App() {
  const [adapterIds, setAdapterIds] = useState<string[]>([]);

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col">
      <StatusHeader />
      <main className="flex-1 p-6 space-y-8">
        <CountPanel adapterIds={adapterIds.length > 0 ? adapterIds : null} />
        <NetworkPanel onSelectionChange={setAdapterIds} />
      </main>
    </div>
  );
}
