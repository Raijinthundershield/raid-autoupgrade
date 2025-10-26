"""Unit tests for stop condition classes."""

import pytest

from autoraid.core.stop_conditions import (
    StopReason,
    MaxAttemptsCondition,
    MaxFramesCondition,
    UpgradedCondition,
    ConnectionErrorCondition,
    StopConditionChain,
)
from autoraid.core.progress_bar_monitor import ProgressBarMonitorState
from autoraid.core.progress_bar_detector import ProgressBarState


class TestMaxAttemptsCondition:
    """Tests for MaxAttemptsCondition."""

    def test_triggers_at_threshold(self):
        """Verify MaxAttemptsCondition triggers at exact threshold."""
        condition = MaxAttemptsCondition(max_attempts=5)

        state_below = ProgressBarMonitorState(
            frames_processed=10,
            fail_count=4,
            recent_states=(),
            current_state=None,
        )
        state_at = ProgressBarMonitorState(
            frames_processed=11,
            fail_count=5,
            recent_states=(),
            current_state=None,
        )
        state_above = ProgressBarMonitorState(
            frames_processed=12,
            fail_count=6,
            recent_states=(),
            current_state=None,
        )

        assert condition.check(state_below) is False
        assert condition.check(state_at) is True
        assert condition.check(state_above) is True

    def test_get_reason_returns_correct_enum(self):
        """Verify get_reason returns MAX_ATTEMPTS_REACHED."""
        condition = MaxAttemptsCondition(max_attempts=5)
        assert condition.get_reason() == StopReason.MAX_ATTEMPTS_REACHED

    def test_rejects_zero_max_attempts(self):
        """Verify constructor rejects zero max_attempts."""
        with pytest.raises(ValueError, match="max_attempts must be positive"):
            MaxAttemptsCondition(max_attempts=0)

    def test_rejects_negative_max_attempts(self):
        """Verify constructor rejects negative max_attempts."""
        with pytest.raises(ValueError, match="max_attempts must be positive"):
            MaxAttemptsCondition(max_attempts=-1)


class TestMaxFramesCondition:
    """Tests for MaxFramesCondition."""

    def test_triggers_at_threshold(self):
        """Verify MaxFramesCondition triggers at exact threshold."""
        condition = MaxFramesCondition(max_frames=100)

        state_below = ProgressBarMonitorState(
            frames_processed=99,
            fail_count=0,
            recent_states=(),
            current_state=None,
        )
        state_at = ProgressBarMonitorState(
            frames_processed=100,
            fail_count=0,
            recent_states=(),
            current_state=None,
        )
        state_above = ProgressBarMonitorState(
            frames_processed=101,
            fail_count=0,
            recent_states=(),
            current_state=None,
        )

        assert condition.check(state_below) is False
        assert condition.check(state_at) is True
        assert condition.check(state_above) is True

    def test_get_reason_returns_correct_enum(self):
        """Verify get_reason returns MAX_FRAMES_CAPTURED."""
        condition = MaxFramesCondition(max_frames=100)
        assert condition.get_reason() == StopReason.MAX_FRAMES_CAPTURED

    def test_rejects_zero_max_frames(self):
        """Verify constructor rejects zero max_frames."""
        with pytest.raises(ValueError, match="max_frames must be positive"):
            MaxFramesCondition(max_frames=0)

    def test_rejects_negative_max_frames(self):
        """Verify constructor rejects negative max_frames."""
        with pytest.raises(ValueError, match="max_frames must be positive"):
            MaxFramesCondition(max_frames=-1)


