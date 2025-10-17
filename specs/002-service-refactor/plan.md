# Implementation Plan: Service-Based Architecture Refactoring

**Branch**: `002-service-refactor` | **Date**: 2025-10-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-service-refactor/spec.md`

## Summary

Refactor the AutoRaid upgrade tool from monolithic functions into a service-based architecture with dependency injection. The goal is to improve testability (state machine testable with fixture images), maintainability (services <200 LOC), and debuggability (clear service boundaries with logging). The refactoring will use `dependency-injector` for DI container management and will be performed in 9 sequential phases, each leaving the codebase in a working state. User-facing CLI commands and cache formats remain unchanged for backward compatibility.

## Technical Context

**Language/Version**: Python 3.11 (existing project constraint)
**Primary Dependencies**:
- **Existing**: opencv-python, pyautogui, pygetwindow, click, diskcache, loguru, rich
- **New**: dependency-injector (6.4 trust score, 700+ examples, excellent type hinting)

**Storage**: diskcache for persistent caching (cache-raid-autoupgrade/ directory)
**Testing**: pytest with unittest.mock for service mocking, fixture images from test/images/
**Target Platform**: Windows 10+ only (uses WMI, pywinauto)
**Project Type**: Single CLI application with service layer
**Performance Goals**:
- DI container initialization <100ms
- State machine test suite <1 second
- No runtime performance degradation vs current implementation

**Constraints**:
- Backward compatibility with existing cache keys (regions_{width}_{height})
- CLI signatures unchanged (autoraid upgrade count/spend)
- Each refactoring phase must pass all tests
- Services <200 LOC each, CLI commands <20 LOC
- No third-party DI frameworks beyond dependency-injector
- Fix-forward approach (no rollbacks during phases)

**Scale/Scope**:
- 7 services to extract (UpgradeStateMachine, CacheService, ScreenshotService, LocateRegionService, WindowInteractionService, UpgradeOrchestrator, DependencyContainer)
- ~600 lines of service code to create
- 5 new unit test files
- 9 sequential refactoring phases

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I - Simplicity Over Complexity

**Status**: ✅ PASS with JUSTIFICATION

**Evaluation**:
- ✅ Service pattern keeps each service <200 LOC (simpler than current monolithic functions)
- ✅ Explicit constructor dependencies (no magic, clear relationships)
- ⚠️ Introducing DI framework (`dependency-injector`) adds dependency

**Justification for DI Framework**:
The `dependency-injector` library is justified because:
1. **Simpler than manual DI**: Eliminates manual singleton management and service wiring boilerplate
2. **Explicit dependencies**: Type-hinted constructors make relationships clear (vs hidden global imports)
3. **Testability**: Container overrides for mocking are simpler than manual dependency replacement
4. **Mature, battle-tested**: 700+ examples, stable API, good documentation

**Simpler Alternative Rejected**: Manual dependency injection with global service instances was considered but rejected because:
- Requires manual singleton pattern implementation
- Global state complicates testing
- Hidden dependencies in module-level imports
- More boilerplate than using a mature library

### Principle II - Readability First

**Status**: ✅ PASS

**Evaluation**:
- ✅ Service names are descriptive (CacheService, ScreenshotService, UpgradeOrchestrator)
- ✅ Clear module organization (src/autoraid/services/)
- ✅ Explicit dependencies in constructors with type hints
- ✅ Service responsibilities documented in docstrings
- ✅ Container shows all wiring relationships in one place

### Principle III - Pragmatic Testing

**Status**: ✅ PASS

**Evaluation**:
- ✅ Focus on core logic: UpgradeStateMachine with fixture images (MUST test)
- ✅ Pragmatic approach: Skip GUI automation tests (manual verification)
- ✅ Service mocking enables fast unit tests without external dependencies
- ⚠️ User note: "Only make concise smoke tests" - will prioritize smoke tests over comprehensive coverage

**Testing Strategy**:
- **MUST test**: UpgradeStateMachine state transitions, CacheService key generation
- **SHOULD test**: UpgradeOrchestrator workflow coordination with mocks
- **CAN skip**: ScreenshotService (GUI dependent), WindowInteractionService (GUI dependent)
- **Smoke tests**: Each service has 1-2 smoke tests verifying basic functionality

### Principle IV - Debug-Friendly Architecture

**Status**: ✅ PASS

**Evaluation**:
- ✅ Service boundaries with entry/exit logging (DEBUG level)
- ✅ Workflow milestones at INFO level
- ✅ Debug mode continues to save screenshots to cache-raid-autoupgrade/debug/
- ✅ Service name prefixes in logs (e.g., [ScreenshotService])
- ✅ Container wiring visible and inspectable

### Principle V - Incremental Improvement Over Perfection

**Status**: ✅ PASS

**Evaluation**:
- ✅ 9 sequential phases, each shippable
- ✅ Fix-forward approach (no perfect phase required before moving on)
- ✅ Backward compatibility ensures existing workflows keep working
- ✅ Refactor only - no new features added
- ✅ Minimal testing scope (smoke tests, not 100% coverage)

**Gate Result**: ✅ **PASSED** - Proceed to Phase 0

## Project Structure

### Documentation (this feature)

```
specs/002-service-refactor/
├── plan.md              # This file
├── research.md          # Phase 0: DI framework evaluation and best practices
├── data-model.md        # Phase 1: Service entities and relationships
├── quickstart.md        # Phase 1: Developer guide for service architecture
├── contracts/           # Phase 1: Service interface definitions
│   ├── cache_service.py
│   ├── screenshot_service.py
│   ├── locate_region_service.py
│   ├── window_interaction_service.py
│   ├── upgrade_state_machine.py
│   └── upgrade_orchestrator.py
└── tasks.md             # Phase 2: Generated by /speckit.tasks (NOT part of /speckit.plan)
```

### Source Code (repository root)

```
src/autoraid/
├── services/            # NEW: Service layer
│   ├── __init__.py
│   ├── cache_service.py              (~50 LOC)
│   ├── screenshot_service.py         (~60 LOC)
│   ├── locate_region_service.py      (~80 LOC)
│   ├── window_interaction_service.py (~40 LOC)
│   └── upgrade_orchestrator.py       (~150 LOC)
├── autoupgrade/
│   ├── __init__.py
│   ├── state_machine.py              (~100 LOC, NEW - extracted from autoupgrade.py)
│   ├── autoupgrade.py                (simplified after extraction)
│   ├── progress_bar.py               (unchanged - pure functions)
│   ├── locate_upgrade_region.py      (unchanged - used by LocateRegionService)
│   └── artifact_icon.py              (unchanged)
├── cli/
│   ├── __init__.py
│   ├── cli.py                        (add container setup)
│   ├── upgrade_cli.py                (refactored to use @inject decorator)
│   └── network_cli.py                (minor updates if needed)
├── container.py         # NEW: DependencyContainer definition (~60 LOC)
├── interaction.py       # (possibly deprecated after refactor - Phase 8 decision)
├── network.py           # (unchanged - used by orchestrator, not a service)
├── visualization.py     # (unchanged)
├── locate.py            # (unchanged)
├── average_color.py     # (unchanged)
└── utils.py             # (unchanged)

