---
status: accepted
---

# Frontend keeps independent per-panel job streams despite a single active job

The backend `JobRegistry` enforces exactly one active job at a time (one `_active_job` slot; a second start raises `ConflictError`). The frontend, however, gives `CountPanel` and `SpendPanel` each their own `useJobStream(jobId)` and renders the phase-independent **Bar state** box once per panel rather than from a single shared stream.

We chose this deliberately. Lifting to one shared active-job stream (a Run-tab context owning the single `jobId`, with a standalone Bar state box both panels read from) is the cleaner model and matches both the backend's one-job rule and the glossary's phase-independent definition of **Progress Bar State**. But it is a refactor of how the panels own `jobId`, and the panels are otherwise independent today. We took the lower-risk path now and recorded the trade-off so a future reader doesn't mistake the dual-stream wiring for an oversight.

## Considered options

- **Lift to one shared active-job stream** — cleanest, honors the single-job invariant and the glossary, enables a truly shared Bar state box. Rejected for now: requires reworking panel ownership of `jobId`.
- **Lift only the active `barState`** — lighter, but introduces two notions of "active job" that can drift.
- **Per-panel cosmetic-shared box (chosen)** — least change; each panel renders its own Bar state box from its own stream, styled to read as one shared, phase-independent concept.

## Consequences

- The Bar state box is duplicated per panel and its "shared, phase-independent" nature is cosmetic, not structural.
- The frontend does not enforce the single-active-job invariant; it relies on the backend `ConflictError`. If we later want shared run state across the Run tab, revisit the lift-to-shared-stream option above.
