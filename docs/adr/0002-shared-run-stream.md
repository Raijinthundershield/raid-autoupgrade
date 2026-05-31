---
status: accepted
---

# Run tab owns one shared job stream with per-phase result slices

> **Refined by [0005](0005-discriminated-progress-events.md).** The "single merged
> `progress` type with optional fields" decided here is replaced by two discriminated
> per-phase events (`count_progress` / `spend_progress`). Everything else below — the
> shared stream, the live-part-plus-per-phase-slices reducer, the one sidebar Progress
> Bar State box — still stands.

The Run tab now owns a single active `jobId` and one `useJobStream`, replacing
the per-panel streams of [0001](0001-per-panel-job-streams.md). `CountPanel` and
`SpendPanel` start jobs through it and read their numbers from it; the
phase-independent **Progress Bar State** box moves out of both panels into a
single shared card in the sidebar. We did this to make the box structurally
shared (not cosmetically duplicated), to honor the backend's one-active-job rule
in the UI, and because the glossary defines Progress Bar State as one
phase-independent concept.

## Considered options

- **Lift to one shared stream (chosen)** — a single source of truth for the live
  run. Matches the backend `_active_job` invariant and the glossary. Cost: the
  reducer grows from a flat shape to a live part plus per-phase slices, and the
  hook's `start` action becomes phase-tagged.
- **Read the box from whichever stream is running** — keeps two streams; the box
  reads `barState` from the running panel. Rejected: two notions of "active job"
  that can drift (the risk 0001 already named).

## Consequences

- The reducer carries a **live** part (`status`, `barState`, `logs`, `result`,
  the active job's banner) and **per-phase result slices** (`count`, `spend`). A
  phase-tagged `start` resets only the starting phase's slice, so a finished
  Count's numbers stay on screen while Spend runs (a Session reads Count→Spend).
- The single-job invariant is now visible: while any job runs, **both** phases'
  controls are disabled, making the `ConflictError` path nearly unreachable from
  the UI (the conflict badge remains only as a defensive fallback).
- The shared Progress Bar State card lives in the sidebar with a state-colored
  dot; the panels no longer render their own. Box-count asymmetry between the
  rows (Count 2, Spend 3) is now inherent to the data, not the bar-state box.
