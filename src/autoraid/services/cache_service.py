"""Cache service for managing persistent storage of regions and screenshots."""

import numpy as np
from diskcache import Cache
from loguru import logger


class CacheService:
    """Service for centralized caching operations.

    Manages caching of UI regions and screenshots, keyed by window size
    to ensure regions remain valid when window dimensions change.
    """

    def __init__(self, cache: Cache):
        """Initialize CacheService with a diskcache.Cache instance.

        Args:
            cache: diskcache.Cache instance for persistent storage
        """
        self._cache = cache

    @staticmethod
    def create_regions_key(window_size: tuple[int, int]) -> str:
        """Generate cache key for regions based on window size.

        Args:
            window_size: Tuple of (height, width)

        Returns:
            Cache key string in format "regions_{height}_{width}"
        """
        return f"regions_{window_size[0]}_{window_size[1]}"

    @staticmethod
    def create_screenshot_key(window_size: tuple[int, int]) -> str:
        """Generate cache key for screenshots based on window size.

        Args:
            window_size: Tuple of (height, width)

        Returns:
            Cache key string in format "screenshot_{height}_{width}"
        """
        return f"screenshot_{window_size[0]}_{window_size[1]}"

    def get_regions(self, window_size: tuple[int, int]) -> dict | None:
        """Retrieve cached regions for window size.

        Args:
            window_size: Tuple of (height, width)

        Returns:
            Dictionary of region data if found, None otherwise
        """
        logger.debug(f"Retrieving cached regions for window size {window_size}")
        cache_key = self.create_regions_key(window_size)
        regions = self._cache.get(cache_key)
        if regions is not None:
            logger.debug("Found cached regions for window size {}", window_size)
        else:
            logger.debug("No cached regions for window size {}", window_size)
        return regions

    def set_regions(self, window_size: tuple[int, int], regions: dict) -> None:
        """Store regions in cache for window size.

        Args:
            window_size: Tuple of (height, width)
            regions: Dictionary of region data to cache
        """
        cache_key = self.create_regions_key(window_size)
        self._cache.set(cache_key, regions)
        logger.debug("Cached regions for window size {}", window_size)

    def get_screenshot(self, window_size: tuple[int, int]) -> np.ndarray | None:
        """Retrieve cached screenshot for window size.

        Args:
            window_size: Tuple of (height, width)

        Returns:
            Screenshot as numpy array if found, None otherwise
        """
        cache_key = self.create_screenshot_key(window_size)
        screenshot = self._cache.get(cache_key)
        if screenshot is not None:
            logger.debug("Found cached screenshot for window size {}", window_size)
        else:
            logger.debug("No cached screenshot for window size {}", window_size)
        return screenshot

    def set_screenshot(
        self, window_size: tuple[int, int], screenshot: np.ndarray
    ) -> None:
        """Store screenshot in cache for window size.

        Args:
            window_size: Tuple of (height, width)
            screenshot: Screenshot as numpy array to cache
        """
        cache_key = self.create_screenshot_key(window_size)
        self._cache.set(cache_key, screenshot)
        logger.debug("Cached screenshot for window size {}", window_size)
