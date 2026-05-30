"""Service for locating and managing UI regions in the Raid window."""

from loguru import logger

from raid_autoupgrade.detection.locate_region import (
    MissingRegionException,
    locate_progress_bar,
    locate_upgrade_button,
)
from raid_autoupgrade.protocols import CacheProtocol, ScreenshotProtocol

import numpy as np


class LocateRegionService:
    """Service for region detection.

    Responsibilities:
    - Locate UI regions automatically via template matching
    - Cache regions per window size
    """

    def __init__(
        self, cache_service: CacheProtocol, screenshot_service: ScreenshotProtocol
    ) -> None:
        logger.debug("Initializing")
        self._cache_service = cache_service
        self._screenshot_service = screenshot_service

    def get_regions(
        self, screenshot: np.ndarray, override_cache: bool = False
    ) -> dict[str, tuple[int, int, int, int]] | None:
        """Return cached regions, or attempt auto-detection.

        Returns None if no cached regions and auto-detection fails.
        """
        logger.info("Getting regions")

        window_size = (screenshot.shape[0], screenshot.shape[1])

        if not override_cache:
            regions = self._cache_service.get_regions(window_size)
            if regions is not None:
                return regions

        return self._try_automatic_detection(screenshot)

    def _try_automatic_detection(
        self, screenshot: np.ndarray
    ) -> dict[str, tuple[int, int, int, int]] | None:
        logger.info("Attempting automatic detection")

        locate_funcs = {
            "upgrade_button": locate_upgrade_button,
            "upgrade_bar": locate_progress_bar,
        }

        regions = {}
        for name, fn in locate_funcs.items():
            try:
                regions[name] = fn(screenshot)
            except MissingRegionException:
                logger.warning(f"Failed to locate {name}")
                return None

        logger.info("Automatic detection successful")
        return regions
