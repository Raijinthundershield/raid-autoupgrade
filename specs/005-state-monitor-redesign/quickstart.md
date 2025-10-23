# Quickstart: State Monitor Redesign

**Audience**: Developers working on AutoRaid state monitoring refactoring
**Date**: 2025-10-23
**Status**: Complete

## Overview

This guide helps you understand and work with the refactored state monitoring system. The monolithic `UpgradeStateMachine` has been split into two focused components:

1. **ProgressBarStateDetector** - Stateless CV layer (detects colors)
2. **UpgradeAttemptMonitor** - Stateful business logic (counts failures, checks stop conditions)

## Quick Reference

### Import Statements

```python
# New components
from autoraid.core.progress_bar_detector import ProgressBarStateDetector
from autoraid.core.state_machine import (
    UpgradeAttemptMonitor,
    ProgressBarState,
    StopReason,  # Renamed from StopCountReason
)

# DI container
from autoraid.container import Container
```

### Creating Instances via DI

```python
# In orchestrator or workflow code
container = Container()
container.wire(modules=[__name__])

# Detector (singleton - reuse across workflows)
detector = container.progress_bar_detector()

# Monitor (factory - new instance per workflow)
monitor = container.upgrade_attempt_monitor(max_attempts=10)
```

### Using the Monitor

```python
# Main monitoring loop
while monitor.stop_reason is None:
    # Capture screenshot and extract ROI
    roi_image = screenshot_service.take_screenshot()
    upgrade_bar_roi = roi_image[y:y+h, x:x+w]

    # Process frame (updates internal state)
    current_state = monitor.process_frame(upgrade_bar_roi)

    # Optional: Check current state for logging
    print(f"Current state: {current_state.value}")

# When stopped, check reason and fail count
print(f"Stopped: {monitor.stop_reason.value}")
print(f"Total failures: {monitor.fail_count}")
```

---

## Component Deep Dive

### ProgressBarStateDetector

**What it does**: Takes a progress bar image (BGR numpy array) and returns what color it detected.

**When to use**: You need to detect progress bar state from an image without tracking history or counting failures.

**Example**:
```python
import cv2
from autoraid.core.progress_bar_detector import ProgressBarStateDetector
from autoraid.core.state_machine import ProgressBarState

# Create detector (or get from DI container)
detector = ProgressBarStateDetector()

# Load image
image = cv2.imread("test/fixtures/images/fail_state.png")

# Detect state
state = detector.detect_state(image)

# Check result
if state == ProgressBarState.FAIL:
    print("Upgrade failed!")
elif state == ProgressBarState.UNKNOWN:
    print("Warning: Could not recognize state")
```

**Error Handling**:
```python
try:
    state = detector.detect_state(None)  # Invalid input
except ValueError as e:
    print(f"Validation error: {e}")
    # Output: "Validation error: roi_image cannot be None"
```

**Key Points**:
- Stateless (same image always returns same result)
- Validates input (raises ValueError for bad images)
- No side effects (safe to call multiple times)
- Fast (~50ms typical latency)

---

### UpgradeAttemptMonitor

**What it does**: Tracks upgrade attempts by calling the detector for each frame, counting failures, and determining when to stop.

**When to use**: You're running a Count or Spend workflow and need to monitor multiple upgrade attempts with stop conditions.

**Example**:
```python
from autoraid.core.progress_bar_detector import ProgressBarStateDetector
from autoraid.core.state_machine import UpgradeAttemptMonitor, StopReason

# Setup (typically via DI container)
detector = ProgressBarStateDetector()
monitor = UpgradeAttemptMonitor(detector, max_attempts=10)

# Monitoring loop
while monitor.stop_reason is None:
    roi_image = capture_next_frame()  # Your capture logic
    state = monitor.process_frame(roi_image)

    print(f"State: {state.value}, Fails: {monitor.fail_count}")

    time.sleep(0.25)  # Poll every 250ms

# Check why stopped
if monitor.stop_reason == StopReason.MAX_ATTEMPTS_REACHED:
    print(f"Reached max attempts: {monitor.fail_count}")
elif monitor.stop_reason == StopReason.SUCCESS:
    print("Upgrade succeeded!")
elif monitor.stop_reason == StopReason.CONNECTION_ERROR:
    print("Connection error detected")
```

