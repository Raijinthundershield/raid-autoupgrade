# Quick Start: Service-Based Architecture

**Date**: 2025-10-17
**Feature**: Service-Based Architecture Refactoring
**Branch**: `002-service-refactor`

## Overview

This guide helps developers understand and work with the refactored service-based architecture. It covers the architecture overview, adding new services, testing with mocks, debugging, and common patterns.

## Architecture Overview

### Service Dependency Graph

```
CLI Commands (upgrade_cli.py)
    │
    │ @inject
    ▼
UpgradeOrchestrator (Factory)
    ├──► CacheService (Singleton)
    │      └──► diskcache.Cache
    ├──► ScreenshotService (Singleton)
    ├──► LocateRegionService (Singleton)
    │      ├──► CacheService
    │      └──► ScreenshotService
    ├──► WindowInteractionService (Singleton)
    └──► UpgradeStateMachine (Factory via provider)
```

### Key Concepts

**Dependency Injection Container**:
- Wires all services with explicit dependencies
- Lives in `src/autoraid/container.py`
- Uses `dependency-injector` library

**Service Lifetimes**:
- **Singleton**: Shared instance across application (CacheService, ScreenshotService, etc.)
- **Factory**: New instance per operation (UpgradeStateMachine, UpgradeOrchestrator)

**Service Protocols**:
- Define interfaces in `specs/002-service-refactor/contracts/`
- Enable type checking and clear contracts
- Make mocking easier in tests

## Quick Reference

### Project Structure

```
src/autoraid/
├── services/                  # Service layer
│   ├── cache_service.py
│   ├── screenshot_service.py
│   ├── locate_region_service.py
│   ├── window_interaction_service.py
│   └── upgrade_orchestrator.py
├── autoupgrade/
│   ├── state_machine.py       # NEW: Extracted state machine
│   └── ... (existing files)
├── container.py               # NEW: DI container
└── exceptions.py              # NEW: Custom exceptions

test/
├── test_state_machine.py      # NEW: State machine unit tests
├── test_cache_service.py      # NEW: Cache service tests
├── test_screenshot_service.py # NEW: Screenshot service tests
├── test_locate_region_service.py  # NEW: Locate region tests
└── test_upgrade_orchestrator.py   # NEW: Orchestrator tests
```

### Running the Tool

```bash
# Normal mode (INFO logging)
uv run autoraid upgrade count -n 1

# Debug mode (DEBUG logging + debug artifacts)
uv run autoraid --debug upgrade count -n 1

# Spend workflow
uv run autoraid upgrade spend --fail-count 5
```

### Running Tests

```bash
# All tests
uv run pytest

# Specific service tests
uv run pytest test/test_cache_service.py

# With coverage
uv run pytest --cov=autoraid --cov-report=html
```

## Adding a New Service

### Step 1: Create Service Class

```python
# src/autoraid/services/my_service.py
from loguru import logger

class MyService:
    """Service description.

    Responsibilities:
    - Responsibility 1
    - Responsibility 2
    """

    def __init__(self, dependency: SomeOtherService):
        """Initialize with dependencies.

        Args:
            dependency: Injected dependency
        """
        logger.debug("[MyService] Initializing")
        self._dep = dependency

    def operation(self, param: str) -> str:
        """Perform an operation.

        Args:
            param: Operation parameter

        Returns:
            Operation result

        Raises:
            ValueError: If param invalid
        """
        logger.info("[MyService] Starting operation")
        logger.debug(f"[MyService] operation called with param={param}")

        if not param:
            raise ValueError("param cannot be empty")

        try:
            result = self._do_work(param)
            logger.debug(f"[MyService] operation succeeded, result={result}")
            return result
        except Exception as e:
            logger.error(f"[MyService] operation failed: {e}")
            raise

    def _do_work(self, param: str) -> str:
        """Internal implementation."""
        # Business logic here
        return f"processed: {param}"
```

### Step 2: Create Protocol (Contract)

