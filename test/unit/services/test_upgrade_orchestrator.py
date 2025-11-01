"""Unit tests for UpgradeOrchestrator."""

import numpy as np
import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from autoraid.services.upgrade_orchestrator import (
    UpgradeOrchestrator,
    UpgradeSession,
)
from autoraid.core.progress_bar_monitor import (
    ProgressBarMonitor,
    ProgressBarMonitorState,
)
from autoraid.core.stop_conditions import (
    StopConditionChain,
    MaxAttemptsCondition,
    StopReason,
)
from autoraid.core.progress_bar_detector import ProgressBarState
from autoraid.services.screenshot_service import ScreenshotService
from autoraid.services.window_interaction_service import WindowInteractionService
from autoraid.services.cache_service import CacheService
from autoraid.services.network import NetworkManager
from autoraid.exceptions import WindowNotFoundException, WorkflowValidationError


class TestUpgradeOrchestrator:
    """Tests for UpgradeOrchestrator class."""

    def test_validate_prerequisites_passes_when_window_exists_and_regions_cached(self):
        """Verify validate_prerequisites passes when window exists and regions cached."""
        mock_screenshot = Mock(spec=ScreenshotService)
        mock_window = Mock(spec=WindowInteractionService)
        mock_cache = Mock(spec=CacheService)
        mock_network = Mock(spec=NetworkManager)
        mock_monitor = Mock(spec=ProgressBarMonitor)

        # Configure mocks
        mock_window.window_exists.return_value = True
        mock_window.get_window_size.return_value = (800, 600)
        mock_cache.get_regions.return_value = {
            "upgrade_bar": (0, 0, 100, 50),
            "upgrade_button": (0, 0, 100, 50),
        }

        orchestrator = UpgradeOrchestrator(
            screenshot_service=mock_screenshot,
            window_interaction_service=mock_window,
            cache_service=mock_cache,
            network_manager=mock_network,
            monitor=mock_monitor,
        )

        session = UpgradeSession(
            upgrade_bar_region=(0, 0, 100, 50),
            upgrade_button_region=(0, 0, 100, 50),
            stop_conditions=StopConditionChain([]),
        )

        # Should not raise
        orchestrator.validate_prerequisites(session)

    def test_validate_prerequisites_raises_when_window_not_found(self):
        """Verify validate_prerequisites raises WindowNotFoundException when window not found."""
        mock_screenshot = Mock(spec=ScreenshotService)
        mock_window = Mock(spec=WindowInteractionService)
        mock_cache = Mock(spec=CacheService)
        mock_network = Mock(spec=NetworkManager)
        mock_monitor = Mock(spec=ProgressBarMonitor)

        # Window does not exist
        mock_window.window_exists.return_value = False

        orchestrator = UpgradeOrchestrator(
            screenshot_service=mock_screenshot,
            window_interaction_service=mock_window,
            cache_service=mock_cache,
            network_manager=mock_network,
            monitor=mock_monitor,
        )

        session = UpgradeSession(
            upgrade_bar_region=(0, 0, 100, 50),
            upgrade_button_region=(0, 0, 100, 50),
            stop_conditions=StopConditionChain([]),
        )

        with pytest.raises(WindowNotFoundException, match="Raid window not found"):
            orchestrator.validate_prerequisites(session)

    def test_validate_prerequisites_raises_when_regions_not_cached(self):
        """Verify validate_prerequisites raises WorkflowValidationError when regions not cached."""
        mock_screenshot = Mock(spec=ScreenshotService)
        mock_window = Mock(spec=WindowInteractionService)
        mock_cache = Mock(spec=CacheService)
        mock_network = Mock(spec=NetworkManager)
        mock_monitor = Mock(spec=ProgressBarMonitor)

        # Window exists but regions not cached
        mock_window.window_exists.return_value = True
        mock_window.get_window_size.return_value = (800, 600)
        mock_cache.get_regions.return_value = None

        orchestrator = UpgradeOrchestrator(
            screenshot_service=mock_screenshot,
            window_interaction_service=mock_window,
            cache_service=mock_cache,
            network_manager=mock_network,
            monitor=mock_monitor,
        )

        session = UpgradeSession(
            upgrade_bar_region=(0, 0, 100, 50),
            upgrade_button_region=(0, 0, 100, 50),
            stop_conditions=StopConditionChain([]),
        )

        with pytest.raises(WorkflowValidationError, match="No regions cached"):
            orchestrator.validate_prerequisites(session)

    @patch("autoraid.services.upgrade_orchestrator.time.sleep")
    def test_run_upgrade_session_calls_services_in_correct_order(self, mock_sleep):
        """Verify run_upgrade_session calls services in expected sequence."""
        mock_screenshot = Mock(spec=ScreenshotService)
        mock_window = Mock(spec=WindowInteractionService)
        mock_cache = Mock(spec=CacheService)
        mock_network = Mock(spec=NetworkManager)
        mock_monitor = Mock(spec=ProgressBarMonitor)

        # Configure mock behavior
        fake_screenshot = np.zeros((100, 200, 3), dtype=np.uint8)
        fake_roi = np.zeros((50, 200, 3), dtype=np.uint8)
        mock_screenshot.take_screenshot.return_value = fake_screenshot
        mock_screenshot.extract_roi.return_value = fake_roi

        mock_window.window_exists.return_value = True
        mock_window.get_window_size.return_value = (800, 600)
        mock_cache.get_regions.return_value = {
            "upgrade_bar": (0, 0, 100, 50),
            "upgrade_button": (0, 0, 100, 50),
        }

        # Configure monitor to stop after 2 frames
        mock_state = Mock(spec=ProgressBarMonitorState)
        mock_state.fail_count = 2
        mock_state.frames_processed = 2
        mock_monitor.get_state.return_value = mock_state
        mock_monitor.process_frame.return_value = ProgressBarState.FAIL

        # Create stop conditions
        stop_conditions = StopConditionChain([MaxAttemptsCondition(max_attempts=2)])

        # Mock the stop conditions check to return stop reason after 2 calls
        call_count = 0

        def check_side_effect(state):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                return StopReason.MAX_ATTEMPTS_REACHED
            return None

        with patch.object(stop_conditions, "check", side_effect=check_side_effect):
            orchestrator = UpgradeOrchestrator(
                screenshot_service=mock_screenshot,
                window_interaction_service=mock_window,
                cache_service=mock_cache,
                network_manager=mock_network,
                monitor=mock_monitor,
            )

            session = UpgradeSession(
                upgrade_bar_region=(0, 0, 100, 50),
                upgrade_button_region=(0, 0, 100, 50),
                stop_conditions=stop_conditions,
            )

            result = orchestrator.run_upgrade_session(session)

            # Verify service calls
            mock_window.click_region.assert_called_once()
            assert mock_screenshot.take_screenshot.call_count >= 2
            assert mock_monitor.process_frame.call_count >= 2

            assert result.fail_count == 2
            assert result.stop_reason == StopReason.MAX_ATTEMPTS_REACHED

    @patch("autoraid.services.upgrade_orchestrator.time.sleep")
    @patch("autoraid.services.upgrade_orchestrator.DebugFrameLogger")
    def test_run_upgrade_session_with_debug_dir(
        self, mock_debug_logger_class, mock_sleep
    ):
        """Verify run_upgrade_session creates debug logger when debug_dir is set."""
        mock_screenshot = Mock(spec=ScreenshotService)
        mock_window = Mock(spec=WindowInteractionService)
        mock_cache = Mock(spec=CacheService)
        mock_network = Mock(spec=NetworkManager)
        mock_monitor = Mock(spec=ProgressBarMonitor)

        # Mock the DebugFrameLogger instance
        mock_debug_logger = MagicMock()
        mock_debug_logger.session_dir = Path("/tmp/debug")
        mock_debug_logger_class.return_value = mock_debug_logger

        # Configure mock behavior
        fake_screenshot = np.zeros((100, 200, 3), dtype=np.uint8)
        fake_roi = np.zeros((50, 200, 3), dtype=np.uint8)
        mock_screenshot.take_screenshot.return_value = fake_screenshot
        mock_screenshot.extract_roi.return_value = fake_roi

        mock_window.window_exists.return_value = True
        mock_window.get_window_size.return_value = (800, 600)
        mock_cache.get_regions.return_value = {
            "upgrade_bar": (0, 0, 100, 50),
            "upgrade_button": (0, 0, 100, 50),
        }

        mock_state = Mock(spec=ProgressBarMonitorState)
        mock_state.fail_count = 1
        mock_state.frames_processed = 1
        mock_monitor.get_state.return_value = mock_state
        mock_monitor.process_frame.return_value = ProgressBarState.FAIL

        stop_conditions = StopConditionChain([MaxAttemptsCondition(max_attempts=1)])

        call_count = 0

        def check_side_effect(state):
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                return StopReason.MAX_ATTEMPTS_REACHED
            return None

        with patch.object(stop_conditions, "check", side_effect=check_side_effect):
            orchestrator = UpgradeOrchestrator(
                screenshot_service=mock_screenshot,
                window_interaction_service=mock_window,
                cache_service=mock_cache,
                network_manager=mock_network,
                monitor=mock_monitor,
            )

            session = UpgradeSession(
                upgrade_bar_region=(0, 0, 100, 50),
                upgrade_button_region=(0, 0, 100, 50),
                stop_conditions=stop_conditions,
                debug_dir=Path("/tmp/debug"),
            )

            result = orchestrator.run_upgrade_session(session)

            # Verify debug logger was created and used
            mock_debug_logger_class.assert_called_once_with(
                output_dir=Path("/tmp/debug")
            )
            assert mock_debug_logger.log_frame.call_count >= 1
            mock_debug_logger.save_summary.assert_called_once()
            assert result.debug_session_dir == Path("/tmp/debug")

    @patch("autoraid.services.upgrade_orchestrator.NetworkContext")
    @patch("autoraid.services.upgrade_orchestrator.time.sleep")
    def test_run_upgrade_session_uses_network_context(
        self, mock_sleep, mock_network_context
    ):
        """Verify run_upgrade_session uses NetworkContext for network management."""
        mock_screenshot = Mock(spec=ScreenshotService)
        mock_window = Mock(spec=WindowInteractionService)
        mock_cache = Mock(spec=CacheService)
        mock_network = Mock(spec=NetworkManager)
        mock_monitor = Mock(spec=ProgressBarMonitor)

        # Configure mock behavior
        fake_screenshot = np.zeros((100, 200, 3), dtype=np.uint8)
        fake_roi = np.zeros((50, 200, 3), dtype=np.uint8)
        mock_screenshot.take_screenshot.return_value = fake_screenshot
        mock_screenshot.extract_roi.return_value = fake_roi

        mock_window.window_exists.return_value = True
        mock_window.get_window_size.return_value = (800, 600)
        mock_cache.get_regions.return_value = {
            "upgrade_bar": (0, 0, 100, 50),
            "upgrade_button": (0, 0, 100, 50),
        }

        mock_state = Mock(spec=ProgressBarMonitorState)
        mock_state.fail_count = 1
        mock_state.frames_processed = 1
        mock_monitor.get_state.return_value = mock_state
        mock_monitor.process_frame.return_value = ProgressBarState.FAIL

        stop_conditions = StopConditionChain([MaxAttemptsCondition(max_attempts=1)])

        call_count = 0

        def check_side_effect(state):
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                return StopReason.MAX_ATTEMPTS_REACHED
            return None

        with patch.object(stop_conditions, "check", side_effect=check_side_effect):
            orchestrator = UpgradeOrchestrator(
                screenshot_service=mock_screenshot,
                window_interaction_service=mock_window,
                cache_service=mock_cache,
                network_manager=mock_network,
                monitor=mock_monitor,
            )

            session = UpgradeSession(
                upgrade_bar_region=(0, 0, 100, 50),
                upgrade_button_region=(0, 0, 100, 50),
                stop_conditions=stop_conditions,
                network_adapter_ids=[1, 2],
                disable_network=True,
            )

            orchestrator.run_upgrade_session(session)

            # Verify NetworkContext was called with correct parameters
            mock_network_context.assert_called_once_with(
                network_manager=mock_network,
                adapter_ids=[1, 2],
                disable_network=True,
            )
