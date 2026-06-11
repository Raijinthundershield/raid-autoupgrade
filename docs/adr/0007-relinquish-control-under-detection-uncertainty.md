# Relinquish control under detection uncertainty

When monitoring stalls (no new fail and no resolution within ~5 s / ~20 frames,
the signature of broken progress-bar detection) or the user presses Stop, the
tool **stops without clicking the game** and hands control back to the human. It
does *not* attempt to halt the in-progress upgrade by clicking. This is in
deliberate contrast to the `MAX_ATTEMPTS_REACHED` path, which *does* click
`cancel_attempt()` to halt the game.

## Why

The upgrade button is a **state-dependent toggle**: one click starts the game's
auto-run upgrade sequence, a second click halts it. Whether a given click starts
or halts therefore depends on the current game state. On the `MAX_ATTEMPTS` path
detection is known to be working (we counted fails up to the limit), so we are
confident an auto-run is in progress and a halt-click is correct. On the
**stall** path the premise is the opposite — detection is broken, so we do *not*
know the game state. A blind click could just as easily *start* an unintended,
real, online upgrade as halt one. Under that uncertainty the safe action is to
stop touching the game. Stopping the monitor loop also ends the per-frame window
re-activation, so relinquishing control naturally returns focus to the user.

## Consequences

- A future reader will notice the asymmetry (`MAX_ATTEMPTS` halt-clicks; `STALL`
  and `MANUAL_STOP` do not) and may be tempted to "fix" it for consistency.
  Don't — making the stall path halt-click reintroduces the
  blind-click-starts-an-upgrade hazard.
- After a stall or manual stop the game may be left mid-auto-run, continuing to
  spend online attempts. This is accepted: the surfaced warning tells the user
  to check the game manually, and a human reading the screen is safer than the
  tool acting on detection it already knows is unreliable.
