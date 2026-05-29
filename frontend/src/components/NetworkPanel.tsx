import { useEffect, useState } from "react";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";

interface Adapter {
  id: string;
  name: string;
  enabled: boolean;
}

interface Props {
  onSelectionChange: (ids: string[]) => void;
}

async function fetchAdapters(): Promise<Adapter[]> {
  const res = await fetch("/api/adapters");
  return res.json();
}

async function fetchSettings(): Promise<{ selected_adapters: string[] }> {
  const res = await fetch("/api/settings");
  return res.json();
}

async function saveSettings(selectedAdapters: string[]): Promise<void> {
  await fetch("/api/settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ selected_adapters: selectedAdapters, last_count_result: null }),
  });
}

export function NetworkPanel({ onSelectionChange }: Props) {
  const [adapters, setAdapters] = useState<Adapter[]>([]);
  const [selected, setSelected] = useState<string[]>([]);

  useEffect(() => {
    Promise.all([fetchAdapters(), fetchSettings()]).then(([adapters, settings]) => {
      setAdapters(adapters);
      setSelected(settings.selected_adapters);
      onSelectionChange(settings.selected_adapters);
    });
  }, []);

  function toggle(id: string) {
    const next = selected.includes(id)
      ? selected.filter((x) => x !== id)
      : [...selected, id];
    setSelected(next);
    onSelectionChange(next);
    saveSettings(next);
  }

  return (
    <section className="space-y-2">
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">
        Network Adapters
      </h2>
      <ul className="space-y-1">
        {adapters.map((a) => (
          <li key={a.id} className="flex items-center gap-3 text-sm">
            <Checkbox
              id={`adapter-${a.id}`}
              aria-label={a.name}
              checked={selected.includes(a.id)}
              onCheckedChange={() => toggle(a.id)}
            />
            <Label htmlFor={`adapter-${a.id}`} className="cursor-pointer">
              {a.name}
            </Label>
            <span className={`text-xs ${a.enabled ? "text-green-400" : "text-gray-500"}`}>
              {a.enabled ? "online" : "offline"}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
