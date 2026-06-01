"""Unit tests for SpendWorkflow with mocked dependencies.

Tests the validation and execution logic with mocked services.
Following smoke test philosophy - verify basic functionality and regressions.
"""

from unittest.mock import Mock, patch

import pytest

from raid_autoupgrade.detection.progress_bar_detector import (
    ProgressBarState,
    ProgressBarStateDetector,
)
from raid_autoupgrade.exceptions import WorkflowValidationError
from raid_autoupgrade.orchestration.stop_conditions import StopReason
from raid_autoupgrade.orchestration.upgrade_orchestrator import (
    ProgressEvent,
    UpgradeResult,
)
from raid_autoupgrade.services.network import NetworkState
from raid_autoupgrade.workflows.spend_workflow import (
    SpendProgress,
    SpendResult,
    SpendWorkflow,
    enrich_spend_progress,
)


def _online_network_manager() -> Mock:
    """A NetworkManager mock that reports internet ON, so SpendWorkflow.run()
    passes its pre-flight validation (spend requires internet)."""
    manager = Mock()
    manager.check_network_access.return_value = NetworkState.ONLINE
    return manager


class TestEnrichSpendProgress:
    """The pure enrichment function: session ProgressEvent + base loop totals
    → cumulative Spend snapshot."""

    def test_within_session_counts_up_used_and_down_remaining(self):
        # Base totals at the start of a session: 2 attempts already used, 8 left,
        # 1 upgrade so far. The orchestrator reports 3 fails this session.
        event = ProgressEvent(fail_count=3, frames=40, state=ProgressBarState.FAIL)

        snapshot = enrich_spend_progress(
            attempt_count=2,
            remaining_attempts=8,
            upgrade_count=1,
            event=event,
        )

        assert snapshot.attempts_used == 5  # 2 base + 3 this session
        assert snapshot.remaining == 5  # 8 base - 3 this session
        assert snapshot.upgrades == 1
        assert snapshot.state is ProgressBarState.FAIL

    def test_across_session_boundary_stays_monotonic(self):
        # Session 1 (max 10): starts at base 0/10/0. Its last live frame reports
        # 3 fails just before the piece upgrades.
        last = enrich_spend_progress(
            attempt_count=0,
            remaining_attempts=10,
            upgrade_count=0,
            event=ProgressEvent(fail_count=3, frames=30, state=ProgressBarState.FAIL),
        )
        assert (last.attempts_used, last.remaining, last.upgrades) == (3, 7, 0)

        # Session boundary: the upgrade consumed those 3 fails + 1 success, and
        # the upgrade count ticks. The next session's base totals.
        first = enrich_spend_progress(
            attempt_count=3,  # 0 + 3 fails
            remaining_attempts=6,  # 10 - 3 fails - 1 success
            upgrade_count=1,
            event=ProgressEvent(
                fail_count=0, frames=31, state=ProgressBarState.PROGRESS
            ),
        )

        # Crossing the boundary never regresses: used does not drop, remaining
        # does not rise, upgrades does not drop.
        assert first.attempts_used >= last.attempts_used
        assert first.remaining <= last.remaining
        assert first.upgrades >= last.upgrades
        assert (first.attempts_used, first.remaining, first.upgrades) == (3, 6, 1)


class TestSpendWorkflowValidation:
    """Test validation phase of SpendWorkflow."""

    def test_validate_internet_unavailable(self):
        """Test validation fails when internet is not available (T050)."""
        # Arrange: Mock services
        mock_network_manager = Mock()
        mock_network_manager.check_network_access.return_value = NetworkState.OFFLINE

        workflow = SpendWorkflow(
            cache_service=Mock(),
            window_interaction_service=Mock(),
            network_manager=mock_network_manager,
            screenshot_service=Mock(),
            detector=Mock(spec=ProgressBarStateDetector),
            max_upgrade_attempts=10,
            continue_upgrade=False,
            debug_dir=None,
        )

        # Act & Assert: Validation should raise WorkflowValidationError
        with pytest.raises(WorkflowValidationError):
            workflow.validate()

    def test_validate_internet_available_passes(self):
        """Test validation passes when internet is available."""
        # Arrange: Mock services
        mock_network_manager = Mock()
        mock_network_manager.check_network_access.return_value = NetworkState.ONLINE

        workflow = SpendWorkflow(
            cache_service=Mock(),
            window_interaction_service=Mock(),
            network_manager=mock_network_manager,
            screenshot_service=Mock(),
            detector=Mock(spec=ProgressBarStateDetector),
            max_upgrade_attempts=10,
            continue_upgrade=False,
            debug_dir=None,
        )

        # Act & Assert: Validation should pass without raising
        workflow.validate()  # Should not raise


