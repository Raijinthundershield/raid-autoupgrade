"""Integration tests for SpendWorkflow with mocked orchestrator.

Tests workflow configuration and session setup with mocked orchestrator.
Verifies correct stop condition configuration and result mapping.
"""

from unittest.mock import Mock


from autoraid.core.stop_conditions import (
    StopReason,
)
from autoraid.services.upgrade_orchestrator import UpgradeResult
from autoraid.workflows.spend_workflow import SpendWorkflow


class TestSpendWorkflowIntegration:
    """Integration tests for SpendWorkflow with mocked orchestrator."""

    def test_workflow_creates_session_per_upgrade_iteration(self):
        """Test that workflow creates new session for each upgrade iteration in continue mode."""
        # Arrange: Mock orchestrator to return multiple results
        mock_orchestrator = Mock()

        # First upgrade: 3 attempts
        mock_result_1 = UpgradeResult(
            fail_count=3,
            frames_processed=12,
            stop_reason=StopReason.UPGRADED,
            debug_session_dir=None,
        )

        # Second upgrade: 7 attempts (exhausts remaining)
        mock_result_2 = UpgradeResult(
            fail_count=7,
            frames_processed=28,
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
            continue_upgrade=True,
            debug_dir=None,
        )

        # Act: Run workflow
        workflow.run()

        # Assert: Verify orchestrator was called twice with different max_attempts
        assert mock_orchestrator.run_upgrade_session.call_count == 2

        # First call: max_upgrade_attempts=10
        first_call = mock_orchestrator.run_upgrade_session.call_args_list[0]
        first_session = first_call[0][0]
        assert first_session.stop_conditions._conditions[0].max_attempts == 10

        # Second call: max_upgrade_attempts=6 (10 - 3 fails - 1 success)
        second_call = mock_orchestrator.run_upgrade_session.call_args_list[1]
        second_session = second_call[0][0]
        assert second_session.stop_conditions._conditions[0].max_attempts == 6

    def test_workflow_tracks_upgrade_count_across_iterations(self):
        """Test that workflow tracks upgrade_count correctly (continues once: lvl 10->11->12)."""
        # Arrange: Mock orchestrator to return multiple UPGRADED results
        mock_orchestrator = Mock()

        results = [
            UpgradeResult(3, 12, StopReason.UPGRADED, None),
            UpgradeResult(4, 16, StopReason.UPGRADED, None),
            # Workflow stops after 2 upgrades (only continues once)
        ]
        mock_orchestrator.run_upgrade_session.side_effect = results

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
            continue_upgrade=True,
            debug_dir=None,
        )

        # Act: Run workflow
        result = workflow.run()

        # Assert: Verify upgrade_count incremented for each UPGRADED result
        assert result.upgrade_count == 2  # Two successful upgrades (continues once)
        assert result.attempt_count == 7  # 3 + 4
        assert result.remaining_attempts == 1  # 10 - 3 - 1 - 4 - 1
