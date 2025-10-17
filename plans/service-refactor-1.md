# Service-Based Architecture Refactoring Plan v1.1

## Current Architecture Issues

**Problems identified**:
1. **Mixed responsibilities**: `count_upgrade_fails()` combines state machine logic, screenshot capture, caching, and debug output (273-line file)
2. **Hard to test**: Core upgrade counting requires actual Raid window and GUI interaction
3. **Tight coupling**: CLI directly orchestrates all components with business logic embedded
4. **Code duplication**: Cache key generation, screenshot→ROI patterns repeated

## Proposed Services (Simple & Focused)

Following **Constitution Principle I (Simplicity)** and **Principle II (Readability)**:

### 1. **UpgradeStateMachine** (NEW)
- **Purpose**: Pure state machine for upgrade counting logic
- **Input**: Takes ROI images (BGR numpy arrays)
- **Output**: State transitions, fail count, stop reason
- **Why**: Makes core logic testable with fixture images (no GUI needed)
- **File**: `src/autoraid/autoupgrade/state_machine.py`

### 2. **CacheService** (NEW)
- **Purpose**: Centralize all caching operations
- **Responsibility**: Window-size-based keys, get/set regions and screenshots
- **Why**: Caching logic currently scattered across 3+ functions
- **File**: `src/autoraid/services/cache_service.py`

### 3. **ScreenshotService** (NEW)
- **Purpose**: Window screenshot capture + ROI extraction
- **Why**: Consolidates interaction with pyautogui/pygetwindow
- **File**: `src/autoraid/services/screenshot_service.py`

### 4. **LocateRegionService** (RENAMED from RegionService)
- **Purpose**: Automatic detection + manual selection + caching
- **Consolidates**: `select_upgrade_regions()` + cache integration
- **File**: `src/autoraid/services/locate_region_service.py`

### 5. **WindowInteractionService** (RENAMED from ClickService)
- **Purpose**: Region clicking, window activation, and window state management
- **Why**: Isolates all pyautogui/pygetwindow interaction for GUI operations
- **File**: `src/autoraid/services/window_interaction_service.py`

### 6. **UpgradeOrchestrator** (NEW)
- **Purpose**: Coordinates services for count/spend workflows
- **Why**: Moves business logic out of CLI
- **File**: `src/autoraid/services/upgrade_orchestrator.py`

### 7. **ProgressBarStateDetector** (KEEP AS IS)
- Already pure functions, well-tested ✅

## Dependency Injection with `dependency-injector`

We'll use the `dependency-injector` package to wire services together, following these principles:

### Container Structure

```python
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    """Main application container for AutoRaid services."""

    # Configuration
    config = providers.Configuration()

    # Core Services (Singletons - shared state)
    cache_service = providers.Singleton(
        CacheService,
        cache=config.cache,
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

    # State Machine (Factory - new instance per upgrade)
    state_machine = providers.Factory(
        UpgradeStateMachine,
    )

    # Orchestrator (Factory - new instance per workflow)
    upgrade_orchestrator = providers.Factory(
        UpgradeOrchestrator,
        cache_service=cache_service,
        screenshot_service=screenshot_service,
        locate_region_service=locate_region_service,
        window_interaction_service=window_interaction_service,
        state_machine=state_machine,
    )
```

### Wiring Strategy

**Automatic wiring** in CLI module:

```python
# src/autoraid/cli/cli.py
from dependency_injector.wiring import inject, Provide

class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "autoraid.cli.upgrade_cli",
            "autoraid.cli.network_cli",
        ],
    )
    # ... providers ...

# src/autoraid/cli/upgrade_cli.py
@upgrade.command()
@inject
def count(
    network_adapter_id: list[int],
    orchestrator: UpgradeOrchestrator = Provide[Container.upgrade_orchestrator],
):
    """Count the number of upgrade fails."""
    orchestrator.count_workflow(network_adapter_id=network_adapter_id)
```

### Benefits of DI Approach

✅ **Testability**: Easy to inject mocks in tests
✅ **Flexibility**: Swap implementations without changing consumer code
✅ **Clear dependencies**: Container shows all service relationships
✅ **Lifetime management**: Singleton vs Factory provider types
✅ **Configuration**: Centralized config injection

## Phased Refactoring (Each Phase = Runnable State)