**Stop Conditions** (checked in priority order):
1. **MAX_ATTEMPTS_REACHED**: `fail_count >= max_attempts`
2. **SUCCESS**: 4 consecutive STANDBY states
3. **CONNECTION_ERROR**: 4 consecutive CONNECTION_ERROR states

**Key Points**:
- Stateful (maintains fail_count and state history)
- Factory pattern (create new instance per workflow)
- Read-only properties (cannot directly modify fail_count)
- Logs transitions at DEBUG level

---

## Migration Guide

### Updating Orchestrator Code

**Before** (Old UpgradeStateMachine):
```python
class UpgradeOrchestrator:
    def __init__(self, ..., state_machine_provider):
        self._state_machine_provider = state_machine_provider

    def _count_upgrade_fails(self, max_attempts: int, ...):
        state_machine = self._state_machine_provider(max_attempts=max_attempts)

        stop_reason = None
        while stop_reason is None:
            upgrade_bar_roi = self._screenshot_service.take_screenshot(...)

            # Tuple unpacking
            fail_count, stop_reason = state_machine.process_frame(upgrade_bar_roi)

            print(f"Fails: {fail_count}")

        return fail_count, stop_reason
```

**After** (New UpgradeAttemptMonitor):
```python
class UpgradeOrchestrator:
    def __init__(self, ..., upgrade_attempt_monitor):
        self._monitor_provider = upgrade_attempt_monitor  # Renamed

    def _count_upgrade_fails(self, max_attempts: int, ...):
        monitor = self._monitor_provider(max_attempts=max_attempts)

        while monitor.stop_reason is None:  # Property access
            upgrade_bar_roi = self._screenshot_service.take_screenshot(...)

            # Returns state (not tuple)
            state = monitor.process_frame(upgrade_bar_roi)

            print(f"Fails: {monitor.fail_count}")  # Property access

        return monitor.fail_count, monitor.stop_reason  # Properties
```

**Key Changes**:
1. Renamed provider: `state_machine_provider` → `upgrade_attempt_monitor`
2. Loop condition: `while stop_reason is None` → `while monitor.stop_reason is None`
3. process_frame() return: `fail_count, stop_reason = ...` → `state = ...`
4. Property access: `fail_count` and `stop_reason` via properties

---

### Updating DI Container

**Before**:
```python
class Container(containers.DeclarativeContainer):
    # Old state machine factory
    state_machine = providers.Factory(
        UpgradeStateMachine,
        max_attempts=providers.Dependency(),
    )
```

**After**:
```python
class Container(containers.DeclarativeContainer):
    # New detector singleton
    progress_bar_detector = providers.Singleton(
        ProgressBarStateDetector,
    )

    # New monitor factory
    upgrade_attempt_monitor = providers.Factory(
        UpgradeAttemptMonitor,
        detector=progress_bar_detector,
        max_attempts=providers.Dependency(),
    )
```

**Key Changes**:
1. Added `progress_bar_detector` singleton
2. Renamed `state_machine` → `upgrade_attempt_monitor`
3. Monitor receives detector via DI

---

### Updating Tests

**Before** (Testing with UpgradeStateMachine):
```python
def test_state_machine_counts_fails():
    state_machine = UpgradeStateMachine(max_attempts=10)

    # Must use real images
    fail_image = cv2.imread("test/fixtures/images/fail_state.png")

    fail_count, stop_reason = state_machine.process_frame(fail_image)

    assert fail_count == 1
```

**After** (Testing Detector and Monitor Separately):

**Option 1: Test Detector with Real Images**
```python
def test_detector_recognizes_fail_state():
    detector = ProgressBarStateDetector()
    fail_image = cv2.imread("test/fixtures/images/fail_state.png")

    state = detector.detect_state(fail_image)

    assert state == ProgressBarState.FAIL
```