test/
├── test_state_machine.py              # NEW: State machine unit tests with fixtures
├── test_cache_service.py              # NEW: Cache key generation, get/set operations
├── test_screenshot_service.py         # NEW: ROI extraction logic (mock window capture)
├── test_locate_region_service.py      # NEW: Fallback logic with mocked dependencies
├── test_upgrade_orchestrator.py       # NEW: Workflow coordination with mocked services
├── test_progressbar_state.py          # EXISTING: No changes needed
└── test_locate.py                     # EXISTING: No changes needed
```

**Structure Decision**: Single project structure (Option 1) is appropriate. This is a CLI application with a service layer, not a web app or mobile app. The service layer sits between the CLI (presentation) and existing logic (domain). No need for separate backend/frontend or multi-project structure.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Adding DI framework (dependency-injector) | Eliminates manual singleton management, provides type-safe dependency resolution, simplifies testing with container overrides | Manual DI with global singletons: Requires boilerplate singleton patterns, global state complicates testing, hidden dependencies in imports, more code to maintain |

## Phase 0: Research & Technical Decisions

**Goal**: Document DI framework choice, best practices, and architectural patterns.

**Output**: `research.md` with the following sections:

### 1. Dependency Injection Framework Selection

**Decision**: Use `dependency-injector` library

**Rationale**:
- Mature library (Trust Score: 6.4, 700+ code examples)
- Excellent type hinting support (Python 3.8+)
- Simple patterns: DeclarativeContainer, Singleton/Factory providers
- Automatic wiring with `@inject` decorator
- Easy testing with container overrides
- No complex configuration files (Python-based DSL)
- Active maintenance and community support

**Alternatives Considered**:
1. **Manual DI (no library)**:
   - Pros: No dependencies, full control
   - Cons: Boilerplate singleton management, testing complexity, hidden global dependencies
   - **Rejected**: Increases maintenance burden vs mature library

2. **`injector` library**:
   - Pros: More Pythonic, simpler API
   - Cons: Less documentation, fewer examples, weaker type hinting
   - **Rejected**: dependency-injector has better docs and examples

3. **`python-dependency-injector` (same as dependency-injector)**:
   - This is the same library (dependency-injector is the package name)

### 2. Service Lifetime Best Practices

**Decision**: Singletons for stateful/integration services, Factories for workflow services

**Singleton Services** (shared instance across application):
- `CacheService`: Wraps diskcache.Cache, maintains cache state
- `ScreenshotService`: Stateless but singleton for consistency
- `WindowInteractionService`: Manages window state
- `LocateRegionService`: Integrates with other singletons

**Factory Services** (new instance per operation):
- `UpgradeStateMachine`: Requires fresh state per upgrade workflow
- `UpgradeOrchestrator`: Workflow-specific instance to avoid state contamination

**Rationale**:
- Singletons reduce object creation overhead for reusable services
- Factories ensure clean state for stateful workflows
- Pattern aligns with Spring Framework and NestJS conventions

### 3. Testing Patterns with DI

**Pattern**: Test containers with mocked providers

**Example**:
```python
from dependency_injector import containers, providers
from unittest.mock import Mock

