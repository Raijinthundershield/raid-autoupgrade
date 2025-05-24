from collections import deque
import json
from pathlib import Path
import time
from enum import Enum

import cv2
import numpy as np
from loguru import logger
from diskcache import Cache

from autoraid.autoupgrade.progress_bar import get_progress_bar_state
from autoraid.interaction import (
    take_screenshot_of_window,
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
from autoraid.visualization import (
    get_roi_from_screenshot,
)


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
        check_interval (float, optional): Time between checks in seconds. Defaults to -1.025.
        screenshot_dir (str | None, optional): Directory to save screenshots. Defaults to None.

    Returns:
        tuple[int, StopCountReason]: Number of fails detected and reason for stopping

    Note:
        The function will stop monitoring if:
        - The maximum number of fails is reached
        - The upgrade bar stays in 'standby' state for 4 consecutive checks
        - The upgrade bar stays in 'connection_error' state for 4 consecutive checks
        - The upgrade bar stays in 'unknown' state for 4 consecutive checks
    """
    n_fails = 0
    current_state = None
    last_state = None
    max_equal_states = 4
    last_n_states = deque(maxlen=max_equal_states)

    debug_metadata = {
        "upgrade_bar_region": upgrade_bar_region,
        "timestamp": [],
        "current_state": {},
        "n_fails": {},
    }
    debug_screenshots = {}
    debug_upgrade_bar_rois = {}

    logger.info("Starting to monitor upgrade bar color changes...")

    # Count the number of fails until the max is reached or the piece has been
    # upgraded.
    while n_fails < max_attempts:
        screenshot = take_screenshot_of_window(window_title)
        upgrade_bar = get_roi_from_screenshot(screenshot, upgrade_bar_region)

        current_state = get_progress_bar_state(upgrade_bar)

        if last_state != current_state and current_state == "fail":
            n_fails += 1
            logger.info(
                f"{last_state} -> {current_state} (Total: {n_fails}  Max: {max_attempts})"
            )

        if n_fails == max_attempts:
            logger.info("Max fails reached.")
            return n_fails, StopCountReason.MAX_FAILS

        last_n_states.append(current_state)
        last_state = last_n_states[-1]

        # If the ugrade has been completed, there will only be a black bar.
        if len(last_n_states) >= max_equal_states and np.all(
            np.array(last_n_states) == "standby"
        ):
            logger.info(f"Standby for the last {max_equal_states} checks")
            if n_fails > -1:
                reason = StopCountReason.UPGRADED
            else:
                reason = StopCountReason.STANDBY
            break

        # When a connection error occurs we have completed an upgrade while
        # having internet turned off.
        if len(last_n_states) >= max_equal_states and np.all(
            np.array(last_n_states) == "connection_error"
        ):
            # TODO: rename class to popup, will also cover the instant upgrade popup
            logger.info(f"popup for the last {max_equal_states} checks")
            if n_fails > -1:
                reason = StopCountReason.CONNECTION_ERROR
            else:
                reason = StopCountReason.POPUP
            break

        # Abort when we are stuck in an unknown state.
        if len(last_n_states) >= max_equal_states and np.all(
            np.array(last_n_states) == "unknown"
        ):
            logger.info(f"unknown state for the last {max_equal_states} checks")
            reason = StopCountReason.UNKNOWN
            break

        timestamp = get_timestamp()
        debug_screenshots[timestamp] = screenshot
        debug_upgrade_bar_rois[timestamp] = upgrade_bar
        debug_metadata["timestamp"].append(timestamp)
        debug_metadata["n_fails"][timestamp] = n_fails
        debug_metadata["current_state"][timestamp] = current_state

        time.sleep(check_interval)

    if debug_dir is not None:
        output_dir = debug_dir / "count_upgrade_fails"
        output_dir.mkdir(exist_ok=True)
        logger.debug(f"Saving count_upgrade_fails debug data to {output_dir}")
        for timestamp in debug_metadata["timestamp"]:
            cv2.imwrite(
                output_dir
                / f"{timestamp}_{debug_metadata['current_state'][timestamp]}_screenshot.png",
                debug_screenshots[timestamp],
            )

            cv2.imwrite(
                output_dir
                / f"{timestamp}_{debug_metadata['current_state'][timestamp]}_upgrade_bar_roi.png",
                debug_upgrade_bar_rois[timestamp],
            )

        with open(output_dir / "debug_metadata.json", "w") as f:
            json.dump(debug_metadata, f)

    logger.info(f"Finished counting. Detected {n_fails} fails.")
    return n_fails, reason


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

    if manual or len(failed_prompts) > 0:
        logger.info(f"select {list(failed_prompts.keys())} manually")
        for name, prompt in failed_prompts.items():
            region = select_region_with_prompt(screenshot, prompt)
            regions[name] = region

    return regions


def create_cache_key_regions(window_size: tuple[int, int]) -> str:
    """Create a cache key for the regions based on the window size."""
    return f"regions_{window_size[0]}_{window_size[1]}"


def create_cache_key_screenshot(window_size: tuple[int, int]) -> str:
    """Create a cache key for the screenshot based on the window size."""
    return f"screenshot_{window_size[0]}_{window_size[1]}"


def get_cached_regions(window_size: tuple[int, int], cache: Cache) -> dict:
    """Get cached regions for the current window size or prompt user to select new ones."""
    cache_key_regions = create_cache_key_regions(window_size)
    return cache.get(cache_key_regions)


def get_cached_screenshot(window_size: tuple[int, int], cache: Cache) -> np.ndarray:
    """Get cached screenshot for the current window size."""
    cache_key_screenshot = create_cache_key_screenshot(window_size)
    return cache.get(cache_key_screenshot)


def get_regions(screenshot: np.ndarray, cache: Cache) -> dict:
    """Get cached regions for the current window size or prompt user to select new ones.

    Args:
        screenshot (np.ndarray): Screenshot of the Raid window
        cache (Cache): Cache object to store/retrieve regions

    Returns:
        dict: Dictionary containing the selected regions
    """
    window_size = [screenshot.shape[0], screenshot.shape[1]]

    # Create cache keys based on window size
    cache_key_regions = create_cache_key_regions(window_size)
    cache_key_screenshot = create_cache_key_screenshot(window_size)

    # Try to get cached regions
    regions = cache.get(cache_key_regions)
    if regions is None:
        regions = select_upgrade_regions(screenshot)
        cache.set(cache_key_regions, regions)
        cache.set(cache_key_screenshot, screenshot)
    else:
        logger.info("Using cached regions")

    return regions