### **Phase 0: Setup Dependency Injection Infrastructure** (Foundation)
**Goal**: Add dependency-injector and create basic container structure

**Changes**:
- Add `dependency-injector` to `pyproject.toml`
- Create `src/autoraid/container.py` with basic container
- Wire container in CLI entry point (`cli.py`)
- Add container to Click context object

**Files modified**:
- MODIFY: `pyproject.toml` (add dependency-injector)
- NEW: `src/autoraid/container.py`
- MODIFY: `src/autoraid/cli/cli.py` (create container, wire modules)

**Result**: DI infrastructure ready. Existing code unchanged but container available.

---

### **Phase 1: Extract State Machine** (Core Logic Testable)
**Goal**: Separate pure state machine from I/O operations

**Changes**:
- Create `UpgradeStateMachine` class in `state_machine.py`
- Extract state transition logic from `count_upgrade_fails()`
- `count_upgrade_fails()` becomes thin wrapper calling state machine
- Add comprehensive tests with fixture images
- Add state_machine provider to container

**Files modified**:
- NEW: `src/autoraid/autoupgrade/state_machine.py`
- NEW: `test/test_state_machine.py`
- MODIFY: `src/autoraid/autoupgrade/autoupgrade.py` (make it use state machine)
- MODIFY: `src/autoraid/container.py` (add state_machine provider)

**Result**: State machine testable without GUI. Original code still works.

---

### **Phase 2: Extract Cache Service** (Centralized Caching)
**Goal**: One place for all caching operations

**Changes**:
- Create `CacheService` class
- Move cache key generation functions
- Move get/set operations
- Update callers: `autoupgrade.py`, `upgrade_cli.py`
- Add cache_service provider to container (Singleton)
- Inject via DI where needed

**Files modified**:
- NEW: `src/autoraid/services/cache_service.py`
- NEW: `test/test_cache_service.py`
- MODIFY: `src/autoraid/autoupgrade/autoupgrade.py`
- MODIFY: `src/autoraid/cli/upgrade_cli.py`
- MODIFY: `src/autoraid/container.py` (add cache_service provider)

**Result**: All caching through one service. No scattered cache logic.

---

### **Phase 3: Extract Screenshot Service** (Consolidated Window I/O)
**Goal**: All screenshot operations through one service

**Changes**:
- Create `ScreenshotService` class
- Move `take_screenshot_of_window()`, `window_exists()` from `interaction.py`
- Add ROI extraction method (from `visualization.py`)
- Update callers
- Add screenshot_service provider to container (Singleton)
- Inject via DI

**Files modified**:
- NEW: `src/autoraid/services/screenshot_service.py`
- NEW: `test/test_screenshot_service.py` (mock-based)
- MODIFY: `src/autoraid/autoupgrade/autoupgrade.py`
- MODIFY: `src/autoraid/cli/upgrade_cli.py`
- MODIFY: `src/autoraid/container.py` (add screenshot_service provider)

**Result**: Single point for all window screenshot operations.

---

### **Phase 4: Extract LocateRegion Service** (Unified Region Management)
**Goal**: One service handles all region detection and selection

**Changes**:
- Create `LocateRegionService` class
- Consolidate automatic detection + manual fallback
- Integrate with `CacheService` via DI
- Move `select_upgrade_regions()`, `get_regions()` logic
- Add locate_region_service provider to container (Singleton)
- Inject cache_service and screenshot_service

**Files modified**:
- NEW: `src/autoraid/services/locate_region_service.py`
- NEW: `test/test_locate_region_service.py`
- MODIFY: `src/autoraid/autoupgrade/autoupgrade.py`
- MODIFY: `src/autoraid/cli/upgrade_cli.py`
- MODIFY: `src/autoraid/container.py` (add locate_region_service provider)

**Result**: Region management in one place, testable.

---

### **Phase 5: Extract WindowInteraction Service** (Isolated GUI Operations)
**Goal**: Separate clicking and window operations from other interaction logic

**Changes**:
- Create `WindowInteractionService` class
- Move `click_region_center()` from `interaction.py`
- Add window activation, `window_exists()` if not in ScreenshotService
- Add window_interaction_service provider to container (Singleton)

**Files modified**:
- NEW: `src/autoraid/services/window_interaction_service.py`
- MODIFY: `src/autoraid/cli/upgrade_cli.py`
- MODIFY: `src/autoraid/container.py` (add window_interaction_service provider)

