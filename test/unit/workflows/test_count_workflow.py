"""Unit tests for CountWorkflow with mocked dependencies.

Tests the validation and execution logic with mocked orchestrator.
Following smoke test philosophy - verify basic functionality and regressions.
"""

from unittest.mock import Mock, patch
from pathlib import Path

import pytest

from autoraid.core.stop_conditions import (
    StopReason,
    MaxAttemptsCondition,
    UpgradedCondition,
)
from autoraid.exceptions import WorkflowValidationError
from autoraid.services.network import NetworkState
from autoraid.services.upgrade_orchestrator import UpgradeResult, UpgradeSession
from autoraid.workflows.count_workflow import CountResult, CountWorkflow


class TestCountWorkflowValidation:
    """Test validation phase of CountWorkflow."""

    def test_validate_internet_on_without_adapters_raises_error(self):
        """Test validation fails when internet is on but no adapters specified.

        This is the "network safety" check - prevents accidental upgrades.
        """
        # Arrange: Mock services
        mock_window_service = Mock()
        mock_window_service.get_window_size.return_value = (1920, 1080)

        mock_network_manager = Mock()
        mock_network_manager.check_network_access.return_value = NetworkState.ONLINE

        mock_cache_service = Mock()
        mock_cache_service.get_regions.return_value = {
            "upgrade_button": (100, 200, 50, 30),
            "upgrade_bar": (100, 250, 200, 10),
        }

        workflow = CountWorkflow(
            cache_service=mock_cache_service,
            window_interaction_service=mock_window_service,
            network_manager=mock_network_manager,
            orchestrator=Mock(),
            network_adapter_ids=None,  # No adapters specified
            max_attempts=99,
            debug_dir=None,
        )

        # Act & Assert: Validation should raise WorkflowValidationError
        with pytest.raises(
            WorkflowValidationError,
            match="Internet access detected but no network adapter specified",
        ):
            workflow.validate()

    def test_validate_internet_off_without_adapters_passes(self):
        """Test validation passes when internet is off and no adapters specified."""
        # Arrange: Mock services
        mock_window_service = Mock()
        mock_window_service.get_window_size.return_value = (1920, 1080)

        mock_network_manager = Mock()
        mock_network_manager.check_network_access.return_value = NetworkState.OFFLINE

        mock_cache_service = Mock()
        mock_cache_service.get_regions.return_value = {
            "upgrade_button": (100, 200, 50, 30),
            "upgrade_bar": (100, 250, 200, 10),
        }

        workflow = CountWorkflow(
            cache_service=mock_cache_service,
            window_interaction_service=mock_window_service,
            network_manager=mock_network_manager,
            orchestrator=Mock(),
            network_adapter_ids=None,  # No adapters specified
            max_attempts=99,
            debug_dir=None,
        )

        # Act & Assert: Validation should pass without raising
        workflow.validate()  # Should not raise

    def test_validate_with_adapters_passes(self):
        """Test validation passes when adapters are specified (regardless of internet state)."""
        # Arrange: Mock services
        mock_window_service = Mock()
        mock_window_service.get_window_size.return_value = (1920, 1080)

        mock_network_manager = Mock()
        mock_network_manager.check_network_access.return_value = NetworkState.ONLINE

        mock_cache_service = Mock()
        mock_cache_service.get_regions.return_value = {
            "upgrade_button": (100, 200, 50, 30),
            "upgrade_bar": (100, 250, 200, 10),
        }

        workflow = CountWorkflow(
            cache_service=mock_cache_service,
            window_interaction_service=mock_window_service,
            network_manager=mock_network_manager,
            orchestrator=Mock(),
            network_adapter_ids=[1, 2],  # Adapters specified
            max_attempts=99,
            debug_dir=None,
        )

        # Act & Assert: Validation should pass
        workflow.validate()  # Should not raise


