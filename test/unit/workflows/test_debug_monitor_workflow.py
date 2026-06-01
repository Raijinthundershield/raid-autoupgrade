"""Unit tests for DebugMonitorWorkflow with mocked dependencies.

Region resolution now goes through ``UpgradeScreen`` construction, so an
uncalibrated run surfaces the friendly "open Calibration first" error instead of
the opaque ``KeyError`` the old inline indexing produced.
"""

from unittest.mock import Mock, patch

import pytest

from raid_autoupgrade.detection.progress_bar_detector import ProgressBarStateDetector
from raid_autoupgrade.exceptions import WorkflowValidationError
from raid_autoupgrade.orchestration.stop_conditions import StopReason
from raid_autoupgrade.orchestration.upgrade_orchestrator import (
    MonitorRun,
    UpgradeResult,
)
from raid_autoupgrade.workflows.debug_monitor_workflow import (
    DebugMonitorResult,
    DebugMonitorWorkflow,
)


class TestDebugMonitorWorkflowRegionResolution:
    """Region resolution is delegated to UpgradeScreen construction."""

    def test_uncalibrated_run_raises_friendly_error_not_keyerror(self, tmp_path):
        """With no Regions saved for the current window size, the run must raise
        the friendly WorkflowValidationError (from UpgradeScreen construction),
        not the opaque KeyError the old inline region indexing produced.

        ``pytest.raises(WorkflowValidationError)`` would not swallow a KeyError —
        a KeyError would surface as a test error — so this also pins "not KeyError".
        """
        mock_window_service = Mock()
        mock_window_service.get_window_size.return_value = (1920, 1080)

        mock_cache_service = Mock()
        mock_cache_service.get_regions.return_value = None  # uncalibrated

        workflow = DebugMonitorWorkflow(
            cache_service=mock_cache_service,
            window_interaction_service=mock_window_service,
            network_manager=Mock(),
            screenshot_service=Mock(),
            detector=Mock(spec=ProgressBarStateDetector),
            disable_network=False,
            max_frames=10,
            debug_dir=tmp_path,
        )

        with pytest.raises(WorkflowValidationError):
            workflow.run()


class TestDebugMonitorWorkflowExecution:
    """Happy-path wiring through UpgradeScreen + the renamed MonitorRun."""

    @patch("raid_autoupgrade.workflows.debug_monitor_workflow.UpgradeScreen")
    @patch("raid_autoupgrade.workflows.debug_monitor_workflow.UpgradeOrchestrator")
    def test_run_drives_monitor_and_maps_result(
        self, mock_orchestrator_class, mock_screen_class, tmp_path
    ):
        """A calibrated run builds a MonitorRun, drives the orchestrator, and maps
        the UpgradeResult into a DebugMonitorResult."""
        session_dir = tmp_path / "session"
        mock_orchestrator = Mock()
        mock_orchestrator.run_monitor.return_value = UpgradeResult(
            fail_count=0,
            frames_processed=7,
            stop_reason=StopReason.MAX_FRAMES_CAPTURED,
            debug_session_dir=session_dir,
        )
        mock_orchestrator_class.return_value = mock_orchestrator

        workflow = DebugMonitorWorkflow(
            cache_service=Mock(),
            window_interaction_service=Mock(),
            network_manager=Mock(),
            screenshot_service=Mock(),
            detector=Mock(spec=ProgressBarStateDetector),
            disable_network=False,
            max_frames=7,
            check_interval=0.2,
            debug_dir=tmp_path,
        )

        result = workflow.run()

        # The orchestrator was driven with a coordinate-free MonitorRun.
        mock_orchestrator.run_monitor.assert_called_once()
        run = mock_orchestrator.run_monitor.call_args[0][0]
        assert isinstance(run, MonitorRun)
        assert run.check_interval == 0.2
        assert run.disable_network is False

        # Result mapping.
        assert isinstance(result, DebugMonitorResult)
        assert result.total_frames == 7
        assert result.output_dir == session_dir
        assert result.stop_reason == StopReason.MAX_FRAMES_CAPTURED
