# Data Model: State Monitor Redesign

**Feature**: State Monitor Redesign
**Date**: 2025-10-23
**Status**: Complete

## Overview

This document defines the data structures and interfaces for the refactored state monitoring system. The model consists of two enumerations (state representation) and two class interfaces (detector and monitor).

## Enumerations

### ProgressBarState

**Location**: `src/autoraid/core/state_machine.py` (existing file, new enum)

**Purpose**: Represents the five possible visual states of the upgrade progress bar detected through computer vision.

**Definition**:
```python
from enum import Enum

class ProgressBarState(Enum):
    """Progress bar visual state detected from ROI image.

    Each state corresponds to a specific color pattern in the progress bar:
    - FAIL: Red bar (b<70, g<90, r>130)
    - PROGRESS: Yellow bar (b<70, abs(r-g)<50)
    - STANDBY: Black bar (b<30, g<60, r<70)
    - CONNECTION_ERROR: Blue bar (b>g, b>r, b>50)
    - UNKNOWN: No matching color pattern
    """
    FAIL = "fail"
    PROGRESS = "progress"
    STANDBY = "standby"
    CONNECTION_ERROR = "connection_error"
    UNKNOWN = "unknown"
```

**States Description**:

| State | Color | BGR Threshold | Meaning |
|-------|-------|---------------|---------|
| FAIL | Red | b<70, g<90, r>130 | Upgrade attempt failed |
| PROGRESS | Yellow | b<70, abs(r-g)<50 | Upgrade in progress |
| STANDBY | Black | b<30, g<60, r<70 | Ready/waiting state |
| CONNECTION_ERROR | Blue | b>g, b>r, b>50 | Network connection lost |
| UNKNOWN | N/A | None match | Unrecognized pattern |

**Usage**:
- Returned by `ProgressBarStateDetector.detect_state()`
- Consumed by `UpgradeAttemptMonitor.process_frame()`
- Stored in monitor's state history (`deque[ProgressBarState]`)

**Relationship to Existing Code**:
- Replaces string-based state representation from `progress_bar.get_progress_bar_state()`
- Provides type safety and IDE autocomplete
- Maps directly to existing color detection algorithm (FR-004)

---

### StopReason

**Location**: `src/autoraid/core/state_machine.py` (existing file, renamed enum)

**Purpose**: Represents the reason for stopping upgrade attempt monitoring, used by both Count and Spend workflows.

**Migration**: Renamed from `StopCountReason` to `StopReason` (FR-014)

**Definition**:
```python
from enum import Enum

class StopReason(Enum):
    """Reason for stopping upgrade attempt monitoring.

    Used by both Count and Spend workflows to indicate why
    monitoring terminated.

    Formerly named StopCountReason (renamed for clarity).
    """
    MAX_ATTEMPTS_REACHED = "max_attempts_reached"
    SUCCESS = "upgraded"
    CONNECTION_ERROR = "connection_error"
```

**Values Description**:

| Value | Trigger Condition | Meaning |
|-------|------------------|---------|
| MAX_ATTEMPTS_REACHED | `fail_count >= max_attempts` | Configured failure limit reached |
| SUCCESS | 4 consecutive STANDBY states | Upgrade succeeded (no more attempts needed) |
| CONNECTION_ERROR | 4 consecutive CONNECTION_ERROR states | Network error persists (cannot continue) |

**Priority Order** (checked in this sequence):
1. **MAX_ATTEMPTS_REACHED** - Always checked first
2. **4-state requirement** - Must have at least 4 states in history
3. **SUCCESS** - Check for 4 consecutive STANDBY
4. **CONNECTION_ERROR** - Check for 4 consecutive CONNECTION_ERROR

**Usage**:
- Returned by `UpgradeAttemptMonitor.stop_reason` property
- Checked by orchestrator to determine when to exit monitoring loop
- Logged at DEBUG level when monitoring terminates (FR-019)

**Backward Compatibility**:
- Replaces `StopCountReason` enum (same values, different name)
- String values unchanged for serialization compatibility
- SUCCESS value mapping: `"upgraded"` (unchanged from UPGRADED in old enum)

---

## Class Interfaces

