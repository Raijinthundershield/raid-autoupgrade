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
   - Zero business logic duplication - all workflows use existing orchestrator and services via DI

3. **Service Layer** ([src/autoraid/services/](autoraid/src/autoraid/services/))
   - **UpgradeOrchestrator** (Factory): Coordinates all services for upgrade workflows
   - **CacheService** (Singleton): Manages region/screenshot caching with diskcache
   - **ScreenshotService** (Singleton): Captures window screenshots and extracts ROIs
   - **LocateRegionService** (Singleton): Detects and caches UI regions (upgrade bar, button)
   - **WindowInteractionService** (Singleton): Checks window existence, handles window activation and clicking

3. **Core Domain Logic** ([src/autoraid/core/](autoraid/src/autoraid/core/))
   - **UpgradeStateMachine** (Factory): Pure logic for tracking upgrade attempts
     - Processes progress bar frames and counts fail states
     - No I/O dependencies - testable with fixture images
     - Tracks recent states in deque to detect stop conditions
   - **Progress Bar Detection**: Color-based state detection (fail/standby/progress/connection_error)
   - **Region Location**: Automatic detection of UI regions using template matching
   - **Artifact Icon**: OCR-based artifact level detection

4. **Utilities** ([src/autoraid/utils/](autoraid/src/autoraid/utils/))
   - **Interaction**: Low-level region selection with OpenCV GUI
   - **Visualization**: Image display and annotation for debugging
   - **Common**: General utilities (timestamps, etc.)

5. **Platform-Specific** ([src/autoraid/platform/](autoraid/src/autoraid/platform/))
   - **NetworkManager**: Windows WMI-based network adapter control
   - Windows-only implementations for OS-specific operations

6. **Infrastructure**
   - [exceptions.py](autoraid/src/autoraid/exceptions.py): Custom exception classes
   - [container.py](autoraid/src/autoraid/container.py): Dependency injection container configuration

### Dependency Injection Container

```
Container (DeclarativeContainer)
│
├── Configuration
│   ├── cache_dir: str
│   └── debug: bool
│
├── Providers (Singleton)
│   ├── disk_cache: Cache(cache_dir)
│   ├── cache_service: CacheService(disk_cache)
│   ├── screenshot_service: ScreenshotService()
│   ├── window_interaction_service: WindowInteractionService()
│   └── locate_region_service: LocateRegionService(cache_service, screenshot_service)
│
└── Providers (Factory)
    ├── state_machine: UpgradeStateMachine(max_attempts)
    └── upgrade_orchestrator: UpgradeOrchestrator(all services + state_machine.provider)
```

**Wiring**: CLI modules (`autoraid.cli.upgrade_cli`, `autoraid.cli.network_cli`) and GUI modules (`autoraid.gui.components.upgrade_panel`, `autoraid.gui.components.region_panel`, `autoraid.gui.components.network_panel`) are wired to enable `@inject` decorator.

**Lifecycle**:
- **Singleton**: One instance per container (services with no per-request state)
- **Factory**: New instance per call (state machine, orchestrator with per-workflow state)

### GUI Architecture

The GUI layer is a **thin presentation layer** that provides a native desktop interface without duplicating business logic:

**Design Principles**:
- **Zero Logic Duplication**: GUI components inject and call the same services used by CLI
- **Async Threading**: Blocking operations (workflows, region selection) run via `asyncio.to_thread()` to keep UI responsive
- **State Persistence**: User preferences (selected adapters, last count result) persist via `app.storage.user`
- **External OpenCV**: Region selection popups remain external windows (not embedded in GUI)
- **Real-time Updates**: Log streaming and progress updates use NiceGUI's reactive UI elements (`ui.refreshable()`, `ui.log()`)

**Component Structure**:
- **UpgradePanel** (`upgrade_panel.py`): Count and Spend workflows with real-time progress displays
  - Injects `UpgradeOrchestrator` to run workflows
  - Uses `ui.refreshable()` for live count/spent updates
  - Displays error toasts for exceptions (WindowNotFoundException, NetworkAdapterError, etc.)
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
| **CacheService** | Singleton | Region/screenshot caching | disk_cache |
| **ScreenshotService** | Singleton | Window screenshots, ROI extraction | None |
| **LocateRegionService** | Singleton | Region detection (auto + manual) | cache_service, screenshot_service |
| **WindowInteractionService** | Singleton | Window existence checking, activation, clicking | None |
| **UpgradeStateMachine** | Factory | Frame processing, fail counting | None (pure logic) |
| **UpgradeOrchestrator** | Factory | Workflow coordination | All services + state_machine.provider |

### Key Design Patterns