class TestContainer(containers.DeclarativeContainer):
    cache_service = providers.Singleton(Mock)
    screenshot_service = providers.Singleton(Mock)
    orchestrator = providers.Factory(
        UpgradeOrchestrator,
        cache_service=cache_service,
        screenshot_service=screenshot_service,
    )

@pytest.fixture
def container():
    return TestContainer()

def test_workflow(container):
    orchestrator = container.orchestrator()
    # Configure mocks
    container.screenshot_service().take_screenshot.return_value = fake_image
    # Test orchestrator
    result = orchestrator.count_workflow()
    # Assert mock calls
    assert container.screenshot_service().take_screenshot.called
```

**Best Practices**:
- Use `unittest.mock.Mock` for simple mocks
- Use `unittest.mock.MagicMock` when magic methods needed
- Configure mock return values before injecting
- Assert on mock method calls to verify service coordination

### 4. Migration Strategy for Monolithic Functions

**Pattern**: Extract function → Service method → Wire via DI

**Steps**:
1. Create service class if not exists
2. Move function logic to service method
3. Add dependencies to service constructor
4. Register service in container
5. Update callers to use injected service
6. Keep deprecated wrapper for backward compat (Phase 8 cleanup)

**Example Migration** (Cache Key Generation):

Before:
```python
# In autoupgrade.py
def create_cache_key_regions(window_size: tuple[int, int]) -> str:
    return f"regions_{window_size[0]}_{window_size[1]}"
```

After:
```python
# In services/cache_service.py
class CacheService:
    def create_regions_key(self, window_size: tuple[int, int]) -> str:
        return f"regions_{window_size[0]}_{window_size[1]}"
