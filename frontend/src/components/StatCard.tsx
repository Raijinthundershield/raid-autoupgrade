// Shared presentational box used by the Run-tab panels for their per-phase
// result numbers (Count: Fails/Frames; Spend: Attempts used/Remaining/Upgrades).
// The phase-independent Progress Bar State has its own sidebar card (ADR-0002).
export function StatCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="stat-card">
      <div className="stat-val">{value}</div>
      <div className="stat-lbl">{label}</div>
    </div>
  );
}
