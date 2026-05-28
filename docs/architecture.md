# Architecture

AutoRaid uses a **service-based architecture** with **dependency injection** to separate concerns, improve testability, and enable mocking. The architecture is organized into distinct layers with clear responsibilities.

## Component Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│             CLI/GUI Layer (Entry Points)                     │
│  - Injects infrastructure services (8 singletons)            │
│  - Constructs workflows directly with runtime parameters     │
└───────────┬──────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Workflow Layer                            │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐ │
│  │ CountWorkflow  │  │ SpendWorkflow  │  │DebugMonitor    │ │
│  │  - Validation  │  │  - Validation  │  │  Workflow      │ │
│  │  - Config stop │  │  - Config stop │  │  - Validation  │ │
│  │    conditions  │  │    conditions  │  │  - Config stop │ │
│  │  - Create orch │  │  - Create orch │  │    conditions  │ │
│  └────────┬───────┘  └────────┬───────┘  └────────┬───────┘ │
└───────────┼──────────────────┼──────────────────┼──────────┘
            │                  │                  │
            └──────────────────┼──────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  Orchestration Layer                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            UpgradeOrchestrator                       │   │
│  │  - Start upgrade (click button)                      │   │
│  │  - Monitor loop (screenshot + ROI extraction)        │   │
│  │  - Check stop conditions each iteration              │   │
│  │  - Creates ProgressBarMonitor (per session)          │   │
│  │  - Coordinate monitor + DebugFrameLogger             │   │
│  │  - Network management (via NetworkContext)           │   │
│  └──────────────┬───────────────────────────────────────┘   │
└─────────────────┼───────────────────────────────────────────┘
                  │
    ┌─────────────┼─────────────┬──────────────┐
    │             │             │              │
    ▼             ▼             ▼              ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐
│Progress  │ │  Stop    │ │  Debug   │ │ Network          │
│Bar       │ │Condition │ │  Frame   │ │ Context          │
│Monitor   │ │ Chain    │ │  Logger  │ │ (ctx manager)    │
└──────────┘ └──────────┘ └──────────┘ └──────────────────┘
     │
     ▼
