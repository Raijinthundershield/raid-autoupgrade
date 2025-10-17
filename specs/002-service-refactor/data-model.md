# Data Model: Service Entities and Relationships

**Date**: 2025-10-17
**Feature**: Service-Based Architecture Refactoring
**Branch**: `002-service-refactor`

## Overview

This document defines the service entities, their responsibilities, state, methods, and relationships in the refactored service-based architecture. All services follow dependency injection patterns with explicit constructor dependencies.

## Service Entity Definitions

### 1. UpgradeStateMachine

**Purpose**: Track upgrade attempt states and count failures

**Lifecycle**: Factory (new instance per workflow)

**State**:
```python
recent_states: deque[ProgressBarState]  # maxlen=4
fail_count: int
max_attempts: int
```

**Methods**:
- `__init__(max_attempts: int = 100)`: Initialize with max attempts limit
- `process_frame(roi_image: np.ndarray) -> tuple[int, StopCountReason | None]`: Process progress bar frame, return (fail_count, stop_reason)
- `_detect_state(roi_image: np.ndarray) -> ProgressBarState`: Detect current state from image (uses ProgressBarStateDetector)
- `_check_stop_condition() -> StopCountReason | None`: Check if stop condition met

**State Transitions**:
```
fail → progress → standby (upgraded)
fail → connection_error
unknown → (logs warning, continues)
```

**Stop Conditions**:
- 4 consecutive `STANDBY` states → `StopCountReason.UPGRADED`
- 4 consecutive `CONNECTION_ERROR` states → `StopCountReason.CONNECTION_ERROR`
- `fail_count >= max_attempts` → `StopCountReason.MAX_ATTEMPTS_REACHED`

**Dependencies**: None (pure logic with progress_bar module)

**File Location**: `src/autoraid/autoupgrade/state_machine.py`

---

### 2. CacheService

**Purpose**: Centralize caching operations for regions and screenshots

**Lifecycle**: Singleton (shared instance)

**State**:
```python
_cache: diskcache.Cache  # Cache instance
```

**Methods**:
- `__init__(cache: diskcache.Cache)`: Initialize with cache instance
- `create_regions_key(window_size: tuple[int, int]) -> str`: Generate cache key for regions
- `get_regions(window_size: tuple[int, int]) -> dict | None`: Retrieve cached regions
- `set_regions(window_size: tuple[int, int], regions: dict) -> None`: Store regions
- `get_screenshot(window_size: tuple[int, int]) -> np.ndarray | None`: Retrieve cached screenshot
- `set_screenshot(window_size: tuple[int, int], screenshot: np.ndarray) -> None`: Store screenshot

**Cache Keys**:
- Regions: `regions_{width}_{height}` (e.g., `regions_1920_1080`)
- Screenshots: `screenshot_{width}_{height}`

**Dependencies**:
- `diskcache.Cache` (injected via constructor)

**File Location**: `src/autoraid/services/cache_service.py`

---

### 3. ScreenshotService

**Purpose**: Capture window screenshots and extract regions of interest

**Lifecycle**: Singleton (shared instance)

**State**: None (stateless)

**Methods**:
- `__init__()`: Initialize (no dependencies)
- `take_screenshot(window_title: str) -> np.ndarray`: Capture screenshot of window
- `window_exists(window_title: str) -> bool`: Check if window exists
- `extract_roi(screenshot: np.ndarray, region: tuple[int, int, int, int]) -> np.ndarray`: Extract ROI from screenshot

**Region Format**: `(left, top, width, height)`

**Dependencies**: None (uses pyautogui, pygetwindow directly)

**Error Handling**:
- Raises `WindowNotFoundException` if window not found
- Raises `ValueError` for invalid region coordinates

**File Location**: `src/autoraid/services/screenshot_service.py`

---

### 4. LocateRegionService

**Purpose**: Detect upgrade UI regions (automatic template matching or manual selection)

**Lifecycle**: Singleton (shared instance)

**State**: None (stateless, delegates to dependencies)

**Methods**:
- `__init__(cache_service: CacheService, screenshot_service: ScreenshotService)`: Initialize with dependencies
- `get_regions(screenshot: np.ndarray, window_size: tuple[int, int], manual: bool = False) -> dict`: Get regions (check cache → auto-detect → manual)
- `_try_automatic_detection(screenshot: np.ndarray) -> dict | None`: Attempt automatic template matching
- `_manual_selection(screenshot: np.ndarray) -> dict`: Prompt user for manual region selection

