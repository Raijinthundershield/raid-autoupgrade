# Architecture

Raid Autoupgrade is a Windows desktop app: a **React** frontend rendered in a native **pywebview** window, talking to an in-process **FastAPI** backend over HTTP + WebSocket. The Python side keeps the original **service-based architecture** — workflows, orchestration, and a stateless CV detection layer — with services wired explicitly at a single composition root (no DI container).

## Component Hierarchy

```
┌──────────────────────────────────────────────────────────────┐
│  Frontend (React + Vite, served in a pywebview window)         │
│  - Panels: Count / Spend / Calibration / Network              │
│  - useJobStream hook: WebSocket → live progress + logs        │
└───────────┬────────────────────────────────────────────────────┘
            │  HTTP (REST)  +  WS (/ws/workflows/{job_id})
            ▼
┌──────────────────────────────────────────────────────────────┐
│  FastAPI API layer (src/raid_autoupgrade/api/)                         │
│  - create_app(): builds app, mounts routers, error handler    │
│  - routes/: status, count, spend, regions, settings, adapters │
│  - deps.py: read services off app.state                       │
└───────────┬────────────────────────────────────────────────────┘
            │
            ▼
┌──────────────────────────────────────────────────────────────┐
│  Jobs layer (src/raid_autoupgrade/jobs/)                               │
│  - JobRegistry: one active job, queue + cancel Event per job  │
│  - run_fn factories: build a workflow run_fn, stream events   │
└───────────┬────────────────────────────────────────────────────┘
            │
            ▼
┌──────────────────────────────────────────────────────────────┐
│  Workflow Layer                                                │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐   │
│  │ CountWorkflow  │  │ SpendWorkflow  │  │ DebugMonitor   │   │
│  │  - Validation  │  │  - Validation  │  │  Workflow      │   │
│  │  - Stop config │  │  - Stop config │  │                │   │
│  └────────┬───────┘  └────────┬───────┘  └────────┬───────┘   │
└───────────┼──────────────────┼──────────────────┼────────────┘
            └──────────────────┼──────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                  Orchestration Layer                           │
│  ┌────────────────────────────────────────────────────────┐   │
│  │            UpgradeOrchestrator                          │   │
│  │  - Start upgrade (click button)                         │   │
│  │  - Monitor loop (screenshot + ROI extraction)           │   │
│  │  - Check stop conditions each iteration                 │   │
│  │  - Creates ProgressBarMonitor (per session)             │   │
│  │  - Coordinate monitor + DebugFrameLogger                │   │
│  │  - Network management (via NetworkContext)              │   │
│  └──────────────┬─────────────────────────────────────────┘   │
└─────────────────┼──────────────────────────────────────────────┘
    ┌─────────────┼─────────────┬──────────────┐
    ▼             ▼             ▼              ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐
│Progress  │ │  Stop    │ │  Debug   │ │ Network          │
│Bar       │ │Condition │ │  Frame   │ │ Context          │
│Monitor   │ │ Chain    │ │  Logger  │ │ (ctx manager)    │
└────┬─────┘ └──────────┘ └──────────┘ └──────────────────┘
     ▼
┌──────────────────┐
│ ProgressBar      │
│ StateDetector    │
│ (CV layer)       │
└──────────────────┘
```

## Core Components

### 1. Entry point ([../src/raid_autoupgrade/main.py](../src/raid_autoupgrade/main.py))