**Option 2: Test Monitor with Mocked Detector**
```python
from unittest.mock import Mock

def test_monitor_counts_fail_transitions():
    # Mock detector to return controlled sequence
    mock_detector = Mock(spec=ProgressBarStateDetector)
    mock_detector.detect_state.side_effect = [
        ProgressBarState.PROGRESS,  # Not a fail
        ProgressBarState.FAIL,      # Count: 1
        ProgressBarState.PROGRESS,  # Not a fail
        ProgressBarState.FAIL,      # Count: 2
    ]

    monitor = UpgradeAttemptMonitor(mock_detector, max_attempts=10)

    # Provide dummy image (detector is mocked, image not used)
    fake_image = np.zeros((50, 200, 3), dtype=np.uint8)

    for _ in range(4):
        monitor.process_frame(fake_image)

    assert monitor.fail_count == 2
```

**Key Benefits**:
- Test CV logic independently with fixture images
- Test business logic independently with mocked detector
- Faster tests (no CV operations when testing logic)
- Easier to test edge cases (mock any state sequence)

---

## Common Patterns

### Pattern 1: Workflow with Logging

```python
import logging
from loguru import logger

def run_count_workflow(container, max_attempts=10):
    monitor = container.upgrade_attempt_monitor(max_attempts=max_attempts)
    screenshot_service = container.screenshot_service()

    logger.info(f"Starting Count workflow (max_attempts={max_attempts})")

    while monitor.stop_reason is None:
        # Capture and process
        roi_image = screenshot_service.take_screenshot()
        state = monitor.process_frame(roi_image)

        # State transitions are automatically logged at DEBUG level
        # by the monitor, so no need to log manually

        time.sleep(0.25)

    # Final summary
    logger.info(
        f"Workflow stopped: {monitor.stop_reason.value}, "
        f"Failures: {monitor.fail_count}"
    )

    return monitor.fail_count, monitor.stop_reason
```

### Pattern 2: Testing with Fixture Images

```python
import cv2
import pytest

@pytest.fixture
def detector():
    return ProgressBarStateDetector()

@pytest.fixture
def fail_image():
    return cv2.imread("test/fixtures/images/fail_state.png")

@pytest.fixture
def progress_image():
    return cv2.imread("test/fixtures/images/progress_state.png")

def test_detector_with_fixtures(detector, fail_image, progress_image):
    assert detector.detect_state(fail_image) == ProgressBarState.FAIL
    assert detector.detect_state(progress_image) == ProgressBarState.PROGRESS
```

### Pattern 3: Testing Monitor with Mock Sequence

```python
from unittest.mock import Mock
import numpy as np

def test_monitor_stops_on_success():
    # Setup mock detector
    mock_detector = Mock(spec=ProgressBarStateDetector)
    mock_detector.detect_state.side_effect = [
        ProgressBarState.STANDBY,  # 1
        ProgressBarState.STANDBY,  # 2
        ProgressBarState.STANDBY,  # 3
        ProgressBarState.STANDBY,  # 4 → SUCCESS
    ]

    monitor = UpgradeAttemptMonitor(mock_detector, max_attempts=10)

    # Simulate processing 4 frames
    fake_image = np.zeros((50, 200, 3), dtype=np.uint8)
    for _ in range(4):
        monitor.process_frame(fake_image)

    # Verify stop condition
    assert monitor.stop_reason == StopReason.SUCCESS
    assert monitor.fail_count == 0  # No failures
```

### Pattern 4: Error Handling

