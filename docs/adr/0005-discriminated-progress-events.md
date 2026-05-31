---
status: accepted
---

# Run-event shapes live in one `events` module, with discriminated per-phase progress

One run-event shape was re-described at every hop: dict literals in `jobs/run_fn.py`
(four of them) and `jobs/registry.py` (two), forwarded verbatim by the WS route, then
hand-mirrored in `frontend/src/hooks/useJobStream.ts` with `result` typed as the opaque
`Record<string, unknown>`. A renamed backend field reached the panel as `undefined →
"NaN fails"` — no build error, no test failure, no log. The single flat `progress` event
(every count/spend field optional) made it worse: the frontend could not require a
phase's fields and routed them by presence (`event.fail_count ?? state.count.failCount`),
so a missing field silently kept a stale value.

We decided to:

- Add a single backend module, `jobs/events.py` (Pydantic), as the source of truth for
  every shape that crosses to the frontend — `done`, `error`, the two progress events,
  and the `CountResultPayload` / `SpendResultPayload` carried by `done`. Producers build
  these models and `.model_dump()`; the queue/WS/threading plumbing is unchanged.
- **Split progress into discriminated events end to end**: `count_progress`
  (`fail_count`, `frames`) and `spend_progress` (`attempts_used`, `remaining`,
  `upgrades`), each carrying `state`. The reducer gains a case per event; each writes its
  own slice plus the shared `barState`. This makes the fields *required* in the TS types
  and deletes the presence-based merge.
- Guard cross-language drift with **no codegen**: a single committed fixture,
  `contract/events_contract.json`, bound three ways — Python models vs fixture (`pytest`),
  TS types vs fixture (compile-time assignment), reducer vs fixture (`vitest`). A backend
  rename triggers a chain of loud failures with no silent path.

## Relationship to ADR-0002

This **refines** [0002](0002-shared-run-stream.md); it does not reverse it. The shared
single stream, the live-part-plus-per-phase-slices reducer shape, and the one sidebar
Progress Bar State box all stand. Only 0002's sub-decision — "a single merged `progress`
type with optional fields" — is replaced by the two discriminated events above.

## Consequences

- The cross-language guarantee is **dev-time** (the contract test), not runtime: a
  backend *bug* emitting malformed data still slips, because we deliberately added no
  `zod` parser at the WS boundary. The failure this addresses is dev-time drift.
- `ErrorEvent` stays minimal (`type, error, message`) and is **not** unified with the
  HTTP error envelope (`{error, message, detail}` in `api/app.py`): different transports,
  and the frontend reads only `message` from the event and ignores the HTTP body.
- The GET-poll envelope `{job_id, status, result}` (`JobStatus`) stays in the route and
  *reuses* the result payloads from `events`; it is a status snapshot, not an event, so it
  does not move into the module.
- The dead `log` event is removed: `architecture.md`'s "loguru sink onto the queue" claim
  and the `{"type": "log"}` fixtures in `test_job_registry.py` are dropped (log-streaming
  was removed in the React migration; nothing produced or consumed it).
