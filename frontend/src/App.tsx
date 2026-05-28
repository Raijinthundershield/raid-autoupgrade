import { CountPanel } from "./components/CountPanel";
import { StatusHeader } from "./components/StatusHeader";

export default function App() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col">
      <StatusHeader />
      <main className="flex-1 p-6">
        <CountPanel />
      </main>
    </div>
  );
}
