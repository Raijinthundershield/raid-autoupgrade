# Protocol-Based Dependency Injection - Implementation Plan

## Overview

### Purpose
Introduce `typing.Protocol` classes for all injected infrastructure services to improve type safety, testability, and enable better static analysis without coupling consumers to concrete implementations.

### Scope
- **In Scope:**
  - Create 7 protocol classes for all DI container services
  - Update type annotations in workflows, orchestration, services, CLI, and GUI
  - Update test mocks to use protocols instead of concrete classes
  - Maintain backward compatibility (no runtime behavior changes)

- **Out of Scope:**
  - Creating alternative service implementations
  - Changing DI container configuration
  - Modifying service business logic
  - Adding new services or protocols beyond the existing 7

### Success Criteria
1. All injected services have corresponding Protocol definitions
2. All consumers (workflows, orchestration, CLI, GUI) use protocol type annotations
3. All tests mock against protocols instead of concrete classes
4. Full test suite passes without modification to test assertions
5. Type checker (mypy) passes with no new errors
6. Zero runtime behavior changes

---

## Architecture & Design

### Component Overview

The AutoRaid codebase uses dependency injection with 7 singleton infrastructure services. This refactor introduces protocol definitions to decouple type annotations from concrete implementations.

**Current State:**
```python
# Concrete class coupling
def __init__(self, cache_service: CacheService):
    self._cache = cache_service
```

**Target State:**
```python
# Protocol-based interface
def __init__(self, cache_service: CacheProtocol):
    self._cache = cache_service
```

### Project Structure

```
src/autoraid/
├── protocols.py                        [CREATE] - Protocol definitions
├── container.py                        [MODIFY] - No changes needed (provides concrete impls)
├── services/
│   ├── cache_service.py                [VERIFY] - Satisfies CacheProtocol
│   ├── screenshot_service.py           [MODIFY] - Accept WindowInteractionProtocol
│   ├── locate_region_service.py        [MODIFY] - Accept CacheProtocol + ScreenshotProtocol
│   ├── window_interaction_service.py   [VERIFY] - Satisfies WindowInteractionProtocol
│   ├── network.py                      [VERIFY] - Satisfies NetworkManagerProtocol
│   └── app_data.py                     [VERIFY] - Satisfies AppDataProtocol
├── detection/
│   └── progress_bar_detector.py        [VERIFY] - Satisfies ProgressBarDetectorProtocol
├── orchestration/
│   ├── upgrade_orchestrator.py         [MODIFY] - Accept 5 protocol parameters
│   └── progress_bar_monitor.py         [MODIFY] - Accept ProgressBarDetectorProtocol
├── workflows/
│   ├── count_workflow.py               [MODIFY] - Accept 5 protocol parameters
│   ├── spend_workflow.py               [MODIFY] - Accept 5 protocol parameters
│   └── debug_monitor_workflow.py       [MODIFY] - Accept 5 protocol parameters
├── cli/
│   ├── upgrade_cli.py                  [MODIFY] - Protocol annotations in @inject signatures
│   ├── network_cli.py                  [MODIFY] - Protocol annotations in @inject signatures
│   └── debug_cli.py                    [MODIFY] - Protocol annotations in @inject signatures
└── gui/
    ├── app.py                          [MODIFY] - Protocol annotations in header
    └── components/
        ├── upgrade_panel.py            [MODIFY] - Protocol annotations in panel
        ├── region_panel.py             [MODIFY] - Protocol annotations in panel
        └── network_panel.py            [MODIFY] - Protocol annotations in panel

test/
├── unit/
│   ├── orchestration/
│   │   ├── test_progress_bar_monitor.py    [MODIFY] - Mock ProgressBarDetectorProtocol
│   │   └── test_upgrade_orchestrator.py    [MODIFY] - Mock 5 protocols
│   └── workflows/
│       ├── test_count_workflow.py          [MODIFY] - Mock 5 protocols
│       ├── test_spend_workflow.py          [MODIFY] - Mock 5 protocols
│       └── test_debug_monitor_workflow.py  [MODIFY] - Mock 5 protocols
└── integration/
    ├── test_count_workflow_integration.py  [MODIFY] - Mock protocols
    └── test_spend_workflow_integration.py  [MODIFY] - Mock protocols
```