**Result**: All clicking and window interaction through one service.

---

### **Phase 6: Create Orchestrator** (Business Logic Layer)
**Goal**: Coordinate all services for workflows

**Changes**:
- Create `UpgradeOrchestrator` class
- Implement `count_workflow()` and `spend_workflow()` methods
- Move orchestration logic from CLI commands
- Integrate network management, debug output coordination
- Add upgrade_orchestrator provider to container (Factory)
- Inject all required services via constructor

**Files modified**:
- NEW: `src/autoraid/services/upgrade_orchestrator.py`
- NEW: `test/test_upgrade_orchestrator.py` (integration tests)
- MODIFY: `src/autoraid/container.py` (add upgrade_orchestrator provider)

**Result**: Business logic separated from CLI presentation.

---

### **Phase 7: Simplify CLI with DI** (Thin Presentation Layer)
**Goal**: CLI becomes thin wrapper using @inject decorator

**Changes**:
- Use `@inject` decorator on CLI commands
- Inject `UpgradeOrchestrator` via `Provide[Container.upgrade_orchestrator]`
- Update `count()` command to call `orchestrator.count_workflow()`
- Update `spend()` command to call `orchestrator.spend_workflow()`
- Remove business logic from CLI
- CLI only handles: argument parsing, context setup, output formatting

**Files modified**:
- MODIFY: `src/autoraid/cli/upgrade_cli.py` (major simplification, add @inject)
- MODIFY: `src/autoraid/cli/cli.py` (ensure wiring configuration)

**Result**: Clean separation. CLI is thin, testable business logic in orchestrator.

---

### **Phase 8: Cleanup** (Optional Refinement)
**Goal**: Remove duplicated code, consolidate utilities

**Changes**:
- Deprecate/remove old functions in `autoupgrade.py` if no longer needed
- Update `interaction.py` (may become simpler or merge into services)
- Documentation updates
- Add container diagram to CLAUDE.md

**Files modified**:
- MODIFY: `src/autoraid/autoupgrade/autoupgrade.py`
- MODIFY: `src/autoraid/interaction.py`
- MODIFY: `CLAUDE.md` (architecture section with DI container info)

**Result**: Clean codebase with no dead code.

---

## Testing Strategy (Constitution Principle III: Pragmatic Testing)

### Unit Tests (with DI)

**MUST test**:
- ✅ `UpgradeStateMachine`: State transitions with fixture images (pure logic)
- ✅ `CacheService`: Key generation, get/set operations (mocked diskcache)
- ✅ `LocateRegionService`: Automatic detection fallback logic (mocked dependencies)

**SHOULD test**:
- `UpgradeOrchestrator`: Integration tests with mocked services (DI makes this easy!)
- Error handling in services

**CAN skip** (manual testing):
- GUI interactions in `ScreenshotService`, `WindowInteractionService` (hard to automate Windows GUI)
- CLI argument parsing (simple Click decorators)

### Testing with DI Container

```python
# test/test_upgrade_orchestrator.py
import pytest
from unittest.mock import Mock
from dependency_injector import containers, providers

from autoraid.services.upgrade_orchestrator import UpgradeOrchestrator

class TestContainer(containers.DeclarativeContainer):
    """Test container with mocked services."""

    cache_service = providers.Singleton(Mock)
    screenshot_service = providers.Singleton(Mock)
    locate_region_service = providers.Singleton(Mock)
    window_interaction_service = providers.Singleton(Mock)
    state_machine = providers.Factory(Mock)

    orchestrator = providers.Factory(
        UpgradeOrchestrator,
        cache_service=cache_service,
        screenshot_service=screenshot_service,
        locate_region_service=locate_region_service,
        window_interaction_service=window_interaction_service,
        state_machine=state_machine,
    )

@pytest.fixture
def container():
    return TestContainer()

def test_count_workflow(container):
    orchestrator = container.orchestrator()
    # Mock service behavior
    container.locate_region_service().get_regions.return_value = {...}
    # Test workflow
    result = orchestrator.count_workflow(network_adapter_id=[1])
    # Assertions
    assert container.window_interaction_service().click_region.called
```

## Benefits Aligned with Constitution