class TestSpendWorkflowExecution:
    """Test execution phase of SpendWorkflow (T051)."""

    @patch("raid_autoupgrade.workflows.spend_workflow.UpgradeOrchestrator")
    def test_run_aborts_when_offline(self, mock_orchestrator_class):
        """run() must validate up front: no internet → raise, never touch the
        orchestrator (spend needs internet to persist upgrades)."""
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_network_manager = Mock()
        mock_network_manager.check_network_access.return_value = NetworkState.OFFLINE

        mock_window_service = Mock()
        mock_window_service.get_window_size.return_value = (1920, 1080)

        workflow = SpendWorkflow(
            cache_service=Mock(),
            window_interaction_service=mock_window_service,
            network_manager=mock_network_manager,
            screenshot_service=Mock(),
            detector=Mock(spec=ProgressBarStateDetector),
            max_upgrade_attempts=10,
        )

        with pytest.raises(WorkflowValidationError):
            workflow.run()

        mock_orchestrator.run_monitor.assert_not_called()

    @patch("raid_autoupgrade.workflows.spend_workflow.UpgradeOrchestrator")
    def test_run_raises_when_regions_not_cached(self, mock_orchestrator_class):
        """run() raises a clear error when no regions are cached for the window
        size, instead of crashing on regions[...] indexing."""
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_cache_service = Mock()
        mock_cache_service.get_regions.return_value = None

        mock_window_service = Mock()
        mock_window_service.get_window_size.return_value = (1920, 1080)

        workflow = SpendWorkflow(
            cache_service=mock_cache_service,
            window_interaction_service=mock_window_service,
            network_manager=_online_network_manager(),
            screenshot_service=Mock(),
            detector=Mock(spec=ProgressBarStateDetector),
            max_upgrade_attempts=10,
        )

        with pytest.raises(WorkflowValidationError):
            workflow.run()

        mock_orchestrator.run_monitor.assert_not_called()

    @patch("raid_autoupgrade.workflows.spend_workflow.UpgradeOrchestrator")
    def test_run_single_upgrade_success(self, mock_orchestrator_class):
        """Test workflow execution with single upgrade success."""
        # Arrange: Mock orchestrator to return UPGRADED result
        mock_orchestrator = Mock()
        mock_result = UpgradeResult(
            fail_count=5,
            frames_processed=20,
            stop_reason=StopReason.UPGRADED,
            debug_session_dir=None,
        )
        mock_orchestrator.run_monitor.return_value = mock_result
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_cache_service = Mock()
        mock_cache_service.get_regions.return_value = {
            "upgrade_button": (100, 200, 50, 30),
            "upgrade_bar": (100, 250, 200, 10),
        }

        mock_window_service = Mock()
        mock_window_service.get_window_size.return_value = (1920, 1080)

        workflow = SpendWorkflow(
            cache_service=mock_cache_service,
            window_interaction_service=mock_window_service,
            network_manager=_online_network_manager(),
            screenshot_service=Mock(),
            detector=Mock(spec=ProgressBarStateDetector),
            max_upgrade_attempts=10,
            continue_upgrade=False,
            debug_dir=None,
        )

        # Act: Run workflow
        result = workflow.run()

        # Assert: Verify result
        assert isinstance(result, SpendResult)
        assert result.upgrade_count == 1
        assert result.attempt_count == 5
        assert result.remaining_attempts == 4  # 10 max - 5 fails - 1 success
        assert result.stop_reason == StopReason.UPGRADED

        # Verify orchestrator was called once
        mock_orchestrator.run_monitor.assert_called_once()

    @patch("raid_autoupgrade.workflows.spend_workflow.UpgradeScreen")
    @patch("raid_autoupgrade.workflows.spend_workflow.UpgradeOrchestrator")
    def test_run_max_attempts_exhausted(
        self, mock_orchestrator_class, mock_screen_class
    ):
        """Test workflow stops when max_attempts is exhausted, aborting the
        pending attempt through the screen's intent-named cancel_attempt() —
        no raw Region coordinate is handled in the workflow."""
        # Arrange: Mock orchestrator to return MAX_ATTEMPTS_REACHED
        mock_orchestrator = Mock()
        mock_result = UpgradeResult(
            fail_count=10,
            frames_processed=40,
            stop_reason=StopReason.MAX_ATTEMPTS_REACHED,
            debug_session_dir=None,
        )
        mock_orchestrator.run_monitor.return_value = mock_result
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_screen = mock_screen_class.return_value

        mock_window_service = Mock()
        mock_window_service.get_window_size.return_value = (1920, 1080)

        workflow = SpendWorkflow(
            cache_service=Mock(),
            window_interaction_service=mock_window_service,
            network_manager=_online_network_manager(),
            screenshot_service=Mock(),
            detector=Mock(spec=ProgressBarStateDetector),
            max_upgrade_attempts=10,
            continue_upgrade=False,
            debug_dir=None,
        )

        # Act: Run workflow
        result = workflow.run()

        # Assert: Verify result shows max attempts exhausted
        assert result.upgrade_count == 0  # No upgrades
        assert result.attempt_count == 10
        assert result.remaining_attempts == 0
        assert result.stop_reason == StopReason.MAX_ATTEMPTS_REACHED

        # Abort goes through the screen, not a raw coordinate click.
        mock_screen.cancel_attempt.assert_called_once()
        mock_window_service.click_region.assert_not_called()

    @patch("raid_autoupgrade.workflows.spend_workflow.UpgradeOrchestrator")
    def test_run_connection_error(self, mock_orchestrator_class):
        """Test workflow stops on connection error."""
        # Arrange: Mock orchestrator to return CONNECTION_ERROR
        mock_orchestrator = Mock()
        mock_result = UpgradeResult(
            fail_count=3,
            frames_processed=15,
            stop_reason=StopReason.CONNECTION_ERROR,
            debug_session_dir=None,
        )
        mock_orchestrator.run_monitor.return_value = mock_result
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_cache_service = Mock()
        mock_cache_service.get_regions.return_value = {
            "upgrade_button": (100, 200, 50, 30),
            "upgrade_bar": (100, 250, 200, 10),
        }

        mock_window_service = Mock()
        mock_window_service.get_window_size.return_value = (1920, 1080)

        workflow = SpendWorkflow(
            cache_service=mock_cache_service,
            window_interaction_service=mock_window_service,
            network_manager=_online_network_manager(),
            screenshot_service=Mock(),
            detector=Mock(spec=ProgressBarStateDetector),
            max_upgrade_attempts=10,
            continue_upgrade=False,
            debug_dir=None,
        )

        # Act: Run workflow
        result = workflow.run()

        # Assert: Verify result shows connection error
        assert result.upgrade_count == 0
        assert result.attempt_count == 3
        assert result.remaining_attempts == 7
        assert result.stop_reason == StopReason.CONNECTION_ERROR


