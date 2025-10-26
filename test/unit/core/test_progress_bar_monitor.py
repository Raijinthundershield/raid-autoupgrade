"""Unit tests for ProgressBarMonitor."""

import numpy as np
from unittest.mock import Mock

from autoraid.core.progress_bar_monitor import (
    ProgressBarMonitor,
    ProgressBarMonitorState,
)
from autoraid.core.progress_bar_detector import (
    ProgressBarState,
    ProgressBarStateDetector,
)


class TestProgressBarMonitor:
    """Tests for ProgressBarMonitor class."""

    def test_process_frame_counts_fail_transitions(self):
        """Verify fail count increments only on FAIL transitions."""
        mock_detector = Mock(spec=ProgressBarStateDetector)
        mock_detector.detect_state.side_effect = [
            ProgressBarState.PROGRESS,  # Not a fail
            ProgressBarState.FAIL,  # Count: 1 (transition)
            ProgressBarState.FAIL,  # Count: 1 (no transition)
            ProgressBarState.PROGRESS,  # Not a fail
            ProgressBarState.FAIL,  # Count: 2 (transition)
        ]

        monitor = ProgressBarMonitor(detector=mock_detector)
        fake_image = np.zeros((50, 200, 3), dtype=np.uint8)

        for _ in range(5):
            monitor.process_frame(fake_image)

        assert monitor.fail_count == 2
        assert monitor.frames_processed == 5

    def test_get_state_returns_immutable_snapshot(self):
        """Verify state snapshot is immutable."""
        mock_detector = Mock(spec=ProgressBarStateDetector)
        mock_detector.detect_state.return_value = ProgressBarState.PROGRESS

        monitor = ProgressBarMonitor(detector=mock_detector)
        fake_image = np.zeros((50, 200, 3), dtype=np.uint8)

        monitor.process_frame(fake_image)
        state1 = monitor.get_state()

        monitor.process_frame(fake_image)
        state2 = monitor.get_state()

        # State1 should be unchanged (immutable)
        assert state1.frames_processed == 1
        assert state2.frames_processed == 2

    def test_recent_states_maintains_maxlen_4(self):
        """Verify recent_states deque maintains max length of 4."""
        mock_detector = Mock(spec=ProgressBarStateDetector)
        mock_detector.detect_state.side_effect = [
            ProgressBarState.STANDBY,
            ProgressBarState.PROGRESS,
            ProgressBarState.FAIL,
            ProgressBarState.STANDBY,
            ProgressBarState.PROGRESS,  # Should evict first STANDBY
            ProgressBarState.FAIL,  # Should evict first PROGRESS
        ]

        monitor = ProgressBarMonitor(detector=mock_detector)
        fake_image = np.zeros((50, 200, 3), dtype=np.uint8)

        for _ in range(6):
            monitor.process_frame(fake_image)

        state = monitor.get_state()
        assert len(state.recent_states) == 4
        # Should be the last 4 states
        assert state.recent_states == (
            ProgressBarState.FAIL,
            ProgressBarState.STANDBY,
            ProgressBarState.PROGRESS,
            ProgressBarState.FAIL,
        )

    def test_frames_processed_counter(self):
        """Verify frames_processed increments correctly."""
        mock_detector = Mock(spec=ProgressBarStateDetector)
        mock_detector.detect_state.return_value = ProgressBarState.STANDBY

        monitor = ProgressBarMonitor(detector=mock_detector)
        fake_image = np.zeros((50, 200, 3), dtype=np.uint8)

        assert monitor.frames_processed == 0

        monitor.process_frame(fake_image)
        assert monitor.frames_processed == 1

        monitor.process_frame(fake_image)
        assert monitor.frames_processed == 2

    def test_current_state_property(self):
        """Verify current_state property returns most recent state."""
        mock_detector = Mock(spec=ProgressBarStateDetector)
        mock_detector.detect_state.side_effect = [
            ProgressBarState.STANDBY,
            ProgressBarState.PROGRESS,
            ProgressBarState.FAIL,
        ]

        monitor = ProgressBarMonitor(detector=mock_detector)
        fake_image = np.zeros((50, 200, 3), dtype=np.uint8)

        assert monitor.current_state is None

        monitor.process_frame(fake_image)
        assert monitor.current_state == ProgressBarState.STANDBY

        monitor.process_frame(fake_image)
        assert monitor.current_state == ProgressBarState.PROGRESS

        monitor.process_frame(fake_image)
        assert monitor.current_state == ProgressBarState.FAIL

    def test_process_frame_returns_detected_state(self):
        """Verify process_frame returns the detected state."""
        mock_detector = Mock(spec=ProgressBarStateDetector)
        mock_detector.detect_state.return_value = ProgressBarState.PROGRESS

        monitor = ProgressBarMonitor(detector=mock_detector)
        fake_image = np.zeros((50, 200, 3), dtype=np.uint8)

        result = monitor.process_frame(fake_image)
        assert result == ProgressBarState.PROGRESS

    def test_fail_count_only_increments_on_transition_to_fail(self):
        """Verify fail count only increments when transitioning TO fail state."""
        mock_detector = Mock(spec=ProgressBarStateDetector)
        mock_detector.detect_state.side_effect = [
            ProgressBarState.FAIL,  # Count: 1 (first frame is a transition from None)
            ProgressBarState.FAIL,  # Count: 1 (no transition)
            ProgressBarState.FAIL,  # Count: 1 (no transition)
        ]

        monitor = ProgressBarMonitor(detector=mock_detector)
        fake_image = np.zeros((50, 200, 3), dtype=np.uint8)

        for _ in range(3):
            monitor.process_frame(fake_image)

        # First FAIL from None should count as a transition
        assert monitor.fail_count == 1

    def test_state_snapshot_contains_all_fields(self):
        """Verify state snapshot contains all required fields."""
        mock_detector = Mock(spec=ProgressBarStateDetector)
        mock_detector.detect_state.side_effect = [
            ProgressBarState.PROGRESS,
            ProgressBarState.FAIL,
        ]

        monitor = ProgressBarMonitor(detector=mock_detector)
        fake_image = np.zeros((50, 200, 3), dtype=np.uint8)

        monitor.process_frame(fake_image)
        monitor.process_frame(fake_image)

        state = monitor.get_state()

        assert isinstance(state, ProgressBarMonitorState)
        assert state.frames_processed == 2
        assert state.fail_count == 1
        assert state.recent_states == (ProgressBarState.PROGRESS, ProgressBarState.FAIL)
        assert state.current_state == ProgressBarState.FAIL

    def test_multiple_fail_transitions_counted_correctly(self):
        """Verify multiple fail transitions are counted correctly."""
        mock_detector = Mock(spec=ProgressBarStateDetector)
        mock_detector.detect_state.side_effect = [
            ProgressBarState.PROGRESS,
            ProgressBarState.FAIL,  # Count: 1
            ProgressBarState.STANDBY,
            ProgressBarState.FAIL,  # Count: 2
            ProgressBarState.PROGRESS,
            ProgressBarState.FAIL,  # Count: 3
        ]

        monitor = ProgressBarMonitor(detector=mock_detector)
        fake_image = np.zeros((50, 200, 3), dtype=np.uint8)

        for _ in range(6):
            monitor.process_frame(fake_image)

        assert monitor.fail_count == 3

    def test_recent_states_tuple_is_immutable(self):
        """Verify recent_states in state snapshot is a tuple (immutable)."""
        mock_detector = Mock(spec=ProgressBarStateDetector)
        mock_detector.detect_state.return_value = ProgressBarState.PROGRESS

        monitor = ProgressBarMonitor(detector=mock_detector)
        fake_image = np.zeros((50, 200, 3), dtype=np.uint8)

        monitor.process_frame(fake_image)
        state = monitor.get_state()

        assert isinstance(state.recent_states, tuple)
        # Tuples are immutable, so this should work
        assert len(state.recent_states) == 1
