"""Unit tests for DebugMonitorWorkflow."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from autoraid.core.stop_conditions import StopReason
from autoraid.exceptions import WorkflowValidationError
from autoraid.services.cache_service import CacheService
from autoraid.services.network import NetworkManager, NetworkState
from autoraid.services.upgrade_orchestrator import (
    UpgradeOrchestrator,
    UpgradeResult,
)
from autoraid.services.window_interaction_service import WindowInteractionService
from autoraid.workflows.debug_monitor_workflow import (
    DebugMonitorResult,
    DebugMonitorWorkflow,
)


@pytest.fixture
def mock_orchestrator():
    """Create mock UpgradeOrchestrator."""
    mock = Mock(spec=UpgradeOrchestrator)
    return mock


@pytest.fixture
def mock_cache_service():
    """Create mock CacheService."""
    mock = Mock(spec=CacheService)
    mock.get_regions.return_value = {
        "upgrade_bar": (100, 200, 300, 50),
        "upgrade_button": (400, 500, 100, 50),
    }
    return mock


@pytest.fixture
def mock_window_service():
    """Create mock WindowInteractionService."""
    mock = Mock(spec=WindowInteractionService)
    mock.window_exists.return_value = True
    mock.get_window_size.return_value = (800, 600)
    return mock


@pytest.fixture
def mock_network_manager():
    """Create mock NetworkManager."""
    mock = Mock(spec=NetworkManager)
    mock.check_network_access.return_value = NetworkState.OFFLINE
    return mock


@pytest.fixture
def workflow(
    mock_orchestrator, mock_cache_service, mock_window_service, mock_network_manager
):
    """Create DebugMonitorWorkflow with mocked dependencies."""
    return DebugMonitorWorkflow(
        orchestrator=mock_orchestrator,
        cache_service=mock_cache_service,
        window_interaction_service=mock_window_service,
        network_manager=mock_network_manager,
        network_adapter_ids=[1, 2],
        disable_network=True,
        max_frames=10,
        check_interval=0.2,
        debug_dir=Path("/tmp/debug"),
    )


def test_workflow_initializes_with_correct_parameters(workflow):
    """Test workflow initializes with provided parameters."""
    assert workflow._network_adapter_ids == [1, 2]
    assert workflow._disable_network is True
    assert workflow._max_frames == 10
    assert workflow._check_interval == 0.2
    assert workflow._debug_dir == Path("/tmp/debug")


def test_validate_passes_when_network_disabled_and_adapters_specified(
    workflow, mock_network_manager
):
    """Test validation passes when network is disabled with adapters specified."""
    mock_network_manager.check_network_access.return_value = NetworkState.ONLINE

    # Should not raise
    workflow.validate()


def test_validate_fails_when_network_online_and_no_adapters_specified(
    mock_orchestrator, mock_cache_service, mock_window_service, mock_network_manager
):
    """Test validation fails when network is online but no adapters specified."""
    mock_network_manager.check_network_access.return_value = NetworkState.ONLINE

    workflow = DebugMonitorWorkflow(
        orchestrator=mock_orchestrator,
        cache_service=mock_cache_service,
        window_interaction_service=mock_window_service,
        network_manager=mock_network_manager,
        network_adapter_ids=None,  # No adapters specified
        disable_network=True,
    )

    with pytest.raises(WorkflowValidationError) as exc_info:
        workflow.validate()

    assert "no network adapter specified" in str(exc_info.value).lower()


def test_validate_passes_when_network_disabled_flag_is_false(
    mock_orchestrator, mock_cache_service, mock_window_service, mock_network_manager
):
    """Test validation passes when disable_network is False (keep network)."""
    mock_network_manager.check_network_access.return_value = NetworkState.ONLINE

    workflow = DebugMonitorWorkflow(
        orchestrator=mock_orchestrator,
        cache_service=mock_cache_service,
        window_interaction_service=mock_window_service,
        network_manager=mock_network_manager,
        network_adapter_ids=None,
        disable_network=False,  # Keep network enabled
    )

    # Should not raise even without adapters
    workflow.validate()


def test_run_creates_correct_upgrade_session(
    workflow, mock_orchestrator, mock_cache_service
):
    """Test run() creates UpgradeSession with correct configuration."""
    # Mock orchestrator to return result
    mock_result = UpgradeResult(
        fail_count=0,
        frames_processed=10,
        stop_reason=StopReason.MAX_FRAMES_CAPTURED,
        debug_session_dir=Path("/tmp/debug/progressbar_monitor/session123"),
    )
    mock_orchestrator.run_upgrade_session.return_value = mock_result

    result = workflow.run()

    # Verify orchestrator was called
    assert mock_orchestrator.run_upgrade_session.called
    call_args = mock_orchestrator.run_upgrade_session.call_args
    session = call_args[0][0]

    # Verify session configuration
    assert session.upgrade_bar_region == (100, 200, 300, 50)
    assert session.upgrade_button_region == (400, 500, 100, 50)
    assert session.check_interval == 0.2
    assert session.network_adapter_ids == [1, 2]
    assert session.disable_network is True
    assert session.debug_logger is not None

    # Verify stop conditions (should have MaxFramesCondition)
    assert len(session.stop_conditions._conditions) == 1

    # Verify result
    assert isinstance(result, DebugMonitorResult)
    assert result.stop_reason == StopReason.MAX_FRAMES_CAPTURED


def test_run_creates_empty_stop_conditions_when_max_frames_none(
    mock_orchestrator, mock_cache_service, mock_window_service, mock_network_manager
):
    """Test run() creates empty stop condition chain when max_frames is None."""
    workflow = DebugMonitorWorkflow(
        orchestrator=mock_orchestrator,
        cache_service=mock_cache_service,
        window_interaction_service=mock_window_service,
        network_manager=mock_network_manager,
        max_frames=None,  # No frame limit
    )

    # Mock orchestrator to return result
    mock_result = UpgradeResult(
        fail_count=0,
        frames_processed=50,
        stop_reason=StopReason.MANUAL_STOP,
        debug_session_dir=Path("/tmp/debug/progressbar_monitor/session123"),
    )
    mock_orchestrator.run_upgrade_session.return_value = mock_result

    workflow.run()

    # Verify stop conditions is empty
    call_args = mock_orchestrator.run_upgrade_session.call_args
    session = call_args[0][0]
    assert len(session.stop_conditions._conditions) == 0


def test_run_uses_default_debug_dir_when_none_provided(
    mock_orchestrator, mock_cache_service, mock_window_service, mock_network_manager
):
    """Test run() uses default debug directory when none provided."""
    workflow = DebugMonitorWorkflow(
        orchestrator=mock_orchestrator,
        cache_service=mock_cache_service,
        window_interaction_service=mock_window_service,
        network_manager=mock_network_manager,
        debug_dir=None,  # No debug dir specified
    )

    # Mock orchestrator to return result
    mock_result = UpgradeResult(
        fail_count=0,
        frames_processed=10,
        stop_reason=StopReason.MAX_FRAMES_CAPTURED,
        debug_session_dir=Path(
            "cache-raid-autoupgrade/debug/progressbar_monitor/session123"
        ),
    )
    mock_orchestrator.run_upgrade_session.return_value = mock_result

    workflow.run()

    # Verify debug logger was created with default path
    call_args = mock_orchestrator.run_upgrade_session.call_args
    session = call_args[0][0]
    assert session.debug_logger is not None


def test_run_handles_keyboard_interrupt(
    workflow, mock_orchestrator, mock_cache_service
):
    """Test run() handles KeyboardInterrupt gracefully."""
    # Mock orchestrator to raise KeyboardInterrupt
    mock_orchestrator.run_upgrade_session.side_effect = KeyboardInterrupt()

    result = workflow.run()

    # Should return result with MANUAL_STOP
    assert isinstance(result, DebugMonitorResult)
    assert result.stop_reason == StopReason.MANUAL_STOP


def test_run_retrieves_regions_from_cache(
    workflow, mock_orchestrator, mock_cache_service, mock_window_service
):
    """Test run() retrieves regions from cache using current window size."""
    # Mock orchestrator to return result
    mock_result = UpgradeResult(
        fail_count=0,
        frames_processed=10,
        stop_reason=StopReason.MAX_FRAMES_CAPTURED,
        debug_session_dir=Path("/tmp/debug/progressbar_monitor/session123"),
    )
    mock_orchestrator.run_upgrade_session.return_value = mock_result

    workflow.run()

    # Verify window size was retrieved
    mock_window_service.get_window_size.assert_called_once_with("Raid: Shadow Legends")

    # Verify regions were retrieved using window size
    mock_cache_service.get_regions.assert_called_once_with((800, 600))
