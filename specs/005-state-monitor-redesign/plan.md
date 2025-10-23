# Implementation Plan: State Monitor Redesign

**Branch**: `005-state-monitor-redesign` | **Date**: 2025-10-23 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-state-monitor-redesign/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Refactor the monolithic `UpgradeStateMachine` into two focused components following separation of concerns: a stateless `ProgressBarStateDetector` for computer vision operations and a stateful `UpgradeAttemptMonitor` for business logic (failure counting and stop condition detection). This improves testability by allowing independent testing with image fixtures (detector) and mocked state sequences (monitor), while maintaining identical workflow behavior through atomic replacement.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: opencv-python (CV operations), numpy (image arrays), dependency-injector (DI container), loguru (logging)
**Storage**: N/A (in-memory state only - no persistence)
**Testing**: pytest with unittest.mock for mocking, fixture images in test/fixtures/images/
**Target Platform**: Windows 10+ (existing constraint, no changes)
**Project Type**: Single project (CLI tool with native GUI)
**Performance Goals**: No new requirements - maintain existing detection latency (<250ms per frame within 0.25s polling interval)
**Constraints**: Zero functional changes to workflows (FR-016), 90% test coverage for core logic (SC-005), atomic replacement (FR-017)
**Scale/Scope**: ~2 new classes, ~3 modified files, ~300 LOC total, existing test fixtures reused

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Simplicity Over Complexity
✅ **PASS** - Refactoring reduces complexity by separating concerns. Each new class has single responsibility (detector=CV, monitor=logic). No deep inheritance (0 levels). Straightforward delegation pattern.

### Principle II: DRY & Separation of Concerns
✅ **PASS** - Enforces separation: detector (core/CV) is stateless, monitor (core/logic) is stateful. No code duplication - existing `progress_bar.get_progress_bar_state()` function reused. Clear layering: Orchestrator → Monitor → Detector.

### Principle III: Readability First
✅ **PASS** - Class names self-document purpose (`ProgressBarStateDetector`, `UpgradeAttemptMonitor`). Properties provide read-only access (`fail_count`, `stop_reason`, `current_state`). Type hints on all public methods. Enum rename (`StopCountReason` → `StopReason`) improves clarity.

### Principle IV: Pragmatic Testing (Smoke Tests)
✅ **PASS** - Aligns with smoke test approach. Detector tests use existing fixture images. Monitor tests use mocked detector. Integration tests verify workflow parity. Target: 90% coverage for both components (matches existing state machine standard). No TDD required - tests written after implementation.

### Principle V: Debug-Friendly Architecture
✅ **PASS** - Adds DEBUG-level logging for state transitions (FR-018) and stop conditions (FR-019). Monitor provides read-only properties for inspection. Existing `--debug` flag behavior unchanged. Clear error messages for invalid inputs (exception on null/empty images).

### Principle VI: Incremental Improvement
✅ **PASS** - Minimal viable refactoring: splits one class into two focused classes. No feature additions. Atomic replacement (no gradual migration complexity). Addresses pain point: hard to test CV independently from logic.

**Overall Result**: ✅ **ALL GATES PASSED** - No violations. Refactoring aligns with all constitutional principles.

## Project Structure

### Documentation (this feature)

```
specs/005-state-monitor-redesign/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (current)
├── research.md          # Phase 0 output (no research needed - using existing patterns)
├── data-model.md        # Phase 1 output (state enums and class interfaces)
├── quickstart.md        # Phase 1 output (developer guide for new architecture)
├── contracts/           # Phase 1 output (N/A for internal refactoring - no external APIs)
└── tasks.md             # Phase 2 output (created by /speckit.tasks command)
```

### Source Code (repository root)

```
autoraid/
├── src/autoraid/
│   ├── core/                           # Core domain logic
│   │   ├── progress_bar_detector.py    # NEW: Stateless detector class
│   │   ├── state_machine.py            # MODIFIED: Add UpgradeAttemptMonitor, rename StopCountReason → StopReason
│   │   └── progress_bar.py             # UNCHANGED: Existing color detection function
│   ├── services/
│   │   └── upgrade_orchestrator.py     # MODIFIED: Use new monitor API instead of state machine
│   ├── container.py                    # MODIFIED: Add detector singleton, monitor factory provider
│   └── exceptions.py                   # UNCHANGED: May add InvalidImageError (TBD in Phase 1)
├── test/
│   ├── unit/
│   │   └── core/
│   │       ├── test_progress_bar_detector.py    # NEW: Detector tests with fixtures
│   │       ├── test_upgrade_attempt_monitor.py  # NEW: Monitor tests with mocked detector
│   │       └── test_state_machine.py            # MODIFIED: Update for new API
│   ├── integration/
│   │   └── test_upgrade_orchestrator.py         # MODIFIED: Verify workflow parity
│   └── fixtures/
│       └── images/                              # UNCHANGED: Reuse existing test images
└── CLAUDE.md                                    # MODIFIED: Update architecture section
```

