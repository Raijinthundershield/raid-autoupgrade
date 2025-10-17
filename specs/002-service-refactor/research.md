# Research: Service-Based Architecture Refactoring

**Date**: 2025-10-17
**Feature**: Service-Based Architecture Refactoring
**Branch**: `002-service-refactor`

## Overview

This document captures research findings and technical decisions for refactoring AutoRaid into a service-based architecture with dependency injection. Research focused on DI framework selection, service lifetime patterns, testing strategies, migration patterns, error handling, and logging conventions.

## 1. Dependency Injection Framework Selection

### Decision

**Use `dependency-injector` library** (version 4.x)

### Rationale

1. **Mature and battle-tested**:
   - Trust Score: 6.4 on Context7
   - 700+ code examples in official documentation
   - Active maintenance since 2015
   - Used in production by multiple organizations

2. **Excellent type hinting support**:
   - Full support for Python 3.8+ type hints
   - Type-safe dependency resolution
   - IDE autocomplete for injected dependencies
   - MyPy compatibility

3. **Simple and explicit patterns**:
   - `DeclarativeContainer` for service registration
   - `Singleton` and `Factory` providers for lifecycle management
   - `@inject` decorator for automatic dependency injection
   - No XML/YAML configuration files (Python-based DSL)

4. **Testing-friendly**:
   - Container overrides for mocking services
   - Test containers with mock providers
   - No global state (each container is isolated)

5. **Documentation and examples**:
   - Comprehensive official docs at https://python-dependency-injector.ets-labs.org/
   - Real-world examples (Flask, FastAPI, Django integrations)
   - Active community on GitHub

### Alternatives Considered

#### Option A: Manual Dependency Injection (no library)

**Pros**:
- No external dependencies
- Full control over service lifecycle
- Simple to understand for small codebases

**Cons**:
- Requires manual singleton pattern implementation
- Global state complicates testing (need to reset singletons between tests)
- Hidden dependencies in module-level imports
- Boilerplate code for service wiring
- No type-safe resolution

**Verdict**: ❌ Rejected - Increases maintenance burden vs using a mature library

#### Option B: `injector` library

**Pros**:
- More Pythonic API (`@inject` as a simple decorator)
- Simpler API surface (fewer concepts)
- No container concept (uses modules)

**Cons**:
- Less comprehensive documentation
- Fewer real-world examples
- Weaker type hinting support
- Less active maintenance
- No built-in testing utilities

**Verdict**: ❌ Rejected - `dependency-injector` has better docs and type safety

#### Option C: Third-party frameworks (Spring-like frameworks)

**Options considered**: `python-dependency-injection`, `punq`, `lagom`

**Pros**:
- Various philosophical approaches to DI
- Some are lighter-weight

**Cons**:
- Less mature, fewer examples
- Smaller communities
- Limited documentation
- Uncertain long-term maintenance

**Verdict**: ❌ Rejected - `dependency-injector` is the de facto standard for Python DI

### Installation

```bash
cd autoraid
uv add dependency-injector
```

### Basic Usage Pattern

```python
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    # Configuration
    config = providers.Configuration()

    # Singletons
    cache_service = providers.Singleton(
        CacheService,
        cache_dir=config.cache_dir,
    )

    # Factories
    orchestrator = providers.Factory(
        UpgradeOrchestrator,
        cache_service=cache_service,
    )

# Usage in CLI
container = Container()
container.config.from_dict({"cache_dir": "/path/to/cache"})
orchestrator = container.orchestrator()
```

## 2. Service Lifetime Best Practices

### Decision

**Use Singleton pattern for stateful/integration services, Factory pattern for workflow services**

### Service Lifetime Assignments

#### Singleton Services (shared instance across application)

1. **CacheService**:
   - **Rationale**: Wraps `diskcache.Cache` instance, maintains cache state
   - **State**: Cache handle, cache directory path
   - **Lifecycle**: Created once at application startup, reused for all operations

