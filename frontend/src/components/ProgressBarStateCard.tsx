// The phase-independent Progress Bar State, rendered once as a shared sidebar
// card (ADR-0002) rather than duplicated per panel. Always visible: shows "—"
// when idle and the live state otherwise, with a status dot colored per state.
//
// Labelled with the full canonical glossary term "Progress Bar State" — the
// glossary lists "bar state" on its Avoid list, so it must not be shortened.
//
// The dot carries the raw state on `data-state` (idle when no run is live);
// CSS colors it: progress → amber, fail → red, standby → dark,
// connection_error → dimmed red, idle → muted.
export function ProgressBarStateCard({ barState }: { barState: string | null }) {
  return (
    <div className="pbs-card">
      <div className="pbs-head">
        <span
          className="pbs-dot"
          data-state={barState ?? "idle"}
          data-testid="pbs-dot"
          aria-hidden="true"
        />
        <span className="pbs-label">Progress Bar State</span>
      </div>
      <div className="pbs-value">{barState ?? "—"}</div>
    </div>
  );
}
