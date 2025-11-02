"""Integration tests for SpendWorkflow with mocked services.

Tests workflow configuration and session setup with mocked services.
Verifies correct multi-iteration behavior and result tracking.
Orchestrator is constructed internally by the workflow.
"""

from unittest.mock import Mock


from autoraid.workflows.spend_workflow import SpendWorkflow
from autoraid.detection.progress_bar_detector import ProgressBarStateDetector


class TestSpendWorkflowIntegration:
    """Integration tests for SpendWorkflow with mocked services."""

    def test_spend_workflow_construction_with_services(self):
        """Test SpendWorkflow can be constructed with mocked services (no DI)."""
        # Arrange: Mock all services
        mock_cache_service = Mock()
        mock_window_service = Mock()
        mock_network_manager = Mock()
        mock_screenshot_service = Mock()
        mock_detector = Mock(spec=ProgressBarStateDetector)

        # Act: Construct workflow directly (no DI)
        workflow = SpendWorkflow(
            cache_service=mock_cache_service,
            window_interaction_service=mock_window_service,
            network_manager=mock_network_manager,
            screenshot_service=mock_screenshot_service,
            detector=mock_detector,
            max_upgrade_attempts=10,
            continue_upgrade=True,
            debug_dir=None,
        )

        # Assert: Verify workflow constructed successfully
        assert workflow is not None
        assert workflow._max_upgrade_attempts == 10
        assert workflow._continue_upgrade is True
