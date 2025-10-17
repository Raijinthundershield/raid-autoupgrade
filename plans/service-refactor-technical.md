# Service-Based Architecture Refactoring - Technical Details

## Dependency Injection Framework

### Library Choice: `dependency-injector`

**Rationale**:
- Mature library (Trust Score: 6.4)
- 700+ code examples in documentation
- Excellent type hinting support
- Simple patterns (DeclarativeContainer, Singleton/Factory providers)
- Automatic wiring with `@inject` decorator
- Easy testing with container overrides

### Container Structure

```python
from dependency_injector import containers, providers
from diskcache import Cache

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

### CLI Integration

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

### Automatic Injection in Commands

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

## Service Architecture Details

### Provider Lifetime Strategy

**Singleton Providers** (shared instance):
- `CacheService`: Maintains cache state across operations
- `ScreenshotService`: Stateless, but singleton for consistency
- `WindowInteractionService`: Window state management
- `LocateRegionService`: Integrates with other singletons

**Factory Providers** (new instance per call):
- `UpgradeStateMachine`: Fresh state per upgrade operation
- `UpgradeOrchestrator`: Workflow-specific instance

### Service Dependencies Graph

```
Container
├── config (Configuration)
├── disk_cache (Singleton) → diskcache.Cache
│
├── cache_service (Singleton)
│   └── depends on: disk_cache
│
├── screenshot_service (Singleton)
│   └── depends on: (none)
│
├── window_interaction_service (Singleton)
│   └── depends on: (none)
│
├── locate_region_service (Singleton)
│   ├── depends on: cache_service
│   └── depends on: screenshot_service
│
├── state_machine (Factory)
│   └── depends on: (none)
│
└── upgrade_orchestrator (Factory)
    ├── depends on: cache_service
    ├── depends on: screenshot_service
    ├── depends on: locate_region_service
    ├── depends on: window_interaction_service
    └── depends on: state_machine (provider, not instance)
```

### Service Interfaces

#### UpgradeStateMachine
- **Constructor**: No dependencies
- **Key Method**: `process_frame(roi_image: np.ndarray) -> tuple[int, StopCountReason]`
- **State**: Internal deque of last N states, fail counter
- **Output**: Returns fail count and reason when done

#### CacheService
- **Constructor**: `__init__(cache: Cache)`
- **Key Methods**:
  - `create_regions_key(window_size: tuple[int, int]) -> str`
  - `get_regions(window_size: tuple[int, int]) -> dict | None`
  - `set_regions(window_size: tuple[int, int], regions: dict)`
  - `get_screenshot(window_size: tuple[int, int]) -> np.ndarray | None`
  - `set_screenshot(window_size: tuple[int, int], screenshot: np.ndarray)`

#### ScreenshotService
- **Constructor**: No dependencies
- **Key Methods**:
  - `take_screenshot(window_title: str) -> np.ndarray`
  - `window_exists(window_title: str) -> bool`
  - `extract_roi(screenshot: np.ndarray, region: tuple) -> np.ndarray`

#### LocateRegionService
- **Constructor**: `__init__(cache_service: CacheService, screenshot_service: ScreenshotService)`
- **Key Methods**:
  - `get_regions(screenshot: np.ndarray, manual: bool = False) -> dict`
  - `select_regions(screenshot: np.ndarray, manual: bool = False) -> dict`

#### WindowInteractionService
- **Constructor**: No dependencies
- **Key Methods**:
  - `click_region(window_title: str, region: tuple)`
  - `activate_window(window_title: str)`

#### UpgradeOrchestrator
- **Constructor**: Takes all services + state_machine provider
- **Key Methods**:
  - `count_workflow(network_adapter_id: list[int] = None, **kwargs) -> tuple[int, StopCountReason]`
  - `spend_workflow(max_attempts: int, continue_upgrade: bool = False, **kwargs) -> dict`

## Testing Strategy

### Unit Tests with Mocked Dependencies

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

### Test Coverage Priorities

**MUST test** (core logic):
- `UpgradeStateMachine`: All state transitions with fixture images
- `CacheService`: Key generation, get/set operations
- `LocateRegionService`: Automatic detection fallback logic

**SHOULD test** (integration):
- `UpgradeOrchestrator`: Workflow coordination with mocked services
- Error handling in all services

**CAN skip** (manual verification):
- GUI interactions (`ScreenshotService`, `WindowInteractionService`)
- CLI argument parsing

## File Organization

### New Directory Structure

```
src/autoraid/
├── services/
│   ├── __init__.py
│   ├── cache_service.py           # ~50 lines
│   ├── screenshot_service.py      # ~60 lines
│   ├── locate_region_service.py   # ~80 lines
│   ├── window_interaction_service.py  # ~40 lines
│   └── upgrade_orchestrator.py    # ~150 lines
├── autoupgrade/
│   ├── __init__.py
│   ├── state_machine.py           # ~100 lines (NEW)
│   ├── autoupgrade.py             # Simplified after extraction
│   ├── progress_bar.py            # Unchanged
│   ├── locate_upgrade_region.py   # Unchanged (used by LocateRegionService)
│   └── artifact_icon.py           # Unchanged
├── cli/
│   ├── __init__.py
│   ├── cli.py                     # Add container setup
│   ├── upgrade_cli.py             # Simplified with @inject
│   └── network_cli.py             # Minor updates
├── container.py                    # ~60 lines (NEW)
├── interaction.py                  # Possibly deprecated after refactor
├── visualization.py                # Unchanged
├── locate.py                       # Unchanged
└── utils.py                        # Unchanged

