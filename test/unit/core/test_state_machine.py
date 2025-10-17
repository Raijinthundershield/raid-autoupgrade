"""Smoke tests for UpgradeStateMachine.

These tests verify basic functionality of the state machine with fixture images.
"""

import cv2
import pytest

from autoraid.core.state_machine import (
    ProgressBarState,
    StopCountReason,
    UpgradeStateMachine,
)


@pytest.fixture
def fail_image():
    """Load a fixture image showing fail state."""
    return cv2.imread("test/fixtures/images/progress_bar_state/fail.png")


@pytest.fixture
def standby_image():
    """Load a fixture image showing standby state."""
    return cv2.imread("test/fixtures/images/progress_bar_state/standby.png")


@pytest.fixture
def progress_image():
    """Load a fixture image showing progress state."""
    return cv2.imread("test/fixtures/images/progress_bar_state/progress.png")


@pytest.fixture
def connection_error_image():
    """Load a fixture image showing connection error state."""
    return cv2.imread("test/fixtures/images/progress_bar_state/connection_error.png")


def test_state_machine_instantiates():
    """Test that UpgradeStateMachine instantiates correctly."""
    state_machine = UpgradeStateMachine(max_attempts=10)

    assert state_machine is not None
    assert state_machine.max_attempts == 10
    assert state_machine.fail_count == 0
    assert len(state_machine.recent_states) == 0


def test_state_machine_rejects_invalid_max_attempts():
    """Test that UpgradeStateMachine rejects invalid max_attempts."""
    with pytest.raises(ValueError, match="max_attempts must be greater than 0"):
        UpgradeStateMachine(max_attempts=0)

    with pytest.raises(ValueError, match="max_attempts must be greater than 0"):
        UpgradeStateMachine(max_attempts=-5)


def test_state_machine_multiple_fails(fail_image):
    """Test that state machine correctly counts fail states."""
    state_machine = UpgradeStateMachine(max_attempts=10)

    # Process 3 fail images, only one fail should be counted when multiple fails
    # in a row occur
    fail_count_1, stop_reason_1 = state_machine.process_frame(fail_image)
    assert fail_count_1 == 1
    assert stop_reason_1 is None

    fail_count_2, stop_reason_2 = state_machine.process_frame(fail_image)
    assert fail_count_2 == 1
    assert stop_reason_2 is None

    fail_count_3, stop_reason_3 = state_machine.process_frame(fail_image)
    assert fail_count_3 == 1
    assert stop_reason_3 is None


def test_state_machine_upgrades(fail_image, standby_image):
    """Test that state machine correctly counts fail states."""
    state_machine = UpgradeStateMachine(max_attempts=10)

    # Process 3 fail images, only one fail should be counted when multiple fails
    # in a row occur
    fail_count_1, stop_reason_1 = state_machine.process_frame(fail_image)
    assert fail_count_1 == 1
    assert stop_reason_1 is None

    fail_count_2, stop_reason_2 = state_machine.process_frame(standby_image)
    assert fail_count_2 == 1
    assert stop_reason_2 is None

    fail_count_3, stop_reason_3 = state_machine.process_frame(fail_image)
    assert fail_count_3 == 2
    assert stop_reason_3 is None


def test_state_machine_stops_on_upgraded(standby_image):
    """Test that state machine stops after 4 consecutive standby states."""
    state_machine = UpgradeStateMachine(max_attempts=10)

    # Process 4 consecutive standby images
    fail_count_1, stop_reason_1 = state_machine.process_frame(standby_image)
    assert stop_reason_1 is None

    fail_count_2, stop_reason_2 = state_machine.process_frame(standby_image)
    assert stop_reason_2 is None

    fail_count_3, stop_reason_3 = state_machine.process_frame(standby_image)
    assert stop_reason_3 is None

    fail_count_4, stop_reason_4 = state_machine.process_frame(standby_image)
    assert stop_reason_4 == StopCountReason.UPGRADED
    assert fail_count_4 == 0  # No fails detected


def test_state_machine_stops_on_max_attempts(fail_image, standby_image):
    """Test that state machine stops when max attempts reached."""
    state_machine = UpgradeStateMachine(max_attempts=2)

    # Process 3 fail images (reaching max attempts)
    fail_count_1, stop_reason_1 = state_machine.process_frame(fail_image)
    assert fail_count_1 == 1
    assert stop_reason_1 is None

    fail_count_2, stop_reason_2 = state_machine.process_frame(standby_image)
    assert fail_count_2 == 1
    assert stop_reason_2 is None

    fail_count_3, stop_reason_3 = state_machine.process_frame(fail_image)
    assert fail_count_3 == 2
    assert stop_reason_3 == StopCountReason.MAX_ATTEMPTS_REACHED


def test_state_machine_stops_on_connection_error(connection_error_image):
    """Test that state machine stops after 4 consecutive connection error states."""
    state_machine = UpgradeStateMachine(max_attempts=10)

    # Process 4 consecutive connection error images
    for i in range(3):
        fail_count, stop_reason = state_machine.process_frame(connection_error_image)
        assert stop_reason is None

    # Fourth connection error should trigger stop
    fail_count, stop_reason = state_machine.process_frame(connection_error_image)
    assert stop_reason == StopCountReason.CONNECTION_ERROR


def test_state_machine_tracks_recent_states(fail_image, progress_image):
    """Test that state machine tracks recent states correctly."""
    state_machine = UpgradeStateMachine(max_attempts=10)

    # Process fail, then progress
    state_machine.process_frame(fail_image)
    state_machine.process_frame(progress_image)

    # Should have 2 states in recent_states
    assert len(state_machine.recent_states) == 2
    assert state_machine.recent_states[0] == ProgressBarState.FAIL
    assert state_machine.recent_states[1] == ProgressBarState.PROGRESS


def test_state_machine_recent_states_maxlen():
    """Test that recent_states deque has maxlen of 4."""
    state_machine = UpgradeStateMachine(max_attempts=10)

    # Deque should have maxlen of 4
    assert state_machine.recent_states.maxlen == 4


def test_state_machine_rejects_invalid_image():
    """Test that state machine rejects invalid images."""
    state_machine = UpgradeStateMachine(max_attempts=10)

    import numpy as np

    # Test with empty array
    with pytest.raises(ValueError, match="roi_image must be a valid numpy array"):
        state_machine.process_frame(np.array([]))

    # Test with None
    with pytest.raises(ValueError, match="roi_image must be a valid numpy array"):
        state_machine.process_frame(None)
