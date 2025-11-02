"""Integration tests for CountWorkflow with mocked services.

Tests session configuration and result mapping with mocked services.
Orchestrator is constructed internally by the workflow.
"""

from unittest.mock import Mock


from autoraid.workflows.count_workflow import CountWorkflow
from autoraid.detection.progress_bar_detector import ProgressBarStateDetector


class TestCountWorkflowIntegration:
    """Integration tests for CountWorkflow with mocked services."""

    def test_count_workflow_construction_with_services(self):
        """Test CountWorkflow can be constructed with mocked services (no DI)."""
        # Arrange: Mock all services
        mock_cache_service = Mock()
        mock_window_service = Mock()
        mock_network_manager = Mock()
        mock_screenshot_service = Mock()
        mock_detector = Mock(spec=ProgressBarStateDetector)

        # Act: Construct workflow directly (no DI)
        workflow = CountWorkflow(
            cache_service=mock_cache_service,
            window_interaction_service=mock_window_service,
            network_manager=mock_network_manager,
            screenshot_service=mock_screenshot_service,
            detector=mock_detector,
            network_adapter_ids=[1, 2],
            max_attempts=10,
            debug_dir=None,
        )

        # Assert: Verify workflow constructed successfully
        assert workflow is not None
        assert workflow._network_adapter_ids == [1, 2]
        assert workflow._max_attempts == 10
