"""Unit tests for UpgradeAttemptMonitor.

Tests the stateful monitor class with mocked detector.
Coverage target: ≥90%
"""

import numpy as np
import pytest
from unittest.mock import Mock

from autoraid.core.progress_bar_detector import ProgressBarStateDetector
from autoraid.core.state_machine import (
    UpgradeAttemptMonitor,
    ProgressBarState,
    StopReason,
)


@pytest.fixture
def mock_detector():
    """Create a mock detector for testing."""
    return Mock(spec=ProgressBarStateDetector)


@pytest.fixture
def fake_image():
    """Create a dummy image for testing (detector is mocked, image not used)."""
    return np.zeros((50, 200, 3), dtype=np.uint8)


def test_monitor_counts_fail_transitions(mock_detector, fake_image):
    """Test monitor counts only transitions to FAIL state, not consecutive fails."""
    # Configure mock to return a sequence with 2 fail transitions
    mock_detector.detect_state.side_effect = [
        ProgressBarState.PROGRESS,  # Not a fail
        ProgressBarState.FAIL,  # Transition: count = 1
        ProgressBarState.PROGRESS,  # Not a fail
        ProgressBarState.FAIL,  # Transition: count = 2
    ]

    monitor = UpgradeAttemptMonitor(mock_detector, max_attempts=10)

    # Process all 4 frames
    for _ in range(4):
        monitor.process_frame(fake_image)

    assert monitor.fail_count == 2


def test_monitor_ignores_consecutive_fails(mock_detector, fake_image):
    """Test monitor ignores consecutive FAIL states (only counts transitions)."""
    # Configure mock to return consecutive fails
    mock_detector.detect_state.side_effect = [
        ProgressBarState.PROGRESS,  # Not a fail
        ProgressBarState.FAIL,  # Transition: count = 1
        ProgressBarState.FAIL,  # Consecutive fail: count still 1
        ProgressBarState.FAIL,  # Consecutive fail: count still 1
    ]

    monitor = UpgradeAttemptMonitor(mock_detector, max_attempts=10)

    # Process all 4 frames
    for _ in range(4):
        monitor.process_frame(fake_image)

    assert monitor.fail_count == 1


def test_monitor_stops_on_max_attempts(mock_detector, fake_image):
    """Test monitor stops with MAX_ATTEMPTS_REACHED when fail count reaches max."""
    # Configure mock to return 3 fail transitions (max_attempts=2)
    mock_detector.detect_state.side_effect = [
        ProgressBarState.PROGRESS,
        ProgressBarState.FAIL,  # Count = 1
        ProgressBarState.PROGRESS,
        ProgressBarState.FAIL,  # Count = 2 (max reached)
        ProgressBarState.PROGRESS,
        ProgressBarState.FAIL,  # Count = 3 (over max)
    ]

    monitor = UpgradeAttemptMonitor(mock_detector, max_attempts=2)

    # Process frames until stopped
    for i in range(4):
        monitor.process_frame(fake_image)
        if monitor.stop_reason == StopReason.MAX_ATTEMPTS_REACHED:
            break

    assert monitor.stop_reason == StopReason.MAX_ATTEMPTS_REACHED
    assert monitor.fail_count == 2


def test_monitor_stops_on_success(mock_detector, fake_image):
    """Test monitor stops with SUCCESS after 4 consecutive STANDBY states."""
    # Configure mock to return 4 consecutive STANDBY states
    mock_detector.detect_state.side_effect = [
        ProgressBarState.PROGRESS,
        ProgressBarState.STANDBY,  # 1st STANDBY
        ProgressBarState.STANDBY,  # 2nd STANDBY
        ProgressBarState.STANDBY,  # 3rd STANDBY
        ProgressBarState.STANDBY,  # 4th STANDBY → SUCCESS
    ]

    monitor = UpgradeAttemptMonitor(mock_detector, max_attempts=10)

    # Process all 5 frames
    for _ in range(5):
        monitor.process_frame(fake_image)

    assert monitor.stop_reason == StopReason.SUCCESS
    assert monitor.fail_count == 0  # No failures


