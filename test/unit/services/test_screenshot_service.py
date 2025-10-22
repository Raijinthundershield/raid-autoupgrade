"""Smoke tests for ScreenshotService.

These tests verify basic functionality of the ScreenshotService:
- Service instantiation with window interaction service dependency
- ROI extraction from numpy arrays
"""

import numpy as np
import pytest
from unittest.mock import Mock

from autoraid.services.screenshot_service import (
    ScreenshotService,
)


def test_screenshot_service_instantiates():
    """Smoke test: Service instantiates correctly with window interaction service."""
    mock_window_service = Mock()
    service = ScreenshotService(window_interaction_service=mock_window_service)
    assert service is not None
    assert isinstance(service, ScreenshotService)


def test_screenshot_service_extracts_roi():
    """Smoke test: ROI extraction works with fake numpy array."""
    # Arrange
    mock_window_service = Mock()
    service = ScreenshotService(window_interaction_service=mock_window_service)

    # Create a fake 100x100 screenshot (BGR format)
    screenshot = np.zeros((100, 100, 3), dtype=np.uint8)
    # Fill with a pattern to verify extraction
    screenshot[:, :] = [50, 100, 150]  # BGR values

    # Define region to extract (left=10, top=20, width=30, height=40)
    region = (10, 20, 30, 40)

    # Act
    roi = service.extract_roi(screenshot, region)

    # Assert
    assert roi is not None
    assert isinstance(roi, np.ndarray)
    # Check ROI dimensions match requested region
    assert roi.shape[0] == 40  # height
    assert roi.shape[1] == 30  # width
    assert roi.shape[2] == 3  # BGR channels
    # Check ROI contains expected color
    assert np.array_equal(roi[0, 0], [50, 100, 150])


def test_screenshot_service_extract_roi_validates_coordinates():
    """Smoke test: Service validates region coordinates."""
    mock_window_service = Mock()
    service = ScreenshotService(window_interaction_service=mock_window_service)
    screenshot = np.zeros((100, 100, 3), dtype=np.uint8)

    # Test negative coordinates
    with pytest.raises(ValueError, match="Coordinates must be non-negative"):
        service.extract_roi(screenshot, (-10, 20, 30, 40))

    with pytest.raises(ValueError, match="Coordinates must be non-negative"):
        service.extract_roi(screenshot, (10, -20, 30, 40))


def test_screenshot_service_extract_roi_validates_dimensions():
    """Smoke test: Service validates region dimensions."""
    mock_window_service = Mock()
    service = ScreenshotService(window_interaction_service=mock_window_service)
    screenshot = np.zeros((100, 100, 3), dtype=np.uint8)

    # Test zero/negative dimensions
    with pytest.raises(ValueError, match="Dimensions must be positive"):
        service.extract_roi(screenshot, (10, 20, 0, 40))

    with pytest.raises(ValueError, match="Dimensions must be positive"):
        service.extract_roi(screenshot, (10, 20, 30, -40))


def test_screenshot_service_extract_roi_validates_bounds():
    """Smoke test: Service validates region is within screenshot bounds."""
    mock_window_service = Mock()
    service = ScreenshotService(window_interaction_service=mock_window_service)
    screenshot = np.zeros((100, 100, 3), dtype=np.uint8)

    # Test region exceeding screenshot bounds
    with pytest.raises(ValueError, match="exceeds screenshot bounds"):
        service.extract_roi(screenshot, (90, 20, 30, 40))  # 90 + 30 > 100

    with pytest.raises(ValueError, match="exceeds screenshot bounds"):
        service.extract_roi(screenshot, (10, 90, 30, 40))  # 90 + 40 > 100


def test_screenshot_service_take_screenshot_validates_input():
    """Smoke test: Service validates window_title input for take_screenshot."""
    mock_window_service = Mock()
    service = ScreenshotService(window_interaction_service=mock_window_service)

    # Test empty window title
    with pytest.raises(ValueError, match="window_title cannot be empty"):
        service.take_screenshot("")
