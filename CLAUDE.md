# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AutoRaid** is a Windows-only automation tool for Raid: Shadow Legends that helps with the "airplane mode trick" for gear upgrades. The tool uses computer vision (OpenCV) and GUI automation (pyautogui) to detect upgrade states and automate the upgrade process.

Key feature: The tool can count the number of upgrade fails needed before a successful upgrade (with internet off), then automatically spend those attempts (with internet on) to guarantee an upgrade at the right time.

## Development Commands

This project uses `uv` for package management and virtual environment management.

### Environment Setup
```bash
cd autoraid
uv sync  # Install dependencies and create virtual environment
```

### Running the Tool
```bash
cd autoraid
uv run autoraid --help    # View all CLI commands
uv run autoraid gui       # Launch native desktop GUI
```

### Testing
```bash
cd autoraid
uv run pytest
```

### Linting and Formatting
```bash
cd autoraid
uv run ruff check .        # Lint code
uv run ruff check --fix .  # Fix linting issues
uv run ruff format .       # Format code
```

### Pre-commit Hooks
```bash
cd autoraid
uv run pre-commit install  # Install pre-commit hooks
uv run pre-commit run --all-files  # Run hooks manually
```

## Architecture

AutoRaid uses a **service-based architecture** with **dependency injection** to separate concerns, improve testability, and enable mocking. The architecture is organized into distinct layers with clear responsibilities.

### Component Hierarchy

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

### Core Components

1. **CLI Layer** ([src/autoraid/cli/](autoraid/src/autoraid/cli/))
   - [cli.py](autoraid/src/autoraid/cli/cli.py): Main entry point with `autoraid` command group, creates DI container
   - [upgrade_cli.py](autoraid/src/autoraid/cli/upgrade_cli.py): Thin CLI commands (<20 LOC) using @inject decorator
   - [network_cli.py](autoraid/src/autoraid/cli/network_cli.py): Commands for network adapter management
   - Uses Click for CLI framework with dependency injection via `dependency-injector`

2. **GUI Layer** ([src/autoraid/gui/](autoraid/src/autoraid/gui/))
   - [app.py](autoraid/src/autoraid/gui/app.py): Main NiceGUI application with single-page scrollable layout
   - [components/upgrade_panel.py](autoraid/src/autoraid/gui/components/upgrade_panel.py): Count/Spend workflows with real-time updates
   - [components/region_panel.py](autoraid/src/autoraid/gui/components/region_panel.py): Region selection and status display
   - [components/network_panel.py](autoraid/src/autoraid/gui/components/network_panel.py): Network adapter management table
   - Uses NiceGUI native mode for desktop application window
   - Zero business logic duplication - all workflows use workflow factories and services via DI

3. **Workflow Layer** ([src/autoraid/workflows/](autoraid/src/autoraid/workflows/))
   - **Workflow** (Abstract Base): Template Method pattern for validation and execution lifecycle
   - **CountWorkflow** (Factory): Counts upgrade fails offline with network adapter management
     - Validates window existence, network configuration, and cached regions before execution
     - Disables network adapters (if specified) during counting
     - Returns structured CountResult with fail_count and stop_reason
   - **SpendWorkflow** (Factory): Spends counted attempts online with internet verification
     - Validates window existence, internet availability, and cached regions before execution
     - Supports continue_upgrade mode for level 10+ artifacts
     - Returns structured SpendResult with upgrade_count, attempt_count, remaining_attempts, and stop_reason

4. **Service Layer** ([src/autoraid/services/](autoraid/src/autoraid/services/))
   - **AppData** (Singleton): Centralized application directory configuration
     - Manages cache_dir and debug_dir paths
     - Provides directory creation and validation
     - Single source of truth for all application directories
   - **CacheService** (Singleton): Manages region/screenshot caching with diskcache
   - **ScreenshotService** (Singleton): Captures window screenshots and extracts ROIs
   - **LocateRegionService** (Singleton): Detects and caches UI regions (upgrade bar, button)
   - **WindowInteractionService** (Singleton): Checks window existence, handles window activation and clicking
   - **NetworkManager** (Singleton): Windows WMI-based network adapter control with automatic state waiting