```python
from autoraid.core.progress_bar_detector import ProgressBarStateDetector
from autoraid.core.state_machine import UpgradeAttemptMonitor

def safe_detect_state(detector, roi_image):
    """Wrapper with error handling."""
    try:
        return detector.detect_state(roi_image)
    except ValueError as e:
        logger.error(f"Image validation failed: {e}")
        # Return UNKNOWN or raise depending on error handling strategy
        return ProgressBarState.UNKNOWN

def create_monitor_safely(container, max_attempts):
    """Create monitor with validation."""
    if max_attempts <= 0:
        raise ValueError(f"max_attempts must be positive, got {max_attempts}")

    try:
        monitor = container.upgrade_attempt_monitor(max_attempts=max_attempts)
        return monitor
    except Exception as e:
        logger.error(f"Failed to create monitor: {e}")
        raise
```

---

## Debugging Tips

### Enable DEBUG Logging

State transitions are logged at DEBUG level. Enable with:

```bash
# CLI flag
autoraid upgrade count --debug

# Or set environment variable
export AUTORAID_DEBUG=1
```

**Example DEBUG output**:
```
DEBUG | State transition: PROGRESS → FAIL (fail_count=1)
DEBUG | State transition: FAIL → PROGRESS (fail_count=1)
DEBUG | State transition: PROGRESS → FAIL (fail_count=2)
DEBUG | Stopping: MAX_ATTEMPTS_REACHED after 2 failures
```

### Inspect Monitor State

```python
# During workflow execution
print(f"Current state: {monitor.current_state}")
print(f"Fail count: {monitor.fail_count}")
print(f"Stop reason: {monitor.stop_reason}")

# Check recent state history (requires accessing private attribute - for debugging only)
print(f"Recent states: {list(monitor._recent_states)}")
```

### Test with Single Image

```python
import cv2
from autoraid.core.progress_bar_detector import ProgressBarStateDetector

detector = ProgressBarStateDetector()

# Test detection on your own image
image = cv2.imread("path/to/your/progress_bar.png")
state = detector.detect_state(image)

print(f"Detected state: {state.value}")

# Verify repeatability
for _ in range(10):
    assert detector.detect_state(image) == state
print("✓ Detector is stateless (same result 10 times)")
```

### Mock Detector in Integration Tests

```python
from unittest.mock import Mock, patch

def test_orchestrator_with_mocked_detector():
    with patch('autoraid.core.progress_bar_detector.ProgressBarStateDetector') as MockDetector:
        # Configure mock
        mock_instance = MockDetector.return_value
        mock_instance.detect_state.return_value = ProgressBarState.FAIL

        # Run orchestrator workflow
        container = Container()
        orchestrator = container.upgrade_orchestrator()
        result = orchestrator.count_workflow(max_attempts=1)

        # Verify mock was called
        assert mock_instance.detect_state.called
```

---

## Enum Reference

### ProgressBarState Values

| Enum | String Value | Visual | Meaning |
|------|--------------|--------|---------|
| `ProgressBarState.FAIL` | `"fail"` | Red bar | Upgrade failed |
| `ProgressBarState.PROGRESS` | `"progress"` | Yellow bar | Upgrade in progress |
| `ProgressBarState.STANDBY` | `"standby"` | Black bar | Ready/waiting |
| `ProgressBarState.CONNECTION_ERROR` | `"connection_error"` | Blue bar | Network error |
| `ProgressBarState.UNKNOWN` | `"unknown"` | N/A | Unrecognized |

**Usage**:
```python
if state == ProgressBarState.FAIL:
    print("Failed!")

# Access string value for logging/serialization
print(state.value)  # "fail"
```

### StopReason Values

| Enum | String Value | Condition |
|------|--------------|-----------|
| `StopReason.MAX_ATTEMPTS_REACHED` | `"max_attempts_reached"` | `fail_count >= max_attempts` |
| `StopReason.SUCCESS` | `"upgraded"` | 4 consecutive STANDBY |
| `StopReason.CONNECTION_ERROR` | `"connection_error"` | 4 consecutive CONNECTION_ERROR |

**Usage**:
```python
if monitor.stop_reason == StopReason.SUCCESS:
    print("Workflow succeeded!")

# Access string value
print(monitor.stop_reason.value)  # "upgraded"
```

**Note**: `SUCCESS` value is `"upgraded"` for backward compatibility with old `StopCountReason.UPGRADED`.