### Design Decisions

#### 1. **Protocol Location: Root Level (`src/autoraid/protocols.py`)**
**Decision:** Place protocols at root level alongside `container.py` and `exceptions.py`

**Why:**
- Protocols are cross-cutting concerns used by all layers (CLI, GUI, workflows, orchestration, services)
- Avoids circular import issues (services implement protocols, consumers import protocols)
- Consistent with other infrastructure files (`container.py`, `exceptions.py`)
- High discoverability for developers

**Alternatives Considered:**
- `services/protocols.py` - Rejected because protocols are not exclusive to services layer
- Separate `protocols/` directory - Rejected as overkill for 7 simple protocols

#### 2. **Minimal Protocol Definitions**
**Decision:** Include only methods actually used by consumers

**Why:**
- Protocols define contracts based on actual usage, not theoretical completeness
- Smaller interfaces are easier to understand and maintain
- Follows Interface Segregation Principle (ISP)
- Reduces test mock surface area

**Example:**
```python
@runtime_checkable
class CacheProtocol(Protocol):
    # Only include methods actually called by consumers
    def get_regions(self, window_size: tuple[int, int]) -> dict | None: ...
    def set_regions(self, window_size: tuple[int, int], regions: dict) -> None: ...
    # Omit unused methods even if present in concrete class
```

#### 3. **Runtime Checkable Protocols**
**Decision:** Mark all protocols with `@runtime_checkable` decorator

**Why:**
- Enables `isinstance()` checks for runtime validation
- Supports Liskov Substitution Principle (LSP) verification
- Minimal overhead (only used in validation/testing scenarios)
- Provides safety net for protocol compliance

**Trade-off:** Slight runtime overhead for isinstance checks (acceptable for validation scenarios)

#### 4. **Bottom-Up Migration Strategy**
**Decision:** Update type annotations from leaf components upward (detection → orchestration → workflows → entry points)

**Why:**
- Ensures dependencies are protocol-typed before dependents
- Reduces risk of incomplete refactoring
- Allows incremental validation at each layer
- Natural progression following dependency graph

**Phasing:**
1. Leaf services (ProgressBarDetector, WindowInteractionService, NetworkManager)
2. Mid-level services (ScreenshotService, CacheService, LocateRegionService)
3. Orchestration layer (ProgressBarMonitor, UpgradeOrchestrator)
4. Workflow layer (CountWorkflow, SpendWorkflow, DebugMonitorWorkflow)
5. Entry points (CLI commands, GUI components)
6. Test mocks

#### 5. **No Container Changes**
**Decision:** DI container continues providing concrete implementations unchanged

**Why:**
- Protocols are satisfied structurally by concrete classes (duck typing)
- Separation of concerns: container manages instances, protocols define interfaces
- Zero impact on application wiring and initialization
- Maintains single source of truth for service instantiation

### Data Flow

No changes to data flow - protocols are purely a type system enhancement:

```
┌─────────────────────────────────────────────┐
│  CLI/GUI Entry Points                       │
│  - @inject with Protocol type hints         │  ← Phase 5
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│  Workflows (CountWorkflow, SpendWorkflow)   │
│  - Constructor params use Protocols         │  ← Phase 4
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│  Orchestration (UpgradeOrchestrator)        │
│  - Constructor params use Protocols         │  ← Phase 3
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│  Services (Cache, Screenshot, etc.)         │
│  - Implement Protocols (structural typing)  │  ← Phase 2
│  - Internal dependencies use Protocols      │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│  Detection (ProgressBarStateDetector)       │
│  - Implements ProgressBarDetectorProtocol   │  ← Phase 2
└─────────────────────────────────────────────┘

    DI Container (unchanged)
    ├── Provides concrete implementations
    └── Satisfies protocols structurally
```

---

## Technical Approach

### Dependencies

**New Dependencies:** None (uses standard library `typing.Protocol`)

**Existing Dependencies:**
- `typing.Protocol` (Python 3.8+) - already available
- `@runtime_checkable` (Python 3.8+) - already available

### Integration Points

#### 1. **Service Implementations**
Services continue implementing their existing public APIs. Protocol compliance is verified structurally (duck typing).