5. **Core Domain Logic** ([src/autoraid/core/](autoraid/src/autoraid/core/))
   - **ProgressBarStateDetector** (Singleton): Stateless CV layer for progress bar state detection
     - Wraps existing color-based algorithm with type-safe enum output
     - Validates input images and returns ProgressBarState enum
     - No side effects - testable with fixture images
   - **ProgressBarMonitor** (Factory): Stateful monitoring for progress bar without stop condition logic
     - Processes progress bar frames and counts fail state transitions
     - Maintains state history (last 4 states) in deque
     - Provides immutable state snapshots via ProgressBarMonitorState dataclass
     - No I/O dependencies - testable with mocked detector
   - **StopCondition Classes** (Strategy Pattern): Pluggable stop condition strategies
     - MaxAttemptsCondition: Stop when fail count reaches threshold
     - MaxFramesCondition: Stop when frame count reaches threshold
     - UpgradedCondition: Stop on 4 consecutive STANDBY or CONNECTION_ERROR states
     - ConnectionErrorCondition: Stop on 4 consecutive CONNECTION_ERROR states
     - StopConditionChain: Evaluates conditions in priority order
   - **DebugFrameLogger**: Optional debug data capture during monitoring
     - Saves screenshots and ROIs with timestamped filenames
     - Records metadata (state, frame number, counts, colors)
     - Writes JSON summary log at end of session
   - **Progress Bar Detection**: Color-based state detection (fail/standby/progress/connection_error)
   - **Region Location**: Automatic detection of UI regions using template matching

6. **Orchestration Layer** ([src/autoraid/orchestration/](autoraid/src/autoraid/orchestration/))
   - **UpgradeOrchestrator** (Direct Construction): Coordinates upgrade monitoring sessions
     - Validates prerequisites (window existence, region cache, window size)
     - Creates ProgressBarMonitor internally per session
     - Manages monitoring loop (screenshot, ROI extraction, monitor, stop conditions)
     - Integrates NetworkContext for automatic adapter management
     - Supports optional DebugFrameLogger for diagnostic data capture
     - Returns immutable UpgradeResult with fail_count, frames_processed, stop_reason

7. **Utilities** ([src/autoraid/utils/](autoraid/src/autoraid/utils/))
   - **Interaction**: Low-level region selection with OpenCV GUI
   - **Visualization**: Image display and annotation for debugging
   - **Common**: General utilities (timestamps, etc.)
   - **NetworkContext**: Context manager for automatic network adapter lifecycle management
     - Disables adapters on entry, re-enables on exit (exception-safe)
     - Ensures adapters always re-enabled, even on exceptions

8. **Infrastructure**
   - [exceptions.py](autoraid/src/autoraid/exceptions.py): Custom exception classes (including WorkflowValidationError)
   - [container.py](autoraid/src/autoraid/container.py): Dependency injection container configuration

### Dependency Injection Container

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

**Application Logic (Direct Construction)**:
- **ProgressBarMonitor**: Created internally by UpgradeOrchestrator per session
- **UpgradeOrchestrator**: Created by workflows with injected services
- **CountWorkflow, SpendWorkflow, DebugMonitorWorkflow**: Created by CLI/GUI with injected services

**Wiring**: CLI modules (`autoraid.cli.upgrade_cli`, `autoraid.cli.network_cli`, `autoraid.cli.debug_cli`) and GUI modules (`autoraid.gui.components.upgrade_panel`, `autoraid.gui.components.region_panel`, `autoraid.gui.components.network_panel`) are wired to enable `@inject` decorator for infrastructure services.

**Lifecycle**:
- **Singleton**: Infrastructure services with no per-request state (8 total)
- **Direct Construction**: Application logic (workflows, orchestrator, monitor) constructed as needed with explicit dependencies

### GUI Architecture

The GUI layer is a **thin presentation layer** that provides a native desktop interface without duplicating business logic:

**Design Principles**:
- **Zero Logic Duplication**: GUI components inject and call the same services used by CLI
- **Centralized Configuration**: GUI creates DI container with AppData for consistent directory management
- **Async Threading**: Blocking operations (workflows, region selection) run via `asyncio.to_thread()` to keep UI responsive
- **State Persistence**: User preferences (selected adapters, last count result) persist via `app.storage.user`
- **External OpenCV**: Region selection popups remain external windows (not embedded in GUI)
- **Real-time Updates**: Log streaming and progress updates use NiceGUI's reactive UI elements (`ui.refreshable()`, `ui.log()`)