test/
├── test_state_machine.py           # NEW
├── test_cache_service.py           # NEW
├── test_screenshot_service.py      # NEW
├── test_locate_region_service.py   # NEW
├── test_upgrade_orchestrator.py    # NEW
├── test_progressbar_state.py       # Existing
└── test_locate.py                  # Existing
```

## Migration Path

### Extracting Functions to Services

**Pattern for extraction**:
1. Identify function to extract (e.g., `create_cache_key_regions()`)
2. Create service class if not exists
3. Move function as method to service
4. Update function signature to use service dependencies
5. Update all callers to use service method
6. Add service to container
7. Wire dependencies via DI

**Example - Cache Key Generation**:

Before:
```python
# In autoupgrade.py
def create_cache_key_regions(window_size: tuple[int, int]) -> str:
    return f"regions_{window_size[0]}_{window_size[1]}"

# Usage
cache_key = create_cache_key_regions(window_size)
regions = cache.get(cache_key)
```

After:
```python
# In cache_service.py
class CacheService:
    def __init__(self, cache: Cache):
        self._cache = cache

    def create_regions_key(self, window_size: tuple[int, int]) -> str:
        return f"regions_{window_size[0]}_{window_size[1]}"

    def get_regions(self, window_size: tuple[int, int]) -> dict | None:
        cache_key = self.create_regions_key(window_size)
        return self._cache.get(cache_key)

# Usage (with DI)
regions = cache_service.get_regions(window_size)
```

### Backward Compatibility During Migration

Each phase maintains backward compatibility by keeping wrapper functions that call the new service implementations. These wrappers are marked deprecated and removed in Phase 8 (Cleanup).

## Configuration Management

### Configuration Provider

The container's `Configuration` provider allows:
- Loading from dict
- Loading from environment variables
- Loading from YAML/JSON files
- Type coercion (e.g., strings to ints)

### Usage Pattern

```python
container = Container()
container.config.from_dict({
    "cache_dir": Path.cwd() / "cache-raid-autoupgrade",
    "debug": False,
    "window_title": "Raid: Shadow Legends",
})

# Services access config through injected dependencies
# No global state or environment variable reads scattered throughout code
```

## Performance Considerations

### Singleton vs Factory Impact

- **Singletons**: Instantiated once on first access, reused afterward
- **Factories**: New instance on each call (minimal overhead for small objects)
- **State Machine**: Factory ensures clean state per operation
- **Orchestrator**: Factory ensures no cross-workflow contamination

### Container Initialization Cost

- Container creation: O(1) - just object instantiation
- Wiring: O(modules) - happens once at startup
- Provider resolution: O(1) - dict lookup
- Service instantiation: Lazy (only when first accessed)

**Impact**: Negligible (<1ms additional startup time)

## Error Handling Strategy

### Service-Level Error Handling

Each service should:
1. Validate inputs (raise `ValueError` for invalid arguments)
2. Catch expected exceptions (e.g., `ImageNotFoundException`)
3. Re-raise unexpected exceptions with context
4. Log errors with structured context

### Orchestrator-Level Error Handling

Orchestrator catches service exceptions and:
1. Logs the error with full context
2. Performs cleanup (e.g., re-enable network)
3. Returns error result or re-raises with user-friendly message

### CLI-Level Error Handling

CLI catches orchestrator exceptions and:
1. Displays user-friendly error message
2. Exits with appropriate status code
3. Suggests remediation steps

## Logging Strategy

### Service Logging Pattern

```python
from loguru import logger

class ExampleService:
    def operation(self, param: str):
        logger.debug(f"ExampleService.operation called with param={param}")
        try:
            result = self._do_work(param)
            logger.debug(f"ExampleService.operation succeeded")
            return result
        except Exception as e:
            logger.error(f"ExampleService.operation failed: {e}")
            raise
```

### Log Levels

- **DEBUG**: Entry/exit of service methods, parameter values
- **INFO**: User-visible state changes, workflow milestones
- **WARNING**: Recoverable errors, fallback scenarios
- **ERROR**: Unrecoverable errors, exceptions

## Benefits of DI Approach

### Testability
- Inject mocks instead of real services
- No global state to reset between tests
- Test containers provide clean isolation

### Flexibility
- Swap implementations (e.g., file cache → redis cache)
- No changes to consumer code
- Configuration-driven behavior

### Clarity
- Container shows all service relationships
- Explicit dependencies in constructors
- No hidden dependencies or globals

### Lifetime Management
- Framework handles service lifecycle
- Singleton vs Factory semantics clear
- No manual singleton pattern implementation