- A thin [Click](https://click.palletsclick.com/) launcher exposing a single command: `raid-autoupgrade gui`.
- Checks for admin rights (required for WMI adapter control) and, if missing, prompts a native UAC dialog to re-launch elevated.
- `--dev` runs against the Vite dev server (HMR); `--debug` enables verbose logging and the pywebview devtools.
- Delegates to `raid_autoupgrade.gui.server.start()`.

### 2. Composition root ([../src/raid_autoupgrade/gui/server.py](../src/raid_autoupgrade/gui/server.py))

This is the **only** place services are constructed and wired — there is no DI container.

- Instantiates the infrastructure services (`WindowInteractionService`, `ScreenshotService`, `NetworkManager`, `CacheService`, `SettingsService`, `ProgressBarStateDetector`).
- Builds the Count/Spend **runner factories** (`make_count_runner` / `make_spend_runner`) with those services.
- Calls `create_app(...)`, passing services and runners; they are stashed on `app.state` via the FastAPI lifespan.
- Runs uvicorn in a daemon thread on `127.0.0.1:8765` (configurable via `RAID_AUTOUPGRADE_API_PORT`), then opens a pywebview window.
  - **Dev mode** (`RAID_AUTOUPGRADE_DEV=1`): window points at the Vite dev server.
  - **Prod mode**: FastAPI mounts `frontend/dist/` as static files and the window points at the API.

### 3. API layer ([../src/raid_autoupgrade/api/](../src/raid_autoupgrade/api/))

- [app.py](../src/raid_autoupgrade/api/app.py): `create_app(...)` factory. Mounts routers, registers a lifespan that puts injected services/runners on `app.state`, and installs exception handlers that map domain errors to an error envelope (`{error, message, detail}`):
  - `WindowNotFoundException` → 409, `WorkflowValidationError` → 422, `NetworkAdapterError` → 502, other `RaidAutoupgradeError` → 500, unexpected → 500.
- [deps.py](../src/raid_autoupgrade/api/deps.py): FastAPI `Depends` providers that read services/runners off `app.state` (e.g. `get_job_registry`, `get_count_runner`). This indirection keeps routes testable — `create_app(...)` accepts test doubles.
- [routes/](../src/raid_autoupgrade/api/routes/): one router per concern.

| Route | Method(s) | Purpose |
|-------|-----------|---------|
| `/api/status` | GET | Raid window presence + size, region/network state |
| `/api/workflows/count` | POST | Start a Count job → `{job_id}` |
| `/api/workflows/spend` | POST | Start a Spend job → `{job_id}` |
| `/api/workflows/{job_id}` | GET | Poll job status + result |
| `/api/workflows/{job_id}/cancel` | POST | Cancel (204, idempotent) |
| `/ws/workflows/{job_id}` | WS | Live event stream (log / progress / done / error) |
| `/api/screenshot` | GET | Current Raid screenshot for calibration |
| `/api/regions` | GET / PUT | Read / save calibrated regions |
| `/api/settings` | GET / PUT | Selected adapters, last count result |
| `/api/adapters` | GET | List network adapters |

### 4. Jobs layer ([../src/raid_autoupgrade/jobs/](../src/raid_autoupgrade/jobs/))

Decouples long-running workflows from the request/response cycle.

- [registry.py](../src/raid_autoupgrade/jobs/registry.py) — **JobRegistry**: enforces a single active job (a second start raises `ConflictError` → HTTP 409). Each job gets a `queue.Queue` for events and a `threading.Event` for cancellation. The workflow runs on a daemon thread; on completion/error it enqueues a terminal `done`/`error` event and clears the active slot. `cancel()` is idempotent — it just sets the event.
- [run_fn.py](../src/raid_autoupgrade/jobs/run_fn.py) — **runner factories**: `make_count_runner` / `make_spend_runner` return a factory `(params) → run_fn`, where `run_fn(queue, cancel_event)` constructs the workflow, attaches a loguru sink that serializes log records onto the queue, and wires a progress callback. Count results are persisted to `SettingsService` as `last_count_result` to pre-fill the Spend panel.

Event shapes on the queue: `{type: "log", level, msg, ts}`, `{type: "progress", ...}`, `{type: "done", result}`, `{type: "error", error, message}`. The WebSocket route drains the queue and forwards each event as JSON until a terminal event.

### 5. Frontend ([../frontend/](../frontend/))

React + TypeScript + Vite, styled with Tailwind + shadcn/ui components.

- **Panels**: `CountPanel`, `SpendPanel`, `CalibrationBanner` + `RegionPanel` (region overlay / draw mode), `NetworkPanel`. Shared bits: `ProgressBarStateCard`, `StatCard`, `StatusHeader`.
- **`useJobStream` hook** ([../frontend/src/hooks/useJobStream.ts](../frontend/src/hooks/useJobStream.ts)): opens the job WebSocket and reduces the event stream into a live view (`status`, `barState`, `logs`, `result`). The Run tab shares **one** job stream across panels (see [ADR 0002](adr/0002-shared-run-stream.md)).

### 6. Workflow Layer ([../src/raid_autoupgrade/workflows/](../src/raid_autoupgrade/workflows/))

- **CountWorkflow**: counts upgrade fails offline. Validates window existence, network configuration, and cached regions; disables network adapters (if specified) during counting; returns `CountResult` with `fail_count` and `stop_reason`.
- **SpendWorkflow**: spends counted attempts online with internet verification. Supports `continue_upgrade` for level 10+ artifacts; returns `SpendResult` with `upgrade_count`, `attempt_count`, `remaining_attempts`, `stop_reason`.
- **DebugMonitorWorkflow**: monitoring workflow with frame capture for diagnostics.

### 7. Service Layer ([../src/raid_autoupgrade/services/](../src/raid_autoupgrade/services/))

- **AppData**: centralized application directory configuration (`cache_dir`, `debug_dir`).
- **CacheService**: region/screenshot caching backed by diskcache.
- **ScreenshotService**: window screenshots and ROI extraction.
- **LocateRegionService**: detects and caches UI regions (upgrade bar, button).
- **WindowInteractionService**: window existence checks, clicking, and multi-strategy activation:
  1. ALT key + SetForegroundWindow (invisible, bypasses UIPI when Raid runs admin via RSLHelper)
  2. Minimize/Restore trick (guaranteed but visually disruptive fallback)
- **SettingsService**: persists selected adapters and last count result (diskcache).
- **NetworkManager**: Windows WMI-based adapter control with automatic state waiting.

### 8. Detection Layer ([../src/raid_autoupgrade/detection/](../src/raid_autoupgrade/detection/))

- **ProgressBarStateDetector**: stateless CV layer; wraps the color-based algorithm with type-safe `ProgressBarState` output. No side effects — testable with fixture images.
- **locate_region**: automatic region detection via template matching.

### 9. Orchestration Layer ([../src/raid_autoupgrade/orchestration/](../src/raid_autoupgrade/orchestration/))

- **UpgradeOrchestrator**: coordinates an upgrade session — validates prerequisites, creates a `ProgressBarMonitor` per session, runs the monitoring loop (screenshot → ROI → monitor → stop conditions), integrates `NetworkContext`, and optionally drives `DebugFrameLogger`. Emits `ProgressEvent`s via callback.
- **ProgressBarMonitor**: stateful frame tracking (counts fail transitions, keeps the last 4 states); no stop logic; immutable snapshots. Testable with a mocked detector.
- **StopCondition classes** (Strategy): `MaxAttemptsCondition`, `MaxFramesCondition`, `UpgradedCondition` (4 consecutive STANDBY), `ConnectionErrorCondition` (4 consecutive CONNECTION_ERROR), composed by `StopConditionChain` in priority order.
- **DebugFrameLogger**: optional capture of screenshots/ROIs + metadata, with a JSON summary at session end.

### 10. Utilities & Infrastructure

- [utils/network_context.py](../src/raid_autoupgrade/utils/network_context.py) — **NetworkContext**: context manager that disables adapters on entry and re-enables on exit (exception-safe).
- [utils/admin.py](../src/raid_autoupgrade/utils/admin.py), [utils/browser_detection.py](../src/raid_autoupgrade/utils/browser_detection.py), [utils/visualization.py](../src/raid_autoupgrade/utils/visualization.py), [utils/common.py](../src/raid_autoupgrade/utils/common.py).
- [exceptions.py](../src/raid_autoupgrade/exceptions.py): domain exceptions (`RaidAutoupgradeError` base, `WindowNotFoundException`, `WorkflowValidationError`, `NetworkAdapterError`, …).
- [protocols.py](../src/raid_autoupgrade/protocols.py): `@runtime_checkable` protocols for the infrastructure services, so consumers depend on interfaces, not concretes.

## Dependency Wiring

There is **no DI container**. Construction and wiring happen exactly once, in `gui/server.py` (the composition root):

```
gui/server.py (start)
├── window_service      = WindowInteractionService()
├── screenshot_service  = ScreenshotService(window_service)
├── network_manager     = NetworkManager()
├── cache_service       = CacheService(diskcache regions)
├── settings_service    = SettingsService(diskcache settings)
├── detector            = ProgressBarStateDetector()
├── count_runner        = make_count_runner(... services ...)
├── spend_runner        = make_spend_runner(... services ...)
└── app = create_app(services + runners)   # stashed on app.state via lifespan
```

- **Infrastructure services**: constructed once and shared.
- **Application logic** (workflows, orchestrator, monitor): constructed per job inside the `run_fn`, with explicit dependencies.
- **Testability**: `create_app(...)` takes every service/runner as a parameter, so tests inject doubles directly (no patching). Routes pull them via `deps.py`.

## Key Design Patterns

- **Composition Root**: all wiring in one place (`gui/server.py`); business logic never constructs its own infrastructure.
- **Constructor Injection** against protocols (`protocols.py`).
- **Factory functions** (`make_count_runner` / `make_spend_runner`) bind services up front and yield per-job `run_fn`s.
- **Strategy Pattern**: pluggable stop conditions evaluated by `StopConditionChain`.
- **Context Manager**: `NetworkContext` guarantees adapter cleanup, even on exceptions.
- **Orchestrator Pattern**: `UpgradeOrchestrator` coordinates monitoring with validation, stop conditions, and network management.
- **Separated Concerns**: stateless detector vs. stateful monitor vs. isolated stop conditions vs. coordination layer vs. thin workflows — each independently testable.
- **Immutable State**: monitor exposes frozen dataclass snapshots.
- **Region-based Detection**: all UI interaction uses cached regions (left, top, width, height) relative to the Raid window; regions are cached **per window size** and must be re-calibrated if the window resizes.

## Progress Bar State Detection

The core algorithm in [progress_bar_detector.py](../src/raid_autoupgrade/detection/progress_bar_detector.py) uses average BGR color values to determine state:

- **fail**: Red (b<70, g<90, r>130)
- **progress**: Yellow (b<70, |r-g|<50)
- **standby**: Black (b<30, g<60, r<70)
- **connection_error**: Blue dominant (b>g, b>r, b>50)

## Upgrade Counting Flow

1. User navigates to the upgrade screen in Raid.
2. Tool disables network adapters (if specified).
3. Tool uses the calibrated UI regions (upgrade bar, button).
4. Tool clicks the upgrade button programmatically.
5. Tool monitors progress bar color changes each iteration.
6. Counts transitions to the "fail" state (red bar).
7. Stops on: max attempts reached, 4 consecutive "standby" states (upgraded), or 4 consecutive "connection_error" states.
8. Re-enables network adapters (guaranteed via `NetworkContext`).

## Project Structure

```
autoraid/
├── src/raid_autoupgrade/
│   ├── main.py                   # Click launcher (admin/UAC, raid-autoupgrade gui)
│   ├── api/
│   │   ├── app.py                # create_app() factory + error handlers
│   │   ├── deps.py               # Depends providers (read app.state)
│   │   └── routes/               # status, count, spend, regions, settings, adapters
│   ├── jobs/
│   │   ├── registry.py           # JobRegistry (single active job, cancel, queue)
│   │   └── run_fn.py             # Count/Spend runner factories
│   ├── gui/
│   │   └── server.py             # Composition root: wire services, run uvicorn + pywebview
│   ├── workflows/                # CountWorkflow, SpendWorkflow, DebugMonitorWorkflow
│   ├── orchestration/            # UpgradeOrchestrator, ProgressBarMonitor, stop_conditions, debug_frame_logger
│   ├── detection/                # ProgressBarStateDetector, locate_region (CV layer)
│   ├── services/                 # cache, screenshot, window, network, settings, app_data
│   ├── utils/                    # network_context, admin, browser_detection, visualization
│   ├── protocols.py              # service protocols
│   └── exceptions.py             # domain exceptions
├── frontend/                     # React + Vite + Tailwind/shadcn
│   ├── src/components/           # Count/Spend/Region/Network panels + shared cards
│   ├── src/hooks/useJobStream.ts # WebSocket → live progress/logs reducer
│   └── dist/                     # built assets (served by FastAPI in prod)
└── docs/adr/                     # architecture decision records
```

> **Note:** the CLI-based interface and the NiceGUI desktop GUI were removed in the React migration. The CV-classification debug-review GUI was also removed and is tracked for reimplementation in issue #2.
