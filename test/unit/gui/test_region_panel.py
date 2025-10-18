"""Smoke tests for RegionPanel component."""

from unittest.mock import Mock

from autoraid.gui.components.region_panel import create_region_panel
from autoraid.services.cache_service import CacheService
from autoraid.services.locate_region_service import LocateRegionService
from autoraid.services.screenshot_service import ScreenshotService
from autoraid.services.window_interaction_service import WindowInteractionService


def test_create_region_panel_smoke():
    """Verify RegionPanel creation without errors."""
    # Create mock services
    mock_locate = Mock(spec=LocateRegionService)
    mock_screenshot = Mock(spec=ScreenshotService)
    mock_window = Mock(spec=WindowInteractionService)
    mock_cache = Mock(spec=CacheService)

    # Configure mock behavior for initial status update
    mock_window.get_window_size.return_value = (1920, 1080)
    mock_cache.get_regions.return_value = None

    # Create panel - should not raise
    create_region_panel(
        locate_region_service=mock_locate,
        screenshot_service=mock_screenshot,
        window_interaction_service=mock_window,
        cache_service=mock_cache,
    )

    # Verify services were called (status update happens immediately)
    mock_window.get_window_size.assert_called()
    mock_cache.get_regions.assert_called()
