import json
from pathlib import Path
import time
from enum import Enum

import cv2
import numpy as np
from loguru import logger
from diskcache import Cache

from autoraid.autoupgrade.state_machine import (
    UpgradeStateMachine,
    StopCountReason as NewStopCountReason,
)
from autoraid.interaction import (
    select_region_with_prompt,
)
from autoraid.autoupgrade.locate_upgrade_region import (
    locate_instant_upgrade_tickbox,
    locate_upgrade_button,
    locate_progress_bar,
    locate_artifact_icon,
)
from autoraid.locate import MissingRegionException
from autoraid.utils import get_timestamp
from autoraid.services.cache_service import CacheService
from autoraid.services.screenshot_service import ScreenshotService


# TODO: Look into screenshot and click of inactive window
# https://stackoverflow.com/questions/19695214/screenshot-of-inactive-window-printwindow-win32gui/24352388#24352388
# https://www.reddit.com/r/AutoHotkey/comments/1btj6jx/i_need_help_in_trying_to_click_a_window_without/
# https://stackoverflow.com/questions/32846550/python-control-window-with-pywinauto-while-the-window-is-minimized-or-hidden/32847266#32847266


class StopCountReason(Enum):
    MAX_FAILS = "max_fails"
    UPGRADED = "upgraded"
    UNKNOWN = "unknown"
    STANDBY = "standby"
    POPUP = "popup"
    CONNECTION_ERROR = "connection_error"


def count_upgrade_fails(
    window_title: str,
    upgrade_bar_region: tuple[int, int, int, int],
    max_attempts: int = 99,
    check_interval: float = 0.25,
    debug_dir: Path | None = None,
) -> tuple[int, StopCountReason]:
    """
    Assumptions:
        * Raid window is in the upgrade section of a piece of equipment.

    Start upgrade and count the number of upgrade fails by counting the number
    of times the upgrade bar changes color to red.

    Args:
        window_title (str): Title of the window to monitor
        upgrade_bar_region (tuple): Region coordinates (left, top, width, height) relative to the window
        max_attempts (int, optional): Maximum number of upgrade attempts to count before stopping. Defaults to 98.
        check_interval (float, optional): Time between checks in seconds. Defaults to 0.25.
        debug_dir (Path | None, optional): Directory to save debug screenshots. Defaults to None.

    Returns:
        tuple[int, StopCountReason]: Number of fails detected and reason for stopping

    Note:
        The function will stop monitoring if:
        - The maximum number of fails is reached
        - The upgrade bar stays in 'standby' state for 4 consecutive checks
        - The upgrade bar stays in 'connection_error' state for 4 consecutive checks
        - The upgrade bar stays in 'unknown' state for 4 consecutive checks
    """
    # Create state machine for tracking upgrade attempts
    state_machine = UpgradeStateMachine(max_attempts=max_attempts)

    debug_metadata = {
        "upgrade_bar_region": upgrade_bar_region,
        "timestamp": [],
        "current_state": {},
        "n_fails": {},
    }
    debug_screenshots = {}
    debug_upgrade_bar_rois = {}

    logger.info("Starting to monitor upgrade bar color changes...")

    # Count the number of fails until the max is reached or stop condition met
    # Create temporary screenshot service instance (will be injected in Phase 6)
    screenshot_service = ScreenshotService()

    stop_reason = None
    while stop_reason is None:
        screenshot = screenshot_service.take_screenshot(window_title)
        upgrade_bar = screenshot_service.extract_roi(screenshot, upgrade_bar_region)

        # Process frame using state machine
        n_fails, stop_reason = state_machine.process_frame(upgrade_bar)

        # Store debug information
        timestamp = get_timestamp()
        debug_screenshots[timestamp] = screenshot
        debug_upgrade_bar_rois[timestamp] = upgrade_bar
        debug_metadata["timestamp"].append(timestamp)
        debug_metadata["n_fails"][timestamp] = n_fails
        if len(state_machine.recent_states) > 0:
            current_state = state_machine.recent_states[-1].value
            debug_metadata["current_state"][timestamp] = current_state

        time.sleep(check_interval)

    # Save debug data if debug_dir specified
    if debug_dir is not None:
        output_dir = debug_dir / "count_upgrade_fails"
        output_dir.mkdir(exist_ok=True)
        logger.debug(f"Saving count_upgrade_fails debug data to {output_dir}")
        for timestamp in debug_metadata["timestamp"]:
            current_state = debug_metadata["current_state"].get(timestamp, "unknown")
            cv2.imwrite(
                output_dir / f"{timestamp}_{current_state}_screenshot.png",
                debug_screenshots[timestamp],
            )

            cv2.imwrite(
                output_dir / f"{timestamp}_{current_state}_upgrade_bar_roi.png",
                debug_upgrade_bar_rois[timestamp],
            )

        with open(output_dir / "debug_metadata.json", "w") as f:
            json.dump(debug_metadata, f)

    logger.info(f"Finished counting. Detected {n_fails} fails.")

    # Map new StopCountReason to old StopCountReason for backward compatibility
    old_reason = _map_stop_reason(stop_reason)
    return n_fails, old_reason


