"""Smoke tests for LocateRegionService.

These are basic tests to verify the service instantiates and integrates
with its dependencies correctly.
"""

import numpy as np
import pytest
from unittest.mock import Mock

from autoraid.services.locate_region_service import LocateRegionService
from autoraid.services.cache_service import CacheService
from autoraid.services.screenshot_service import ScreenshotService


def test_locate_region_service_instantiates():
    """Smoke test: Service instantiates correctly with dependencies."""
    cache_service = Mock(spec=CacheService)
    screenshot_service = Mock(spec=ScreenshotService)

    service = LocateRegionService(cache_service, screenshot_service)

    assert service is not None
    assert service._cache_service is cache_service
    assert service._screenshot_service is screenshot_service


@pytest.skip(
    "Automatic detection currently not working, and this hence need a popup for selection"
)
def test_locate_region_service_uses_cache():
    """Smoke test: Service uses cached regions when available."""
    # Setup mocks
    cache_service = Mock(spec=CacheService)
    screenshot_service = Mock(spec=ScreenshotService)

    # Mock cached regions
    cached_regions = {
        "upgrade_bar": (10, 20, 30, 40),
        "upgrade_button": (50, 60, 70, 80),
    }
    cache_service.get_regions.return_value = cached_regions

    # Create service and test
    service = LocateRegionService(cache_service, screenshot_service)

    # Create fake screenshot
    screenshot = np.zeros((100, 100, 3), dtype=np.uint8)

    # Get regions
    regions = service.get_regions(screenshot)

    # Verify cache was checked
    cache_service.get_regions.assert_called_once()
    assert regions == cached_regions

    # Verify no new regions were cached (since we used cached ones)
    cache_service.set_regions.assert_not_called()
    cache_service.set_screenshot.assert_not_called()
