"""Service for locating and managing UI regions in the Raid window.

This service handles:
- Automatic region detection using computer vision
- Manual region selection when automatic detection fails
- Caching of regions per window size
- Integration with CacheService and ScreenshotService
"""

import numpy as np
from loguru import logger

from autoraid.services.cache_service import CacheService
from autoraid.services.screenshot_service import ScreenshotService
from autoraid.autoupgrade.locate_upgrade_region import (
    locate_upgrade_button,
    locate_progress_bar,
)
from autoraid.locate import MissingRegionException
from autoraid.interaction import select_region_with_prompt


class LocateRegionService:
    """Service for region detection and selection.

    Responsibilities:
    - Locate UI regions automatically or manually
    - Cache regions per window size
    - Orchestrate cache checking, auto-detection, and manual fallback
    """

    def __init__(
        self, cache_service: CacheService, screenshot_service: ScreenshotService
    ) -> None:
        """Initialize LocateRegionService with dependencies.

        Args:
            cache_service: Service for caching regions
            screenshot_service: Service for screenshot operations
        """
        logger.debug("[LocateRegionService] Initializing")
        self._cache_service = cache_service
        self._screenshot_service = screenshot_service

    def get_regions(
        self, screenshot: np.ndarray, manual: bool = False
    ) -> dict[str, tuple[int, int, int, int]]:
        """Get regions for upgrade UI elements.

        Flow: check cache → auto-detect → manual fallback → cache result

        Args:
            screenshot: Screenshot of the Raid window
            manual: If True, skip automatic detection and prompt for manual selection

        Returns:
            Dictionary mapping region names to (left, top, width, height) tuples
        """
        logger.info("[LocateRegionService] Getting regions")
        window_size = (screenshot.shape[0], screenshot.shape[1])

        # Try to get cached regions
        if not manual:
            cached_regions = self._cache_service.get_regions(window_size)
            if cached_regions is not None:
                logger.info("[LocateRegionService] Using cached regions")
                return cached_regions

        # Try automatic detection if not manual mode
        regions = None
        if not manual:
            regions = self._try_automatic_detection(screenshot)

        # Fall back to manual selection if automatic detection failed or manual mode
        if regions is None:
            regions = self._manual_selection(screenshot)

        # Cache the regions and screenshot
        self._cache_service.set_regions(window_size, regions)
        self._cache_service.set_screenshot(window_size, screenshot)

        return regions

    def _try_automatic_detection(
        self, screenshot: np.ndarray
    ) -> dict[str, tuple[int, int, int, int]] | None:
        """Try to automatically detect all required regions.

        Args:
            screenshot: Screenshot of the Raid window

        Returns:
            Dictionary of regions if all detected successfully, None otherwise
        """
        logger.info("[LocateRegionService] Attempting automatic detection")

        region_prompts = {
            "upgrade_bar": "Click and drag to select upgrade bar",
            "upgrade_button": "Click and drag to select upgrade button",
        }

        locate_funcs = {
            "upgrade_button": locate_upgrade_button,
            "upgrade_bar": locate_progress_bar,
        }

        regions = {}
        failed_regions = []

        for name, prompt in region_prompts.items():
            try:
                logger.info(f"[LocateRegionService] Automatic selection of {name}")
                regions[name] = locate_funcs[name](screenshot)
            except MissingRegionException:
                logger.warning(
                    f"[LocateRegionService] Failed to locate {name}. Will need manual input."
                )
                failed_regions.append(name)

        # If any region failed, return None to trigger full manual selection
        if failed_regions:
            logger.info(
                f"[LocateRegionService] Automatic detection failed for: {failed_regions}"
            )
            return None

        logger.info("[LocateRegionService] Automatic detection successful")
        return regions

    def _manual_selection(
        self, screenshot: np.ndarray
    ) -> dict[str, tuple[int, int, int, int]]:
        """Manually select all required regions via user prompts.

        Args:
            screenshot: Screenshot of the Raid window

        Returns:
            Dictionary of manually selected regions
        """
        logger.info("[LocateRegionService] Starting manual region selection")

        region_prompts = {
            "upgrade_bar": "Click and drag to select upgrade bar",
            "upgrade_button": "Click and drag to select upgrade button",
        }

        regions = {}
        for name, prompt in region_prompts.items():
            region = select_region_with_prompt(screenshot, prompt)
            regions[name] = region

        logger.info("[LocateRegionService] Manual selection complete")
        return regions