**Verification approach:**
```python
from autoraid.protocols import CacheProtocol
from autoraid.services.cache_service import CacheService

# Runtime check (optional, for validation)
assert isinstance(CacheService(...), CacheProtocol)
```

#### 2. **DI Container**
No changes required. Container provides concrete implementations that satisfy protocols:

```python
# container.py (unchanged)
class Container(containers.DeclarativeContainer):
    cache_service = providers.Singleton(CacheService, disk_cache=disk_cache)
    # Concrete CacheService satisfies CacheProtocol structurally
```

#### 3. **Type Annotations**
Replace concrete class annotations with protocol annotations:

**Before:**
```python
def __init__(self, cache_service: CacheService):
```

**After:**
```python
def __init__(self, cache_service: CacheProtocol):
```

#### 4. **Test Mocks**
Update mock specifications from concrete classes to protocols:

**Before:**
```python
mock_cache = Mock(spec=CacheService)
```

**After:**
```python
mock_cache = Mock(spec=CacheProtocol)
```

### Error Handling

**No new error handling required.** This is a pure type system refactor with no runtime behavior changes.

**Potential issues:**
1. **Protocol compliance violations** - Caught by type checker (mypy) during development
2. **Incomplete protocol definitions** - Tests will fail if mocked methods are missing
3. **Import errors** - Caught immediately during module load

**Mitigation:**
- Run full test suite after each phase
- Use mypy for static type checking (optional but recommended)
- Verify no runtime behavior changes with integration tests

---

## Implementation Strategy

### Phase Breakdown

#### **Phase 0: Branch Setup**
- Create feature branch `feat-protocols-di`
- Set up clean working environment

#### **Phase 1: Protocol Definitions**
- Create `src/autoraid/protocols.py` with all 7 protocols
- Define minimal protocol interfaces based on actual usage
- Add docstrings and type hints
- Verify protocols are importable

**Deliverable:** Complete protocol definitions file

#### **Phase 2: Service Layer Updates**
- Update service internal dependencies to use protocols
- Verify concrete services satisfy protocols
- Update service type hints where services depend on other services

**Deliverable:** Services with protocol-based internal dependencies

#### **Phase 3: Orchestration Layer Updates**
- Update `ProgressBarMonitor` to accept `ProgressBarDetectorProtocol`
- Update `UpgradeOrchestrator` to accept 5 protocol parameters
- Verify orchestration logic unchanged

**Deliverable:** Orchestration layer using protocol type hints

#### **Phase 4: Workflow Layer Updates**
- Update `CountWorkflow` constructor to use 5 protocols
- Update `SpendWorkflow` constructor to use 5 protocols
- Update `DebugMonitorWorkflow` constructor to use 5 protocols
- Verify workflow validation logic unchanged

**Deliverable:** Workflows with protocol-based constructors

#### **Phase 5: Entry Point Updates**
- Update CLI command signatures (`upgrade_cli.py`, `network_cli.py`, `debug_cli.py`)
- Update GUI component signatures (`app.py`, `upgrade_panel.py`, `region_panel.py`, `network_panel.py`)
- Verify injection still works correctly

**Deliverable:** All entry points using protocol type hints

#### **Phase 6: Test Updates**
- Update unit test mocks to use protocols
- Update integration test mocks to use protocols
- Verify all tests pass unchanged

**Deliverable:** Test suite passing with protocol-based mocks

#### **Phase 7: Verification & Documentation**
- Run full test suite
- Run type checker (mypy) if configured
- Update `CLAUDE.md` to document protocol usage
- Verify zero runtime behavior changes

**Deliverable:** Fully verified protocol-based DI system

### Testing Approach

#### **Unit Tests**
- Mock protocols instead of concrete classes
- Verify protocol compliance with `isinstance()` checks (optional)
- Test behavior unchanged (same assertions)

**Example:**
```python
from autoraid.protocols import ProgressBarDetectorProtocol

def test_monitor_counts_fails():
    mock_detector = Mock(spec=ProgressBarDetectorProtocol)
    mock_detector.detect_state.side_effect = [
        ProgressBarState.FAIL,
        ProgressBarState.PROGRESS,
        ProgressBarState.FAIL,
    ]

    monitor = ProgressBarMonitor(mock_detector)
    # ... rest of test unchanged
```