```

### 5. Error Handling Strategy

**Pattern**: Fail fast with descriptive exceptions

**Service Level**:
- Validate inputs → raise `ValueError`
- Expected errors → raise custom exceptions (e.g., `CacheInitializationError`)
- Unexpected errors → re-raise with context

**Orchestrator Level**:
- Catch service exceptions
- Log with full context
- Perform cleanup (finally block for network re-enable)
- Return error result or re-raise with user-friendly message

**CLI Level**:
- Catch orchestrator exceptions
- Display user-friendly error message
- Exit with appropriate code
- Suggest remediation

### 6. Logging Strategy

**Levels**:
- **DEBUG**: Entry/exit of service methods, parameter values
- **INFO**: User-visible milestones ("Starting count workflow", "Captured screenshot")
- **WARNING**: Recoverable errors, fallback scenarios
- **ERROR**: Unrecoverable errors, exceptions

**Pattern**:
```python
from loguru import logger

class ExampleService:
    def operation(self, param: str):
        logger.info(f"[ExampleService] Starting operation")
        logger.debug(f"[ExampleService] operation called with param={param}")
        try:
            result = self._do_work(param)
            logger.debug(f"[ExampleService] operation succeeded")
            return result
        except Exception as e:
            logger.error(f"[ExampleService] operation failed: {e}")
            raise
```

**Service Prefixes**: Each service logs with `[ServiceName]` prefix to aid debugging

## Phase 1: Design & Contracts

**Goal**: Define service entities, interfaces, and developer quickstart guide.

**Prerequisites**: `research.md` complete

### Outputs

#### 1. data-model.md

**Service Entities**:

**UpgradeStateMachine**:
- **Purpose**: Track upgrade attempt states and count failures
- **State**:
  - `recent_states: deque[ProgressBarState]` (maxlen=4)
  - `fail_count: int`
  - `max_attempts: int`
- **Methods**:
  - `process_frame(roi_image: np.ndarray) -> tuple[int, StopCountReason | None]`
  - `_detect_state(roi_image: np.ndarray) -> ProgressBarState`
  - `_check_stop_condition() -> StopCountReason | None`
- **State Transitions**: fail → progress → standby (upgraded), fail → connection_error
- **Stop Conditions**: 4 consecutive standby, 4 consecutive connection_error, max_attempts reached

**CacheService**:
- **Purpose**: Centralize caching operations for regions and screenshots
- **Dependencies**: `diskcache.Cache`
- **Methods**:
  - `create_regions_key(window_size: tuple[int, int]) -> str`
  - `get_regions(window_size: tuple[int, int]) -> dict | None`
  - `set_regions(window_size: tuple[int, int], regions: dict) -> None`
  - `get_screenshot(window_size: tuple[int, int]) -> np.ndarray | None`
  - `set_screenshot(window_size: tuple[int, int], screenshot: np.ndarray) -> None`
- **Cache Keys**: `regions_{width}_{height}`, `screenshot_{width}_{height}`

**ScreenshotService**:
- **Purpose**: Capture window screenshots and extract regions of interest
- **Dependencies**: None (uses pyautogui, pygetwindow)
- **Methods**:
  - `take_screenshot(window_title: str) -> np.ndarray`
  - `window_exists(window_title: str) -> bool`
  - `extract_roi(screenshot: np.ndarray, region: tuple[int, int, int, int]) -> np.ndarray`
- **Region Format**: (left, top, width, height)

**LocateRegionService**:
- **Purpose**: Detect upgrade UI regions (automatic or manual)
- **Dependencies**: `CacheService`, `ScreenshotService`
- **Methods**:
  - `get_regions(screenshot: np.ndarray, window_size: tuple[int, int], manual: bool = False) -> dict`
  - `_try_automatic_detection(screenshot: np.ndarray) -> dict | None`
  - `_manual_selection(screenshot: np.ndarray) -> dict`
- **Region Keys**: `upgrade_bar`, `upgrade_button`, `artifact_icon`

**WindowInteractionService**:
- **Purpose**: Click regions and activate windows
- **Dependencies**: None (uses pyautogui, pygetwindow)
- **Methods**:
  - `click_region(window_title: str, region: tuple[int, int, int, int]) -> None`
  - `activate_window(window_title: str) -> None`

**UpgradeOrchestrator**:
- **Purpose**: Coordinate services to execute count/spend workflows
- **Dependencies**: `CacheService`, `ScreenshotService`, `LocateRegionService`, `WindowInteractionService`, `UpgradeStateMachine` (provider)
- **Methods**:
  - `count_workflow(network_adapter_id: list[int] | None = None, max_attempts: int = 100) -> tuple[int, StopCountReason]`
  - `spend_workflow(fail_count: int, max_attempts: int, continue_upgrade: bool = False) -> dict`
- **Workflow Steps**: See contracts/upgrade_orchestrator.py for detailed flowcharts

**DependencyContainer**:
- **Purpose**: Wire all services with explicit dependencies
- **Base Class**: `containers.DeclarativeContainer`
- **Providers**:
  - Singletons: cache_service, screenshot_service, window_interaction_service, locate_region_service
  - Factories: state_machine, upgrade_orchestrator
- **Wiring**: `autoraid.cli.upgrade_cli`, `autoraid.cli.network_cli`

#### 2. contracts/

Create Python protocol files for each service defining interfaces:

**contracts/cache_service.py**:
```python
from typing import Protocol
import numpy as np