### ProgressBarStateDetector

**Location**: `src/autoraid/core/progress_bar_detector.py` (new file)

**Type**: Stateless detector (Singleton in DI container)

**Responsibility**: Wraps existing `progress_bar.get_progress_bar_state()` function to provide type-safe, validated state detection.

**Interface**:
```python
import numpy as np
from autoraid.core.state_machine import ProgressBarState

class ProgressBarStateDetector:
    """Stateless detector for progress bar state from ROI images.

    Uses existing color-based algorithm to classify progress bar state.
    Provides input validation and type-safe enum output.
    """

    def detect_state(self, roi_image: np.ndarray) -> ProgressBarState:
        """Detect progress bar state from ROI image.

        Args:
            roi_image: BGR numpy array of progress bar region (H x W x 3)
                      Expected dtype: np.uint8
                      Expected shape: (height, width, 3)

        Returns:
            ProgressBarState enum value:
            - FAIL: Red bar detected
            - PROGRESS: Yellow bar detected
            - STANDBY: Black bar detected
            - CONNECTION_ERROR: Blue bar detected
            - UNKNOWN: No recognizable pattern

        Raises:
            ValueError: If roi_image is None, empty, or has invalid shape
                       Error message includes details of validation failure

        Side Effects:
            - Logs warning at DEBUG level if UNKNOWN state detected
            - No persistent state changes (stateless operation)

        Performance:
            - Typical latency: <50ms on modern CPU
            - No GPU required
            - Same performance as existing progress_bar.get_progress_bar_state()
        """
```

**Internal State**: None (stateless)

**Dependencies**:
- `progress_bar.get_progress_bar_state()` - Existing CV function
- `numpy` - Image array operations
- `loguru` - DEBUG logging

**Validation Rules**:
1. `roi_image is not None` → ValueError if None
2. `roi_image.size > 0` → ValueError if empty array
3. `roi_image.ndim == 3` → ValueError if not 3D
4. `roi_image.shape[2] == 3` → ValueError if not BGR (3 channels)

**Error Messages** (examples):
```python
raise ValueError("roi_image cannot be None")
raise ValueError(f"roi_image is empty (size=0)")
raise ValueError(f"roi_image must be 3D array, got shape {roi_image.shape}")
raise ValueError(f"roi_image must have 3 channels (BGR), got {roi_image.shape[2]}")
```

**Testing Approach**:
- Unit tests with fixture images from `test/fixtures/images/`
- Test all 5 state mappings (FAIL, PROGRESS, STANDBY, CONNECTION_ERROR, UNKNOWN)
- Test all 4 validation error cases
- Test statefulness: 100 consecutive calls on same image return same result

---

### UpgradeAttemptMonitor

**Location**: `src/autoraid/core/state_machine.py` (existing file, new class)

**Type**: Stateful monitor (Factory in DI container)

**Responsibility**: Tracks upgrade attempts by pulling states from detector, counting failure transitions, and evaluating stop conditions.