**Component Structure**:
- **UpgradePanel** (`upgrade_panel.py`): Count and Spend workflows with real-time progress displays
  - Injects infrastructure services (cache, screenshot, window, network, detector, app_data)
  - Constructs workflows directly with injected services
  - Uses `ui.refreshable()` for live count/spent updates
  - Displays error toasts for exceptions (WindowNotFoundException, WorkflowValidationError, NetworkAdapterError, etc.)
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

**State Management**:
- `app.storage.user['selected_adapters']`: Network adapter IDs for Count workflow
- `app.storage.user['last_count_result']`: Auto-populates Spend workflow max attempts
- Region cache uses existing diskcache (same as CLI)

**Layout**: Single-page vertical scrollable interface with three sections:
1. **Upgrade Workflows** (top): Count, Spend, Live Logs
2. **Region Management** (middle): Window size, cached regions, show/select buttons
3. **Network Adapters** (bottom): Adapter table with multi-select

### Service Responsibilities

| Service | Lifecycle | Responsibilities | Dependencies |
|---------|-----------|------------------|--------------|
| **AppData** | Singleton | Centralized directory configuration (cache_dir, debug_dir) | None |
| **CacheService** | Singleton | Region/screenshot caching | disk_cache |
| **ScreenshotService** | Singleton | Window screenshots, ROI extraction | None |
| **LocateRegionService** | Singleton | Region detection (auto + manual) | cache_service, screenshot_service |
| **WindowInteractionService** | Singleton | Window existence checking, activation, clicking | None |
| **NetworkManager** | Singleton | Network adapter management with automatic state waiting | None |
| **ProgressBarStateDetector** | Singleton | Progress bar state detection from images | None (stateless CV layer) |
| **ProgressBarMonitor** | Direct Construction | Frame processing, fail transition counting, state history tracking | progress_bar_detector |
| **UpgradeOrchestrator** | Direct Construction | Coordinate upgrade sessions with stop conditions, network management | screenshot_service, window_interaction_service, cache_service, network_manager, detector |
| **CountWorkflow** | Direct Construction | Count workflow with validation and orchestration | cache_service, window_interaction_service, network_manager, screenshot_service, detector |
| **SpendWorkflow** | Direct Construction | Spend workflow with validation and orchestration | cache_service, window_interaction_service, network_manager, screenshot_service, detector |
| **DebugMonitorWorkflow** | Direct Construction | Debug workflow with frame capture and orchestration | cache_service, window_interaction_service, network_manager, screenshot_service, detector |

### Key Design Patterns

- **Dependency Injection**: Constructor injection for all services, configured via DeclarativeContainer
- **Service Layer**: Business logic separated from CLI/I/O in testable services
- **Strategy Pattern**: Stop conditions are pluggable strategies evaluated by StopConditionChain
- **Context Manager Pattern**: NetworkContext ensures automatic network adapter cleanup (exception-safe)
- **Orchestrator Pattern**: UpgradeOrchestrator coordinates monitoring sessions with validation, stop conditions, and network management
- **Separated Concerns**: Clear separation of responsibilities across layers
  - **ProgressBarStateDetector**: Stateless CV layer, testable with fixture images
  - **ProgressBarMonitor**: Stateful frame tracking (no stop logic), testable with mocked detector
  - **StopCondition classes**: Isolated stop logic, independently testable
  - **UpgradeOrchestrator**: Coordination layer, testable with mocked services
  - **Workflows**: Thin configuration layers, testable with mocked orchestrator
- **Composition Over Inheritance**: Workflows compose orchestrator instead of inheriting from base class
- **Immutable State**: Monitor provides frozen dataclass snapshots (ProgressBarMonitorState)
- **Direct Construction**: Workflows, orchestrator, and monitor constructed directly with explicit dependencies (no factory pattern)
- **Explicit Dependencies**: CLI/GUI inject infrastructure services and construct application logic directly
- **Region-based Detection**: All UI interactions use cached regions (left, top, width, height) relative to Raid window
- **Window Size Dependency**: Regions cached per window size, requiring re-selection if window resized
- **Debug Mode**: Global `--debug` flag enables DEBUG logging and saves debug artifacts

### Progress Bar State Detection