class CacheServiceProtocol(Protocol):
    """Interface for cache operations."""

    def create_regions_key(self, window_size: tuple[int, int]) -> str:
        """Generate cache key for regions based on window size."""
        ...

    def get_regions(self, window_size: tuple[int, int]) -> dict | None:
        """Retrieve cached regions for window size."""
        ...

    def set_regions(self, window_size: tuple[int, int], regions: dict) -> None:
        """Store regions in cache for window size."""
        ...

    def get_screenshot(self, window_size: tuple[int, int]) -> np.ndarray | None:
        """Retrieve cached screenshot for window size."""
        ...

    def set_screenshot(self, window_size: tuple[int, int], screenshot: np.ndarray) -> None:
        """Store screenshot in cache for window size."""
        ...
```

**contracts/screenshot_service.py**:
```python
from typing import Protocol
import numpy as np

class ScreenshotServiceProtocol(Protocol):
    """Interface for screenshot operations."""

    def take_screenshot(self, window_title: str) -> np.ndarray:
        """Capture screenshot of window with given title."""
        ...

    def window_exists(self, window_title: str) -> bool:
        """Check if window with title exists."""
        ...

    def extract_roi(self, screenshot: np.ndarray, region: tuple[int, int, int, int]) -> np.ndarray:
        """Extract region of interest from screenshot."""
        ...
```

**contracts/locate_region_service.py**:
```python
from typing import Protocol
import numpy as np

class LocateRegionServiceProtocol(Protocol):
    """Interface for region detection."""

    def get_regions(
        self,
        screenshot: np.ndarray,
        window_size: tuple[int, int],
        manual: bool = False
    ) -> dict:
        """Get upgrade UI regions (automatic or manual selection)."""
        ...
```

**contracts/window_interaction_service.py**:
```python
from typing import Protocol

class WindowInteractionServiceProtocol(Protocol):
    """Interface for window interaction."""

    def click_region(self, window_title: str, region: tuple[int, int, int, int]) -> None:
        """Click center of region within window."""
        ...

    def activate_window(self, window_title: str) -> None:
        """Bring window to foreground."""
        ...
```

**contracts/upgrade_state_machine.py**:
```python
from typing import Protocol
from enum import Enum
import numpy as np

class ProgressBarState(Enum):
    FAIL = "fail"
    PROGRESS = "progress"
    STANDBY = "standby"
    CONNECTION_ERROR = "connection_error"
    UNKNOWN = "unknown"

class StopCountReason(Enum):
    UPGRADED = "upgraded"
    CONNECTION_ERROR = "connection_error"
    MAX_ATTEMPTS_REACHED = "max_attempts_reached"

