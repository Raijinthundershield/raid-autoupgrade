"""Unit tests for SpendWorkflow with mocked dependencies.

Tests the validation and execution logic with mocked services.
Following smoke test philosophy - verify basic functionality and regressions.
"""

from unittest.mock import Mock
from pathlib import Path

import pytest

from autoraid.core.stop_conditions import StopReason
from autoraid.exceptions import WorkflowValidationError
from autoraid.services.network import NetworkState
from autoraid.services.upgrade_orchestrator import UpgradeResult
from autoraid.workflows.spend_workflow import SpendResult, SpendWorkflow


class TestSpendWorkflowValidation:
    """Test validation phase of SpendWorkflow."""

    def test_validate_internet_unavailable(self):
        """Test validation fails when internet is not available (T050)."""
        # Arrange: Mock services
        mock_network_manager = Mock()
        mock_network_manager.check_network_access.return_value = NetworkState.OFFLINE

        workflow = SpendWorkflow(
            orchestrator=Mock(),
            cache_service=Mock(),
            window_interaction_service=Mock(),
            network_manager=mock_network_manager,
            max_upgrade_attempts=10,
            continue_upgrade=False,
            debug_dir=None,
        )

        # Act & Assert: Validation should raise WorkflowValidationError
        with pytest.raises(
            WorkflowValidationError,
            match="No internet access detected",
        ):
            workflow.validate()

    def test_validate_internet_available_passes(self):
        """Test validation passes when internet is available."""
        # Arrange: Mock services
        mock_network_manager = Mock()
        mock_network_manager.check_network_access.return_value = NetworkState.ONLINE

        workflow = SpendWorkflow(
            orchestrator=Mock(),
            cache_service=Mock(),
            window_interaction_service=Mock(),
            network_manager=mock_network_manager,
            max_upgrade_attempts=10,
            continue_upgrade=False,
            debug_dir=None,
        )

        # Act & Assert: Validation should pass without raising
        workflow.validate()  # Should not raise


