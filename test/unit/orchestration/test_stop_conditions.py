"""Unit tests for stop condition classes."""

from raid_autoupgrade.detection.progress_bar_detector import ProgressBarState
from raid_autoupgrade.orchestration.progress_bar_monitor import ProgressBarMonitorState
from raid_autoupgrade.orchestration.stop_conditions import (
    STALL_THRESHOLD_FRAMES,
    ConnectionErrorCondition,
    MaxAttemptsCondition,
    MaxFramesCondition,
    StallCondition,
    StopConditionChain,
    StopReason,
    UpgradedCondition,
)


def _state(frames_processed: int, fail_count: int) -> ProgressBarMonitorState:
    """A monitor-state snapshot carrying only the counters StallCondition reads."""
    return ProgressBarMonitorState(
        frames_processed=frames_processed,
        fail_count=fail_count,
        recent_states=(),
        current_state=None,
    )


class TestStallCondition:
    """Tests for StallCondition — the fail-count heartbeat watchdog."""

    def test_fires_after_threshold_failless_frames(self):
        """With no fail ever landing, the stall fires once frames have advanced
        the threshold past the start mark."""
        condition = StallCondition()

        # One fail lands at frame 1, then frames keep flowing without new fails.
        assert condition.check(_state(frames_processed=1, fail_count=1)) is False
        assert condition.get_reason() == StopReason.STALLED
        assert (
            condition.check(
                _state(frames_processed=1 + STALL_THRESHOLD_FRAMES, fail_count=1)
            )
            is True
        )

    def test_steady_fails_never_stall(self):
        """A new fail every few frames keeps resetting the heartbeat, so the
        stall never fires no matter how long the run goes."""
        condition = StallCondition()

        fail_count = 0
        for frame in range(1, 5 * STALL_THRESHOLD_FRAMES + 1):
            # Land a new fail well within the threshold (every 3 frames).
            if frame % 3 == 0:
                fail_count += 1
            assert (
                condition.check(_state(frames_processed=frame, fail_count=fail_count))
                is False
            )

    def test_does_not_fire_one_frame_before_threshold(self):
        """One frame short of the threshold, the stall has not yet fired."""
        condition = StallCondition()

        condition.check(_state(frames_processed=1, fail_count=1))
        assert (
            condition.check(
                _state(frames_processed=STALL_THRESHOLD_FRAMES, fail_count=1)
            )
            is False
        )


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