class UpgradeStateMachineProtocol(Protocol):
    """Interface for upgrade state tracking."""

    def process_frame(self, roi_image: np.ndarray) -> tuple[int, StopCountReason | None]:
        """Process progress bar frame and return (fail_count, stop_reason)."""
        ...
```

**contracts/upgrade_orchestrator.py**:
```python
from typing import Protocol

class UpgradeOrchestratorProtocol(Protocol):
    """Interface for upgrade workflow orchestration."""

    def count_workflow(
        self,
        network_adapter_id: list[int] | None = None,
        max_attempts: int = 100
    ) -> tuple[int, StopCountReason]:
        """Execute count workflow and return (fail_count, stop_reason)."""
        ...

    def spend_workflow(
        self,
        fail_count: int,
        max_attempts: int,
        continue_upgrade: bool = False
    ) -> dict:
        """Execute spend workflow and return result summary."""
        ...
```

#### 3. quickstart.md

**Content**:
- Architecture overview diagram (ASCII art showing service dependencies)
- Quick start guide for adding a new service
- Testing guide for mocking services
- Debugging guide for service logging
- Common patterns (extracting functions to services)
- Troubleshooting (container resolution errors)

**Example Section** (Service Creation):
```markdown
## Adding a New Service

1. Create service file in `src/autoraid/services/my_service.py`
2. Define service class with typed dependencies in constructor
3. Implement service methods
4. Add protocol to `contracts/my_service.py`
5. Register provider in `container.py`
6. Wire module in container if using @inject
7. Add smoke test to `test/test_my_service.py`

Example:

\```python
# services/my_service.py
from dependency_injector.wiring import inject

class MyService:
    def __init__(self, cache_service: CacheService):
        self._cache = cache_service

    def operation(self) -> str:
        # Implementation
        return "result"

# container.py
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    # ... other services
    my_service = providers.Singleton(
        MyService,
        cache_service=cache_service,
    )
\```
```

## Constitution Check (Post-Design)

**Re-evaluation after Phase 1 design**:

### Principle I - Simplicity Over Complexity

**Status**: ✅ PASS

**Changes**: None - service interfaces are straightforward protocols with clear methods. No complex abstractions introduced.

### Principle II - Readability First

**Status**: ✅ PASS

**Changes**: Contracts make service interfaces explicit and self-documenting. Protocol definitions serve as living documentation.

### Principle III - Pragmatic Testing

**Status**: ✅ PASS

**Changes**: Testing strategy confirmed - protocols enable easy mocking, smoke tests prioritized per user guidance.

### Principle IV - Debug-Friendly Architecture

**Status**: ✅ PASS

**Changes**: Service logging patterns documented, prefix convention established.

### Principle V - Incremental Improvement Over Perfection

**Status**: ✅ PASS

**Changes**: Phase plan remains incremental and safe.

**Gate Result**: ✅ **PASSED** - Ready for Phase 2 (task generation via `/speckit.tasks`)

## Next Steps

1. **Review this plan**: Ensure technical context and constitution checks are accurate
2. **Run `/speckit.tasks`**: Generate phase-by-phase implementation tasks from this plan
3. **Begin Phase 0**: Create research.md documenting DI decisions
4. **Begin Phase 1**: Create data-model.md, contracts/, and quickstart.md
5. **Update agent context**: Run `.specify/scripts/powershell/update-agent-context.ps1 -AgentType claude`
6. **Begin implementation**: Follow tasks.md for sequential phase execution

## Implementation Phases Overview

The detailed tasks will be generated by `/speckit.tasks`, but here's the high-level phase structure:

- **Phase 0**: Setup DI container infrastructure
- **Phase 1**: Extract UpgradeStateMachine
- **Phase 2**: Extract CacheService
- **Phase 3**: Extract ScreenshotService
- **Phase 4**: Extract LocateRegionService
- **Phase 5**: Extract WindowInteractionService
- **Phase 6**: Create UpgradeOrchestrator
- **Phase 7**: Refactor CLI to use DI
- **Phase 8**: Cleanup and remove deprecated wrappers

Each phase includes: implementation → tests → smoke test → commit.