```python
# specs/002-service-refactor/contracts/my_service.py
from typing import Protocol

class MyServiceProtocol(Protocol):
    """Interface for MyService."""

    def operation(self, param: str) -> str:
        """Perform an operation.

        Args:
            param: Operation parameter

        Returns:
            Operation result

        Raises:
            ValueError: If param invalid
        """
        ...
```

### Step 3: Register in Container

```python
# src/autoraid/container.py
from dependency_injector import containers, providers
from autoraid.services.my_service import MyService

class Container(containers.DeclarativeContainer):
    # ... existing providers ...

    # Choose Singleton or Factory based on service needs
    my_service = providers.Singleton(
        MyService,
        dependency=some_other_service,  # Inject dependencies
    )
```

### Step 4: Wire Module (if using @inject)

```python
# In Container class
wiring_config = containers.WiringConfiguration(
    modules=[
        "autoraid.cli.upgrade_cli",
        "autoraid.cli.my_module",  # Add your module here
    ],
)
```

### Step 5: Use in CLI or Other Services

```python
# In CLI command
from dependency_injector.wiring import inject, Provide
from autoraid.container import Container
from autoraid.services.my_service import MyService

@my_group.command()
@inject
def my_command(
    param: str,
    service: MyService = Provide[Container.my_service],
):
    """My command description."""
    result = service.operation(param)
    console.print(f"Result: {result}")

# In another service
class AnotherService:
    def __init__(self, my_service: MyService):
        self._my = my_service

    def workflow(self):
        result = self._my.operation("value")
        # Use result...
```

### Step 6: Add Smoke Tests

```python
# test/test_my_service.py
import pytest
from unittest.mock import Mock
from autoraid.services.my_service import MyService

def test_my_service_instantiates():
    """Smoke test: Service instantiates correctly."""
    dep = Mock()
    service = MyService(dependency=dep)
    assert service is not None

def test_my_service_operation():
    """Smoke test: Basic operation succeeds."""
    dep = Mock()
    service = MyService(dependency=dep)

    result = service.operation("test")

    assert result == "processed: test"

def test_my_service_operation_raises_on_empty():
    """Smoke test: Service validates input."""
    dep = Mock()
    service = MyService(dependency=dep)

    with pytest.raises(ValueError, match="param cannot be empty"):
        service.operation("")
```

## Testing with Mocks

### Pattern: Test Container

```python
# test/test_orchestrator.py
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
        state_machine=state_machine.provider,
    )

@pytest.fixture
def container():
    """Provide test container."""
    return TestContainer()

def test_count_workflow(container):
    """Test orchestrator coordinates services correctly."""
    # Arrange
    orchestrator = container.orchestrator()

    # Configure mock behaviors BEFORE using orchestrator
    container.screenshot_service().take_screenshot.return_value = fake_screenshot
    container.locate_region_service().get_regions.return_value = {
        "upgrade_bar": (100, 200, 300, 50),
        "upgrade_button": (150, 400, 100, 40),
    }
    container.state_machine().process_frame.return_value = (5, StopCountReason.UPGRADED)

    # Act
    fail_count, reason = orchestrator.count_workflow(network_adapter_id=[1])

    # Assert
    assert fail_count == 5
    assert reason == StopCountReason.UPGRADED
    container.screenshot_service().take_screenshot.assert_called()
    container.window_interaction_service().click_region.assert_called()
```

### Pattern: Testing State Machine with Fixtures

```python
# test/test_state_machine.py
import pytest
import cv2
from autoraid.autoupgrade.state_machine import UpgradeStateMachine
from autoraid.contracts.upgrade_state_machine import StopCountReason

@pytest.fixture
def fixture_image_fail():
    """Load fixture image showing fail state."""
    return cv2.imread("test/images/progress_bar_fail.png")

@pytest.fixture
def fixture_image_standby():
    """Load fixture image showing standby state."""
    return cv2.imread("test/images/progress_bar_standby.png")

def test_state_machine_counts_fails(fixture_image_fail):
    """Test state machine counts fail transitions."""
    state_machine = UpgradeStateMachine(max_attempts=10)

    # Process 3 fail frames
    for _ in range(3):
        fail_count, reason = state_machine.process_frame(fixture_image_fail)

    assert fail_count == 3
    assert reason is None  # Not stopped yet

def test_state_machine_stops_on_upgraded(fixture_image_standby):
    """Test state machine stops after 4 consecutive standby."""
    state_machine = UpgradeStateMachine(max_attempts=10)

    # Process 4 consecutive standby frames
    for _ in range(4):
        fail_count, reason = state_machine.process_frame(fixture_image_standby)

    assert reason == StopCountReason.UPGRADED
```