**Region Keys**:
- `upgrade_bar`: Progress bar region
- `upgrade_button`: Upgrade button region
- `artifact_icon`: Artifact icon region

**Workflow**:
1. Check cache via CacheService
2. If cache miss → try automatic detection
3. If automatic fails → fallback to manual selection
4. Cache result for future use

**Dependencies**:
- `CacheService` (for caching regions)
- `ScreenshotService` (for ROI extraction)

**Error Handling**:
- Raises `RegionDetectionError` if all methods fail
- Logs warning on automatic detection failure before manual fallback

**File Location**: `src/autoraid/services/locate_region_service.py`

---

### 5. WindowInteractionService

**Purpose**: Click regions and activate windows

**Lifecycle**: Singleton (shared instance)

**State**: None (stateless)

**Methods**:
- `__init__()`: Initialize (no dependencies)
- `click_region(window_title: str, region: tuple[int, int, int, int]) -> None`: Click center of region
- `activate_window(window_title: str) -> None`: Bring window to foreground

**Click Behavior**:
1. Activate window to foreground
2. Calculate region center: `(left + width/2, top + height/2)`
3. Click at center coordinates

**Dependencies**: None (uses pyautogui, pygetwindow directly)

**Error Handling**:
- Raises `WindowNotFoundException` if window not found
- Raises `ValueError` for invalid region coordinates

**File Location**: `src/autoraid/services/window_interaction_service.py`

---

### 6. UpgradeOrchestrator

**Purpose**: Coordinate services to execute count and spend workflows

**Lifecycle**: Factory (new instance per workflow)

**State**:
```python
_cache: CacheService
_screenshot: ScreenshotService
_locate: LocateRegionService
_window: WindowInteractionService
_state_machine_factory: Callable[[], UpgradeStateMachine]
```

**Methods**:
- `__init__(cache_service, screenshot_service, locate_region_service, window_interaction_service, state_machine: Callable)`: Initialize with dependencies
- `count_workflow(network_adapter_id: list[int] | None = None, max_attempts: int = 100) -> tuple[int, StopCountReason]`: Execute count workflow
- `spend_workflow(fail_count: int, max_attempts: int, continue_upgrade: bool = False) -> dict`: Execute spend workflow

**Count Workflow Steps**:
1. Disable network adapters (if specified)
2. Check window exists
3. Capture screenshot
4. Get upgrade regions (cached or detected)
5. Click upgrade button
6. Create state machine
7. Loop: Capture → Extract ROI → Process frame → Check stop
8. Re-enable network adapters (finally block)
9. Return (fail_count, stop_reason)

**Spend Workflow Steps**:
1. Enable network adapters
2. Check window exists
3. Capture screenshot
4. Get upgrade regions
5. Loop fail_count times: Click → Wait → (Continue upgrade if specified)
6. Return workflow summary

**Dependencies**:
- `CacheService`
- `ScreenshotService`
- `LocateRegionService`
- `WindowInteractionService`
- `UpgradeStateMachine` (factory/provider, not instance)

**Error Handling**:
- Catches all service exceptions
- Logs errors with context
- **Always** re-enables network in finally block
- Re-raises exceptions to CLI

**File Location**: `src/autoraid/services/upgrade_orchestrator.py`

---

### 7. DependencyContainer

**Purpose**: Wire all services with explicit dependencies

**Lifecycle**: Singleton (one container per application)

**Base Class**: `containers.DeclarativeContainer`

**Configuration**:
```python
config = providers.Configuration()
```

**Providers**:

**External Dependencies**:
```python
disk_cache = providers.Singleton(
    diskcache.Cache,
    directory=config.cache_dir,
)
```

**Singleton Services**:
```python
cache_service = providers.Singleton(
    CacheService,
    cache=disk_cache,
)

screenshot_service = providers.Singleton(
    ScreenshotService,
)

window_interaction_service = providers.Singleton(
    WindowInteractionService,
)

locate_region_service = providers.Singleton(
    LocateRegionService,
    cache_service=cache_service,
    screenshot_service=screenshot_service,
)
```