**Structure Decision**: Single project structure (Option 1) - AutoRaid is a single Python CLI tool with NiceGUI. No backend/frontend split. Refactoring stays within existing `src/autoraid/core/` and `src/autoraid/services/` structure per service-based architecture documented in CLAUDE.md.

## Complexity Tracking

*No violations - this section intentionally left empty.*

## Architecture Design

### Component Responsibilities

**ProgressBarStateDetector** (Stateless Singleton):
- **Input**: NumPy BGR image array (ROI of progress bar)
- **Output**: `ProgressBarState` enum value
- **Responsibility**: Wraps existing `progress_bar.get_progress_bar_state()` function, maps string result to enum, validates input
- **Error Handling**: Raises `ValueError` for null/empty images (FR-002)
- **Logging**: Warns on UNKNOWN states at DEBUG level
- **Testing**: Unit tests with fixture images from `test/fixtures/images/`

**UpgradeAttemptMonitor** (Stateful Factory):
- **Input**: `ProgressBarStateDetector` instance (injected), `max_attempts` (constructor param)
- **Output**: Read-only properties (`fail_count`, `stop_reason`, `current_state`)
- **Responsibility**: Calls detector for each frame, counts failure transitions, checks stop conditions, maintains state history
- **State**: `_fail_count` (int), `_recent_states` (deque[ProgressBarState, maxlen=4]), `_detector` (ProgressBarStateDetector)
- **Logging**: Logs state transitions and stop conditions at DEBUG level (FR-018, FR-019)
- **Testing**: Unit tests with mocked detector using `unittest.mock.Mock`

### Data Flow

```
Workflow (Orchestrator)
    ↓ (provides roi_image)
Monitor.process_frame(roi_image)
    ↓ (calls)
Detector.detect_state(roi_image)
    ↓ (returns ProgressBarState)
Monitor (updates internal state, logs transitions)
    ↓ (workflow queries)
Monitor.stop_reason → StopReason | None
Monitor.fail_count → int
```

### Dependency Injection Configuration

```python
# container.py additions
class Container(containers.DeclarativeContainer):
    # Existing providers...

    # NEW: Progress bar detector (stateless, singleton)
    progress_bar_detector = providers.Singleton(
        ProgressBarStateDetector,
    )

    # NEW: Monitor factory (replaces state_machine provider)
    upgrade_attempt_monitor = providers.Factory(
        UpgradeAttemptMonitor,
        detector=progress_bar_detector,
        max_attempts=providers.Dependency(),  # Passed at call time by orchestrator
    )
```

### Integration Points

**UpgradeOrchestrator Changes**:
- Replace `state_machine_provider` with `upgrade_attempt_monitor` provider
- Change `_count_upgrade_fails()` to use `monitor.process_frame()` API
- Access fail count via `monitor.fail_count` property (not tuple unpacking)
- Check `monitor.stop_reason` property in loop condition

**Before**:
```python
state_machine = self._state_machine_provider(max_attempts=max_attempts)
while stop_reason is None:
    fail_count, stop_reason = state_machine.process_frame(upgrade_bar_roi)
```

**After**:
```python
monitor = self._upgrade_attempt_monitor(max_attempts=max_attempts)
while monitor.stop_reason is None:
    state = monitor.process_frame(upgrade_bar_roi)
    # Access monitor.fail_count when needed
```

## API Contracts

### ProgressBarStateDetector API

```python
class ProgressBarStateDetector:
    """Stateless detector for progress bar state from ROI images.

    Uses existing color-based algorithm to classify progress bar state.
    """

    def detect_state(self, roi_image: np.ndarray) -> ProgressBarState:
        """Detect progress bar state from ROI image.

        Args:
            roi_image: BGR numpy array of progress bar region (H x W x 3)

        Returns:
            ProgressBarState enum value (FAIL, PROGRESS, STANDBY,
            CONNECTION_ERROR, or UNKNOWN)

        Raises:
            ValueError: If roi_image is None, empty, or invalid shape
        """
```

### UpgradeAttemptMonitor API