class TestSpendWorkflowContinueUpgrade:
    """Test continue upgrade logic (T052)."""

    @patch("raid_autoupgrade.workflows.spend_workflow.UpgradeOrchestrator")
    def test_continue_upgrade_multiple_upgrades(self, mock_orchestrator_class):
        """Test that workflow continues once after first successful upgrade (lvl 10->11->12)."""
        # Arrange: Mock orchestrator to return multiple UPGRADED results
        mock_orchestrator = Mock()

        # First upgrade: 3 attempts
        mock_result_1 = UpgradeResult(
            fail_count=3,
            frames_processed=12,
            stop_reason=StopReason.UPGRADED,
            debug_session_dir=None,
        )

        # Second upgrade: 4 attempts (then stops - only continue once)
        mock_result_2 = UpgradeResult(
            fail_count=4,
            frames_processed=16,
            stop_reason=StopReason.UPGRADED,
            debug_session_dir=None,
        )

        mock_orchestrator.run_monitor.side_effect = [
            mock_result_1,
            mock_result_2,
        ]
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_cache_service = Mock()
        mock_cache_service.get_regions.return_value = {
            "upgrade_button": (100, 200, 50, 30),
            "upgrade_bar": (100, 250, 200, 10),
        }

        mock_window_service = Mock()
        mock_window_service.get_window_size.return_value = (1920, 1080)

        workflow = SpendWorkflow(
            screenshot_service=Mock(),
            detector=Mock(spec=ProgressBarStateDetector),
            cache_service=mock_cache_service,
            window_interaction_service=mock_window_service,
            network_manager=_online_network_manager(),
            max_upgrade_attempts=10,
            continue_upgrade=True,  # Enable continue mode (only continues once)
            debug_dir=None,
        )

        # Act: Run workflow
        result = workflow.run()

        # Assert: Verify workflow continued only once (2 upgrades total)
        assert result.upgrade_count == 2  # Two successful upgrades
        assert result.attempt_count == 7  # 3 + 4
        assert (
            result.remaining_attempts == 1
        )  # 10 - 3 fails - 1 success - 4 fails - 1 success
        assert result.stop_reason == StopReason.UPGRADED

        # Verify orchestrator was called 2 times (not 3)
        assert mock_orchestrator.run_monitor.call_count == 2

    @patch("raid_autoupgrade.workflows.spend_workflow.UpgradeOrchestrator")
    def test_continue_upgrade_disabled_stops_after_first_upgrade(
        self, mock_orchestrator_class
    ):
        """Test that workflow stops after first upgrade when continue_upgrade=False."""
        # Arrange: Mock orchestrator to return UPGRADED
        mock_orchestrator = Mock()
        mock_result = UpgradeResult(
            fail_count=5,
            frames_processed=20,
            stop_reason=StopReason.UPGRADED,
            debug_session_dir=None,
        )
        mock_orchestrator.run_monitor.return_value = mock_result
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_cache_service = Mock()
        mock_cache_service.get_regions.return_value = {
            "upgrade_button": (100, 200, 50, 30),
            "upgrade_bar": (100, 250, 200, 10),
        }

        mock_window_service = Mock()
        mock_window_service.get_window_size.return_value = (1920, 1080)

        workflow = SpendWorkflow(
            screenshot_service=Mock(),
            detector=Mock(spec=ProgressBarStateDetector),
            cache_service=mock_cache_service,
            window_interaction_service=mock_window_service,
            network_manager=_online_network_manager(),
            max_upgrade_attempts=20,
            continue_upgrade=False,  # Disable continue mode
            debug_dir=None,
        )

        # Act: Run workflow
        result = workflow.run()

        # Assert: Verify workflow stopped after first upgrade
        assert result.upgrade_count == 1
        assert result.attempt_count == 5
        assert result.remaining_attempts == 14  # 20 - 5 fails - 1 success
        assert result.stop_reason == StopReason.UPGRADED

        # Verify orchestrator was called only once
        assert mock_orchestrator.run_monitor.call_count == 1

    @patch("raid_autoupgrade.workflows.spend_workflow.UpgradeOrchestrator")
    def test_continue_upgrade_stops_when_no_remaining_attempts(
        self, mock_orchestrator_class
    ):
        """Test that workflow stops if successful upgrade leaves 0 remaining attempts."""
        # Arrange: Mock orchestrator to return UPGRADED that uses all attempts
        mock_orchestrator = Mock()
        mock_result = UpgradeResult(
            fail_count=10,
            frames_processed=40,
            stop_reason=StopReason.UPGRADED,
            debug_session_dir=None,
        )
        mock_orchestrator.run_monitor.return_value = mock_result
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_cache_service = Mock()
        mock_cache_service.get_regions.return_value = {
            "upgrade_button": (100, 200, 50, 30),
            "upgrade_bar": (100, 250, 200, 10),
        }

        mock_window_service = Mock()
        mock_window_service.get_window_size.return_value = (1920, 1080)

        workflow = SpendWorkflow(
            screenshot_service=Mock(),
            detector=Mock(spec=ProgressBarStateDetector),
            cache_service=mock_cache_service,
            window_interaction_service=mock_window_service,
            network_manager=_online_network_manager(),
            max_upgrade_attempts=10,
            continue_upgrade=True,  # Enable continue mode
            debug_dir=None,
        )

        # Act: Run workflow
        result = workflow.run()

        # Assert: Verify workflow stopped after first upgrade (no remaining attempts)
        # Note: 10 fails + 1 success = 11 total, but max is 10, so remaining is -1
        assert result.upgrade_count == 1
        assert result.attempt_count == 10
        assert (
            result.remaining_attempts == -1
        )  # All attempts used (10 max - 10 fails - 1 success)
        assert result.stop_reason == StopReason.UPGRADED

        # Verify orchestrator was called only once (no attempts left to continue)
        assert mock_orchestrator.run_monitor.call_count == 1