2. **ScreenshotService**:
   - **Rationale**: Stateless but singleton for consistency and performance
   - **State**: None (uses pyautogui/pygetwindow directly)
   - **Lifecycle**: Created once, reused for all screenshot operations

3. **WindowInteractionService**:
   - **Rationale**: Manages window handles and state
   - **State**: Window handles, activation state
   - **Lifecycle**: Created once, maintains window references across operations

4. **LocateRegionService**:
   - **Rationale**: Integrates with other singletons (CacheService, ScreenshotService)
   - **State**: None (delegates to dependencies)
   - **Lifecycle**: Created once, coordinates region detection across operations

#### Factory Services (new instance per operation)

1. **UpgradeStateMachine**:
   - **Rationale**: Requires fresh state per upgrade workflow
   - **State**: `recent_states` deque, `fail_count`, `max_attempts`
   - **Lifecycle**: New instance for each count/spend operation to avoid state contamination

2. **UpgradeOrchestrator**:
   - **Rationale**: Workflow-specific instance to avoid cross-workflow contamination
   - **State**: Network adapter state, workflow progress
   - **Lifecycle**: New instance per CLI command invocation

### Rationale for Pattern Choice

1. **Performance**: Singletons reduce object creation overhead for services used repeatedly
2. **State isolation**: Factories ensure clean state for stateful workflows
3. **Testing**: Both patterns work well with test containers and mocks
4. **Industry alignment**: Pattern matches Spring Framework, NestJS, and ASP.NET Core conventions

### Implementation Pattern

```python
class Container(containers.DeclarativeContainer):
    # Singleton: created once, shared across all operations
    cache_service = providers.Singleton(CacheService)

    # Factory: new instance for each call
    state_machine = providers.Factory(UpgradeStateMachine)

    # Orchestrator gets state_machine PROVIDER (not instance)
    orchestrator = providers.Factory(
        UpgradeOrchestrator,
        state_machine=state_machine.provider,  # Pass provider, not instance
    )
```

### State Machine Provider Pattern

The UpgradeOrchestrator receives the **state_machine provider**, not a state_machine instance. This allows the orchestrator to create fresh state machines for each workflow:

```python
class UpgradeOrchestrator:
    def __init__(self, state_machine: Callable[[], UpgradeStateMachine]):
        self._state_machine_factory = state_machine

    def count_workflow(self):
        # Create fresh state machine for this workflow
        state_machine = self._state_machine_factory()
        # Use state_machine...
```

## 3. Testing Patterns with Dependency Injection

### Decision

**Use test containers with mocked service providers for unit testing**

### Pattern: Test Container with Mocks