```python
class UpgradeAttemptMonitor:
    """Stateful monitor for upgrade attempt tracking and stop detection.

    Tracks failure count, state history, and determines when to stop
    monitoring based on configured conditions.
    """

    def __init__(self, detector: ProgressBarStateDetector, max_attempts: int):
        """Initialize monitor with detector and max attempts.

        Args:
            detector: ProgressBarStateDetector instance (injected)
            max_attempts: Maximum failures before stopping (must be > 0)

        Raises:
            ValueError: If max_attempts <= 0
        """

    def process_frame(self, roi_image: np.ndarray) -> ProgressBarState:
        """Process frame and update internal state.

        Side effects:
        - Calls detector.detect_state()
        - Updates fail_count on FAIL transitions
        - Appends state to recent_states deque
        - Logs state transitions at DEBUG level

        Args:
            roi_image: BGR numpy array of progress bar region

        Returns:
            Detected ProgressBarState

        Raises:
            ValueError: If roi_image is invalid (propagated from detector)
        """

    @property
    def fail_count(self) -> int:
        """Current failure count (read-only)."""

    @property
    def stop_reason(self) -> StopReason | None:
        """Reason for stopping if stop condition met, None otherwise.

        Evaluates conditions on each access:
        1. MAX_ATTEMPTS_REACHED if fail_count >= max_attempts
        2. SUCCESS if last 4 states all STANDBY
        3. CONNECTION_ERROR if last 4 states all CONNECTION_ERROR
        4. None if no stop condition met
        """

    @property
    def current_state(self) -> ProgressBarState | None:
        """Most recently detected state, None if no frames processed yet."""
```

### Enum Definitions

```python
class ProgressBarState(Enum):
    """Progress bar visual state detected from ROI image."""
    FAIL = "fail"                      # Red bar (upgrade failed)
    PROGRESS = "progress"              # Yellow bar (upgrade in progress)
    STANDBY = "standby"                # Black bar (ready/waiting)
    CONNECTION_ERROR = "connection_error"  # Blue bar (network issue)
    UNKNOWN = "unknown"                # Unrecognized color pattern


class StopReason(Enum):
    """Reason for stopping upgrade attempt monitoring.

    Used by both Count and Spend workflows.
    Renamed from StopCountReason for clarity.
    """
    MAX_ATTEMPTS_REACHED = "max_attempts_reached"
    SUCCESS = "upgraded"               # Formerly UPGRADED in StopCountReason
    CONNECTION_ERROR = "connection_error"
```

## Testing Strategy

### Unit Tests: ProgressBarStateDetector

**File**: `test/unit/core/test_progress_bar_detector.py` (new)

**Coverage Target**: ≥90%

**Test Cases**:
1. `test_detect_fail_state()` - Red bar image → FAIL
2. `test_detect_progress_state()` - Yellow bar image → PROGRESS
3. `test_detect_standby_state()` - Black bar image → STANDBY
4. `test_detect_connection_error_state()` - Blue bar image → CONNECTION_ERROR
5. `test_detect_unknown_state()` - Unrecognized color → UNKNOWN
6. `test_detect_state_is_stateless()` - Same image returns same state 100 times
7. `test_detect_state_raises_on_none_image()` - None image → ValueError
8. `test_detect_state_raises_on_empty_image()` - Empty array → ValueError
9. `test_detect_state_raises_on_invalid_shape()` - Wrong dimensions → ValueError

**Fixture Images**: Reuse existing images from `test/fixtures/images/` (fail_state.png, progress_state.png, standby_state.png, connection_error_state.png)

### Unit Tests: UpgradeAttemptMonitor

**File**: `test/unit/core/test_upgrade_attempt_monitor.py` (new)

**Coverage Target**: ≥90%

**Test Cases**:
1. `test_monitor_counts_fail_transitions()` - PROGRESS→FAIL→PROGRESS→FAIL = 2 fails
2. `test_monitor_ignores_consecutive_fails()` - FAIL→FAIL→FAIL = 1 fail
3. `test_monitor_stops_on_max_attempts()` - 10 fails → MAX_ATTEMPTS_REACHED
4. `test_monitor_stops_on_success()` - 4x STANDBY → SUCCESS
5. `test_monitor_stops_on_connection_error()` - 4x CONNECTION_ERROR → CONNECTION_ERROR
6. `test_monitor_does_not_stop_early()` - 3x STANDBY → None (continues)
7. `test_monitor_tracks_current_state()` - current_state property returns last state
8. `test_monitor_logs_state_transitions()` - Verify DEBUG log calls
9. `test_monitor_validates_max_attempts()` - max_attempts=0 → ValueError
10. `test_monitor_fail_count_property_readonly()` - fail_count returns int, no setter

**Mocking Approach**:
```python
from unittest.mock import Mock
mock_detector = Mock(spec=ProgressBarStateDetector)
mock_detector.detect_state.side_effect = [
    ProgressBarState.PROGRESS,
    ProgressBarState.FAIL,
    # ... sequence
]
monitor = UpgradeAttemptMonitor(mock_detector, max_attempts=10)
```

### Integration Tests

**File**: `test/integration/test_upgrade_orchestrator.py` (modified)