class TestSpendWorkflowProgressAndCancel:
    """Test cancel_event and on_progress threading in SpendWorkflow."""

    @patch("raid_autoupgrade.workflows.spend_workflow.UpgradeOrchestrator")
    def test_run_passes_cancel_event_to_orchestrator(self, mock_orchestrator_class):
        mock_orchestrator = Mock()
        mock_orchestrator.run_monitor.return_value = UpgradeResult(
            fail_count=5, frames_processed=20, stop_reason=StopReason.UPGRADED
        )
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_cache_service = Mock()
        mock_cache_service.get_regions.return_value = {
            "upgrade_button": (100, 200, 50, 30),
            "upgrade_bar": (100, 250, 200, 10),
        }
        mock_window_service = Mock()
        mock_window_service.get_window_size.return_value = (1920, 1080)

        import threading

        cancel_event = threading.Event()

        workflow = SpendWorkflow(
            cache_service=mock_cache_service,
            window_interaction_service=mock_window_service,
            network_manager=_online_network_manager(),
            screenshot_service=Mock(),
            detector=Mock(spec=ProgressBarStateDetector),
            max_upgrade_attempts=10,
        )

        workflow.run(cancel_event=cancel_event)

        _, kwargs = mock_orchestrator.run_monitor.call_args
        assert kwargs.get("cancel_event") is cancel_event

    @patch("raid_autoupgrade.workflows.spend_workflow.UpgradeOrchestrator")
    def test_run_forwards_enriched_progress_reflecting_running_totals(
        self, mock_orchestrator_class
    ):
        """As the orchestrator streams per-session ProgressEvents, the workflow
        forwards cumulative SpendProgress snapshots whose attempts_used /
        remaining / upgrades reflect the running loop totals — advancing across
        a session boundary, not resetting each session."""
        mock_orchestrator = Mock()

        def fake_monitor_run(run, cancel_event=None, on_progress=None):
            # The session number is implied by how many times we've been called.
            call = mock_orchestrator.run_monitor.call_count
            if call == 1:
                on_progress(
                    ProgressEvent(fail_count=1, frames=10, state=ProgressBarState.FAIL)
                )
                return UpgradeResult(
                    fail_count=1, frames_processed=10, stop_reason=StopReason.UPGRADED
                )
            on_progress(
                ProgressEvent(fail_count=2, frames=20, state=ProgressBarState.FAIL)
            )
            return UpgradeResult(
                fail_count=2, frames_processed=20, stop_reason=StopReason.UPGRADED
            )

        mock_orchestrator.run_monitor.side_effect = fake_monitor_run
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_cache_service = Mock()
        mock_cache_service.get_regions.return_value = {
            "upgrade_button": (100, 200, 50, 30),
            "upgrade_bar": (100, 250, 200, 10),
        }
        mock_window_service = Mock()
        mock_window_service.get_window_size.return_value = (1920, 1080)

        received: list[SpendProgress] = []

        workflow = SpendWorkflow(
            cache_service=mock_cache_service,
            window_interaction_service=mock_window_service,
            network_manager=_online_network_manager(),
            screenshot_service=Mock(),
            detector=Mock(spec=ProgressBarStateDetector),
            max_upgrade_attempts=10,
            continue_upgrade=True,  # run a second session so totals advance
        )

        workflow.run(on_progress=received.append)

        assert all(isinstance(s, SpendProgress) for s in received)
        # Session 1 base 0/10/0, 1 fail → (1, 9, 0).
        # Boundary: +1 fail, +1 success, +1 upgrade → base 1/8/1.
        # Session 2 base 1/8/1, 2 fails → (3, 6, 1).
        assert [(s.attempts_used, s.remaining, s.upgrades) for s in received] == [
            (1, 9, 0),
            (3, 6, 1),
        ]
        assert [s.state for s in received] == [
            ProgressBarState.FAIL,
            ProgressBarState.FAIL,
        ]