def _map_stop_reason(new_reason: NewStopCountReason) -> StopCountReason:
    """Map new state machine StopCountReason to old StopCountReason for backward compatibility.

    Args:
        new_reason: New StopCountReason from state machine

    Returns:
        Old StopCountReason for CLI compatibility
    """
    mapping = {
        NewStopCountReason.UPGRADED: StopCountReason.UPGRADED,
        NewStopCountReason.CONNECTION_ERROR: StopCountReason.CONNECTION_ERROR,
        NewStopCountReason.MAX_ATTEMPTS_REACHED: StopCountReason.MAX_FAILS,
    }
    return mapping.get(new_reason, StopCountReason.UNKNOWN)


def select_upgrade_regions(screenshot: np.ndarray, manual: bool = False):
    """
    Select regions for upgrade bar and button. Will by default try to find
    upgrade button automatically.

    Args:
        screenshot (np.ndarray): Screenshot of the Raid upgrade window
        manual (bool, optional): If True, prompt user to select all regions. Defaults to False.
    Returns:
        dict: Dictionary containing the selected regions
    """
    regions = {}
    region_prompts = {
        "upgrade_bar": "Click and drag to select upgrade bar",
        "upgrade_button": "Click and drag to select upgrade button",
        "artifact_icon": "Click and drag to select artifact icon",
        "instant_upgrade_tickbox": "Click and drag to select instant upgrade tickbox",
    }
    locate_funcs = {
        "upgrade_button": locate_upgrade_button,
        "upgrade_bar": locate_progress_bar,
        "artifact_icon": locate_artifact_icon,
        "instant_upgrade_tickbox": locate_instant_upgrade_tickbox,
    }

    logger.info("Selecting upgrade regions")

    failed_prompts = {}
    if not manual:
        for name, prompt in region_prompts.items():
            try:
                logger.info(f"Automatic selection of {name}")
                regions[name] = locate_funcs[name](screenshot)
            except MissingRegionException:
                logger.warning(f"Failed to locate {name}. Scheduling manual input.")
                failed_prompts[name] = prompt

    regions_to_get_manually = region_prompts if manual else failed_prompts
    if manual or len(regions_to_get_manually) > 0:
        logger.info(f"select {list(regions_to_get_manually.keys())} manually")
        for name, prompt in regions_to_get_manually.items():
            region = select_region_with_prompt(screenshot, prompt)
            regions[name] = region

    return regions


def create_cache_key_regions(window_size: tuple[int, int]) -> str:
    """Create a cache key for the regions based on the window size.

    Deprecated: Use CacheService.create_regions_key instead.
    This function is kept for backward compatibility with CLI code.
    """
    return CacheService.create_regions_key(window_size)


def create_cache_key_screenshot(window_size: tuple[int, int]) -> str:
    """Create a cache key for the screenshot based on the window size.

    Deprecated: Use CacheService.create_screenshot_key instead.
    This function is kept for backward compatibility with CLI code.
    """
    return CacheService.create_screenshot_key(window_size)


def get_cached_regions(window_size: tuple[int, int], cache: Cache) -> dict:
    """Get cached regions for the current window size.

    Deprecated: Use CacheService.get_regions instead.
    This function is kept for backward compatibility with CLI code.
    """
    cache_service = CacheService(cache)
    return cache_service.get_regions(window_size)


def get_cached_screenshot(window_size: tuple[int, int], cache: Cache) -> np.ndarray:
    """Get cached screenshot for the current window size.

    Deprecated: Use CacheService.get_screenshot instead.
    This function is kept for backward compatibility with CLI code.
    """
    cache_service = CacheService(cache)
    return cache_service.get_screenshot(window_size)


def get_regions(screenshot: np.ndarray, cache: Cache) -> dict:
    """Get cached regions for the current window size or prompt user to select new ones.

    Args:
        screenshot (np.ndarray): Screenshot of the Raid window
        cache (Cache): Cache object to store/retrieve regions

    Returns:
        dict: Dictionary containing the selected regions
    """
    cache_service = CacheService(cache)
    window_size = (screenshot.shape[0], screenshot.shape[1])

    # Try to get cached regions
    regions = cache_service.get_regions(window_size)
    if regions is None:
        regions = select_upgrade_regions(screenshot)
        cache_service.set_regions(window_size, regions)
        cache_service.set_screenshot(window_size, screenshot)
    else:
        logger.info("Using cached regions")

    return regions