**Interface**:
```python
from collections import deque
import numpy as np
from autoraid.core.progress_bar_detector import ProgressBarStateDetector
from autoraid.core.state_machine import ProgressBarState, StopReason

class UpgradeAttemptMonitor:
    """Stateful monitor for upgrade attempt tracking and stop detection.

    Tracks failure count, maintains state history (last 4 states), and
    determines when to stop monitoring based on configured conditions.

    Uses dependency injection to receive detector instance.
    """

    def __init__(self, detector: ProgressBarStateDetector, max_attempts: int):
        """Initialize monitor with detector and max attempts.

        Args:
            detector: ProgressBarStateDetector instance (injected by DI container)
            max_attempts: Maximum failures before stopping (must be positive integer)

        Raises:
            ValueError: If max_attempts <= 0

        Side Effects:
            - Initializes internal state: fail_count=0, recent_states=empty deque

        Example:
            # Via DI container (preferred):
            monitor = container.upgrade_attempt_monitor(max_attempts=10)

            # Direct instantiation (testing only):
            detector = ProgressBarStateDetector()
            monitor = UpgradeAttemptMonitor(detector, max_attempts=10)
        """

    def process_frame(self, roi_image: np.ndarray) -> ProgressBarState:
        """Process frame and update internal state.

        Calls detector to get current state, updates failure count on
        FAIL transitions, appends state to history, and logs transition.

        Args:
            roi_image: BGR numpy array of progress bar region

        Returns:
            Detected ProgressBarState (same as detector.detect_state() result)

        Raises:
            ValueError: If roi_image is invalid (propagated from detector)

        Side Effects:
            - Calls self._detector.detect_state(roi_image)
            - Increments self._fail_count if transition to FAIL detected
            - Appends state to self._recent_states (auto-evicts oldest if >4)
            - Logs state transition at DEBUG level: "State: {prev} → {current}"
            - If state is UNKNOWN, logs warning: "Unknown state detected"

        State Transition Counting:
            - Increments fail_count only when transitioning from non-FAIL to FAIL
            - Examples:
              * PROGRESS → FAIL: count += 1
              * FAIL → FAIL: count unchanged (consecutive fails ignored)
              * STANDBY → FAIL: count += 1

        Performance:
            - Calls detector once per invocation (detector latency applies)
            - Deque operations: O(1) append and length check
            - Total overhead: ~1ms excluding detector call
        """

    @property
    def fail_count(self) -> int:
        """Current failure count (read-only).

        Returns:
            Number of times transition to FAIL state occurred.
            Range: [0, max_attempts]

        Example:
            monitor = container.upgrade_attempt_monitor(max_attempts=10)
            monitor.process_frame(image1)  # PROGRESS
            monitor.process_frame(image2)  # FAIL
            assert monitor.fail_count == 1
        """

    @property
    def stop_reason(self) -> StopReason | None:
        """Reason for stopping if stop condition met, None otherwise.

        Evaluates stop conditions on each access (computed property).

        Returns:
            - StopReason.MAX_ATTEMPTS_REACHED if fail_count >= max_attempts
            - StopReason.SUCCESS if last 4 states all STANDBY
            - StopReason.CONNECTION_ERROR if last 4 states all CONNECTION_ERROR
            - None if no stop condition met

        Evaluation Order (priority):
            1. MAX_ATTEMPTS_REACHED (always checked first)
            2. Require at least 4 states in history (return None if <4)
            3. SUCCESS (4 consecutive STANDBY)
            4. CONNECTION_ERROR (4 consecutive CONNECTION_ERROR)

        Side Effects:
            None (pure computation, no state changes)

        Example:
            monitor = container.upgrade_attempt_monitor(max_attempts=2)
            monitor.process_frame(image1)  # FAIL
            monitor.process_frame(image2)  # FAIL
            assert monitor.stop_reason == StopReason.MAX_ATTEMPTS_REACHED

        Usage in Workflow:
            while monitor.stop_reason is None:
                state = monitor.process_frame(next_image)
                # Continue monitoring...
            print(f"Stopped: {monitor.stop_reason.value}")
        """

    @property
    def current_state(self) -> ProgressBarState | None:
        """Most recently detected state, None if no frames processed yet.

        Returns:
            - Last state from recent_states deque
            - None if process_frame() never called

        Side Effects:
            None (read-only access to internal state)

        Example:
            monitor = container.upgrade_attempt_monitor(max_attempts=10)
            assert monitor.current_state is None  # No frames yet

            monitor.process_frame(image)
            assert monitor.current_state == ProgressBarState.PROGRESS
        """
```

**Internal State**:
```python
self._detector: ProgressBarStateDetector  # Injected dependency (immutable)
self._max_attempts: int                   # Configuration (immutable)
self._fail_count: int                     # Mutable counter (starts at 0)
self._recent_states: deque[ProgressBarState]  # State history (maxlen=4, auto-evict)
```

**State Invariants**:
1. `0 <= self._fail_count <= self._max_attempts` (count never exceeds max)
2. `len(self._recent_states) <= 4` (deque enforces via maxlen)
3. `self._max_attempts > 0` (validated in __init__)
4. `self._detector is not None` (injected by DI, validated by type system)

**Dependencies**:
- `ProgressBarStateDetector` - Injected via constructor
- `loguru` - DEBUG logging for transitions
- `collections.deque` - State history with auto-eviction