**Factory Services**:
```python
state_machine = providers.Factory(
    UpgradeStateMachine,
    max_attempts=config.max_attempts,
)

upgrade_orchestrator = providers.Factory(
    UpgradeOrchestrator,
    cache_service=cache_service,
    screenshot_service=screenshot_service,
    locate_region_service=locate_region_service,
    window_interaction_service=window_interaction_service,
    state_machine=state_machine.provider,  # Provider, not instance
)
```

**Wiring Configuration**:
```python
wiring_config = containers.WiringConfiguration(
    modules=[
        "autoraid.cli.upgrade_cli",
        "autoraid.cli.network_cli",
    ],
)
```

**File Location**: `src/autoraid/container.py`

---

## Service Dependency Graph

```
DependencyContainer
│
├─ config (Configuration)
│
├─ disk_cache (Singleton) ← diskcache.Cache
│
├─ cache_service (Singleton)
│  └─ depends on: disk_cache
│
├─ screenshot_service (Singleton)
│  └─ depends on: (none)
│
├─ window_interaction_service (Singleton)
│  └─ depends on: (none)
│
├─ locate_region_service (Singleton)
│  ├─ depends on: cache_service
│  └─ depends on: screenshot_service
│
├─ state_machine (Factory)
│  └─ depends on: (none, uses max_attempts from config)
│
└─ upgrade_orchestrator (Factory)
   ├─ depends on: cache_service
   ├─ depends on: screenshot_service
   ├─ depends on: locate_region_service
   ├─ depends on: window_interaction_service
   └─ depends on: state_machine (provider)
```

## Data Flow Diagrams

### Count Workflow Data Flow

```
User (CLI)
  │
  │ autoraid upgrade count -n 1
  │
  ▼
CLI Command (upgrade_cli.py)
  │
  │ @inject orchestrator
  │
  ▼
UpgradeOrchestrator.count_workflow()
  │
  ├─► NetworkManager.disable_adapters([1])
  │
  ├─► ScreenshotService.take_screenshot("Raid: Shadow Legends")
  │     └─► returns: np.ndarray (1920x1080 screenshot)
  │
  ├─► LocateRegionService.get_regions(screenshot, (1920, 1080))
  │     │
  │     ├─► CacheService.get_regions((1920, 1080))
  │     │     └─► cache hit: returns cached regions
  │     │     └─► cache miss: returns None
  │     │
  │     ├─► (if cache miss) _try_automatic_detection(screenshot)
  │     │     └─► uses locate_upgrade_region module
  │     │
  │     ├─► (if auto fails) _manual_selection(screenshot)
  │     │     └─► user selects regions with OpenCV GUI
  │     │
  │     └─► CacheService.set_regions((1920, 1080), regions)
  │
  ├─► WindowInteractionService.click_region("Raid", upgrade_button)
  │
  ├─► Create UpgradeStateMachine(max_attempts=100)
  │
  ├─► Loop:
  │     │
  │     ├─► ScreenshotService.take_screenshot("Raid")
  │     ├─► ScreenshotService.extract_roi(screenshot, upgrade_bar)
  │     ├─► UpgradeStateMachine.process_frame(roi_image)
  │     │     │
  │     │     ├─► _detect_state(roi_image)
  │     │     │     └─► uses progress_bar.detect_progressbar_state()
  │     │     │
  │     │     ├─► recent_states.append(state)
  │     │     ├─► if state == FAIL: fail_count += 1
  │     │     ├─► _check_stop_condition()
  │     │     │
  │     │     └─► returns (fail_count, stop_reason)
  │     │
  │     └─► if stop_reason: break
  │
  ├─► (finally) NetworkManager.enable_adapters([1])
  │
  └─► returns (fail_count, stop_reason)
       │
       ▼
     CLI displays result to user
```

### Spend Workflow Data Flow

```
User (CLI)
  │
  │ autoraid upgrade spend --fail-count 5
  │
  ▼
CLI Command (upgrade_cli.py)
  │
  │ @inject orchestrator
  │
  ▼
UpgradeOrchestrator.spend_workflow(fail_count=5)
  │
  ├─► NetworkManager.enable_adapters()
  │
  ├─► ScreenshotService.take_screenshot("Raid")
  │
  ├─► LocateRegionService.get_regions(screenshot, window_size)
  │
  ├─► Loop (5 times):
  │     │
  │     ├─► WindowInteractionService.click_region("Raid", upgrade_button)
  │     ├─► time.sleep(0.5)
  │     └─► (if continue_upgrade) click upgrade_button again
  │
  └─► returns {"spent": 5, "success": True}
       │
       ▼
     CLI displays result to user
```

