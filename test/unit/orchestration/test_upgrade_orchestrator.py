"""Unit tests for UpgradeOrchestrator.

The orchestrator drives the run through a fake ``UpgradeScreen`` — it never
touches the window, screenshot, or cache services directly. Tests inject a fake
screen that records ``start_attempt``/``cancel_attempt`` and hands back a
``BarCapture`` from ``capture_progress_bar``, plus a mock detector and network
manager. Assertions are on side effects (which screen action fired, what the
detector received) rather than message wording.
"""

import threading
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest

from raid_autoupgrade.detection.progress_bar_detector import (
    ProgressBarState,
    ProgressBarStateDetector,
)
from raid_autoupgrade.exceptions import WorkflowValidationError
from raid_autoupgrade.orchestration.stop_conditions import (
    MaxAttemptsCondition,
    StopConditionChain,
    StopReason,
)
from raid_autoupgrade.orchestration.upgrade_orchestrator import (
    MonitorRun,
    ProgressEvent,
    UpgradeOrchestrator,
)
from raid_autoupgrade.orchestration.upgrade_screen import BarCapture
from raid_autoupgrade.services.network import NetworkManager, NetworkState


class FakeUpgradeScreen:
    """Records screen actions; hands back a sentinel frame/ROI per capture.

    The ROI is a distinct array so it can be told apart from the frame when the
    orchestrator routes one to the detector and both to the debug logger.
    """

    def __init__(self):
        self.frame = np.zeros((100, 200, 3), dtype=np.uint8)
        self.roi = np.ones((50, 200, 3), dtype=np.uint8)
        self.start_calls = 0
        self.cancel_calls = 0
        self.captures = 0

    def start_attempt(self) -> None:
        self.start_calls += 1

    def cancel_attempt(self) -> None:
        self.cancel_calls += 1

    def capture_progress_bar(self) -> BarCapture:
        self.captures += 1
        return BarCapture(frame=self.frame, roi=self.roi)


def _offline_network() -> Mock:
    network = Mock(spec=NetworkManager)
    network.check_network_access.return_value = NetworkState.OFFLINE
    return network


