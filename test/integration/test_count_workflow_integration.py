"""Integration tests for CountWorkflow with mocked orchestrator.

Tests session configuration and result mapping with mocked UpgradeOrchestrator.
"""

from unittest.mock import Mock


from autoraid.core.stop_conditions import (
    StopReason,
    MaxAttemptsCondition,
    UpgradedCondition,
    StopConditionChain,
)
from autoraid.services.upgrade_orchestrator import UpgradeResult, UpgradeSession
from autoraid.services.network import NetworkState
from autoraid.workflows.count_workflow import CountWorkflow, CountResult


class TestCountWorkflowIntegration:
    """Integration tests for CountWorkflow with mocked orchestrator."""

    def test_count_workflow_session_configuration(self):
        """Test CountWorkflow configures UpgradeSession correctly for count operations."""
        # Arrange: Mock services
        mock_cache_service = Mock()
        mock_cache_service.get_regions.return_value = {
            "upgrade_button": (100, 200, 50, 30),
            "upgrade_bar": (100, 250, 200, 10),
        }

        mock_window_service = Mock()
        mock_window_service.get_window_size.return_value = (1920, 1080)

        mock_network_manager = Mock()
        mock_network_manager.check_network_access.return_value = NetworkState.OFFLINE

        # Mock orchestrator to capture session config
        mock_orchestrator = Mock()
        mock_orchestrator.run_upgrade_session.return_value = UpgradeResult(
            fail_count=7,
            frames_processed=150,
            stop_reason=StopReason.MAX_ATTEMPTS_REACHED,
            debug_session_dir=None,
        )

        workflow = CountWorkflow(
            cache_service=mock_cache_service,
            window_interaction_service=mock_window_service,
            network_manager=mock_network_manager,
            orchestrator=mock_orchestrator,
            network_adapter_ids=[1, 2],
            max_attempts=10,
            debug_dir=None,
        )

        # Act: Run workflow
        workflow.validate()
        result = workflow.run()

        # Assert: Verify session was configured correctly
        mock_orchestrator.run_upgrade_session.assert_called_once()
        session: UpgradeSession = mock_orchestrator.run_upgrade_session.call_args[0][0]

        # Verify regions
        assert session.upgrade_bar_region == (100, 250, 200, 10)
        assert session.upgrade_button_region == (100, 200, 50, 30)

        # Verify network configuration
        assert session.network_adapter_ids == [1, 2]
        assert session.disable_network is True

        # Verify stop conditions chain
        assert isinstance(session.stop_conditions, StopConditionChain)
        conditions = session.stop_conditions._conditions
        assert len(conditions) == 2

        # First condition: MaxAttemptsCondition
        assert isinstance(conditions[0], MaxAttemptsCondition)
        assert conditions[0].max_attempts == 10

        # Second condition: UpgradedCondition with network_disabled=True
        assert isinstance(conditions[1], UpgradedCondition)
        assert conditions[1].network_disabled is True

        # Verify check interval
        assert session.check_interval == 0.25

        # Verify no debug directory (debug_dir is None)
        assert session.debug_dir is None

        # Verify result mapping
        assert isinstance(result, CountResult)
        assert result.fail_count == 7
        assert result.stop_reason == StopReason.MAX_ATTEMPTS_REACHED