┌──────────────────┐
│ ProgressBar      │
│ StateDetector    │
│ (CV layer)       │
└──────────────────┘
```

## Core Components

1. **CLI Layer** ([../src/autoraid/cli/](../src/autoraid/cli/))
   - [cli.py](../src/autoraid/cli/cli.py): Main entry point with `autoraid` command group, creates DI container
   - [upgrade_cli.py](../src/autoraid/cli/upgrade_cli.py): Thin CLI commands (<20 LOC) using @inject decorator
   - [network_cli.py](../src/autoraid/cli/network_cli.py): Commands for network adapter management
   - Uses Click for CLI framework with dependency injection via `dependency-injector`

2. **GUI Layer** ([../src/autoraid/gui/](../src/autoraid/gui/))
   - [app.py](../src/autoraid/gui/app.py): Main NiceGUI application with single-page scrollable layout
   - [components/upgrade_panel.py](../src/autoraid/gui/components/upgrade_panel.py): Count/Spend workflows with real-time updates
   - [components/region_panel.py](../src/autoraid/gui/components/region_panel.py): Region selection and status display
   - [components/network_panel.py](../src/autoraid/gui/components/network_panel.py): Network adapter management table
   - Uses NiceGUI native mode for desktop application window
   - Zero business logic duplication — all workflows use workflow factories and services via DI

3. **Workflow Layer** ([../src/autoraid/workflows/](../src/autoraid/workflows/))
   - **Workflow** (Abstract Base): Template Method pattern for validation and execution lifecycle
   - **CountWorkflow**: Counts upgrade fails offline with network adapter management
     - Validates window existence, network configuration, and cached regions before execution
     - Disables network adapters (if specified) during counting
     - Returns structured `CountResult` with `fail_count` and `stop_reason`
   - **SpendWorkflow**: Spends counted attempts online with internet verification
     - Validates window existence, internet availability, and cached regions before execution
     - Supports `continue_upgrade` mode for level 10+ artifacts
     - Returns structured `SpendResult` with `upgrade_count`, `attempt_count`, `remaining_attempts`, `stop_reason`

4. **Service Layer** ([../src/autoraid/services/](../src/autoraid/services/))
   - **AppData** (Singleton): Centralized application directory configuration
     - Manages `cache_dir` and `debug_dir` paths
     - Provides directory creation and validation
     - Single source of truth for all application directories
   - **CacheService** (Singleton): Manages region/screenshot caching with diskcache
   - **ScreenshotService** (Singleton): Captures window screenshots and extracts ROIs
   - **LocateRegionService** (Singleton): Detects and caches UI regions (upgrade bar, button)
   - **WindowInteractionService** (Singleton): Checks window existence, handles window activation and clicking
     - Multi-strategy window activation with automatic fallback:
       1. ALT key + SetForegroundWindow (invisible, bypasses UIPI restrictions)
       2. Minimize/Restore trick (guaranteed fallback, visually disruptive)
     - Solves User Interface Privilege Isolation (UIPI) issue when Raid runs with admin privileges via RSLHelper
   - **NetworkManager** (Singleton): Windows WMI-based network adapter control with automatic state waiting

5. **Detection Layer** ([../src/autoraid/detection/](../src/autoraid/detection/))
   - **ProgressBarStateDetector** (Singleton): Stateless CV layer for progress bar state detection
     - Wraps color-based algorithm with type-safe enum output
     - Validates input images and returns `ProgressBarState` enum
     - No side effects — testable with fixture images
   - **locate_region**: Automatic detection of UI regions using template matching
   - **templates/**: CV templates for region detection

6. **Orchestration Layer** ([../src/autoraid/orchestration/](../src/autoraid/orchestration/))
   - **UpgradeOrchestrator**: Coordinates upgrade monitoring sessions
     - Validates prerequisites (window existence, region cache, window size)
     - Creates `ProgressBarMonitor` internally per session
     - Manages monitoring loop (screenshot, ROI extraction, monitor, stop conditions)
     - Integrates `NetworkContext` for automatic adapter management
     - Supports optional `DebugFrameLogger` for diagnostic data capture
     - Returns immutable `UpgradeResult` with `fail_count`, `frames_processed`, `stop_reason`
   - **ProgressBarMonitor**: Stateful monitoring for progress bar without stop condition logic
     - Processes progress bar frames and counts fail state transitions
     - Maintains state history (last 4 states) in deque
     - Provides immutable state snapshots via `ProgressBarMonitorState` dataclass
     - No I/O dependencies — testable with mocked detector
   - **StopCondition classes** (Strategy Pattern): Pluggable stop condition strategies
     - `MaxAttemptsCondition`: Stop when fail count reaches threshold
     - `MaxFramesCondition`: Stop when frame count reaches threshold
     - `UpgradedCondition`: Stop on 4 consecutive STANDBY or CONNECTION_ERROR states
     - `ConnectionErrorCondition`: Stop on 4 consecutive CONNECTION_ERROR states
     - `StopConditionChain`: Evaluates conditions in priority order
   - **DebugFrameLogger**: Optional debug data capture during monitoring
     - Saves screenshots and ROIs with timestamped filenames
     - Records metadata (state, frame number, counts, colors)
     - Writes JSON summary log at end of session

7. **Utilities** ([../src/autoraid/utils/](../src/autoraid/utils/))
   - **interaction**: Low-level region selection with OpenCV GUI
   - **visualization**: Image display and annotation for debugging
   - **common**: General utilities (timestamps, etc.)
   - **NetworkContext**: Context manager for automatic network adapter lifecycle management
     - Disables adapters on entry, re-enables on exit (exception-safe)
     - Ensures adapters always re-enabled, even on exceptions

8. **Infrastructure**
   - [exceptions.py](../src/autoraid/exceptions.py): Custom exception classes (including `WorkflowValidationError`)
   - [container.py](../src/autoraid/container.py): Dependency injection container configuration

## Dependency Injection Container

```
Container (DeclarativeContainer)
│
├── Configuration
│   ├── cache_dir: str
│   └── debug: bool
│
└── Providers (Singleton - Infrastructure Only)
    ├── app_data: AppData(cache_dir, debug_enabled)
    ├── disk_cache: Cache(cache_dir)
    ├── cache_service: CacheService(disk_cache)
    ├── screenshot_service: ScreenshotService()
    ├── window_interaction_service: WindowInteractionService()
    ├── locate_region_service: LocateRegionService(cache_service, screenshot_service)
    ├── network_manager: NetworkManager()
    └── progress_bar_detector: ProgressBarStateDetector()