class TestSpendWorkflowExecution:
    """Test execution phase of SpendWorkflow (T051)."""

    def test_run_single_upgrade_success(self):
        """Test workflow execution with single upgrade success."""
        # Arrange: Mock orchestrator to return UPGRADED result
        mock_orchestrator = Mock()
        mock_result = UpgradeResult(
            fail_count=5,
            frames_processed=20,
            stop_reason=StopReason.UPGRADED,
            debug_session_dir=None,
        )
        mock_orchestrator.run_upgrade_session.return_value = mock_result

        mock_cache_service = Mock()
        mock_cache_service.get_regions.return_value = {
            "upgrade_button": (100, 200, 50, 30),
            "upgrade_bar": (100, 250, 200, 10),
        }

        mock_window_service = Mock()
        mock_window_service.get_window_size.return_value = (1920, 1080)

        workflow = SpendWorkflow(
            orchestrator=mock_orchestrator,
            cache_service=mock_cache_service,
            window_interaction_service=mock_window_service,
            network_manager=Mock(),
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
        assert result.remaining_attempts == 5
        assert result.stop_reason == StopReason.UPGRADED

        # Verify orchestrator was called once
        mock_orchestrator.run_upgrade_session.assert_called_once()

    def test_run_max_attempts_exhausted(self):
        """Test workflow stops when max_attempts is exhausted."""
        # Arrange: Mock orchestrator to return MAX_ATTEMPTS_REACHED
        mock_orchestrator = Mock()
        mock_result = UpgradeResult(
            fail_count=10,
            frames_processed=40,
            stop_reason=StopReason.MAX_ATTEMPTS_REACHED,
            debug_session_dir=None,
        )
        mock_orchestrator.run_upgrade_session.return_value = mock_result

        mock_cache_service = Mock()
        mock_cache_service.get_regions.return_value = {
            "upgrade_button": (100, 200, 50, 30),
            "upgrade_bar": (100, 250, 200, 10),
        }

        mock_window_service = Mock()
        mock_window_service.get_window_size.return_value = (1920, 1080)

        workflow = SpendWorkflow(
            orchestrator=mock_orchestrator,
            cache_service=mock_cache_service,
            window_interaction_service=mock_window_service,
            network_manager=Mock(),
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

        # Verify cancel click was called
        mock_window_service.click_region.assert_called_once()

    def test_run_connection_error(self):
        """Test workflow stops on connection error."""
        # Arrange: Mock orchestrator to return CONNECTION_ERROR
        mock_orchestrator = Mock()
        mock_result = UpgradeResult(
            fail_count=3,
            frames_processed=15,
            stop_reason=StopReason.CONNECTION_ERROR,
            debug_session_dir=None,
        )
        mock_orchestrator.run_upgrade_session.return_value = mock_result

        mock_cache_service = Mock()
        mock_cache_service.get_regions.return_value = {
            "upgrade_button": (100, 200, 50, 30),
            "upgrade_bar": (100, 250, 200, 10),
        }

        mock_window_service = Mock()
        mock_window_service.get_window_size.return_value = (1920, 1080)

        workflow = SpendWorkflow(
            orchestrator=mock_orchestrator,
            cache_service=mock_cache_service,
            window_interaction_service=mock_window_service,
            network_manager=Mock(),
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

    def test_continue_upgrade_multiple_upgrades(self):
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

        mock_orchestrator.run_upgrade_session.side_effect = [
            mock_result_1,
            mock_result_2,
        ]

        mock_cache_service = Mock()
        mock_cache_service.get_regions.return_value = {
            "upgrade_button": (100, 200, 50, 30),
            "upgrade_bar": (100, 250, 200, 10),
        }

        mock_window_service = Mock()
        mock_window_service.get_window_size.return_value = (1920, 1080)

        workflow = SpendWorkflow(
            orchestrator=mock_orchestrator,
            cache_service=mock_cache_service,
            window_interaction_service=mock_window_service,
            network_manager=Mock(),
            max_upgrade_attempts=10,
            continue_upgrade=True,  # Enable continue mode (only continues once)
            debug_dir=None,
        )

        # Act: Run workflow
        result = workflow.run()

        # Assert: Verify workflow continued only once (2 upgrades total)
        assert result.upgrade_count == 2  # Two successful upgrades
        assert result.attempt_count == 7  # 3 + 4
        assert result.remaining_attempts == 3  # 10 - 7
        assert result.stop_reason == StopReason.UPGRADED

        # Verify orchestrator was called 2 times (not 3)
        assert mock_orchestrator.run_upgrade_session.call_count == 2

    def test_continue_upgrade_disabled_stops_after_first_upgrade(self):
        """Test that workflow stops after first upgrade when continue_upgrade=False."""
        # Arrange: Mock orchestrator to return UPGRADED
        mock_orchestrator = Mock()
        mock_result = UpgradeResult(
            fail_count=5,
            frames_processed=20,
            stop_reason=StopReason.UPGRADED,
            debug_session_dir=None,
        )
        mock_orchestrator.run_upgrade_session.return_value = mock_result

        mock_cache_service = Mock()
        mock_cache_service.get_regions.return_value = {
            "upgrade_button": (100, 200, 50, 30),
            "upgrade_bar": (100, 250, 200, 10),
        }

        mock_window_service = Mock()
        mock_window_service.get_window_size.return_value = (1920, 1080)

        workflow = SpendWorkflow(
            orchestrator=mock_orchestrator,
            cache_service=mock_cache_service,
            window_interaction_service=mock_window_service,
            network_manager=Mock(),
            max_upgrade_attempts=20,
            continue_upgrade=False,  # Disable continue mode
            debug_dir=None,
        )

        # Act: Run workflow
        result = workflow.run()

        # Assert: Verify workflow stopped after first upgrade
        assert result.upgrade_count == 1
        assert result.attempt_count == 5
        assert result.remaining_attempts == 15
        assert result.stop_reason == StopReason.UPGRADED

        # Verify orchestrator was called only once
        assert mock_orchestrator.run_upgrade_session.call_count == 1

    def test_continue_upgrade_stops_when_no_remaining_attempts(self):
        """Test that workflow stops if successful upgrade leaves 0 remaining attempts."""
        # Arrange: Mock orchestrator to return UPGRADED that uses all attempts
        mock_orchestrator = Mock()
        mock_result = UpgradeResult(
            fail_count=10,
            frames_processed=40,
            stop_reason=StopReason.UPGRADED,
            debug_session_dir=None,
        )
        mock_orchestrator.run_upgrade_session.return_value = mock_result

        mock_cache_service = Mock()
        mock_cache_service.get_regions.return_value = {
            "upgrade_button": (100, 200, 50, 30),
            "upgrade_bar": (100, 250, 200, 10),
        }

        mock_window_service = Mock()
        mock_window_service.get_window_size.return_value = (1920, 1080)

        workflow = SpendWorkflow(
            orchestrator=mock_orchestrator,
            cache_service=mock_cache_service,
            window_interaction_service=mock_window_service,
            network_manager=Mock(),
            max_upgrade_attempts=10,
            continue_upgrade=True,  # Enable continue mode
            debug_dir=None,
        )

        # Act: Run workflow
        result = workflow.run()

        # Assert: Verify workflow stopped after first upgrade (no remaining attempts)
        assert result.upgrade_count == 1
        assert result.attempt_count == 10
        assert result.remaining_attempts == 0
        assert result.stop_reason == StopReason.UPGRADED

        # Verify orchestrator was called only once (no attempts left to continue)
        assert mock_orchestrator.run_upgrade_session.call_count == 1

    def test_debug_logger_created_when_debug_dir_provided(self):
        """Test that debug logger is created for each upgrade when debug_dir provided."""
        # Arrange: Mock orchestrator
        mock_orchestrator = Mock()
        mock_result = UpgradeResult(
            fail_count=5,
            frames_processed=20,
            stop_reason=StopReason.UPGRADED,
            debug_session_dir=Path("/tmp/debug/session1"),
        )
        mock_orchestrator.run_upgrade_session.return_value = mock_result

        mock_cache_service = Mock()
        mock_cache_service.get_regions.return_value = {
            "upgrade_button": (100, 200, 50, 30),
            "upgrade_bar": (100, 250, 200, 10),
        }

        mock_window_service = Mock()
        mock_window_service.get_window_size.return_value = (1920, 1080)

        debug_dir = Path("/tmp/debug")
        workflow = SpendWorkflow(
            orchestrator=mock_orchestrator,
            cache_service=mock_cache_service,
            window_interaction_service=mock_window_service,
            network_manager=Mock(),
            max_upgrade_attempts=10,
            continue_upgrade=False,
            debug_dir=debug_dir,
        )

        # Act: Run workflow
        workflow.run()

        # Assert: Verify orchestrator was called with session containing debug_logger
        call_args = mock_orchestrator.run_upgrade_session.call_args
        session = call_args[0][0]
        assert session.debug_logger is not None
