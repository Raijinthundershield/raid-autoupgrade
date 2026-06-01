---
status: accepted
---

# Runtime game interaction goes through an `UpgradeScreen` facade

The currency for driving the game was a raw `(window_title, region_tuple)` pair. The
single click primitive — `WindowInteractionService.click_region(title, tuple)` — is
stringly-typed and takes bare coordinates, and regions were a `dict` of tuples pulled
from the cache and threaded around (`regions["upgrade_button"]`, `regions["upgrade_bar"]`).
Consequences:

- The same window-size→regions prologue (`get_window_size` → `get_regions` → raise if
  `None`) was re-typed in all three workflows (`count`, `spend`, `debug_monitor`), and
  the orchestrator's `validate_prerequisites` re-fetched the same regions a fourth time
  just to null-check them. `debug_monitor` even omitted the `None` check, latently
  `KeyError`-ing instead of raising the friendly error.
- Two clicks land on the **same** `upgrade_button` coordinate with different intent —
  *begin* an attempt (orchestrator) and *abort* the pending attempt (Spend, at
  max-reached) — but nothing named either; callers could only ask for pixels.
- Because there was no object to ask "click the upgrade button," Spend had to hold the
  raw button coordinate itself to do its cancel-click, so a coordinate leaked back across
  the orchestrator seam.

We considered the narrower move — "let the orchestrator own region resolution" — and
**rejected it**: it relocates the lookup but leaves the raw-tuple currency and the
stringly-typed click primitive in place, so the cancel-click leak persists.

We decided to introduce **`UpgradeScreen`**, a per-run deep module representing the
in-game upgrade surface (see `CONTEXT.md`). The workflow constructs one per run and shares
the instance with the orchestrator:

- It owns the Raid window title, resolves window-size→regions **once** at construction
  (hard-raising if uncalibrated or the window is missing), and guards each click by
  re-reading the window size and raising if it drifted (preserving today's
  loud-failure-on-resize at attempt granularity).
- Its surface is **intent-named**, never coordinates: `start_attempt()`,
  `cancel_attempt()` (both click the one upgrade-button Region), and
  `capture_progress_bar() -> BarCapture{frame, roi}` (one screenshot per frame; the
  detector takes `.roi`, the debug logger takes both).
- It is a **read-only** consumer of Regions; calibration (`LocateRegionService`,
  `/api/regions`) stays the writer and is untouched, with `CacheService` as the shared
  store.

As a result the orchestrator's dependencies collapse from five to three (`UpgradeScreen`
+ `network_manager` + `detector`); it stops touching the screen directly and keeps only
NetworkContext, the `require_offline` guard, and the monitor loop. `validate_prerequisites`
is deleted (its job is now `UpgradeScreen` construction). The former `UpgradeSession`
config — which collided with the glossary's `Session` (an end-to-end Count→Spend run) and
no longer carries coordinates — is renamed `MonitorRun` (`run_upgrade_session` →
`run_monitor`).

## Consequences

- Mid-monitor-loop resizes are caught at the **next attempt boundary**, not per frame —
  identical to the prior `validate_prerequisites` granularity. A resize during a single
  monitor loop still reads stale ROI pixels until that loop ends, as before.
- The orchestrator depends on an `UpgradeScreenProtocol`, matching the repo's
  Protocol-everywhere style; orchestrator tests fake the screen instead of wiring
  window/screenshot/cache mocks and building region-bearing sessions.
- `MonitorRun` and the facade method names are implementation, not domain language, so
  they stay out of `CONTEXT.md`; only **Upgrade Screen** is added to the glossary.