```python
import pytest
from unittest.mock import Mock, MagicMock
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
    """Provide test container for each test."""
    return TestContainer()

def test_count_workflow_calls_services(container):
    """Test that orchestrator coordinates services correctly."""
    # Arrange
    orchestrator = container.orchestrator()

    # Configure mock behaviors
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

### Best Practices

1. **Mock vs MagicMock**:
   - Use `Mock` for simple services (most cases)
   - Use `MagicMock` when you need magic methods (`__len__`, `__iter__`, etc.)

2. **Configure mocks before injection**:
   ```python
   # Good: Configure before use
   container.cache_service().get_regions.return_value = regions
   orchestrator = container.orchestrator()

   # Bad: Configure after injection (won't work)
   orchestrator = container.orchestrator()
   container.cache_service().get_regions.return_value = regions
   ```

3. **Assert on mock method calls**:
   ```python
   # Verify service was called
   container.screenshot_service().take_screenshot.assert_called()

   # Verify call arguments
   container.window_interaction_service().click_region.assert_called_with(
       window_title="Raid: Shadow Legends",
       region=(150, 400, 100, 40),
   )

   # Verify call count
   assert container.cache_service().set_regions.call_count == 1
   ```

4. **Use fixture images for state machine tests**:
   ```python
   def test_state_machine_detects_fail(fixture_image_fail):
       """Test state machine with real fixture image."""
       state_machine = UpgradeStateMachine(max_attempts=10)
       fail_count, reason = state_machine.process_frame(fixture_image_fail)
       # Assertions...
   ```

### Test Coverage Priorities

Following "Pragmatic Testing" (Principle III), prioritize tests by impact:

**MUST test** (core logic, high fragility):
- `UpgradeStateMachine`: All state transitions with fixture images
- `CacheService`: Key generation, get/set operations

**SHOULD test** (integration, business logic):
- `UpgradeOrchestrator`: Workflow coordination with mocked services
- `LocateRegionService`: Automatic detection fallback logic
- Error handling in all services

**CAN skip** (manual verification acceptable):
- `ScreenshotService`: GUI-dependent, hard to test without live window
- `WindowInteractionService`: GUI-dependent, requires live Raid window
- CLI argument parsing: Straightforward, low complexity

**Smoke tests** (per user guidance: "Only make concise smoke tests"):
Each service should have 1-2 smoke tests verifying:
- Service instantiates correctly
- Basic operation succeeds with mocked dependencies
- Service raises expected exception on invalid input

## 4. Migration Strategy for Monolithic Functions

### Decision

**Extract function → Service method → Wire via DI → Deprecate wrapper**

### Migration Steps

1. **Identify function to extract**:
   - Look for functions with side effects (I/O, state changes)
   - Look for functions that could benefit from dependency injection
   - Look for functions that are hard to test in isolation

2. **Create service class** (if not exists):
   ```python
   # src/autoraid/services/cache_service.py
   from diskcache import Cache

   class CacheService:
       """Service for caching operations."""

       def __init__(self, cache: Cache):
           """Initialize with cache instance."""
           self._cache = cache
   ```

3. **Move function logic to service method**:
   ```python
   def create_regions_key(self, window_size: tuple[int, int]) -> str:
       """Generate cache key for regions based on window size."""
       return f"regions_{window_size[0]}_{window_size[1]}"

   def get_regions(self, window_size: tuple[int, int]) -> dict | None:
       """Retrieve cached regions for window size."""
       cache_key = self.create_regions_key(window_size)
       return self._cache.get(cache_key)
   ```

4. **Add dependencies to service constructor**:
   ```python
   # If service needs other services
   class LocateRegionService:
       def __init__(
           self,
           cache_service: CacheService,
           screenshot_service: ScreenshotService,
       ):
           self._cache = cache_service
           self._screenshot = screenshot_service
   ```

5. **Register service in container**:
   ```python
   # src/autoraid/container.py
   class Container(containers.DeclarativeContainer):
       cache_service = providers.Singleton(
           CacheService,
           cache=disk_cache,
       )
   ```

6. **Update callers to use injected service**:
   ```python
   # Before (in autoupgrade.py)
   cache_key = create_cache_key_regions(window_size)
   regions = cache.get(cache_key)

   # After (in orchestrator)
   regions = self._cache_service.get_regions(window_size)
   ```

7. **Keep deprecated wrapper for backward compat** (Phase 8 cleanup):
   ```python
   # In autoupgrade.py (temporary)
   @deprecated("Use CacheService.get_regions() instead")
   def create_cache_key_regions(window_size: tuple[int, int]) -> str:
       # Call service implementation
       container = Container()
       return container.cache_service().create_regions_key(window_size)
   ```

### Example Migration: Cache Key Generation

#### Before (monolithic)

```python
# In autoupgrade.py
def create_cache_key_regions(window_size: tuple[int, int]) -> str:
    """Create cache key for regions."""
    return f"regions_{window_size[0]}_{window_size[1]}"

def count_fails(cache, window_size):
    cache_key = create_cache_key_regions(window_size)
    regions = cache.get(cache_key)
    if regions is None:
        # Manual region selection
        regions = select_regions()
        cache.set(cache_key, regions)
    # Continue workflow...