```

**Application Logic (Direct Construction):**
- **ProgressBarMonitor**: Created internally by `UpgradeOrchestrator` per session
- **UpgradeOrchestrator**: Created by workflows with injected services
- **CountWorkflow, SpendWorkflow, DebugMonitorWorkflow**: Created by CLI/GUI with injected services

**Wiring:** CLI modules (`autoraid.cli.upgrade_cli`, `autoraid.cli.network_cli`, `autoraid.cli.debug_cli`) and GUI modules (`autoraid.gui.components.upgrade_panel`, `autoraid.gui.components.region_panel`, `autoraid.gui.components.network_panel`) are wired to enable the `@inject` decorator for infrastructure services.

**Lifecycle:**
- **Singleton**: Infrastructure services with no per-request state (8 total)
- **Direct Construction**: Application logic (workflows, orchestrator, monitor) constructed as needed with explicit dependencies

## GUI Architecture

The GUI layer is a **thin presentation layer** that provides a native desktop interface without duplicating business logic.

**Design Principles:**
- **Zero Logic Duplication**: GUI components inject and call the same services used by CLI
- **Centralized Configuration**: GUI creates DI container with `AppData` for consistent directory management
- **Async Threading**: Blocking operations (workflows, region selection) run via `asyncio.to_thread()` to keep UI responsive
- **State Persistence**: User preferences (selected adapters, last count result) persist via `app.storage.user`
- **External OpenCV**: Region selection popups remain external windows (not embedded in GUI)
- **Real-time Updates**: Log streaming and progress updates use NiceGUI's reactive UI elements (`ui.refreshable()`, `ui.log()`)

**Component Structure:**
- **UpgradePanel** (`upgrade_panel.py`): Count and Spend workflows with real-time progress displays
  - Injects infrastructure services (cache, screenshot, window, network, detector, app_data)
  - Constructs workflows directly with injected services
  - Uses `ui.refreshable()` for live count/spent updates
  - Displays error toasts for exceptions (`WindowNotFoundException`, `WorkflowValidationError`, `NetworkAdapterError`, etc.)
  - Shared log section with color-coded streaming via loguru sink
- **RegionPanel** (`region_panel.py`): Region viewing and selection
  - Injects `LocateRegionService`, `ScreenshotService`, `CacheService`
  - "Show Regions" button opens OpenCV window with annotated screenshot
  - "Select Regions (Auto/Manual)" buttons call service methods in background threads
  - Window size monitoring with warnings if Raid window resizes
- **NetworkPanel** (`network_panel.py`): Network adapter management
  - Injects `NetworkManager` via platform layer
  - Table displays adapters with multi-select checkboxes
  - Selected adapter IDs stored in `app.storage.user['selected_adapters']`
  - Internet status indicator polls every 5 seconds

**State Management:**
- `app.storage.user['selected_adapters']`: Network adapter IDs for Count workflow
- `app.storage.user['last_count_result']`: Auto-populates Spend workflow max attempts
- Region cache uses existing diskcache (same as CLI)

**Layout:** Single-page vertical scrollable interface with three sections:
1. **Upgrade Workflows** (top): Count, Spend, Live Logs
2. **Region Management** (middle): Window size, cached regions, show/select buttons
3. **Network Adapters** (bottom): Adapter table with multi-select

## Service Responsibilities

| Service | Lifecycle | Responsibilities | Dependencies |
|---------|-----------|------------------|--------------|
| **AppData** | Singleton | Centralized directory configuration (cache_dir, debug_dir) | None |
| **CacheService** | Singleton | Region/screenshot caching | disk_cache |
| **ScreenshotService** | Singleton | Window screenshots, ROI extraction | None |
| **LocateRegionService** | Singleton | Region detection (auto + manual) | cache_service, screenshot_service |
| **WindowInteractionService** | Singleton | Window existence checking, multi-strategy activation (ALT+SetForegroundWindow → minimize trick), clicking | None |
| **NetworkManager** | Singleton | Network adapter management with automatic state waiting | None |
| **ProgressBarStateDetector** | Singleton | Progress bar state detection from images | None (stateless CV layer) |
| **ProgressBarMonitor** | Direct Construction | Frame processing, fail transition counting, state history tracking | progress_bar_detector |
| **UpgradeOrchestrator** | Direct Construction | Coordinate upgrade sessions with stop conditions, network management | screenshot_service, window_interaction_service, cache_service, network_manager, detector |
| **CountWorkflow** | Direct Construction | Count workflow with validation and orchestration | cache_service, window_interaction_service, network_manager, screenshot_service, detector |
| **SpendWorkflow** | Direct Construction | Spend workflow with validation and orchestration | cache_service, window_interaction_service, network_manager, screenshot_service, detector |
| **DebugMonitorWorkflow** | Direct Construction | Debug workflow with frame capture and orchestration | cache_service, window_interaction_service, network_manager, screenshot_service, detector |

## Key Design Patterns

- **Dependency Injection**: Constructor injection for all services, configured via `DeclarativeContainer`
- **Service Layer**: Business logic separated from CLI/I/O in testable services
- **Strategy Pattern**: Stop conditions are pluggable strategies evaluated by `StopConditionChain`
- **Context Manager Pattern**: `NetworkContext` ensures automatic network adapter cleanup (exception-safe)
- **Orchestrator Pattern**: `UpgradeOrchestrator` coordinates monitoring sessions with validation, stop conditions, and network management
- **Separated Concerns:**
  - `ProgressBarStateDetector`: Stateless CV layer, testable with fixture images
  - `ProgressBarMonitor`: Stateful frame tracking (no stop logic), testable with mocked detector
  - StopCondition classes: Isolated stop logic, independently testable
  - `UpgradeOrchestrator`: Coordination layer, testable with mocked services
  - Workflows: Thin configuration layers, testable with mocked orchestrator
- **Composition Over Inheritance**: Workflows compose orchestrator instead of inheriting from base class
- **Immutable State**: Monitor provides frozen dataclass snapshots (`ProgressBarMonitorState`)
- **Direct Construction**: Workflows, orchestrator, and monitor constructed directly with explicit dependencies (no factory pattern)
- **Explicit Dependencies**: CLI/GUI inject infrastructure services and construct application logic directly
- **Region-based Detection**: All UI interactions use cached regions (left, top, width, height) relative to Raid window
- **Window Size Dependency**: Regions cached per window size, requiring re-selection if window resized
- **Debug Mode**: Global `--debug` flag enables DEBUG logging and saves debug artifacts

## Progress Bar State Detection

The core algorithm in [progress_bar_detector.py](../src/autoraid/detection/progress_bar_detector.py) uses average BGR color values to determine state:
- **fail**: Red (b<70, g<90, r>130)
- **progress**: Yellow (b<70, |r-g|<50)
- **standby**: Black (b<30, g<60, r<70)
- **connection_error**: Blue dominant (b>g, b>r, b>50)

## Upgrade Counting Flow

1. User navigates to upgrade screen in Raid
2. Tool disables network adapters (if specified)
3. Tool locates or prompts for UI regions (upgrade bar, button, artifact icon)
4. User clicks upgrade button programmatically
5. Tool monitors progress bar color changes every 0.25s
6. Counts transitions to "fail" state (red bar)
7. Stops on: max attempts reached, 4 consecutive "standby" states (upgraded), or 4 consecutive "connection_error" states
8. Re-enables network adapters

## Workflow Usage Examples

**CLI Usage:**
```python
# Count workflow — services injected via @inject decorator
from dependency_injector.wiring import inject, Provide
from autoraid.container import Container
from autoraid.workflows.count_workflow import CountWorkflow