**Testing Approach**:
- Unit tests with mocked detector using `unittest.mock.Mock`
- Test fail counting logic with controlled state sequences
- Test all stop condition branches
- Test properties are read-only (no setters)
- Test logging calls with `caplog` fixture

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    UpgradeOrchestrator                       │
│                      (Workflow Layer)                        │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ 1. Create monitor via DI factory
                        │    monitor = container.upgrade_attempt_monitor(max_attempts=N)
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              UpgradeAttemptMonitor (Stateful)                │
│                   (Business Logic Layer)                     │
│                                                              │
│  Internal State:                                             │
│  • _fail_count: int                                          │
│  • _recent_states: deque[ProgressBarState] (maxlen=4)       │
│  • _detector: ProgressBarStateDetector (injected)            │
│  • _max_attempts: int (config)                               │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ 2. For each frame:
                        │    state = monitor.process_frame(roi_image)
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│          ProgressBarStateDetector (Stateless)                │
│                    (CV Layer)                                │
│                                                              │
│  Internal State: None                                        │
│  Dependencies: progress_bar.get_progress_bar_state()         │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ 3. Call existing function:
                        │    color_state = get_progress_bar_state(roi_image)
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│      progress_bar.get_progress_bar_state() (Function)        │
│                   (Existing CV Code)                         │
│                                                              │
│  Returns: str ("fail", "progress", "standby",                │
│                "connection_error", or None)                  │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ 4. Map string to enum:
                        │    return ProgressBarState.FAIL (etc.)
                        │
                        ▼
         Monitor updates internal state:
         • Increment fail_count if transition to FAIL
         • Append state to recent_states deque
         • Log transition at DEBUG level
                        │
                        │ 5. Workflow checks stop condition:
                        │    if monitor.stop_reason is not None:
                        │        break
                        │
                        ▼
         Loop continues or exits based on stop_reason
```

---

## Relationships Between Components

### Component Dependencies
```
UpgradeOrchestrator (services)
  ↓ depends on (injects)
UpgradeAttemptMonitor (core)
  ↓ depends on (injects)
ProgressBarStateDetector (core)
  ↓ depends on (calls)
progress_bar.get_progress_bar_state() (core, existing function)
```

### Data Dependencies
```
ProgressBarState (enum) ← returned by ← ProgressBarStateDetector
  ↓ consumed by
UpgradeAttemptMonitor (stores in _recent_states: deque[ProgressBarState])
  ↓ outputs
StopReason (enum) ← returned by ← stop_reason property
  ↓ consumed by
UpgradeOrchestrator (checks to exit loop)
```

### Lifecycle Relationships
```
Container (DI root)
  ├── progress_bar_detector: Singleton
  │     → Created once, reused for all workflows
  │
  └── upgrade_attempt_monitor: Factory
        → New instance per workflow invocation
        → Receives detector singleton via injection
```

---

## State Transitions

### Monitor State Machine

```
[Initial State]
  • fail_count = 0
  • recent_states = []
  • current_state = None

        ↓ process_frame(image) called

[Detecting State]
  • Call detector.detect_state(image)
  • Receive ProgressBarState enum

        ↓ based on detected state

[Update Counters]
  • If prev_state != FAIL and current_state == FAIL:
      fail_count += 1
  • Append current_state to recent_states

        ↓ evaluate stop conditions

[Check Stop Conditions] (in priority order)
  1. fail_count >= max_attempts?
     → Return MAX_ATTEMPTS_REACHED

  2. len(recent_states) < 4?
     → Return None (continue)

  3. All 4 states == STANDBY?
     → Return SUCCESS

  4. All 4 states == CONNECTION_ERROR?
     → Return CONNECTION_ERROR

  5. Otherwise:
     → Return None (continue)

        ↓ if stop_reason is None

[Continue Monitoring]
  • Wait for next frame
  • Repeat process_frame() cycle

        ↓ if stop_reason is not None

[Terminal State]
  • Log stop reason at DEBUG level
  • Workflow exits monitoring loop