class TestUpgradedCondition:
    """Tests for UpgradedCondition."""

    def test_requires_4_standby_states(self):
        """Verify UpgradedCondition needs exactly 4 consecutive STANDBY."""
        condition = UpgradedCondition(network_disabled=False)

        state_3_standby = ProgressBarMonitorState(
            frames_processed=3,
            fail_count=0,
            recent_states=(
                ProgressBarState.STANDBY,
                ProgressBarState.STANDBY,
                ProgressBarState.STANDBY,
            ),
            current_state=ProgressBarState.STANDBY,
        )
        state_4_standby = ProgressBarMonitorState(
            frames_processed=4,
            fail_count=0,
            recent_states=(
                ProgressBarState.STANDBY,
                ProgressBarState.STANDBY,
                ProgressBarState.STANDBY,
                ProgressBarState.STANDBY,
            ),
            current_state=ProgressBarState.STANDBY,
        )

        assert condition.check(state_3_standby) is False
        assert condition.check(state_4_standby) is True

    def test_network_disabled_accepts_connection_error(self):
        """Verify UpgradedCondition accepts 4 CONNECTION_ERROR when network_disabled=True."""
        condition = UpgradedCondition(network_disabled=True)

        state_4_connection_error = ProgressBarMonitorState(
            frames_processed=4,
            fail_count=0,
            recent_states=(
                ProgressBarState.CONNECTION_ERROR,
                ProgressBarState.CONNECTION_ERROR,
                ProgressBarState.CONNECTION_ERROR,
                ProgressBarState.CONNECTION_ERROR,
            ),
            current_state=ProgressBarState.CONNECTION_ERROR,
        )

        assert condition.check(state_4_connection_error) is True

    def test_network_enabled_rejects_connection_error(self):
        """Verify UpgradedCondition rejects CONNECTION_ERROR when network_disabled=False."""
        condition = UpgradedCondition(network_disabled=False)

        state_4_connection_error = ProgressBarMonitorState(
            frames_processed=4,
            fail_count=0,
            recent_states=(
                ProgressBarState.CONNECTION_ERROR,
                ProgressBarState.CONNECTION_ERROR,
                ProgressBarState.CONNECTION_ERROR,
                ProgressBarState.CONNECTION_ERROR,
            ),
            current_state=ProgressBarState.CONNECTION_ERROR,
        )

        assert condition.check(state_4_connection_error) is False

    def test_rejects_mixed_states(self):
        """Verify UpgradedCondition rejects mixed states."""
        condition = UpgradedCondition(network_disabled=False)

        state_mixed = ProgressBarMonitorState(
            frames_processed=4,
            fail_count=0,
            recent_states=(
                ProgressBarState.STANDBY,
                ProgressBarState.STANDBY,
                ProgressBarState.PROGRESS,
                ProgressBarState.STANDBY,
            ),
            current_state=ProgressBarState.STANDBY,
        )

        assert condition.check(state_mixed) is False

    def test_get_reason_returns_correct_enum(self):
        """Verify get_reason returns UPGRADED."""
        condition = UpgradedCondition(network_disabled=False)
        assert condition.get_reason() == StopReason.UPGRADED


class TestConnectionErrorCondition:
    """Tests for ConnectionErrorCondition."""

    def test_requires_4_connection_error_states(self):
        """Verify ConnectionErrorCondition needs 4 consecutive CONNECTION_ERROR."""
        condition = ConnectionErrorCondition()

        state_3_error = ProgressBarMonitorState(
            frames_processed=3,
            fail_count=0,
            recent_states=(
                ProgressBarState.CONNECTION_ERROR,
                ProgressBarState.CONNECTION_ERROR,
                ProgressBarState.CONNECTION_ERROR,
            ),
            current_state=ProgressBarState.CONNECTION_ERROR,
        )
        state_4_error = ProgressBarMonitorState(
            frames_processed=4,
            fail_count=0,
            recent_states=(
                ProgressBarState.CONNECTION_ERROR,
                ProgressBarState.CONNECTION_ERROR,
                ProgressBarState.CONNECTION_ERROR,
                ProgressBarState.CONNECTION_ERROR,
            ),
            current_state=ProgressBarState.CONNECTION_ERROR,
        )

        assert condition.check(state_3_error) is False
        assert condition.check(state_4_error) is True

    def test_rejects_other_states(self):
        """Verify ConnectionErrorCondition rejects non-CONNECTION_ERROR states."""
        condition = ConnectionErrorCondition()

        state_standby = ProgressBarMonitorState(
            frames_processed=4,
            fail_count=0,
            recent_states=(
                ProgressBarState.STANDBY,
                ProgressBarState.STANDBY,
                ProgressBarState.STANDBY,
                ProgressBarState.STANDBY,
            ),
            current_state=ProgressBarState.STANDBY,
        )

        assert condition.check(state_standby) is False

    def test_get_reason_returns_correct_enum(self):
        """Verify get_reason returns CONNECTION_ERROR."""
        condition = ConnectionErrorCondition()
        assert condition.get_reason() == StopReason.CONNECTION_ERROR


