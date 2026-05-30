// Shared presentational box used by the Run-tab panels. One concept, one
// component — including the phase-independent Progress Bar State box.
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
