# Raid Autoupgrade

Automation tool for the airplane-mode trick in Raid: Shadow Legends — counts upgrade fails offline on a fodder gear piece, then spends those fails online to guarantee an upgrade on a target gear piece.

## Language

### Gear

**Gear Piece**: A piece of equipment that can be upgraded, either an artifact (helm, weapon, shield, gloves, boots, chestplate) or an accessory (ring, amulet, banner). Levels range from 1 to 16.
_Avoid_: artifact, item, piece

**Fodder**: A cheap gear piece used online during Spend to absorb the counted attempts. Not the intended upgrade target.
_Avoid_: counter piece, sacrifice

**Target**: The gear piece the user intends to advance one level. Counted offline during Count; receives its guaranteed upgrade after the Fodder has absorbed the attempts.
_Avoid_: goal piece, destination

### Attempts

**Attempt**: A single paid upgrade action. Each attempt either succeeds (the gear piece advances one level) or fails.
_Avoid_: roll, try, click

**Fail**: An attempt that did not advance the gear piece. Detected by the progress bar entering the Fail state.
_Avoid_: miss, failure, loss

**Success**: An attempt that advances the gear piece one level. Detected by the progress bar entering and remaining in the Standby state.
_Avoid_: upgraded, win, level-up

**Fail Count**: The number of accumulated fails to be consumed during Spend. Typically recorded by running Count, but may be known in advance from a prior session or manual counting.
_Avoid_: pity count, stack, charge

### Phases

**Count**: The phase where attempts are made on the target while offline, recording fails until a Connection Error signals session end.
_Avoid_: offline phase, farming

**Spend**: The phase where attempts are made on the fodder while online, consuming the fail count until a success is detected.
_Avoid_: online phase, upgrading

**Session**: A single end-to-end execution of the trick: Count on the target followed by Spend on the fodder. One session advances the target one level.
_Avoid_: run, operation, workflow

**Stall**: A Count or Spend that stops making progress — no new fail and no resolution within a short window — the signature of broken progress-bar detection (a persistent Unrecognized reading). On a stall the tool stops and relinquishes control to the user rather than clicking the game, because under broken detection the game state is unknown and a click could start an unintended upgrade.
_Avoid_: hang, freeze, timeout, stuck

### Network State

**Adapter**: The physical network interface the user selects to disable during Count and re-enable for Spend. A saved selection refers to the same physical adapter across sessions, regardless of how the operating system orders or re-enumerates its interfaces.
_Avoid_: NIC, network card, connection, device

**Offline**: Network state during Count — the adapter is disabled, preventing the game from reaching the server.
_Avoid_: airplane mode, network-disabled

**Online**: Network state during Spend — the adapter is enabled, allowing the game to process the success.
_Avoid_: connected, network-enabled

### Regions & Calibration

**Upgrade Screen**: The in-game gear-upgrade surface within the Raid window — the screen bearing the upgrade button and the progress bar, where Count and Spend attempts are performed. The tool clicks its button and reads its progress bar.
_Avoid_: upgrade panel, upgrade view, game window

**Region**: A cached bounding box (left, top, width, height) relative to the Raid window, identifying a UI element on the Upgrade Screen for CV detection or interaction. Two regions are tracked: the upgrade bar and the upgrade button. Regions are keyed by window size and become invalid if the window is resized.
_Avoid_: area, zone, coordinate

**Calibration**: The process of setting or verifying regions by drawing on a screenshot of the Raid window. Calibration is a prerequisite for Count and Spend but need not be repeated each session once regions are cached.
_Avoid_: setup, configuration, region selection

### Progress Bar

**Progress Bar State**: The detected state of the upgrade progress bar during an attempt — one of four recognized states, plus Unrecognized when the reading matches none of them.
_Avoid_: bar state, UI state

- **Progress** — bar is filling yellow; an attempt is underway
- **Fail** — bar flashes red; the attempt failed
- **Standby** — bar is dark/black; no active attempt. Persisting Standby signals a success in Spend, or idle state before Count begins
- **Connection Error** — offline only; the game cannot reach the server. Persisting Connection Error signals the end of Count
- **Unrecognized** — the bar reading matches none of the four above (e.g. a mis-calibrated region, an obscuring overlay, or an off-screen window). No phase logic reacts to it, so a persistent Unrecognized reading is the signature of broken detection — the condition the stall guard exists to catch.
_Avoid_: unknown (in user-facing text)
