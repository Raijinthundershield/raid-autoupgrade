"""Smoke tests for UpgradeOrchestrator.

These tests verify basic functionality with mocked service dependencies.
"""

import pytest
from unittest.mock import Mock, patch
import numpy as np

from autoraid.services.upgrade_orchestrator import UpgradeOrchestrator
from autoraid.core.state_machine import StopReason
from autoraid.services.network import NetworkState


class TestUpgradeOrchestrator:
    """Test suite for UpgradeOrchestrator."""

    @pytest.fixture
    def mock_services(self):
        """Create mocked service dependencies."""
        return {
            "cache_service": Mock(),
            "screenshot_service": Mock(),
            "locate_region_service": Mock(),
            "window_interaction_service": Mock(),
            "network_manager": Mock(),
            "upgrade_attempt_monitor": Mock(),
        }

    @pytest.fixture
    def orchestrator(self, mock_services):
        """Create UpgradeOrchestrator instance with mocked dependencies."""
        return UpgradeOrchestrator(
            cache_service=mock_services["cache_service"],
            screenshot_service=mock_services["screenshot_service"],
            locate_region_service=mock_services["locate_region_service"],
            window_interaction_service=mock_services["window_interaction_service"],
            network_manager=mock_services["network_manager"],
            upgrade_attempt_monitor=mock_services["upgrade_attempt_monitor"],
        )

    def test_orchestrator_instantiates(self, orchestrator):
        """Test that UpgradeOrchestrator creates with mocked dependencies."""
        assert orchestrator is not None
        assert isinstance(orchestrator, UpgradeOrchestrator)

    @patch("autoraid.services.upgrade_orchestrator.time.sleep")
    def test_orchestrator_count_workflow_calls_services(
        self,
        mock_sleep,
        orchestrator,
        mock_services,
    ):
        """Test that count workflow calls screenshot_service.take_screenshot."""
        # Setup mocks
        mock_services["window_interaction_service"].window_exists.return_value = True
        mock_services["screenshot_service"].take_screenshot.return_value = np.zeros(
            (100, 100, 3), dtype=np.uint8
        )
        mock_services["locate_region_service"].get_regions.return_value = {
            "upgrade_bar": (10, 10, 50, 5),
            "upgrade_button": (10, 20, 50, 10),
        }
        mock_services["screenshot_service"].extract_roi.return_value = np.zeros(
            (5, 50, 3), dtype=np.uint8
        )

        # Setup monitor mock
        mock_monitor = Mock()
        mock_monitor.process_frame.return_value = Mock()  # Returns ProgressBarState
        mock_monitor.stop_reason = None
        mock_monitor.fail_count = 0

        # Create a side effect function to simulate the monitor behavior
        call_count = [0]

        def monitor_side_effect():
            call_count[0] += 1
            if call_count[0] < 5:
                return None
            return StopReason.MAX_ATTEMPTS_REACHED

        # Use property to control stop_reason
        type(mock_monitor).stop_reason = property(lambda self: monitor_side_effect())
        type(mock_monitor).fail_count = property(lambda self: call_count[0])

        mock_services["upgrade_attempt_monitor"].return_value = mock_monitor

        # Setup network manager mock
        mock_services[
            "network_manager"
        ].check_network_access.return_value = NetworkState.OFFLINE

        # Execute workflow (no network adapters to avoid network toggle logic)
        n_fails, reason = orchestrator.count_workflow(
            network_adapter_id=None, max_attempts=10
        )

        # Verify screenshot_service.take_screenshot was called
        assert mock_services["screenshot_service"].take_screenshot.called
        assert mock_services["screenshot_service"].take_screenshot.call_count >= 1

        # Verify locate_region_service.get_regions was called
        assert mock_services["locate_region_service"].get_regions.called

        # Verify window_interaction_service.click_region was called
        assert mock_services["window_interaction_service"].click_region.called

        # Verify monitor was used
        assert mock_monitor.process_frame.called

        # Verify result
        assert n_fails == 5
        assert reason == StopReason.MAX_ATTEMPTS_REACHED

    @patch("autoraid.services.upgrade_orchestrator.time.sleep")
    def test_orchestrator_count_workflow_re_enables_network(
        self,
        mock_sleep,
        orchestrator,
        mock_services,
    ):
        """Test that finally block re-enables network adapters even on exception."""
        # Setup mocks
        mock_services["window_interaction_service"].window_exists.return_value = True
        mock_services["screenshot_service"].take_screenshot.side_effect = RuntimeError(
            "Test exception"
        )
        mock_services["locate_region_service"].get_regions.return_value = {
            "upgrade_bar": (10, 10, 50, 5),
            "upgrade_button": (10, 20, 50, 10),
        }

        # Setup network manager mock
        mock_services[
            "network_manager"
        ].check_network_access.return_value = NetworkState.OFFLINE

        # Execute workflow with network adapter ID
        network_adapter_id = [1, 2]
        with pytest.raises(RuntimeError, match="Test exception"):
            orchestrator.count_workflow(
                network_adapter_id=network_adapter_id, max_attempts=10
            )

        # Verify network was disabled
        assert mock_services["network_manager"].toggle_adapters.call_count >= 1
        first_call = mock_services["network_manager"].toggle_adapters.call_args_list[0]
        assert first_call[0][0] == network_adapter_id
        assert first_call[0][1] == NetworkState.OFFLINE

        # Verify network was re-enabled in finally block (last call)
        last_call = mock_services["network_manager"].toggle_adapters.call_args_list[-1]
        assert last_call[0][0] == network_adapter_id
        assert last_call[0][1] == NetworkState.ONLINE

    @patch("autoraid.services.upgrade_orchestrator.time.sleep")
    def test_orchestrator_spend_workflow_calls_services(
        self,
        mock_sleep,
        orchestrator,
        mock_services,
    ):
        """Test that spend workflow executes successfully with mocked services."""
        # Setup mocks
        mock_services["window_interaction_service"].window_exists.return_value = True
        mock_services["screenshot_service"].take_screenshot.return_value = np.zeros(
            (100, 100, 3), dtype=np.uint8
        )
        mock_services["locate_region_service"].get_regions.return_value = {
            "upgrade_bar": (10, 10, 50, 5),
            "upgrade_button": (10, 20, 50, 10),
        }
        mock_services["screenshot_service"].extract_roi.return_value = np.zeros(
            (5, 50, 3), dtype=np.uint8
        )

        # Setup monitor mock (simulate upgrade after 3 fails)
        mock_monitor = Mock()
        mock_monitor.process_frame.return_value = Mock()  # Returns ProgressBarState

        # Simulate monitoring behavior
        call_count = [0]

        def monitor_side_effect():
            call_count[0] += 1
            if call_count[0] < 3:
                return None
            return StopReason.SUCCESS

        type(mock_monitor).stop_reason = property(lambda self: monitor_side_effect())
        type(mock_monitor).fail_count = property(lambda self: min(call_count[0], 3))

        mock_services["upgrade_attempt_monitor"].return_value = mock_monitor

        # Setup network manager mock
        mock_services[
            "network_manager"
        ].check_network_access.return_value = NetworkState.ONLINE

        # Execute workflow
        result = orchestrator.spend_workflow(max_attempts=10, continue_upgrade=False)

        # Verify services were called
        assert mock_services["screenshot_service"].take_screenshot.called
        assert mock_services["locate_region_service"].get_regions.called
        assert mock_services["window_interaction_service"].click_region.called
        assert mock_monitor.process_frame.called

        # Verify result structure (SpendResult dataclass)
        assert hasattr(result, "upgrade_count")
        assert hasattr(result, "attempt_count")
        assert hasattr(result, "remaining_attempts")
        assert hasattr(result, "last_reason")

        # Verify result values
        assert result.upgrade_count == 1
        assert result.attempt_count == 4  # 3 fails + 1 success
        assert result.remaining_attempts == 6  # 10 - 4
        assert result.last_reason == StopReason.SUCCESS
