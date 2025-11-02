"""Smoke tests for upgrade panel component."""

from unittest.mock import Mock

from autoraid.gui.components.upgrade_panel import create_upgrade_panel
from autoraid.services.cache_service import CacheService
from autoraid.services.window_interaction_service import WindowInteractionService
from autoraid.services.network import NetworkManager
from autoraid.services.screenshot_service import ScreenshotService
from autoraid.detection.progress_bar_detector import ProgressBarStateDetector


def test_create_upgrade_panel_smoke():
    """Verify panel creation with mocked services (smoke test)."""
    # Create mock services (matching new architecture)
    mock_cache = Mock(spec=CacheService)
    mock_window = Mock(spec=WindowInteractionService)
    mock_network = Mock(spec=NetworkManager)
    mock_screenshot = Mock(spec=ScreenshotService)
    mock_detector = Mock(spec=ProgressBarStateDetector)

    # Create panel with mocked dependencies (services, not factories)
    create_upgrade_panel(
        cache_service=mock_cache,
        window_interaction_service=mock_window,
        network_manager=mock_network,
        screenshot_service=mock_screenshot,
        detector=mock_detector,
    )
    # No exception = pass
