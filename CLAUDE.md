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
uv run autoraid --help
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

2. **Service Layer** ([src/autoraid/services/](autoraid/src/autoraid/services/))
   - **UpgradeOrchestrator** (Factory): Coordinates all services for upgrade workflows
   - **CacheService** (Singleton): Manages region/screenshot caching with diskcache
   - **ScreenshotService** (Singleton): Captures window screenshots and extracts ROIs
   - **LocateRegionService** (Singleton): Detects and caches UI regions (upgrade bar, button)
   - **WindowInteractionService** (Singleton): Handles window activation and clicking

3. **State Machine** ([src/autoraid/autoupgrade/state_machine.py](autoraid/src/autoraid/autoupgrade/state_machine.py))
   - **UpgradeStateMachine** (Factory): Pure logic for tracking upgrade attempts
   - Processes progress bar frames and counts fail states
   - No I/O dependencies - testable with fixture images
   - Tracks recent states in deque to detect stop conditions

4. **Computer Vision** ([src/autoraid/autoupgrade/](autoraid/src/autoraid/autoupgrade/))
   - [progress_bar.py](autoraid/src/autoraid/autoupgrade/progress_bar.py): Progress bar state detection (fail/standby/progress/connection_error)
   - [locate_upgrade_region.py](autoraid/src/autoraid/autoupgrade/locate_upgrade_region.py): Automatic detection of UI regions
   - [artifact_icon.py](autoraid/src/autoraid/autoupgrade/artifact_icon.py): Artifact icon handling

5. **Utilities**
   - [interaction.py](autoraid/src/autoraid/interaction.py): Low-level region selection with OpenCV GUI
   - [network.py](autoraid/src/autoraid/network.py): Windows WMI-based network adapter control
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

**Wiring**: CLI modules (`autoraid.cli.upgrade_cli`, `autoraid.cli.network_cli`) are wired to enable `@inject` decorator.

**Lifecycle**:
- **Singleton**: One instance per container (services with no per-request state)
- **Factory**: New instance per call (state machine, orchestrator with per-workflow state)

### Service Responsibilities

| Service | Lifecycle | Responsibilities | Dependencies |
|---------|-----------|------------------|--------------|
| **CacheService** | Singleton | Region/screenshot caching | disk_cache |
| **ScreenshotService** | Singleton | Window screenshots, ROI extraction | None |
| **LocateRegionService** | Singleton | Region detection (auto + manual) | cache_service, screenshot_service |
| **WindowInteractionService** | Singleton | Window activation, clicking | None |
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

The core algorithm in [progress_bar.py](autoraid/src/autoraid/autoupgrade/progress_bar.py) uses average BGR color values to determine state:
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
│   ├── services/                 # Service layer (business logic)
│   │   ├── cache_service.py      # Region/screenshot caching
│   │   ├── screenshot_service.py # Window screenshot capture
│   │   ├── locate_region_service.py # Region detection
│   │   ├── window_interaction_service.py # Window clicking
│   │   └── upgrade_orchestrator.py # Workflow coordination
│   ├── autoupgrade/              # Core upgrade logic
│   │   ├── state_machine.py      # Pure state machine (testable)
│   │   ├── progress_bar.py       # Progress bar state detection
│   │   ├── locate_upgrade_region.py # Automatic region detection
│   │   └── autoupgrade.py        # Legacy/wrapper functions
│   ├── container.py              # DI container configuration
│   ├── exceptions.py             # Custom exception classes
│   ├── interaction.py            # Low-level region selection
│   ├── network.py                # Network adapter management
│   ├── visualization.py          # Image display/annotation
│   └── utils.py                  # General utilities
├── test/                         # Tests (smoke + integration)
│   ├── test_state_machine.py    # State machine tests
│   ├── test_cache_service.py    # Cache service tests
│   ├── test_screenshot_service.py # Screenshot service tests
│   ├── test_locate_region_service.py # Region service tests
│   ├── test_upgrade_orchestrator.py # Orchestrator tests with mocks
│   └── test_cli_integration.py  # CLI integration tests
├── scripts/                      # Helper scripts
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

1. **Unit Tests** (services layer):
   - [test_state_machine.py](autoraid/test/test_state_machine.py): State machine with fixture images
   - [test_cache_service.py](autoraid/test/test_cache_service.py): Cache key generation and retrieval
   - [test_screenshot_service.py](autoraid/test/test_screenshot_service.py): ROI extraction
   - [test_locate_region_service.py](autoraid/test/test_locate_region_service.py): Region detection

2. **Integration Tests** (with mocks):
   - [test_upgrade_orchestrator.py](autoraid/test/test_upgrade_orchestrator.py): Workflow coordination with mocked services
   - [test_cli_integration.py](autoraid/test/test_cli_integration.py): CLI behavior and backward compatibility

3. **Legacy Tests**:
   - [test_progressbar_state.py](autoraid/test/test_progressbar_state.py): Progress bar color detection
   - [test_locate.py](autoraid/test/test_locate.py): Region location

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
    mock_screenshot.window_exists.return_value = True
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
    mock_screenshot.window_exists.assert_called_once()
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
uv run pytest test/test_state_machine.py

# State machine coverage check
uv run pytest --cov=autoraid.autoupgrade.state_machine --cov-report=term-missing test/test_state_machine.py
```