@inject
def run_count_command(
    cache_service=Provide[Container.cache_service],
    screenshot_service=Provide[Container.screenshot_service],
    window_service=Provide[Container.window_interaction_service],
    network_manager=Provide[Container.network_manager],
    detector=Provide[Container.progress_bar_detector],
):
    workflow = CountWorkflow(
        cache_service=cache_service,
        screenshot_service=screenshot_service,
        window_interaction_service=window_service,
        network_manager=network_manager,
        detector=detector,
        network_adapter_ids=[1, 2],
        max_attempts=99,
        debug_dir=None,
    )

    workflow.validate()
    result = workflow.run()
    print(f"Failed {result.fail_count} times, reason: {result.stop_reason}")
```

**GUI Usage:**
```python
# Spend workflow — services injected, workflow constructed directly
@inject
async def start_spend_workflow(
    cache_service=Provide[Container.cache_service],
    screenshot_service=Provide[Container.screenshot_service],
    window_service=Provide[Container.window_interaction_service],
    network_manager=Provide[Container.network_manager],
    detector=Provide[Container.progress_bar_detector],
):
    workflow = SpendWorkflow(
        cache_service=cache_service,
        screenshot_service=screenshot_service,
        window_interaction_service=window_service,
        network_manager=network_manager,
        detector=detector,
        max_upgrade_attempts=10,
        continue_upgrade=True,
        debug_dir=None,
    )

    # Run in background thread to keep UI responsive
    result = await asyncio.to_thread(workflow.run)
    ui.notify(f"Upgraded {result.upgrade_count} times!")
