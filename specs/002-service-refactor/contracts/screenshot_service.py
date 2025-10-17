"""Screenshot service interface protocol."""

from typing import Protocol
import numpy as np


class ScreenshotServiceProtocol(Protocol):
    """Interface for screenshot operations."""

    def take_screenshot(self, window_title: str) -> np.ndarray:
        """Capture screenshot of window with given title.

        Args:
            window_title: Title of window to capture

        Returns:
            Screenshot as numpy array (BGR format)

        Raises:
            WindowNotFoundException: If window not found
        """
        ...

    def window_exists(self, window_title: str) -> bool:
        """Check if window with title exists.

        Args:
            window_title: Title of window to check

        Returns:
            True if window exists, False otherwise
        """
        ...

    def extract_roi(
        self, screenshot: np.ndarray, region: tuple[int, int, int, int]
    ) -> np.ndarray:
        """Extract region of interest from screenshot.

        Args:
            screenshot: Full screenshot as numpy array
            region: Region as (left, top, width, height)

        Returns:
            ROI as numpy array

        Raises:
            ValueError: If region coordinates invalid
        """
        ...