#### **Integration Tests**
- Continue using mocked orchestrator/services
- Update mock specifications to protocols
- Verify workflow integration unchanged

#### **Smoke Tests**
- Run CLI commands manually: `uv run autoraid --help`
- Launch GUI: `uv run autoraid gui`
- Verify no crashes or import errors

#### **Type Checking (Optional)**
```bash
uv run mypy src/autoraid --strict
```

### Deployment Notes

**This is a non-breaking change:**
- No runtime behavior modifications
- No API changes (protocols satisfied structurally)
- No configuration changes
- No migration required for users

**Rollout:**
1. Merge feature branch to main after all phases complete
2. Run full test suite in CI/CD
3. Deploy as normal (no special steps)

**Rollback plan:**
- Revert single commit if issues arise (atomic change)
- No data migrations or cleanup needed

---

## Risks & Considerations

### Challenges

#### 1. **Incomplete Protocol Definitions**
**Risk:** Protocol missing methods actually used by consumers

**Mitigation:**
- Comprehensive analysis of actual method usage completed upfront
- Run full test suite after protocol creation (Phase 1)
- Tests will fail if mocked protocol methods are incomplete

**Impact:** Low (caught immediately by tests)

#### 2. **Import Circular Dependencies**
**Risk:** Protocols importing from services, services importing protocols

**Mitigation:**
- Protocols placed at root level (no circular imports possible)
- Protocols only import from `typing`, `pathlib`, `numpy`, and enum types
- Services import protocols (one-way dependency)

**Impact:** Very Low (architectural design prevents issue)

#### 3. **Protocol Compliance Violations**
**Risk:** Concrete service doesn't satisfy protocol (signature mismatch)

**Mitigation:**
- Protocols designed from actual service implementations (guaranteed match)
- Optional runtime checks with `isinstance()` for verification
- Type checker (mypy) will catch mismatches statically

**Impact:** Very Low (protocols derived from existing code)

### Performance

**No performance impact:**
- Protocols are compile-time type hints (erased at runtime)
- `@runtime_checkable` only adds overhead for explicit `isinstance()` checks
- No `isinstance()` checks in hot paths (only used for validation)

**Benchmark areas:** None required (pure type system change)

### Security

**No security implications:**
- No changes to authentication, authorization, or data handling
- No new attack surface introduced
- Type safety improvement may prevent type-related bugs

### Technical Debt

**Reduces technical debt:**
- Decouples type annotations from concrete implementations
- Improves testability (easier to mock interfaces)
- Enables future alternative implementations without refactoring consumers
- Better IDE support and static analysis

**Future improvements enabled:**
- Easy to add alternative service implementations (e.g., MockNetworkManager for testing)
- Clearer separation of interface vs. implementation
- Foundation for potential plugin architecture

**Maintenance:**
- Protocols must be updated if service interfaces change
- Same as current: changing service APIs requires updating consumers
- Protocol acts as explicit documentation of required interface

---

## References

### Key Files Analyzed
- `src/autoraid/container.py` - DI container configuration
- `src/autoraid/services/*.py` - All 7 service implementations
- `src/autoraid/detection/progress_bar_detector.py` - Detector service
- `src/autoraid/orchestration/upgrade_orchestrator.py` - Orchestrator coordination
- `src/autoraid/workflows/*.py` - All 3 workflow implementations
- `src/autoraid/cli/*.py` - CLI entry points with @inject
- `src/autoraid/gui/components/*.py` - GUI entry points with @inject

### Method Usage Analysis
Comprehensive analysis identified exact methods used by consumers for each of the 7 services:
- CacheProtocol: 4 methods
- ScreenshotProtocol: 2 methods
- WindowInteractionProtocol: 4 methods
- NetworkManagerProtocol: 4 methods
- ProgressBarDetectorProtocol: 1 method
- LocateRegionProtocol: 1 method
- AppDataProtocol: 3 properties + 2 methods

### Python Documentation
- [PEP 544 - Protocols: Structural subtyping](https://peps.python.org/pep-0544/)
- [typing.Protocol documentation](https://docs.python.org/3/library/typing.html#typing.Protocol)