The core algorithm in [progress_bar.py](autoraid/src/autoraid/core/progress_bar.py) uses average BGR color values to determine state:
- **fail**: Red (b<70, g<90, r>130)
- **progress**: Yellow (b<70, abs(r-g)<50)
- **standby**: Black (b<30, g<60, r<70)
- **connection_error**: Blue dominant (b>g, b>r, b>50)

### Upgrade Counting Flow

1. User navigates to upgrade screen in Raid
2. Tool disables network adapters (if specified)
3. Tool locates or prompts for UI regions (upgrade bar, button, artifact icon)
4. User clicks upgrade button programmatically
5. Tool monitors progress bar color changes every 0.25s
6. Counts transitions to "fail" state (red bar)
7. Stops on: max attempts reached, 4 consecutive "standby" states (upgraded), or 4 consecutive "connection_error" states
8. Re-enables network adapters

### Workflow Usage Examples

**CLI Usage**:
```python
# Count workflow - services injected via @inject decorator
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
    # Construct workflow directly with injected services
    workflow = CountWorkflow(
        cache_service=cache_service,
        screenshot_service=screenshot_service,
        window_interaction_service=window_service,
        network_manager=network_manager,
        detector=detector,
        network_adapter_ids=[1, 2],  # Runtime parameter
        max_attempts=99,
        debug_dir=None,
    )

    # Validate and run
    workflow.validate()
    result = workflow.run()
    print(f"Failed {result.fail_count} times, reason: {result.stop_reason}")
```

**GUI Usage**:
```python
# Spend workflow - services injected, workflow constructed directly
@inject
async def start_spend_workflow(
    cache_service=Provide[Container.cache_service],
    screenshot_service=Provide[Container.screenshot_service],
    window_service=Provide[Container.window_interaction_service],
    network_manager=Provide[Container.network_manager],
    detector=Provide[Container.progress_bar_detector],
):
    # Construct workflow with injected services
    workflow = SpendWorkflow(
        cache_service=cache_service,
        screenshot_service=screenshot_service,
        window_interaction_service=window_service,
        network_manager=network_manager,
        detector=detector,
        max_upgrade_attempts=10,
        continue_upgrade=True,  # Continue to next level after success
        debug_dir=None,
    )

    # Run in background thread to keep UI responsive
    result = await asyncio.to_thread(workflow.run)

    # Display results
    ui.notify(f"Upgraded {result.upgrade_count} times!")
```

**Error Handling**:
```python
from autoraid.exceptions import WorkflowValidationError, WindowNotFoundException

try:
    # Construct workflow with services
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
    workflow.validate()  # Early validation
    result = workflow.run()
except WindowNotFoundException as e:
    print(f"Error: {e}")  # "Raid window not found. Ensure Raid: Shadow Legends is running."
except WorkflowValidationError as e:
    print(f"Validation failed: {e}")  # "Internet access detected but no network adapter specified..."
```

## Important Constraints