class TestCountWorkflowExecution:
    """Test execution phase of CountWorkflow."""

    def test_run_creates_correct_upgrade_session(self):
        """Test workflow creates UpgradeSession with correct configuration."""
        # Arrange: Mock services
        mock_cache_service = Mock()
        mock_cache_service.get_regions.return_value = {
            "upgrade_button": (100, 200, 50, 30),
            "upgrade_bar": (100, 250, 200, 10),
        }

        mock_window_service = Mock()
        mock_window_service.get_window_size.return_value = (1920, 1080)

        # Mock orchestrator to return controlled result
        mock_orchestrator = Mock()
        mock_orchestrator.run_upgrade_session.return_value = UpgradeResult(
            fail_count=5,
            frames_processed=100,
            stop_reason=StopReason.MAX_ATTEMPTS_REACHED,
            debug_session_dir=None,
        )

        workflow = CountWorkflow(
            cache_service=mock_cache_service,
            window_interaction_service=mock_window_service,
            network_manager=Mock(),
            orchestrator=mock_orchestrator,
            network_adapter_ids=[1, 2],
            max_attempts=10,
            debug_dir=None,
        )

        # Act: Run workflow
        with patch.object(workflow, "validate"):
            result = workflow.run()

        # Assert: Verify orchestrator was called with correct session
        mock_orchestrator.run_upgrade_session.assert_called_once()
        session: UpgradeSession = mock_orchestrator.run_upgrade_session.call_args[0][0]

        assert session.upgrade_bar_region == (100, 250, 200, 10)
        assert session.upgrade_button_region == (100, 200, 50, 30)
        assert session.check_interval == 0.25
        assert session.network_adapter_ids == [1, 2]
        assert session.disable_network is True
        assert session.debug_dir is None

        # Verify stop conditions
        assert len(session.stop_conditions._conditions) == 2
        assert isinstance(session.stop_conditions._conditions[0], MaxAttemptsCondition)
        assert session.stop_conditions._conditions[0].max_attempts == 10
        assert isinstance(session.stop_conditions._conditions[1], UpgradedCondition)
        assert session.stop_conditions._conditions[1].network_disabled is True

        # Verify result mapping
        assert isinstance(result, CountResult)
        assert result.fail_count == 5
        assert result.stop_reason == StopReason.MAX_ATTEMPTS_REACHED

    def test_run_without_network_adapters(self):
        """Test workflow configuration when no network adapters specified."""
        # Arrange
        mock_cache_service = Mock()
        mock_cache_service.get_regions.return_value = {
            "upgrade_button": (100, 200, 50, 30),
            "upgrade_bar": (100, 250, 200, 10),
        }

        mock_window_service = Mock()
        mock_window_service.get_window_size.return_value = (1920, 1080)

        mock_orchestrator = Mock()
        mock_orchestrator.run_upgrade_session.return_value = UpgradeResult(
            fail_count=3,
            frames_processed=50,
            stop_reason=StopReason.UPGRADED,
            debug_session_dir=None,
        )

        workflow = CountWorkflow(
            cache_service=mock_cache_service,
            window_interaction_service=mock_window_service,
            network_manager=Mock(),
            orchestrator=mock_orchestrator,
            network_adapter_ids=None,  # No adapters
            max_attempts=99,
            debug_dir=None,
        )

        # Act
        with patch.object(workflow, "validate"):
            result = workflow.run()

        # Assert: Verify session config
        session: UpgradeSession = mock_orchestrator.run_upgrade_session.call_args[0][0]
        assert session.network_adapter_ids is None
        assert session.disable_network is False

        # Verify UpgradedCondition reflects no network disabling
        upgraded_condition = session.stop_conditions._conditions[1]
        assert isinstance(upgraded_condition, UpgradedCondition)
        assert upgraded_condition.network_disabled is False

        # Verify result
        assert result.fail_count == 3
        assert result.stop_reason == StopReason.UPGRADED

    def test_run_with_debug_dir(self):
        """Test workflow creates debug logger when debug_dir provided."""
        # Arrange
        mock_cache_service = Mock()
        mock_cache_service.get_regions.return_value = {
            "upgrade_button": (100, 200, 50, 30),
            "upgrade_bar": (100, 250, 200, 10),
        }

        mock_window_service = Mock()
        mock_window_service.get_window_size.return_value = (1920, 1080)

        mock_orchestrator = Mock()
        mock_orchestrator.run_upgrade_session.return_value = UpgradeResult(
            fail_count=2,
            frames_processed=20,
            stop_reason=StopReason.MAX_ATTEMPTS_REACHED,
            debug_session_dir=Path("/tmp/debug/session_123"),
        )

        workflow = CountWorkflow(
            cache_service=mock_cache_service,
            window_interaction_service=mock_window_service,
            network_manager=Mock(),
            orchestrator=mock_orchestrator,
            network_adapter_ids=None,
            max_attempts=99,
            debug_dir=Path("/tmp/debug"),
        )

        # Act
        with patch.object(workflow, "validate"):
            workflow.run()

        # Assert: Verify debug_dir was set in session
        session: UpgradeSession = mock_orchestrator.run_upgrade_session.call_args[0][0]
        assert session.debug_dir == Path("/tmp/debug") / "count"

    def test_run_raises_when_regions_not_cached(self):
        """Test workflow raises error when regions not cached for current window size."""
        # Arrange
        mock_cache_service = Mock()
        mock_cache_service.get_regions.return_value = None  # No cached regions

        mock_window_service = Mock()
        mock_window_service.get_window_size.return_value = (1920, 1080)

        workflow = CountWorkflow(
            cache_service=mock_cache_service,
            window_interaction_service=mock_window_service,
            network_manager=Mock(),
            orchestrator=Mock(),
            network_adapter_ids=None,
            max_attempts=99,
            debug_dir=None,
        )

        # Act & Assert
        with patch.object(workflow, "validate"):
            with pytest.raises(
                WorkflowValidationError,
                match="No regions cached for window size",
            ):
                workflow.run()
