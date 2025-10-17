"""Cache service interface protocol."""

from typing import Protocol
import numpy as np


class CacheServiceProtocol(Protocol):
    """Interface for cache operations."""

    def create_regions_key(self, window_size: tuple[int, int]) -> str:
        """Generate cache key for regions based on window size.

        Args:
            window_size: Tuple of (width, height) in pixels

        Returns:
            Cache key string in format "regions_{width}_{height}"
        """
        ...

    def get_regions(self, window_size: tuple[int, int]) -> dict | None:
        """Retrieve cached regions for window size.

        Args:
            window_size: Tuple of (width, height) in pixels

        Returns:
            Dictionary of regions {name: (left, top, width, height)} or None if not cached
        """
        ...

    def set_regions(self, window_size: tuple[int, int], regions: dict) -> None:
        """Store regions in cache for window size.

        Args:
            window_size: Tuple of (width, height) in pixels
            regions: Dictionary of regions {name: (left, top, width, height)}
        """
        ...

    def get_screenshot(self, window_size: tuple[int, int]) -> np.ndarray | None:
        """Retrieve cached screenshot for window size.

        Args:
            window_size: Tuple of (width, height) in pixels

        Returns:
            Screenshot as numpy array or None if not cached
        """
        ...

    def set_screenshot(
        self, window_size: tuple[int, int], screenshot: np.ndarray
    ) -> None:
        """Store screenshot in cache for window size.

        Args:
            window_size: Tuple of (width, height) in pixels
            screenshot: Screenshot as numpy array
        """
        ...