- **Windows Only**: Uses WMI for network adapter control and pywinauto for window management
- **Admin Rights**: Required when Raid is launched via RSLHelper (which runs as admin)
- **Window Size**: Must remain constant during operation; resizing invalidates cached regions
- **Foreground Window**: Raid window is activated before each screenshot/click
- **First-Attempt Success**: Tool does not handle upgrades that succeed on first try

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
│   │   ├── __init__.py
│   │   ├── app.py                # Main NiceGUI application & layout
│   │   └── components/           # UI components
│   │       ├── __init__.py
│   │       ├── upgrade_panel.py  # Count/Spend workflows + Live Logs
│   │       ├── region_panel.py   # Region show/select (OpenCV integration)
│   │       └── network_panel.py  # Network adapter table & management
│   ├── debug/                    # Debug tools
│   │   ├── __init__.py
│   │   ├── app.py                # Debug review GUI (NiceGUI)
│   │   ├── models.py             # Debug data models
│   │   ├── progressbar_review_gui.py # Progress bar frame review
│   │   └── utils.py              # Debug utilities
│   ├── workflows/                # Workflow layer (thin configuration)
│   │   ├── __init__.py
│   │   ├── count_workflow.py    # CountWorkflow + CountResult
│   │   ├── spend_workflow.py    # SpendWorkflow + SpendResult
│   │   └── debug_monitor_workflow.py # DebugMonitorWorkflow + DebugMonitorResult
│   ├── services/                 # Service layer (business logic)
│   │   ├── app_data.py           # Application directory management
│   │   ├── cache_service.py      # Region/screenshot caching
│   │   ├── screenshot_service.py # Window screenshot capture
│   │   ├── locate_region_service.py # Region detection
│   │   ├── window_interaction_service.py # Window clicking
│   │   └── network.py            # Network adapter management
│   ├── orchestration/            # Orchestration layer (application logic)
│   │   ├── __init__.py
│   │   ├── upgrade_orchestrator.py # Upgrade session orchestration
│   │   ├── progress_bar_monitor.py  # Progress bar monitoring (stateful)
│   │   ├── stop_conditions.py    # Stop condition strategies
│   │   └── debug_frame_logger.py # Debug data capture
│   ├── detection/                # Detection layer (CV algorithms)
│   │   ├── __init__.py
│   │   ├── progress_bar_detector.py # Progress bar state detection
│   │   ├── locate_region.py      # Automatic region detection
│   │   └── templates/            # CV templates for region detection
│   ├── utils/                    # Utility modules
│   │   ├── common.py             # General utilities (timestamps, etc.)
│   │   ├── interaction.py        # Low-level region selection
│   │   ├── visualization.py      # Image display/annotation
│   │   └── network_context.py   # Network adapter context manager
│   ├── container.py              # DI container configuration
│   ├── exceptions.py             # Custom exception classes
│   └── logging_config.py         # Logging configuration
├── test/                         # Tests organized by type
│   ├── unit/                     # Unit tests
│   │   ├── detection/            # Detection layer tests
│   │   │   └── test_progress_bar_detector.py
│   │   ├── orchestration/        # Orchestration layer tests
│   │   │   ├── test_progress_bar_monitor.py
│   │   │   ├── test_stop_conditions.py
│   │   │   └── test_upgrade_orchestrator.py
│   │   ├── services/             # Service tests
│   │   │   └── test_network_manager.py
│   │   ├── workflows/            # Workflow tests
│   │   │   ├── test_count_workflow.py
│   │   │   ├── test_spend_workflow.py
│   │   │   └── test_debug_monitor_workflow.py
│   │   ├── utils/                # Utility tests
│   │   │   └── test_network_context.py
│   │   └── gui/                  # GUI smoke tests
│   │       ├── test_network_panel.py
│   │       ├── test_region_panel.py
│   │       └── test_upgrade_panel.py
│   ├── integration/              # Integration tests
│   │   ├── test_count_workflow_integration.py # Count workflow integration
│   │   ├── test_spend_workflow_integration.py # Spend workflow integration
│   │   ├── test_cli_integration.py # CLI behavior tests
│   │   └── test_locate.py        # Region detection tests
│   └── fixtures/                 # Test fixtures and images
│       └── images/               # Test images for CV
├── scripts/                      # Helper scripts
│   ├── average_color.py          # Color analysis utility
│   └── get_artifact_icons.py    # Artifact icon scraper
├── docs/                         # Documentation
├── pyproject.toml                # Project config & dependencies
└── .pre-commit-config.yaml
```

## Dependencies

Key libraries:
- **opencv-python**: Computer vision for progress bar detection
- **pyautogui**: GUI automation (clicking, screenshots)
- **pygetwindow**: Window management
- **click**: CLI framework
- **nicegui[native]**: Native desktop GUI framework with reactive UI components
- **dependency-injector**: Dependency injection container
- **diskcache**: Persistent caching
- **wmi**: Windows network adapter control
- **rich**: Terminal UI (tables, colors)
- **loguru**: Logging
- **pytest**: Testing framework
- **pytest-cov**: Test coverage reporting

## Testing

### Test Structure

AutoRaid uses **smoke tests** (not full TDD) to verify basic functionality:

1. **Unit Tests** (detection, orchestration, and services):
   - Detection layer tests:
     - [test/unit/detection/test_progress_bar_detector.py](autoraid/test/unit/detection/test_progress_bar_detector.py): Detector with fixture images (≥90% coverage)
   - Orchestration layer tests:
     - [test/unit/orchestration/test_progress_bar_monitor.py](autoraid/test/unit/orchestration/test_progress_bar_monitor.py): Monitor with mocked detector (≥90% coverage)
     - [test/unit/orchestration/test_stop_conditions.py](autoraid/test/unit/orchestration/test_stop_conditions.py): Stop condition strategies (≥90% coverage)
     - [test/unit/orchestration/test_upgrade_orchestrator.py](autoraid/test/unit/orchestration/test_upgrade_orchestrator.py): Orchestrator coordination (≥80% coverage)
   - Service tests:
     - [test/unit/services/test_cache_service.py](autoraid/test/unit/services/test_cache_service.py): Cache key generation and retrieval
     - [test/unit/services/test_screenshot_service.py](autoraid/test/unit/services/test_screenshot_service.py): ROI extraction
     - [test/unit/services/test_locate_region_service.py](autoraid/test/unit/services/test_locate_region_service.py): Region detection
     - [test/unit/services/test_window_interaction_service.py](autoraid/test/unit/services/test_window_interaction_service.py): Window existence validation
   - Platform tests:
     - [test/unit/utils/test_network_context.py](autoraid/test/unit/utils/test_network_context.py): Network context manager (≥90% coverage)

2. **Integration Tests** (with mocks):
   - [test/integration/test_count_workflow_integration.py](autoraid/test/integration/test_count_workflow_integration.py): Count workflow with mocked orchestrator
   - [test/integration/test_spend_workflow_integration.py](autoraid/test/integration/test_spend_workflow_integration.py): Spend workflow with mocked orchestrator
   - [test/integration/test_cli_integration.py](autoraid/test/integration/test_cli_integration.py): CLI behavior and backward compatibility
   - [test/integration/test_locate.py](autoraid/test/integration/test_locate.py): Region location with test images

### Mock Testing Patterns

The service-based architecture enables testing with mocked dependencies:

**Example 1: Testing Detector with Fixture Images**
```python
import cv2
from autoraid.core.progress_bar_detector import ProgressBarStateDetector, ProgressBarState