## State Enums and Types

### ProgressBarState

```python
from enum import Enum

class ProgressBarState(Enum):
    """Progress bar state detected from color analysis."""
    FAIL = "fail"                # Red bar
    PROGRESS = "progress"         # Yellow bar
    STANDBY = "standby"           # Black bar (upgraded)
    CONNECTION_ERROR = "connection_error"  # Blue bar
    UNKNOWN = "unknown"           # Unrecognized color
```

### StopCountReason

```python
from enum import Enum

class StopCountReason(Enum):
    """Reason for stopping count workflow."""
    UPGRADED = "upgraded"                        # 4 consecutive STANDBY
    CONNECTION_ERROR = "connection_error"        # 4 consecutive CONNECTION_ERROR
    MAX_ATTEMPTS_REACHED = "max_attempts_reached"  # fail_count >= max_attempts
```

### Region Dictionary Type

```python
from typing import TypedDict

class RegionDict(TypedDict):
    """Dictionary of UI regions."""
    upgrade_bar: tuple[int, int, int, int]      # (left, top, width, height)
    upgrade_button: tuple[int, int, int, int]
    artifact_icon: tuple[int, int, int, int]
```

## Entity Relationships

### Composition Relationships

- **UpgradeOrchestrator** *composes* (uses):
  - CacheService (1:1)
  - ScreenshotService (1:1)
  - LocateRegionService (1:1)
  - WindowInteractionService (1:1)
  - UpgradeStateMachine (1:many via factory)

- **LocateRegionService** *composes* (uses):
  - CacheService (1:1)
  - ScreenshotService (1:1)

- **CacheService** *composes* (wraps):
  - diskcache.Cache (1:1)

### Dependency Injection Relationships

- **DependencyContainer** *provides* (creates):
  - All service instances
  - Configuration
  - External dependencies (diskcache.Cache)

- **CLI Commands** *inject* (receive):
  - UpgradeOrchestrator (via @inject decorator)

### Lifecycle Relationships

- **Singleton services** (shared across application):
  - Live for entire application lifecycle
  - Created once on first access
  - Shared by all workflows

- **Factory services** (per-operation):
  - Created fresh for each workflow
  - Destroyed after workflow completes
  - No state carries over between workflows

## Validation Rules

### UpgradeStateMachine

- `max_attempts` must be > 0
- `recent_states` deque has fixed size of 4
- `fail_count` cannot exceed `max_attempts`
- `roi_image` must be valid numpy array

### CacheService

- `window_size` width and height must be > 0
- `regions` dict must contain required keys (upgrade_bar, upgrade_button, artifact_icon)
- `screenshot` must be valid numpy array

### ScreenshotService

- `window_title` must be non-empty string
- `region` coordinates must be non-negative
- `region` width and height must be > 0

### LocateRegionService

- `screenshot` must be valid numpy array
- `window_size` must match screenshot dimensions
- Detected regions must have valid coordinates

### WindowInteractionService

- `window_title` must be non-empty string
- `region` coordinates must be within window bounds
- Window must exist before interaction

### UpgradeOrchestrator

- `network_adapter_id` elements must be valid adapter IDs
- `max_attempts` must be > 0
- `fail_count` must be >= 0 for spend workflow

## File Organization Summary

```
src/autoraid/
├── services/
│   ├── __init__.py
│   ├── cache_service.py           # CacheService entity
│   ├── screenshot_service.py      # ScreenshotService entity
│   ├── locate_region_service.py   # LocateRegionService entity
│   ├── window_interaction_service.py  # WindowInteractionService entity
│   └── upgrade_orchestrator.py    # UpgradeOrchestrator entity
├── autoupgrade/
│   ├── state_machine.py           # UpgradeStateMachine entity
│   └── ... (existing files)
├── container.py                   # DependencyContainer entity
└── exceptions.py                  # Custom exception classes (NEW)
```

## Next Steps

1. Create `contracts/` directory with service interface protocols (TypedProtocol)
2. Create `quickstart.md` with developer guide and examples
3. Implement Phase 0: DI container infrastructure
4. Implement Phase 1: Extract UpgradeStateMachine
5. Implement remaining phases sequentially