```

#### After (service-based)

```python
# In services/cache_service.py
class CacheService:
    def __init__(self, cache: Cache):
        self._cache = cache

    def create_regions_key(self, window_size: tuple[int, int]) -> str:
        """Generate cache key for regions based on window size."""
        return f"regions_{window_size[0]}_{window_size[1]}"

    def get_regions(self, window_size: tuple[int, int]) -> dict | None:
        """Retrieve cached regions for window size."""
        cache_key = self.create_regions_key(window_size)
        return self._cache.get(cache_key)

    def set_regions(self, window_size: tuple[int, int], regions: dict) -> None:
        """Store regions in cache for window size."""
        cache_key = self.create_regions_key(window_size)
        self._cache.set(cache_key, regions)

# In services/upgrade_orchestrator.py
class UpgradeOrchestrator:
    def __init__(self, cache_service: CacheService, ...):
        self._cache = cache_service

    def count_workflow(self, window_size):
        regions = self._cache.get_regions(window_size)
        if regions is None:
            regions = self._locate.get_regions(...)
            self._cache.set_regions(window_size, regions)
        # Continue workflow...
```

### Backward Compatibility During Migration

Each phase maintains backward compatibility by:
1. Keeping original function as deprecated wrapper
2. Original function calls new service implementation
3. Wrappers removed in Phase 8 (Cleanup)

This allows:
- Existing code to continue working during migration
- Gradual migration of callers
- Safe rollback if issues are discovered

## 5. Error Handling Strategy

### Decision

**Fail fast with descriptive exceptions at all layers**

### Service-Level Error Handling

**Pattern**:
1. **Validate inputs** → raise `ValueError` with descriptive message
2. **Expected errors** → raise custom exceptions (e.g., `CacheInitializationError`, `WindowNotFoundException`)
3. **Unexpected errors** → re-raise with added context

**Example**:
```python
class CacheService:
    def __init__(self, cache: Cache):
        if cache is None:
            raise ValueError("cache parameter cannot be None")
        try:
            # Test cache access
            _ = cache.directory
        except Exception as e:
            raise CacheInitializationError(
                f"Failed to initialize cache: {e}"
            ) from e
        self._cache = cache

    def get_regions(self, window_size: tuple[int, int]) -> dict | None:
        if window_size[0] <= 0 or window_size[1] <= 0:
            raise ValueError(
                f"Invalid window size: {window_size}. "
                f"Width and height must be positive."
            )
        try:
            cache_key = self.create_regions_key(window_size)
            return self._cache.get(cache_key)
        except Exception as e:
            logger.error(f"[CacheService] Failed to get regions: {e}")
            raise
```

### Custom Exceptions

```python
# src/autoraid/exceptions.py

class AutoRaidError(Exception):
    """Base exception for AutoRaid errors."""
    pass

class CacheInitializationError(AutoRaidError):
    """Raised when cache initialization fails."""
    pass

class WindowNotFoundException(AutoRaidError):
    """Raised when Raid window is not found."""
    pass

class RegionDetectionError(AutoRaidError):
    """Raised when region detection fails."""
    pass

class DependencyResolutionError(AutoRaidError):
    """Raised when DI container cannot resolve a dependency."""
    pass
```

### Orchestrator-Level Error Handling

**Pattern**:
1. Catch service exceptions
2. Log with full context
3. Perform cleanup (finally block for network re-enable)
4. Return error result or re-raise with user-friendly message

**Example**:
```python
class UpgradeOrchestrator:
    def count_workflow(
        self,
        network_adapter_id: list[int] | None = None,
        max_attempts: int = 100
    ) -> tuple[int, StopCountReason]:
        logger.info("[UpgradeOrchestrator] Starting count workflow")

        try:
            # Disable network
            if network_adapter_id:
                disable_network_adapters(network_adapter_id)

            # Execute workflow
            screenshot = self._screenshot.take_screenshot("Raid: Shadow Legends")
            regions = self._locate.get_regions(screenshot, ...)
            # ... workflow logic ...

        except WindowNotFoundException as e:
            logger.error(f"[UpgradeOrchestrator] Raid window not found: {e}")
            raise
        except Exception as e:
            logger.error(f"[UpgradeOrchestrator] Workflow failed: {e}")
            raise
        finally:
            # Always re-enable network
            if network_adapter_id:
                try:
                    enable_network_adapters(network_adapter_id)
                except Exception as e:
                    logger.error(
                        f"[UpgradeOrchestrator] Failed to re-enable network: {e}"
                    )