- **Dependency Injection**: Constructor injection for all services, configured via DeclarativeContainer
- **Service Layer**: Business logic separated from CLI/I/O in testable services
- **Pure State Machine**: UpgradeStateMachine has no I/O dependencies, testable with fixture images
- **Orchestrator Pattern**: UpgradeOrchestrator coordinates services for complete workflows
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
│   │   └── network_cli.py        # Network adapter commands
│   ├── gui/                      # GUI layer (native desktop interface)
│   │   ├── __init__.py
│   │   ├── app.py                # Main NiceGUI application & layout
│   │   └── components/           # UI components
│   │       ├── __init__.py
│   │       ├── upgrade_panel.py  # Count/Spend workflows + Live Logs
│   │       ├── region_panel.py   # Region show/select (OpenCV integration)
│   │       └── network_panel.py  # Network adapter table & management
│   ├── services/                 # Service layer (business logic)
│   │   ├── cache_service.py      # Region/screenshot caching
│   │   ├── screenshot_service.py # Window screenshot capture
│   │   ├── locate_region_service.py # Region detection
│   │   ├── window_interaction_service.py # Window clicking
│   │   └── upgrade_orchestrator.py # Workflow coordination
│   ├── core/                     # Core domain logic
│   │   ├── state_machine.py      # Pure state machine (testable)
│   │   ├── progress_bar.py       # Progress bar state detection
│   │   ├── locate_region.py      # Automatic region detection
│   │   ├── artifact_icon.py      # Artifact icon OCR
│   │   └── templates/            # CV templates for region detection
│   ├── utils/                    # Utility modules
│   │   ├── common.py             # General utilities (timestamps, etc.)
│   │   ├── interaction.py        # Low-level region selection
│   │   └── visualization.py      # Image display/annotation
│   ├── platform/                 # Platform-specific code
│   │   └── network.py            # Windows network adapter management
│   ├── container.py              # DI container configuration
│   └── exceptions.py             # Custom exception classes
├── test/                         # Tests organized by type
│   ├── unit/                     # Unit tests
│   │   ├── core/                 # Core logic tests
│   │   │   ├── test_state_machine.py
│   │   │   └── test_progressbar_state.py
│   │   ├── services/             # Service tests
│   │   │   ├── test_cache_service.py
│   │   │   ├── test_screenshot_service.py
│   │   │   ├── test_locate_region_service.py
│   │   │   └── test_window_interaction_service.py
│   │   └── gui/                  # GUI smoke tests
│   │       ├── test_network_panel.py
│   │       ├── test_region_panel.py
│   │       └── test_upgrade_panel.py
│   ├── integration/              # Integration tests
│   │   ├── test_upgrade_orchestrator.py # With mocked services
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

1. **Unit Tests** (core and services):
   - Core logic tests:
     - [test/unit/core/test_state_machine.py](autoraid/test/unit/core/test_state_machine.py): State machine with fixture images
     - [test/unit/core/test_progressbar_state.py](autoraid/test/unit/core/test_progressbar_state.py): Progress bar color detection
   - Service tests:
     - [test/unit/services/test_cache_service.py](autoraid/test/unit/services/test_cache_service.py): Cache key generation and retrieval
     - [test/unit/services/test_screenshot_service.py](autoraid/test/unit/services/test_screenshot_service.py): ROI extraction
     - [test/unit/services/test_locate_region_service.py](autoraid/test/unit/services/test_locate_region_service.py): Region detection
     - [test/unit/services/test_window_interaction_service.py](autoraid/test/unit/services/test_window_interaction_service.py): Window existence validation

2. **Integration Tests** (with mocks):
   - [test/integration/test_upgrade_orchestrator.py](autoraid/test/integration/test_upgrade_orchestrator.py): Workflow coordination with mocked services
   - [test/integration/test_cli_integration.py](autoraid/test/integration/test_cli_integration.py): CLI behavior and backward compatibility
   - [test/integration/test_locate.py](autoraid/test/integration/test_locate.py): Region location with test images

### Mock Testing Patterns

The service-based architecture enables testing with mocked dependencies:

```python
from unittest.mock import Mock
from autoraid.services.upgrade_orchestrator import UpgradeOrchestrator

def test_orchestrator_with_mocks():
    # Create mock services
    mock_cache = Mock()
    mock_screenshot = Mock()
    mock_locate = Mock()
    mock_window = Mock()
    mock_state_machine_provider = Mock()

    # Configure mock behavior
    mock_window.window_exists.return_value = True
    mock_screenshot.take_screenshot.return_value = fake_image

    # Instantiate orchestrator with mocks
    orchestrator = UpgradeOrchestrator(
        cache_service=mock_cache,
        screenshot_service=mock_screenshot,
        locate_region_service=mock_locate,
        window_interaction_service=mock_window,
        state_machine_provider=mock_state_machine_provider,
    )

    # Test workflow without external dependencies
    result = orchestrator.count_workflow(network_adapter_id=None, max_attempts=10)

    # Verify service interactions
    mock_window.window_exists.assert_called_once()
    mock_screenshot.take_screenshot.assert_called_once()
```

### Coverage Requirements

- **State machine**: ≥90% code coverage (verified with pytest-cov)
- **Services**: Smoke tests for instantiation and key methods
- **Integration**: CLI behavior unchanged after refactoring

### Running Tests

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=autoraid --cov-report=term-missing

# Specific test file
uv run pytest test/unit/core/test_state_machine.py

# State machine coverage check
uv run pytest --cov=autoraid.core.state_machine --cov-report=term-missing test/unit/core/test_state_machine.py

# Run only unit tests
uv run pytest test/unit/

# Run only integration tests
uv run pytest test/integration/
```
