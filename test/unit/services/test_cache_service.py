"""Smoke tests for CacheService."""

import numpy as np
from unittest.mock import Mock

from autoraid.services.cache_service import CacheService


def test_cache_service_instantiates():
    """Test that CacheService can be instantiated with a mock cache."""
    mock_cache = Mock()
    service = CacheService(mock_cache)
    assert service is not None


def test_cache_service_generates_correct_key():
    """Test that cache key generation follows the expected format."""
    mock_cache = Mock()
    service = CacheService(mock_cache)

    # Test regions key format
    window_size = (1920, 1080)
    regions_key = service.create_regions_key(window_size)
    assert regions_key == "regions_1920_1080"

    # Test screenshot key format
    screenshot_key = service.create_screenshot_key(window_size)
    assert screenshot_key == "screenshot_1920_1080"


def test_cache_service_get_regions_calls_cache():
    """Test that get_regions properly calls the underlying cache."""
    mock_cache = Mock()
    mock_cache.get.return_value = {"upgrade_bar": (0, 0, 100, 100)}

    service = CacheService(mock_cache)
    window_size = (1920, 1080)
    regions = service.get_regions(window_size)

    # Verify cache.get was called with correct key
    mock_cache.get.assert_called_once_with("regions_1920_1080")
    assert regions == {"upgrade_bar": (0, 0, 100, 100)}


def test_cache_service_set_regions_calls_cache():
    """Test that set_regions properly calls the underlying cache."""
    mock_cache = Mock()

    service = CacheService(mock_cache)
    window_size = (1920, 1080)
    regions = {"upgrade_bar": (0, 0, 100, 100)}
    service.set_regions(window_size, regions)

    # Verify cache.set was called with correct key and value
    mock_cache.set.assert_called_once_with("regions_1920_1080", regions)


def test_cache_service_get_screenshot_returns_none_when_not_cached():
    """Test that get_screenshot returns None when screenshot not in cache."""
    mock_cache = Mock()
    mock_cache.get.return_value = None

    service = CacheService(mock_cache)
    window_size = (1920, 1080)
    screenshot = service.get_screenshot(window_size)

    assert screenshot is None
    mock_cache.get.assert_called_once_with("screenshot_1920_1080")


def test_cache_service_set_screenshot_stores_numpy_array():
    """Test that set_screenshot stores numpy array in cache."""
    mock_cache = Mock()

    service = CacheService(mock_cache)
    window_size = (1920, 1080)
    fake_screenshot = np.zeros((1080, 1920, 3), dtype=np.uint8)
    service.set_screenshot(window_size, fake_screenshot)

    # Verify cache.set was called
    mock_cache.set.assert_called_once()
    call_args = mock_cache.set.call_args
    assert call_args[0][0] == "screenshot_1920_1080"
    assert isinstance(call_args[0][1], np.ndarray)