**Test Cases**:
1. `test_count_workflow_with_real_detector_and_monitor()` - End-to-end with fixture images
2. `test_count_workflow_behavior_parity()` - Compare old vs new behavior (before removal)
3. `test_spend_workflow_with_monitor()` - Verify Spend workflow integration

### Behavior Parity Verification

**Approach**:
- Run same test scenarios with old `UpgradeStateMachine` and new `UpgradeAttemptMonitor`
- Compare fail counts, stop reasons, state sequences
- All must match exactly before removing old implementation
- Tests gate progression to removal phase

## Migration Plan

### Phase 0: Preparation (Current)
- ✅ Spec completed with clarifications
- ✅ Plan created with architecture design
- 🔄 Create `research.md` (no research needed - using existing patterns)
- 🔄 Create `data-model.md` (enum definitions and class interfaces)
- 🔄 Create `quickstart.md` (developer guide for new architecture)

### Phase 1: Implementation
1. Create `ProgressBarStateDetector` class in `core/progress_bar_detector.py`
2. Add `UpgradeAttemptMonitor` class to `core/state_machine.py`
3. Rename `StopCountReason` → `StopReason` in `core/state_machine.py`
4. Add DI providers to `container.py`
5. Update CLAUDE.md architecture section

### Phase 2: Testing
1. Write detector unit tests (9 test cases)
2. Write monitor unit tests (10 test cases)
3. Verify ≥90% coverage for both components
4. Run full test suite (must pass)

### Phase 3: Integration
1. Update `UpgradeOrchestrator` to use monitor API
2. Wire monitor provider in container
3. Update integration tests
4. Run behavior parity tests (old vs new)
5. Verify zero functional changes

### Phase 4: Verification
1. Manual testing of Count workflow
2. Manual testing of Spend workflow
3. Verify GUI workflows unchanged
4. Check DEBUG logging output
5. Confirm all success criteria met (SC-001 through SC-007)

### Phase 5: Cleanup
1. Remove old `UpgradeStateMachine` class
2. Remove old state machine tests
3. Remove behavior parity tests
4. Update all references in documentation
5. Final test suite run

### Rollback Safety
- Each phase commits separately
- Tests gate progression
- Can revert to previous phase if issues
- Old implementation kept until Phase 5

## Risk Analysis

### Low Risk Items
✅ Detector wraps existing function (no algorithm changes)
✅ Monitor logic unchanged (just reorganized)
✅ DI pattern already used (same factory approach)
✅ Test fixtures already exist

### Medium Risk Items
⚠️ Orchestrator API changes (mitigated by integration tests)
⚠️ Logging changes (mitigated by manual verification)

### High Risk Items
❌ None identified

### Mitigation Strategies
1. **Behavior Parity Tests**: Compare old vs new before removal
2. **Atomic Replacement**: Single-phase integration (no gradual migration)
3. **Comprehensive Test Coverage**: 90% for core logic
4. **Manual Verification**: Test both workflows in GUI
5. **Git Safety**: Each phase commits separately for easy revert

## Success Criteria Verification

| ID | Criterion | Verification Method | Status |
|----|-----------|---------------------|--------|
| SC-001 | Independent detector testing | Unit tests with fixture images | Phase 2 |
| SC-002 | Independent monitor testing | Unit tests with mocked detector | Phase 2 |
| SC-003 | 100% repeatability (stateless) | Test runs detector 100x on same image | Phase 2 |
| SC-004 | Zero functional changes | Behavior parity tests + manual testing | Phase 4 |
| SC-005 | ≥90% test coverage | pytest --cov verification | Phase 2 |
| SC-006 | Detector changes isolated | Architecture review | Phase 5 |
| SC-007 | Monitor changes isolated | Architecture review | Phase 5 |

## Post-Implementation Tasks

### Documentation Updates
- [ ] Update CLAUDE.md architecture section with new component descriptions
- [ ] Update service responsibilities table
- [ ] Add testing examples for new components
- [ ] Document migration path for future refactorings

### Code Quality Verification
- [ ] Run `uv run ruff check .` (must pass)
- [ ] Run `uv run ruff format .` (apply formatting)
- [ ] Run `uv run pytest --cov=autoraid.core` (verify ≥90% coverage)
- [ ] Run `uv run pre-commit run --all-files` (hooks pass)

### Final Validation
- [ ] All FR-001 through FR-019 requirements met
- [ ] All SC-001 through SC-007 success criteria verified
- [ ] Constitution principles upheld (all gates passed)
- [ ] Zero regressions in existing test suite
- [ ] Manual workflow testing completed (Count + Spend in CLI and GUI)

## Notes

- This is a pure refactoring - no new features or behavior changes
- Existing test fixtures and algorithms reused wherever possible
- Focus on improving testability and maintainability, not adding functionality
- Atomic replacement strategy chosen over gradual migration for simplicity
- No performance impact expected (same operations, just reorganized)