class TestUpgradeOrchestrator:
    """Tests for UpgradeOrchestrator class."""

    @patch("raid_autoupgrade.orchestration.upgrade_orchestrator.time.sleep")
    def test_run_monitor_begins_attempt_and_drives_loop_to_stop(self, mock_sleep):
        """run_monitor begins the Attempt via start_attempt() and drives the
        monitor loop until a stop condition fires, returning the fail count and
        stop reason."""
        screen = FakeUpgradeScreen()
        detector = Mock(spec=ProgressBarStateDetector)
        detector.detect_state.side_effect = [
            ProgressBarState.PROGRESS,
            ProgressBarState.FAIL,
        ]

        orchestrator = UpgradeOrchestrator(
            upgrade_screen=screen,
            network_manager=_offline_network(),
            detector=detector,
        )
        run = MonitorRun(
            stop_conditions=StopConditionChain([MaxAttemptsCondition(max_attempts=1)]),
        )

        result = orchestrator.run_monitor(run)

        assert screen.start_calls == 1
        assert screen.captures >= 2
        assert result.fail_count == 1
        assert result.stop_reason == StopReason.MAX_ATTEMPTS_REACHED

    @patch("raid_autoupgrade.orchestration.upgrade_orchestrator.time.sleep")
    def test_detector_gets_roi_and_debug_logger_gets_frame_and_roi(self, mock_sleep):
        """Each frame routes the ROI to the detector and both the full frame and
        the ROI to the debug logger — served from one capture, no re-derivation."""
        screen = FakeUpgradeScreen()
        detector = Mock(spec=ProgressBarStateDetector)
        detector.detect_state.side_effect = [
            ProgressBarState.PROGRESS,
            ProgressBarState.FAIL,
        ]
        debug_logger = Mock()

        orchestrator = UpgradeOrchestrator(
            upgrade_screen=screen,
            network_manager=_offline_network(),
            detector=detector,
        )
        run = MonitorRun(
            stop_conditions=StopConditionChain([MaxAttemptsCondition(max_attempts=1)]),
        )

        with patch(
            "raid_autoupgrade.orchestration.upgrade_orchestrator.DebugFrameLogger",
            return_value=debug_logger,
        ):
            run = MonitorRun(
                stop_conditions=StopConditionChain(
                    [MaxAttemptsCondition(max_attempts=1)]
                ),
                debug_dir=Path("ignored"),
            )
            orchestrator.run_monitor(run)

        # The detector saw the ROI sentinel, never the full frame.
        for call in detector.detect_state.call_args_list:
            assert call.args[0] is screen.roi

        # The debug logger saw both the full frame and the ROI from the capture.
        assert debug_logger.log_frame.call_count >= 1
        first = debug_logger.log_frame.call_args_list[0]
        assert first.kwargs["screenshot"] is screen.frame
        assert first.kwargs["roi"] is screen.roi

    @patch("raid_autoupgrade.orchestration.upgrade_orchestrator.NetworkContext")
    @patch("raid_autoupgrade.orchestration.upgrade_orchestrator.time.sleep")
    def test_run_monitor_uses_network_context(self, mock_sleep, mock_network_context):
        """run_monitor wraps the run in NetworkContext with the configured
        adapters and disable flag."""
        screen = FakeUpgradeScreen()
        detector = Mock(spec=ProgressBarStateDetector)
        detector.detect_state.side_effect = [
            ProgressBarState.PROGRESS,
            ProgressBarState.FAIL,
        ]
        network = _offline_network()

        orchestrator = UpgradeOrchestrator(
            upgrade_screen=screen,
            network_manager=network,
            detector=detector,
        )
        run = MonitorRun(
            stop_conditions=StopConditionChain([MaxAttemptsCondition(max_attempts=1)]),
            network_adapter_ids=[1, 2],
            disable_network=True,
        )

        orchestrator.run_monitor(run)

        mock_network_context.assert_called_once_with(
            network_manager=network,
            adapter_ids=[1, 2],
            disable_network=True,
        )

    @patch("raid_autoupgrade.orchestration.upgrade_orchestrator.NetworkContext")
    @patch("raid_autoupgrade.orchestration.upgrade_orchestrator.time.sleep")
    def test_require_offline_aborts_when_network_still_reachable(
        self, mock_sleep, mock_network_context
    ):
        """A require_offline run must not begin the Attempt while the network is
        still reachable — that would spend a real attempt. It raises and never
        begins the Attempt or invokes the detector."""
        screen = FakeUpgradeScreen()
        detector = Mock(spec=ProgressBarStateDetector)
        network = Mock(spec=NetworkManager)
        # Network still up after adapter setup (e.g. wrong adapter selected).
        network.check_network_access.return_value = NetworkState.ONLINE

        orchestrator = UpgradeOrchestrator(
            upgrade_screen=screen,
            network_manager=network,
            detector=detector,
        )
        run = MonitorRun(
            stop_conditions=StopConditionChain([]),
            require_offline=True,
        )

        with pytest.raises(WorkflowValidationError):
            orchestrator.run_monitor(run)

        assert screen.start_calls == 0
        detector.detect_state.assert_not_called()

    @patch("raid_autoupgrade.orchestration.upgrade_orchestrator.time.sleep")
    def test_require_offline_proceeds_when_offline(self, mock_sleep):
        """A require_offline run proceeds normally once the network is confirmed
        offline."""
        screen = FakeUpgradeScreen()
        detector = Mock(spec=ProgressBarStateDetector)
        detector.detect_state.side_effect = [
            ProgressBarState.PROGRESS,
            ProgressBarState.FAIL,
        ]

        orchestrator = UpgradeOrchestrator(
            upgrade_screen=screen,
            network_manager=_offline_network(),
            detector=detector,
        )
        run = MonitorRun(
            stop_conditions=StopConditionChain([MaxAttemptsCondition(max_attempts=1)]),
            require_offline=True,
        )

        result = orchestrator.run_monitor(run)

        assert screen.start_calls == 1
        assert result.fail_count == 1

    @patch("raid_autoupgrade.orchestration.upgrade_orchestrator.time.sleep")
    def test_cancel_event_stops_monitor_loop_with_manual_stop(self, mock_sleep):
        """A pre-set cancel event stops the loop immediately with MANUAL_STOP,
        without ever capturing a frame or invoking the detector."""
        screen = FakeUpgradeScreen()
        detector = Mock(spec=ProgressBarStateDetector)
        detector.detect_state.return_value = ProgressBarState.PROGRESS

        cancel_event = threading.Event()
        cancel_event.set()

        orchestrator = UpgradeOrchestrator(
            upgrade_screen=screen,
            network_manager=_offline_network(),
            detector=detector,
        )
        run = MonitorRun(stop_conditions=StopConditionChain([]))

        result = orchestrator.run_monitor(run, cancel_event=cancel_event)

        assert result.stop_reason == StopReason.MANUAL_STOP
        detector.detect_state.assert_not_called()
        assert screen.captures == 0

    @patch("raid_autoupgrade.orchestration.upgrade_orchestrator.time.sleep")
    def test_pre_set_cancel_performs_zero_start_clicks(self, mock_sleep):
        """A cancel present at the start of a run produces zero start_attempt()
        clicks — the cancel is honoured before any click — and returns
        MANUAL_STOP."""
        screen = FakeUpgradeScreen()
        detector = Mock(spec=ProgressBarStateDetector)
        detector.detect_state.return_value = ProgressBarState.PROGRESS

        cancel_event = threading.Event()
        cancel_event.set()

        orchestrator = UpgradeOrchestrator(
            upgrade_screen=screen,
            network_manager=_offline_network(),
            detector=detector,
        )
        run = MonitorRun(stop_conditions=StopConditionChain([]))

        result = orchestrator.run_monitor(run, cancel_event=cancel_event)

        assert screen.start_calls == 0
        assert result.stop_reason == StopReason.MANUAL_STOP

    @patch("raid_autoupgrade.orchestration.upgrade_orchestrator.time.sleep")
    def test_stall_guard_fires_even_when_workflow_chain_omits_it(self, mock_sleep):
        """The stall guard is a per-run safety invariant: a run whose
        workflow-supplied chain has no StallCondition still stalls once
        detection stops producing fails. The stalled run returns STALLED and
        performs no cancel_attempt() halt-click (relinquish-under-uncertainty)."""
        screen = FakeUpgradeScreen()
        detector = Mock(spec=ProgressBarStateDetector)
        # No fail ever lands — pure Unrecognized-style stream.
        detector.detect_state.return_value = ProgressBarState.PROGRESS

        orchestrator = UpgradeOrchestrator(
            upgrade_screen=screen,
            network_manager=_offline_network(),
            detector=detector,
        )
        # Workflow chain that can never stop this run on its own.
        run = MonitorRun(stop_conditions=StopConditionChain([]))

        result = orchestrator.run_monitor(run)

        assert result.stop_reason == StopReason.STALLED
        assert screen.cancel_calls == 0

    @patch("raid_autoupgrade.orchestration.upgrade_orchestrator.time.sleep")
    def test_on_progress_called_once_per_loop_iteration(self, mock_sleep):
        screen = FakeUpgradeScreen()
        detector = Mock(spec=ProgressBarStateDetector)
        detector.detect_state.side_effect = [
            ProgressBarState.PROGRESS,
            ProgressBarState.FAIL,
        ]

        orchestrator = UpgradeOrchestrator(
            upgrade_screen=screen,
            network_manager=_offline_network(),
            detector=detector,
        )
        run = MonitorRun(
            stop_conditions=StopConditionChain([MaxAttemptsCondition(max_attempts=1)]),
        )

        events: list[ProgressEvent] = []
        orchestrator.run_monitor(run, on_progress=events.append)

        assert len(events) == 2

    @patch("raid_autoupgrade.orchestration.upgrade_orchestrator.time.sleep")
    def test_on_progress_events_carry_correct_data(self, mock_sleep):
        screen = FakeUpgradeScreen()
        detector = Mock(spec=ProgressBarStateDetector)
        detector.detect_state.side_effect = [
            ProgressBarState.PROGRESS,
            ProgressBarState.FAIL,
        ]

        orchestrator = UpgradeOrchestrator(
            upgrade_screen=screen,
            network_manager=_offline_network(),
            detector=detector,
        )
        run = MonitorRun(
            stop_conditions=StopConditionChain([MaxAttemptsCondition(max_attempts=1)]),
        )

        events: list[ProgressEvent] = []
        orchestrator.run_monitor(run, on_progress=events.append)

        first, second = events
        assert isinstance(first, ProgressEvent)
        assert first.frames == 1
        assert first.fail_count == 0
        assert first.state == ProgressBarState.PROGRESS

        assert second.frames == 2
        assert second.fail_count == 1
        assert second.state == ProgressBarState.FAIL