---

## API Cheat Sheet

### Detector

```python
from autoraid.core.progress_bar_detector import ProgressBarStateDetector

detector = ProgressBarStateDetector()
state: ProgressBarState = detector.detect_state(roi_image)
# Raises ValueError if roi_image is None, empty, or wrong shape
```

### Monitor

```python
from autoraid.core.state_machine import UpgradeAttemptMonitor

monitor = UpgradeAttemptMonitor(detector, max_attempts=10)
# Raises ValueError if max_attempts <= 0

state: ProgressBarState = monitor.process_frame(roi_image)
# Updates fail_count and recent_states internally

fail_count: int = monitor.fail_count  # Read-only property
stop_reason: StopReason | None = monitor.stop_reason  # Computed property
current_state: ProgressBarState | None = monitor.current_state  # Last state
```

### DI Container

```python
from autoraid.container import Container

container = Container()

detector = container.progress_bar_detector()  # Singleton
monitor = container.upgrade_attempt_monitor(max_attempts=10)  # Factory
```

---

## FAQ

### Q: Why split the state machine into two classes?

**A**: Separation of concerns. CV logic (detector) and business logic (monitor) can now be tested independently. You can test color detection with real images and test counting logic with mocked states.

### Q: Can I still use the old UpgradeStateMachine?

**A**: No. The old class will be removed after Phase 5 cleanup. Update your code to use the new components.

### Q: Do I need to update my tests?

**A**: Yes. Tests using `UpgradeStateMachine` must be updated to use the new components. See "Updating Tests" section above.

### Q: What if I only need state detection without counting?

**A**: Use `ProgressBarStateDetector` directly. You don't need the monitor if you're not tracking failures or stop conditions.

```python
detector = container.progress_bar_detector()
state = detector.detect_state(image)
```

### Q: How do I mock the detector in tests?

**A**: Use `unittest.mock.Mock` with `spec=ProgressBarStateDetector`:

```python
from unittest.mock import Mock
from autoraid.core.progress_bar_detector import ProgressBarStateDetector

mock_detector = Mock(spec=ProgressBarStateDetector)
mock_detector.detect_state.return_value = ProgressBarState.FAIL
```

### Q: Why is StopReason.SUCCESS valued "upgraded" instead of "success"?

**A**: Backward compatibility. The old `StopCountReason.UPGRADED` used `"upgraded"`, and we kept the same string value for serialization compatibility.

### Q: Can I modify fail_count directly?

**A**: No. `fail_count` is a read-only property. The monitor updates it internally when processing frames. This prevents bugs from accidental mutations.

### Q: What happens if I pass None to detector.detect_state()?

**A**: It raises `ValueError` with message `"roi_image cannot be None"`. Null images indicate a programming error (e.g., screenshot failed), not a legitimate runtime condition.

---

## Next Steps

1. **Read the full documentation**:
   - [Feature Spec](spec.md) - Requirements and success criteria
   - [Implementation Plan](plan.md) - Architecture and migration plan
   - [Data Model](data-model.md) - Detailed interface documentation

2. **Run existing tests**:
   ```bash
   cd autoraid
   uv run pytest test/unit/core/test_state_machine.py
   ```

3. **Experiment with the detector**:
   ```bash
   cd autoraid
   uv run python -c "
   from autoraid.core.progress_bar_detector import ProgressBarStateDetector
   import cv2
   detector = ProgressBarStateDetector()
   image = cv2.imread('test/fixtures/images/fail_state.png')
   print(detector.detect_state(image))
   "
   ```

4. **Review the migration checklist** in [plan.md](plan.md#migration-plan)

---

## Getting Help

- **Architecture questions**: See [CLAUDE.md](../../CLAUDE.md)
- **DI container usage**: See [container.py](../../src/autoraid/container.py)
- **Testing patterns**: See existing tests in `test/unit/core/`
- **Constitution principles**: See [.specify/memory/constitution.md](../../.specify/memory/constitution.md)