```

**Error Handling:**
```python
from autoraid.exceptions import WorkflowValidationError, WindowNotFoundException

try:
    workflow = CountWorkflow(
        cache_service=cache_service,
        screenshot_service=screenshot_service,
        window_interaction_service=window_service,
        network_manager=network_manager,
        detector=detector,
        network_adapter_ids=None,
        max_attempts=99,
        debug_dir=None,
    )
    workflow.validate()
    result = workflow.run()
except WindowNotFoundException as e:
    print(f"Error: {e}")  # "Raid window not found. Ensure Raid: Shadow Legends is running."
except WorkflowValidationError as e:
    print(f"Validation failed: {e}")  # "Internet access detected but no network adapter specified..."
```

## Project Structure

```
autoraid/
├── src/autoraid/
│   ├── cli/                      # CLI layer (thin commands)
│   │   ├── cli.py                # Main entry point, DI container creation
│   │   ├── upgrade_cli.py        # Upgrade commands with @inject
│   │   ├── network_cli.py        # Network adapter commands
│   │   └── debug_cli.py          # Debug commands
│   ├── gui/                      # GUI layer (native desktop interface)
│   │   ├── app.py                # Main NiceGUI application & layout
│   │   └── components/
│   │       ├── upgrade_panel.py  # Count/Spend workflows + Live Logs
│   │       ├── region_panel.py   # Region show/select (OpenCV integration)
│   │       └── network_panel.py  # Network adapter table & management
│   ├── debug/                    # Debug review tools
│   │   ├── app.py                # Debug review GUI (NiceGUI)
│   │   ├── models.py             # Debug data models
│   │   ├── progressbar_review_gui.py
│   │   └── utils.py
│   ├── workflows/                # Workflow layer (thin configuration)
│   │   ├── count_workflow.py     # CountWorkflow + CountResult
│   │   ├── spend_workflow.py     # SpendWorkflow + SpendResult
│   │   └── debug_monitor_workflow.py
│   ├── services/                 # Service layer (infrastructure)
│   │   ├── app_data.py
│   │   ├── cache_service.py
│   │   ├── screenshot_service.py
│   │   ├── locate_region_service.py
│   │   ├── window_interaction_service.py
│   │   └── network.py
│   ├── orchestration/            # Application logic
│   │   ├── upgrade_orchestrator.py
│   │   ├── progress_bar_monitor.py
│   │   ├── stop_conditions.py
│   │   └── debug_frame_logger.py
│   ├── detection/                # CV algorithms
│   │   ├── progress_bar_detector.py
│   │   ├── locate_region.py
│   │   └── templates/
│   ├── utils/
│   │   ├── common.py
│   │   ├── interaction.py
│   │   ├── visualization.py
│   │   └── network_context.py
│   ├── container.py              # DI container configuration
│   ├── exceptions.py
│   └── logging_config.py
├── test/
│   ├── unit/                     # Per-layer unit tests
│   ├── integration/              # Workflow + mocked orchestrator tests
│   └── fixtures/images/          # CV test images
├── docs/
├── scripts/
├── pyproject.toml
└── .pre-commit-config.yaml
```