def test_monitor_stops_on_connection_error(mock_detector, fake_image):
    """Test monitor stops with CONNECTION_ERROR after 4 consecutive CONNECTION_ERROR states."""
    # Configure mock to return 4 consecutive CONNECTION_ERROR states
    mock_detector.detect_state.side_effect = [
        ProgressBarState.PROGRESS,
        ProgressBarState.CONNECTION_ERROR,  # 1st ERROR
        ProgressBarState.CONNECTION_ERROR,  # 2nd ERROR
        ProgressBarState.CONNECTION_ERROR,  # 3rd ERROR
        ProgressBarState.CONNECTION_ERROR,  # 4th ERROR → STOP
    ]

    monitor = UpgradeAttemptMonitor(mock_detector, max_attempts=10)

    # Process all 5 frames
    for _ in range(5):
        monitor.process_frame(fake_image)

    assert monitor.stop_reason == StopReason.CONNECTION_ERROR
    assert monitor.fail_count == 0  # No failures


def test_monitor_does_not_stop_early(mock_detector, fake_image):
    """Test monitor continues when less than 4 consecutive states (no early stop)."""
    # Configure mock to return only 3 consecutive STANDBY states
    mock_detector.detect_state.side_effect = [
        ProgressBarState.STANDBY,  # 1st STANDBY
        ProgressBarState.STANDBY,  # 2nd STANDBY
        ProgressBarState.STANDBY,  # 3rd STANDBY (not enough for SUCCESS)
    ]

    monitor = UpgradeAttemptMonitor(mock_detector, max_attempts=10)

    # Process 3 frames
    for _ in range(3):
        monitor.process_frame(fake_image)

    # Should NOT stop yet (need 4 consecutive)
    assert monitor.stop_reason is None


def test_monitor_tracks_current_state(mock_detector, fake_image):
    """Test monitor.current_state property returns last processed state."""
    # Configure mock to return a sequence
    mock_detector.detect_state.side_effect = [
        ProgressBarState.PROGRESS,
        ProgressBarState.FAIL,
        ProgressBarState.STANDBY,
    ]

    monitor = UpgradeAttemptMonitor(mock_detector, max_attempts=10)

    # Initially, no state
    assert monitor.current_state is None

    # After first frame
    monitor.process_frame(fake_image)
    assert monitor.current_state == ProgressBarState.PROGRESS

    # After second frame
    monitor.process_frame(fake_image)
    assert monitor.current_state == ProgressBarState.FAIL

    # After third frame
    monitor.process_frame(fake_image)
    assert monitor.current_state == ProgressBarState.STANDBY


def test_monitor_validates_max_attempts(mock_detector):
    """Test monitor raises ValueError when max_attempts <= 0."""
    # Test zero
    with pytest.raises(ValueError, match="max_attempts must be positive"):
        UpgradeAttemptMonitor(mock_detector, max_attempts=0)

    # Test negative
    with pytest.raises(ValueError, match="max_attempts must be positive"):
        UpgradeAttemptMonitor(mock_detector, max_attempts=-1)


def test_monitor_fail_count_property_readonly(mock_detector, fake_image):
    """Test fail_count property is read-only and returns int."""
    mock_detector.detect_state.return_value = ProgressBarState.PROGRESS

    monitor = UpgradeAttemptMonitor(mock_detector, max_attempts=10)

    # Verify fail_count is an int
    assert isinstance(monitor.fail_count, int)
    assert monitor.fail_count == 0

    # Verify property is read-only (cannot set)
    with pytest.raises(AttributeError):
        monitor.fail_count = 5


def test_monitor_stop_reason_priority_order(mock_detector, fake_image):
    """Test MAX_ATTEMPTS_REACHED has priority over other stop conditions."""
    # Configure mock to return 4 STANDBY states (would trigger SUCCESS)
    # But we set max_attempts=0 so MAX_ATTEMPTS_REACHED fires first
    mock_detector.detect_state.side_effect = [
        ProgressBarState.FAIL,  # Count = 1 (but max_attempts=1, so already at max)
        ProgressBarState.STANDBY,
        ProgressBarState.STANDBY,
        ProgressBarState.STANDBY,
        ProgressBarState.STANDBY,
    ]

    monitor = UpgradeAttemptMonitor(mock_detector, max_attempts=1)

    # Process first frame (reaches max)
    monitor.process_frame(fake_image)

    # MAX_ATTEMPTS_REACHED should fire immediately
    assert monitor.stop_reason == StopReason.MAX_ATTEMPTS_REACHED
    assert monitor.fail_count == 1