## Debugging Guide

### Enabling Debug Mode

```bash
# CLI flag enables DEBUG logging + debug artifacts
uv run autoraid --debug upgrade count -n 1
```

**Debug mode effects**:
- Log level set to DEBUG (entry/exit of all service methods)
- Screenshots saved to `cache-raid-autoupgrade/debug/`
- Metadata saved to `cache-raid-autoupgrade/debug/`

### Understanding Log Output

**Normal mode (INFO level)**:
```
INFO     | [UpgradeOrchestrator] Starting count workflow
INFO     | [ScreenshotService] Captured screenshot
INFO     | [WindowInteractionService] Clicked upgrade button
INFO     | [UpgradeOrchestrator] Count complete: 5 fails
```

**Debug mode (DEBUG level)**:
```
INFO     | [UpgradeOrchestrator] Starting count workflow
DEBUG    | [UpgradeOrchestrator] count_workflow called with network_adapter_id=[1], max_attempts=100
DEBUG    | [ScreenshotService] take_screenshot called with window_title="Raid: Shadow Legends"
INFO     | [ScreenshotService] Captured screenshot
DEBUG    | [ScreenshotService] take_screenshot returned screenshot of size 1920x1080
DEBUG    | [LocateRegionService] get_regions called with window_size=(1920, 1080)
DEBUG    | [CacheService] get_regions called with window_size=(1920, 1080)
DEBUG    | [CacheService] Cache hit for key "regions_1920_1080"
```

### Inspecting Container Wiring

```python
# In Python REPL or test
from autoraid.container import Container

container = Container()
container.config.from_dict({"cache_dir": "/path/to/cache"})

# Inspect providers
print(container.providers)
# Output: DependencyProvider, etc.

# Check if service registered
print(container.cache_service)
# Output: <Singleton(CacheService) at ...>

# Get service instance
cache_service = container.cache_service()
print(type(cache_service))
# Output: <class 'autoraid.services.cache_service.CacheService'>
```

### Common Issues

**Issue**: `DependencyResolutionError: Cannot resolve dependency`

**Cause**: Service not registered in container or circular dependency

**Fix**:
1. Check service is registered in `container.py`
2. Verify dependency order (dependencies must be registered before consumers)
3. Check for circular dependencies (Service A → Service B → Service A)

**Issue**: `AttributeError: 'Mock' object has no attribute 'some_method'`

**Cause**: Mock not configured before injection

**Fix**: Configure mock **before** creating service instance:
```python
# Bad
orchestrator = container.orchestrator()
container.cache_service().get_regions.return_value = regions  # Too late!

# Good
container.cache_service().get_regions.return_value = regions
orchestrator = container.orchestrator()
```

**Issue**: Tests fail with `WindowNotFoundException` but window is open

**Cause**: Test is trying to interact with real window instead of mocked service

**Fix**: Use test container with mocked services (see Testing with Mocks section)

## Common Patterns

### Pattern: Extract Function to Service

**Before (monolithic)**:
```python
# In autoupgrade.py
def create_cache_key_regions(window_size: tuple[int, int]) -> str:
    return f"regions_{window_size[0]}_{window_size[1]}"

def count_fails(cache, window_size):
    cache_key = create_cache_key_regions(window_size)
    regions = cache.get(cache_key)
    # ... workflow logic ...
```