✅ **Simplicity** (Principle I): Flat services, no deep hierarchies, clear single responsibilities
✅ **Readability** (Principle II): Service names describe exactly what they do
✅ **Pragmatic Testing** (Principle III): Core logic testable, GUI parts manually tested, DI enables easy mocking
✅ **Debug-Friendly** (Principle IV): Services can log at entry/exit, clear data flow, container shows wiring
✅ **Incremental** (Principle V): Each phase is shippable, iterative improvement

## Estimated Lines of Code per Service

- `UpgradeStateMachine`: ~100 lines (extracted from 273-line file)
- `CacheService`: ~50 lines
- `ScreenshotService`: ~60 lines
- `LocateRegionService`: ~80 lines
- `WindowInteractionService`: ~40 lines
- `UpgradeOrchestrator`: ~150 lines
- `Container`: ~60 lines (DI configuration)

**Total**: ~540 lines across 6 services + container vs. current 273 lines in one file + 360 in CLI

## Container Wiring Example

```python
# src/autoraid/container.py
from dependency_injector import containers, providers
from diskcache import Cache

from autoraid.services.cache_service import CacheService
from autoraid.services.screenshot_service import ScreenshotService
from autoraid.services.locate_region_service import LocateRegionService
from autoraid.services.window_interaction_service import WindowInteractionService
from autoraid.services.upgrade_orchestrator import UpgradeOrchestrator
from autoraid.autoupgrade.state_machine import UpgradeStateMachine


class Container(containers.DeclarativeContainer):
    """Main dependency injection container for AutoRaid."""

    # Wiring configuration - automatically wire these modules
    wiring_config = containers.WiringConfiguration(
        modules=[
            "autoraid.cli.upgrade_cli",
            "autoraid.cli.network_cli",
        ],
    )

    # Configuration
    config = providers.Configuration()

    # External dependencies
    disk_cache = providers.Singleton(
        Cache,
        directory=config.cache_dir,
    )

    # Core Services (Singletons - shared state)
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

    # State Machine (Factory - new instance per upgrade)
    state_machine = providers.Factory(
        UpgradeStateMachine,
    )

    # Orchestrator (Factory - new instance per workflow)
    upgrade_orchestrator = providers.Factory(
        UpgradeOrchestrator,
        cache_service=cache_service,
        screenshot_service=screenshot_service,
        locate_region_service=locate_region_service,
        window_interaction_service=window_interaction_service,
        state_machine=state_machine,
    )
```

```python
# src/autoraid/cli/cli.py
from pathlib import Path
import click
from autoraid.container import Container

@click.group()
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.pass_context
def cli(ctx, debug):
    """AutoRaid CLI application."""
    # Create container
    container = Container()

    # Configure container
    container.config.from_dict({
        "cache_dir": Path.cwd() / "cache-raid-autoupgrade",
        "debug": debug,
    })

    # Wire container (happens automatically due to wiring_config)
    # container.wire() is called automatically

    # Store in context for non-DI access if needed
    ctx.obj = {"container": container, "debug": debug}
```

```python
# src/autoraid/cli/upgrade_cli.py
from dependency_injector.wiring import inject, Provide
from autoraid.container import Container
from autoraid.services.upgrade_orchestrator import UpgradeOrchestrator

@upgrade.command()
@click.option("--network-adapter-id", "-n", type=int, multiple=True)
@inject
def count(
    network_adapter_id: list[int],
    orchestrator: UpgradeOrchestrator = Provide[Container.upgrade_orchestrator],
):
    """Count the number of upgrade fails."""
    orchestrator.count_workflow(network_adapter_id=list(network_adapter_id))
```

## Risks & Mitigation

**Risk**: Over-engineering for a one-person project
**Mitigation**: Each service is simple (<150 lines), provides clear value, improves testability. DI makes testing trivial.

**Risk**: Breaking existing functionality
**Mitigation**: Each phase keeps code runnable, incremental refactoring, tests guard against regressions

**Risk**: More files to navigate
**Mitigation**: Clear naming convention (`*_service.py`), grouped in `services/` directory, container shows all wiring

**Risk**: Learning curve for dependency-injector
**Mitigation**: Use simple patterns (DeclarativeContainer, Singleton/Factory providers, @inject decorator). Documentation is excellent.

**Risk**: Added dependency
**Mitigation**: `dependency-injector` is well-maintained (6.4 trust score), popular, and provides significant value for testing