def test_detector_recognizes_fail_state():
    detector = ProgressBarStateDetector()
    fail_image = cv2.imread("test/fixtures/images/fail_state.png")

    state = detector.detect_state(fail_image)

    assert state == ProgressBarState.FAIL
```

**Example 2: Testing Monitor with Mocked Detector**
```python
from unittest.mock import Mock
from autoraid.core.progress_bar_detector import ProgressBarStateDetector, ProgressBarState
from autoraid.core.progress_bar_monitor import ProgressBarMonitor
import numpy as np

def test_monitor_counts_fail_transitions():
    # Mock detector to return controlled sequence
    mock_detector = Mock(spec=ProgressBarStateDetector)
    mock_detector.detect_state.side_effect = [
        ProgressBarState.PROGRESS,  # Not a fail
        ProgressBarState.FAIL,      # Count: 1
        ProgressBarState.PROGRESS,  # Not a fail
        ProgressBarState.FAIL,      # Count: 2
    ]

    monitor = ProgressBarMonitor(mock_detector)

    # Provide dummy image (detector is mocked, image not used)
    fake_image = np.zeros((50, 200, 3), dtype=np.uint8)

    for _ in range(4):
        monitor.process_frame(fake_image)

    assert monitor.fail_count == 2
```

**Example 3: Testing Orchestrator with Mocked Services**
```python
from unittest.mock import Mock
from autoraid.services.upgrade_orchestrator import UpgradeOrchestrator

def test_orchestrator_with_mocks():
    # Create mock services
    mock_cache = Mock()
    mock_screenshot = Mock()
    mock_locate = Mock()
    mock_window = Mock()
    mock_monitor_provider = Mock()

    # Configure mock behavior
    mock_window.window_exists.return_value = True
    mock_screenshot.take_screenshot.return_value = fake_image

    # Instantiate orchestrator with mocks
    orchestrator = UpgradeOrchestrator(
        cache_service=mock_cache,
        screenshot_service=mock_screenshot,
        locate_region_service=mock_locate,
        window_interaction_service=mock_window,
        upgrade_attempt_monitor=mock_monitor_provider,
    )

    # Test workflow without external dependencies
    result = orchestrator.count_workflow(network_adapter_id=None, max_attempts=10)

    # Verify service interactions
    mock_window.window_exists.assert_called_once()
    mock_screenshot.take_screenshot.assert_called_once()
```


### Running Tests

```bash
# All tests
uv run pytest

# Specific test file
uv run pytest test/unit/orchestration/test_progress_bar_monitor.py

# Run only unit tests
uv run pytest test/unit/

# Run only integration tests
uv run pytest test/integration/
```