```

### CLI-Level Error Handling

**Pattern**:
1. Catch orchestrator exceptions
2. Display user-friendly error message (rich formatting)
3. Exit with appropriate status code
4. Suggest remediation steps

**Example**:
```python
@upgrade.command()
@inject
def count(
    network_adapter_id: list[int],
    orchestrator: UpgradeOrchestrator = Provide[Container.upgrade_orchestrator],
):
    """Count the number of upgrade fails."""
    try:
        fail_count, reason = orchestrator.count_workflow(
            network_adapter_id=list(network_adapter_id)
        )
        # Display success result
        console.print(f"[green]Fail count: {fail_count}[/green]")

    except WindowNotFoundException:
        console.print(
            "[red]Error:[/red] Raid window not found.\n"
            "[yellow]Suggestion:[/yellow] Ensure Raid: Shadow Legends is running."
        )
        sys.exit(1)

    except CacheInitializationError as e:
        console.print(
            f"[red]Error:[/red] Cache initialization failed: {e}\n"
            f"[yellow]Suggestion:[/yellow] Check cache directory permissions."
        )
        sys.exit(2)

    except Exception as e:
        console.print(
            f"[red]Unexpected error:[/red] {e}\n"
            f"[yellow]Suggestion:[/yellow] Run with --debug for more details."
        )
        sys.exit(255)
```

### Error Handling for Edge Cases

Based on spec edge cases:

1. **Service initialization failure**: Service raises descriptive exception → CLI displays error and exits
2. **Cleanup on shutdown**: Orchestrator finally block ensures network re-enable → Manual cleanup if crash
3. **Hard-coded dependencies**: Not allowed by design → Container enforces constructor injection
4. **Unexpected state transitions**: State machine logs warning, returns "unknown" → Workflow continues
5. **Container misconfiguration**: Container raises `DependencyResolutionError` on startup → App fails to start
6. **Duplicate debug metadata**: Each service uses name prefix → Orchestrator coordinates writes

## 6. Logging Strategy

### Decision

**Use loguru with structured logging and service name prefixes**

### Log Levels

| Level | When to Use | Example |
|-------|-------------|---------|
| DEBUG | Entry/exit of service methods, parameter values | `logger.debug(f"[CacheService] get_regions called with window_size={window_size}")` |
| INFO  | User-visible milestones, workflow progress | `logger.info(f"[UpgradeOrchestrator] Starting count workflow")` |
| WARNING | Recoverable errors, fallback scenarios | `logger.warning(f"[LocateRegionService] Automatic detection failed, falling back to manual")` |
| ERROR | Unrecoverable errors, exceptions | `logger.error(f"[ScreenshotService] Failed to capture screenshot: {e}")` |

### Service Logging Pattern

**Standard Pattern**:
```python
from loguru import logger

class ExampleService:
    """Service with standard logging pattern."""

    def operation(self, param: str) -> str:
        """Perform an operation."""
        logger.info(f"[ExampleService] Starting operation")
        logger.debug(f"[ExampleService] operation called with param={param}")

        try:
            result = self._do_work(param)
            logger.debug(f"[ExampleService] operation succeeded, result={result}")
            return result

        except ValueError as e:
            logger.warning(f"[ExampleService] Invalid parameter: {e}")
            raise

        except Exception as e:
            logger.error(f"[ExampleService] operation failed: {e}")
            raise
