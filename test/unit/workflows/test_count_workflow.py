"""Unit tests for CountWorkflow with mocked dependencies.

Tests the validation and execution logic with mocked orchestrator.
Following smoke test philosophy - verify basic functionality and regressions.
"""

from unittest.mock import Mock, patch

import pytest

from raid_autoupgrade.detection.progress_bar_detector import ProgressBarStateDetector
from raid_autoupgrade.exceptions import WorkflowValidationError
from raid_autoupgrade.orchestration.stop_conditions import (
    MaxAttemptsCondition,
    StopReason,
    UpgradedCondition,
)
from raid_autoupgrade.orchestration.upgrade_orchestrator import (
    MonitorRun,
    UpgradeResult,
)
from raid_autoupgrade.services.network import NetworkState
from raid_autoupgrade.workflows.count_workflow import CountResult, CountWorkflow


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
            screenshot_service=Mock(),
            detector=Mock(spec=ProgressBarStateDetector),
            network_adapter_ids=None,  # No adapters specified
            max_attempts=99,
            debug_dir=None,
        )

        # Act & Assert: Validation should raise WorkflowValidationError
        with pytest.raises(WorkflowValidationError):
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
            screenshot_service=Mock(),
            detector=Mock(spec=ProgressBarStateDetector),
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
            screenshot_service=Mock(),
            detector=Mock(spec=ProgressBarStateDetector),
            network_adapter_ids=[1, 2],  # Adapters specified
            max_attempts=99,
            debug_dir=None,
        )

        # Act & Assert: Validation should pass
        workflow.validate()  # Should not raise


class TestCountWorkflowExecution:
    """Test execution phase of CountWorkflow."""

    @patch("raid_autoupgrade.workflows.count_workflow.UpgradeOrchestrator")
    def test_run_creates_correct_monitor_run(self, mock_orchestrator_class):
        """Test workflow creates a MonitorRun with correct configuration."""
        # Arrange: Mock services
        mock_cache_service = Mock()
        mock_cache_service.get_regions.return_value = {
            "upgrade_button": (100, 200, 50, 30),
            "upgrade_bar": (100, 250, 200, 10),
        }

        mock_window_service = Mock()
        mock_window_service.get_window_size.return_value = (1920, 1080)

        # Mock orchestrator instance to return controlled result
        mock_orchestrator = Mock()
        mock_orchestrator.run_monitor.return_value = UpgradeResult(
            fail_count=5,
            frames_processed=100,
            stop_reason=StopReason.MAX_ATTEMPTS_REACHED,
            debug_session_dir=None,
        )
        mock_orchestrator_class.return_value = mock_orchestrator

        workflow = CountWorkflow(
            cache_service=mock_cache_service,
            window_interaction_service=mock_window_service,
            network_manager=Mock(),
            screenshot_service=Mock(),
            detector=Mock(spec=ProgressBarStateDetector),
            network_adapter_ids=[1, 2],
            max_attempts=10,
            debug_dir=None,
        )

        # Act: Run workflow
        with patch.object(workflow, "validate"):
            result = workflow.run()

        # Assert: Verify orchestrator was called with the correct run intent
        mock_orchestrator.run_monitor.assert_called_once()
        run: MonitorRun = mock_orchestrator.run_monitor.call_args[0][0]

        assert run.check_interval == 0.25
        assert run.network_adapter_ids == [1, 2]
        assert run.disable_network is True
        assert run.require_offline is True
        assert run.debug_dir is None

        # Verify stop conditions
        assert len(run.stop_conditions._conditions) == 2
        assert isinstance(run.stop_conditions._conditions[0], MaxAttemptsCondition)
        assert run.stop_conditions._conditions[0].max_attempts == 10
        assert isinstance(run.stop_conditions._conditions[1], UpgradedCondition)
        assert run.stop_conditions._conditions[1].network_disabled is True

        # Verify result mapping
        assert isinstance(result, CountResult)
        assert result.fail_count == 5
        assert result.stop_reason == StopReason.MAX_ATTEMPTS_REACHED

    @patch("raid_autoupgrade.workflows.count_workflow.UpgradeOrchestrator")
    def test_run_validates_before_counting(self, mock_orchestrator_class):
        """run() must run the network safety check first: online + no adapter →
        raise, and never construct/run the orchestrator (which would click
        upgrade online and spend a real attempt)."""
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator

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
            screenshot_service=Mock(),
            detector=Mock(spec=ProgressBarStateDetector),
            network_adapter_ids=None,  # online + no adapter → unsafe
            max_attempts=99,
        )

        with pytest.raises(WorkflowValidationError):
            workflow.run()

        mock_orchestrator.run_monitor.assert_not_called()

    @patch("raid_autoupgrade.workflows.count_workflow.UpgradeOrchestrator")
    def test_run_passes_on_progress_to_orchestrator(self, mock_orchestrator_class):
        mock_cache_service = Mock()
        mock_cache_service.get_regions.return_value = {
            "upgrade_button": (100, 200, 50, 30),
            "upgrade_bar": (100, 250, 200, 10),
        }
        mock_window_service = Mock()
        mock_window_service.get_window_size.return_value = (1920, 1080)

        mock_orchestrator = Mock()
        mock_orchestrator.run_monitor.return_value = UpgradeResult(
            fail_count=3,
            frames_processed=50,
            stop_reason=StopReason.MAX_ATTEMPTS_REACHED,
        )
        mock_orchestrator_class.return_value = mock_orchestrator

        workflow = CountWorkflow(
            cache_service=mock_cache_service,
            window_interaction_service=mock_window_service,
            network_manager=Mock(),
            screenshot_service=Mock(),
            detector=Mock(spec=ProgressBarStateDetector),
            network_adapter_ids=None,
            max_attempts=99,
        )

        on_progress = Mock()
        with patch.object(workflow, "validate"):
            workflow.run(on_progress=on_progress)

        _, kwargs = mock_orchestrator.run_monitor.call_args
        assert kwargs.get("on_progress") is on_progress

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
            screenshot_service=Mock(),
            detector=Mock(spec=ProgressBarStateDetector),
            network_adapter_ids=None,
            max_attempts=99,
            debug_dir=None,
        )

        # Act & Assert
        with patch.object(workflow, "validate"):
            with pytest.raises(WorkflowValidationError):
                workflow.run()