```

---

## Validation Rules

### Input Validation (Detector)

| Field | Rule | Error Type | Error Message |
|-------|------|-----------|---------------|
| roi_image | Not None | ValueError | "roi_image cannot be None" |
| roi_image | size > 0 | ValueError | "roi_image is empty (size=0)" |
| roi_image | ndim == 3 | ValueError | "roi_image must be 3D array, got shape {shape}" |
| roi_image | shape[2] == 3 | ValueError | "roi_image must have 3 channels (BGR), got {channels}" |

### Configuration Validation (Monitor)

| Field | Rule | Error Type | Error Message |
|-------|------|-----------|---------------|
| max_attempts | > 0 | ValueError | "max_attempts must be positive, got {value}" |
| detector | Not None | TypeError | Handled by type system / DI container |

---

## Testing Data

### Fixture Images (Existing)

Located in `test/fixtures/images/`:

| File | State | Color | Purpose |
|------|-------|-------|---------|
| `fail_state.png` | FAIL | Red | Test FAIL detection |
| `progress_state.png` | PROGRESS | Yellow | Test PROGRESS detection |
| `standby_state.png` | STANDBY | Black | Test STANDBY detection |
| `connection_error_state.png` | CONNECTION_ERROR | Blue | Test CONNECTION_ERROR detection |

### Mock State Sequences (for Monitor Tests)

```python
# Test Case: Fail Counting
mock_sequence = [
    ProgressBarState.STANDBY,    # Initial
    ProgressBarState.PROGRESS,   # Start attempt
    ProgressBarState.FAIL,       # Count: 1
    ProgressBarState.STANDBY,    # Reset
    ProgressBarState.PROGRESS,   # Start attempt
    ProgressBarState.FAIL,       # Count: 2
]

# Test Case: Success Stop Condition
mock_sequence = [
    ProgressBarState.PROGRESS,
    ProgressBarState.STANDBY,    # 1st STANDBY
    ProgressBarState.STANDBY,    # 2nd STANDBY
    ProgressBarState.STANDBY,    # 3rd STANDBY
    ProgressBarState.STANDBY,    # 4th STANDBY → SUCCESS
]

# Test Case: Connection Error Stop Condition
mock_sequence = [
    ProgressBarState.PROGRESS,
    ProgressBarState.CONNECTION_ERROR,  # 1st ERROR
    ProgressBarState.CONNECTION_ERROR,  # 2nd ERROR
    ProgressBarState.CONNECTION_ERROR,  # 3rd ERROR
    ProgressBarState.CONNECTION_ERROR,  # 4th ERROR → STOP
]
```

---

## Migration Notes

### Enum Renaming

**Old Enum**: `StopCountReason`
**New Enum**: `StopReason`

**Migration Steps**:
1. Add `StopReason` enum to `state_machine.py`
2. Update all references to use `StopReason`
3. Deprecate `StopCountReason` with warning (optional grace period)
4. Remove `StopCountReason` after verification

**String Value Compatibility**:
- `MAX_ATTEMPTS_REACHED = "max_attempts_reached"` (unchanged)
- `SUCCESS = "upgraded"` (formerly `UPGRADED = "upgraded"`, name changed but value unchanged)
- `CONNECTION_ERROR = "connection_error"` (unchanged)

### API Compatibility

**Old API** (UpgradeStateMachine):
```python
fail_count, stop_reason = state_machine.process_frame(image)
```

**New API** (UpgradeAttemptMonitor):
```python
state = monitor.process_frame(image)
fail_count = monitor.fail_count
stop_reason = monitor.stop_reason
```

**Migration Impact**:
- Orchestrator code must be updated (not backward compatible)
- Tests must be updated to use property access
- No data format changes (enums serialize to same strings)

---

## References

- [Feature Spec](spec.md) - Functional requirements (FR-001 through FR-019)
- [Implementation Plan](plan.md) - Architecture design and testing strategy
- [Research](research.md) - Technology decisions and patterns
- [CLAUDE.md](../../CLAUDE.md) - AutoRaid architecture documentation
- [Existing state_machine.py](../../src/autoraid/core/state_machine.py) - Current implementation
- [Existing progress_bar.py](../../src/autoraid/core/progress_bar.py) - CV algorithm