```

### Service Name Prefix Convention

Every log message from a service MUST include `[ServiceName]` prefix:
- `[CacheService]`
- `[ScreenshotService]`
- `[LocateRegionService]`
- `[WindowInteractionService]`
- `[UpgradeStateMachine]`
- `[UpgradeOrchestrator]`

This aids debugging by making it easy to filter logs by service.

### Normal Mode vs Debug Mode

**Normal Mode** (INFO level):
```
[INFO] [UpgradeOrchestrator] Starting count workflow
[INFO] [ScreenshotService] Captured screenshot
[INFO] [WindowInteractionService] Clicked upgrade button
[INFO] [UpgradeOrchestrator] Count complete: 5 fails
```

**Debug Mode** (DEBUG level):
```
[INFO] [UpgradeOrchestrator] Starting count workflow
[DEBUG] [UpgradeOrchestrator] count_workflow called with network_adapter_id=[1], max_attempts=100
[DEBUG] [ScreenshotService] take_screenshot called with window_title="Raid: Shadow Legends"
[INFO] [ScreenshotService] Captured screenshot
[DEBUG] [ScreenshotService] take_screenshot returned screenshot of size 1920x1080
[DEBUG] [LocateRegionService] get_regions called with window_size=(1920, 1080)
[DEBUG] [CacheService] get_regions called with window_size=(1920, 1080)
[DEBUG] [CacheService] Cache hit for key "regions_1920_1080"
[DEBUG] [LocateRegionService] get_regions returned 3 regions
[DEBUG] [WindowInteractionService] click_region called with region=(150, 400, 100, 40)
[INFO] [WindowInteractionService] Clicked upgrade button
[DEBUG] [WindowInteractionService] click_region completed
[INFO] [UpgradeOrchestrator] Count complete: 5 fails
[DEBUG] [UpgradeOrchestrator] count_workflow returned (5, StopCountReason.UPGRADED)
```

### Loguru Configuration

```python
# In cli.py (container setup)
from loguru import logger
import sys

def setup_logging(debug: bool):
    """Configure loguru logging based on debug mode."""
    logger.remove()  # Remove default handler

    if debug:
        # Debug mode: DEBUG level to stdout + file
        logger.add(
            sys.stdout,
            level="DEBUG",
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        )
        logger.add(
            "cache-raid-autoupgrade/debug/autoraid.log",
            level="DEBUG",
            rotation="10 MB",
        )
    else:
        # Normal mode: INFO level to stdout only
        logger.add(
            sys.stdout,
            level="INFO",
            format="<level>{level: <8}</level> | <level>{message}</level>",
        )

@click.group()
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.pass_context
def cli(ctx, debug):
    """AutoRaid CLI application."""
    setup_logging(debug)
    # ... container setup ...
```

## Summary

This research establishes the technical foundation for the service-based architecture refactoring:

1. **DI Framework**: `dependency-injector` provides mature, type-safe dependency injection
2. **Service Lifetimes**: Singletons for stateful services, Factories for workflows
3. **Testing**: Test containers with mocked providers enable fast, isolated unit tests
4. **Migration**: Extract → Service → Wire → Deprecate pattern ensures safe incremental refactoring
5. **Error Handling**: Fail fast with descriptive exceptions at all layers
6. **Logging**: Structured logging with service prefixes at INFO (normal) and DEBUG (debug mode) levels

All decisions align with AutoRaid Constitution principles:
- **Simplicity**: Clear patterns, no complex abstractions
- **Readability**: Explicit dependencies, descriptive names
- **Pragmatic Testing**: Focus on core logic, skip GUI tests
- **Debug-Friendly**: Service logging, structured error messages
- **Incremental**: Safe migration path with backward compatibility

## Next Steps

1. Create `data-model.md` defining service entities and relationships
2. Create `contracts/` directory with service interface protocols
3. Create `quickstart.md` with developer guide and examples
4. Run agent context update script
5. Begin Phase 0 implementation (DI container setup)