class TestStopConditionChain:
    """Tests for StopConditionChain."""

    def test_returns_first_match_in_priority_order(self):
        """Verify chain returns first matching condition in order."""
        chain = StopConditionChain(
            [
                MaxAttemptsCondition(max_attempts=5),
                UpgradedCondition(network_disabled=False),
            ]
        )

        # State matches both conditions
        state = ProgressBarMonitorState(
            frames_processed=10,
            fail_count=5,
            recent_states=(
                ProgressBarState.STANDBY,
                ProgressBarState.STANDBY,
                ProgressBarState.STANDBY,
                ProgressBarState.STANDBY,
            ),
            current_state=ProgressBarState.STANDBY,
        )

        # Should return first condition's reason (MAX_ATTEMPTS)
        assert chain.check(state) == StopReason.MAX_ATTEMPTS_REACHED

    def test_returns_none_when_no_match(self):
        """Verify chain returns None when no condition matches."""
        chain = StopConditionChain(
            [
                MaxAttemptsCondition(max_attempts=10),
                UpgradedCondition(network_disabled=False),
            ]
        )

        state = ProgressBarMonitorState(
            frames_processed=5,
            fail_count=3,
            recent_states=(
                ProgressBarState.PROGRESS,
                ProgressBarState.PROGRESS,
            ),
            current_state=ProgressBarState.PROGRESS,
        )

        assert chain.check(state) is None

    def test_should_stop_returns_true_when_condition_met(self):
        """Verify should_stop() convenience method returns True when any condition met."""
        chain = StopConditionChain([MaxAttemptsCondition(max_attempts=5)])

        state = ProgressBarMonitorState(
            frames_processed=10,
            fail_count=5,
            recent_states=(),
            current_state=None,
        )

        assert chain.should_stop(state) is True

    def test_should_stop_returns_false_when_no_condition_met(self):
        """Verify should_stop() convenience method returns False when no condition met."""
        chain = StopConditionChain([MaxAttemptsCondition(max_attempts=10)])

        state = ProgressBarMonitorState(
            frames_processed=5,
            fail_count=3,
            recent_states=(),
            current_state=None,
        )

        assert chain.should_stop(state) is False

    def test_empty_chain_returns_none(self):
        """Verify empty chain returns None."""
        chain = StopConditionChain([])

        state = ProgressBarMonitorState(
            frames_processed=100,
            fail_count=50,
            recent_states=(),
            current_state=None,
        )

        assert chain.check(state) is None
        assert chain.should_stop(state) is False

    def test_chain_with_multiple_conditions(self):
        """Verify chain evaluates multiple conditions correctly."""
        chain = StopConditionChain(
            [
                MaxAttemptsCondition(max_attempts=99),
                UpgradedCondition(network_disabled=False),
                ConnectionErrorCondition(),
            ]
        )

        # Test upgraded condition triggers
        state_upgraded = ProgressBarMonitorState(
            frames_processed=50,
            fail_count=10,
            recent_states=(
                ProgressBarState.STANDBY,
                ProgressBarState.STANDBY,
                ProgressBarState.STANDBY,
                ProgressBarState.STANDBY,
            ),
            current_state=ProgressBarState.STANDBY,
        )
        assert chain.check(state_upgraded) == StopReason.UPGRADED

        # Test connection error triggers
        state_error = ProgressBarMonitorState(
            frames_processed=50,
            fail_count=10,
            recent_states=(
                ProgressBarState.CONNECTION_ERROR,
                ProgressBarState.CONNECTION_ERROR,
                ProgressBarState.CONNECTION_ERROR,
                ProgressBarState.CONNECTION_ERROR,
            ),
            current_state=ProgressBarState.CONNECTION_ERROR,
        )
        assert chain.check(state_error) == StopReason.CONNECTION_ERROR