**After (service-based)**:
```python
# In services/cache_service.py
class CacheService:
    def create_regions_key(self, window_size: tuple[int, int]) -> str:
        return f"regions_{window_size[0]}_{window_size[1]}"

    def get_regions(self, window_size: tuple[int, int]) -> dict | None:
        cache_key = self.create_regions_key(window_size)
        return self._cache.get(cache_key)

# In services/upgrade_orchestrator.py
class UpgradeOrchestrator:
    def __init__(self, cache_service: CacheService, ...):
        self._cache = cache_service

    def count_workflow(self, window_size):
        regions = self._cache.get_regions(window_size)
        # ... workflow logic ...
```

### Pattern: Service Coordination

```python
class UpgradeOrchestrator:
    """Coordinates multiple services for workflow execution."""

    def __init__(
        self,
        cache_service: CacheService,
        screenshot_service: ScreenshotService,
        locate_region_service: LocateRegionService,
    ):
        self._cache = cache_service
        self._screenshot = screenshot_service
        self._locate = locate_region_service

    def workflow(self):
        """Coordinate services to execute workflow."""
        # Step 1: Get cached or captured screenshot
        screenshot = self._screenshot.take_screenshot("Raid")

        # Step 2: Detect regions (uses cache internally)
        window_size = (screenshot.shape[1], screenshot.shape[0])
        regions = self._locate.get_regions(screenshot, window_size)

        # Step 3: Extract and process ROI
        roi = self._screenshot.extract_roi(screenshot, regions["upgrade_bar"])

        # Continue workflow...
```

### Pattern: Error Handling with Cleanup

```python
class UpgradeOrchestrator:
    def count_workflow(self, network_adapter_id: list[int] | None = None):
        """Execute count workflow with cleanup guarantee."""
        logger.info("[UpgradeOrchestrator] Starting count workflow")

        try:
            # Disable network
            if network_adapter_id:
                disable_network_adapters(network_adapter_id)

            # Execute workflow steps
            screenshot = self._screenshot.take_screenshot("Raid")
            # ... workflow logic ...

            return fail_count, reason

        except Exception as e:
            logger.error(f"[UpgradeOrchestrator] Workflow failed: {e}")
            raise

        finally:
            # ALWAYS re-enable network, even if workflow fails
            if network_adapter_id:
                try:
                    enable_network_adapters(network_adapter_id)
                except Exception as e:
                    logger.error(f"[UpgradeOrchestrator] Failed to re-enable network: {e}")
```

## Troubleshooting

### Container Resolution Errors

**Error**: `Cannot resolve dependency 'cache_service' for 'LocateRegionService'`

**Solution**: Ensure `cache_service` is registered **before** `locate_region_service` in container

### Import Errors

**Error**: `ImportError: cannot import name 'MyService'`

**Solution**: Check service is in correct file and `__init__.py` exports it

### Mock Configuration Issues

**Error**: Tests fail with unexpected mock behavior

**Solution**:
1. Configure mocks before creating service instance
2. Use `return_value` for methods, not attributes
3. Check mock was actually called: `mock.assert_called()`

### Type Hinting Errors

**Error**: MyPy complains about service dependencies

**Solution**: Ensure all dependencies have type hints in constructor:
```python
def __init__(self, cache_service: CacheService):  # ✅ Type hint
    self._cache = cache_service
```

## Next Steps

1. **Read Implementation Plan**: See `plan.md` for full architecture details
2. **Review Contracts**: See `contracts/` for service interfaces
3. **Begin Implementation**: Follow `tasks.md` (generated by `/speckit.tasks`)
4. **Run Tests**: `uv run pytest` after each phase
5. **Commit Frequently**: Commit after each working phase

## Resources

- **Dependency Injector Docs**: https://python-dependency-injector.ets-labs.org/
- **AutoRaid Constitution**: `.specify/memory/constitution.md`
- **Project Guide**: `CLAUDE.md` in repo root
- **Service Contracts**: `specs/002-service-refactor/contracts/`
- **Data Model**: `specs/002-service-refactor/data-model.md`
- **Research Decisions**: `specs/002-service-refactor/research.md`
