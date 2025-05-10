from collections import deque
from pathlib import Path
import sys
import cv2
import time
import platform

import click
import numpy as np
from loguru import logger
from diskcache import Cache

from raid_autoupgrade.progress_bar import get_progress_bar_state
from raid_autoupgrade.interaction import (
    take_screenshot_of_window,
    window_exists,
    click_region_center,
    select_region_with_prompt,
)
from raid_autoupgrade.network import NetworkManager

# from raid_autoupgrade.utils import get_timestamp
from raid_autoupgrade.utils import get_timestamp
from raid_autoupgrade.visualization import (
    get_roi_from_screenshot,
    show_regions_in_image,
)


# TODO: Look into screenshot and click of inactive window
# https://stackoverflow.com/questions/19695214/screenshot-of-inactive-window-printwindow-win32gui/24352388#24352388
# https://www.reddit.com/r/AutoHotkey/comments/1btj6jx/i_need_help_in_trying_to_click_a_window_without/
# https://stackoverflow.com/questions/32846550/python-control-window-with-pywinauto-while-the-window-is-minimized-or-hidden/32847266#32847266


def count_upgrade_fails(
    window_title: str,
    upgrade_bar_region: tuple[int, int, int, int],
    upgrade_button_region: tuple[int, int, int, int],
    max_fails: int = 99,
    check_interval: float = 0.025,
    screenshot_dir: str = None,
) -> int:
    """
    Assumptions:
        * Raid window is in the upgrade section of a piece of equipment.

    Start upgrade and count the number of upgrade fails by counting the number
    of times the upgrade bar changes color to red.

    Args:
        window_title (str): Title of the window to monitor
        upgrade_bar_region (tuple): Region coordinates (left, top, width, height) relative to the window
        upgrade_button_region (tuple): Region coordinates (left, top, width, height) relative to the window
        max_fails (int, optional): Maximum number of fails to count before stopping. Defaults to 99.
        check_interval (float, optional): Time between checks in seconds. Defaults to 0.2.

    Returns:
        int: Number of fails detected

    Note:
        The function will stop monitoring if:
        - The maximum number of fails is reached
        - The upgrade bar stays in 'standby' state for 5 consecutive checks
        - The upgrade bar stays in 'connection_error' state for 5 consecutive checks
        - The upgrade bar stays in 'unknown' state for 5 consecutive checks
        - The user presses 'q' to stop monitoring
    """
    n_fails = 0
    current_state = None
    last_state = None
    max_equal_states = 4
    last_n_states = deque(maxlen=max_equal_states)

    logger.info("Starting to monitor upgrade bar color changes...")
    logger.info("Press 'q' to stop monitoring")

    # Click the upgrade level to start monitoring
    logger.info("Clicking upgrade button")
    click_region_center(window_title, upgrade_button_region)

    # Count the number of fails until the max is reached or the piece has been
    # upgraded.
    while n_fails < max_fails:
        screenshot = take_screenshot_of_window(window_title, screenshot_dir)
        upgrade_bar = get_roi_from_screenshot(screenshot, upgrade_bar_region)

        current_state = get_progress_bar_state(upgrade_bar)
        # logger.info(f"Current state: {current_state}")

        if last_state != current_state and current_state == "fail":
            n_fails += 1
            logger.info(
                f"{last_state} -> {current_state} (Total: {n_fails}  Max: {max_fails})"
            )
            # cv2.imwrite(f"upgrade_bar_{current_state}_{get_timestamp()}.png", upgrade_bar)

        if n_fails == max_fails:
            logger.info("Max fails reached. Clicking cancel upgrade.")
            click_region_center(window_title, upgrade_button_region)

        last_n_states.append(current_state)
        last_state = last_n_states[-1]

        # Check for 'q' key press
        if cv2.waitKey(1) & 0xFF == ord("q"):
            logger.info("Monitoring stopped by user")
            break

        # If the ugrade has been completed, there will only be a black bar.
        if len(last_n_states) >= max_equal_states and np.all(
            np.array(last_n_states) == "standby"
        ):
            logger.info(f"Standby for the last {max_equal_states} checks")
            break

        # When a connection error occurs we have completed an upgrade while
        # having internet turned off.
        if len(last_n_states) >= max_equal_states and np.all(
            np.array(last_n_states) == "connection_error"
        ):
            logger.info(f"connection error for the last {max_equal_states} checks")
            break

        if len(last_n_states) >= max_equal_states and np.all(
            np.array(last_n_states) == "unknown"
        ):
            logger.info(f"unknown state for the last {max_equal_states} checks")
            break

        time.sleep(check_interval)

    logger.info(f"Finished monitoring. Detected {n_fails} fails.")
    return n_fails


def select_upgrade_regions(screenshot: np.ndarray):
    """Select regions for upgrade bar and button.

    Assumptions:
        * Raid window is in the upgrade section of a piece of equipment.

    Args:
        screenshot (np.ndarray): Screenshot of the Raid window

    Returns:
        dict: Dictionary containing the selected regions
    """
    regions = {}
    region_prompts = {
        "upgrade_bar": "Click and drag to select upgrade bar",
        "upgrade_button": "Click and drag to select upgrade button",
        # "icon": "Click and drag to select icon",
    }

    logger.info("Selecting new regions")
    # TODO: consider using pyautogui.locateOnScreen('calc7key.png')
    for name, prompt in region_prompts.items():
        region = select_region_with_prompt(screenshot, prompt)
        regions[name] = region

    return regions


@click.group()
@click.option(
    "--save-screenshots",
    "-s",
    is_flag=True,
    default=False,
    help="Save screenshots to cache directory",
)
def raid_autoupgrade(save_screenshots: bool):
    """Raid: Shadow Legends auto-upgrade tool.

    This tool helps automate the process of upgrading equipment in Raid: Shadow Legends
    by monitoring upgrade attempts.


    """

    # Create cache directory
    cache_dir = Path("cache-raid-autoupgrade")
    cache_dir.mkdir(exist_ok=True)

    # Initialize cache
    cache = Cache(str(cache_dir))

    # Store cache in context
    ctx = click.get_current_context()
    ctx.obj = {"cache": cache, "cache_dir": cache_dir}

    if save_screenshots:
        logger.info(f"Saving screenshots to {cache_dir}")
        ctx.obj["screenshot_dir"] = cache_dir
    else:
        ctx.obj["screenshot_dir"] = None


@raid_autoupgrade.command()
@click.option(
    "--network-adapter-id",
    "-n",
    type=int,
    multiple=True,
    help="Enable network management on adapters with given ids",
)
@click.option(
    "--max-fails",
    "-f",
    type=int,
    default=99,
    help="Maximum number of fails to count before stopping.",
)
def count(network_adapter_id: list[int], max_fails: int):
    """Count the number of upgrade fails and stop when the max number of fails is reached.

    Use network adapter ids to enable automatically turning network off and on.
    Use ids from the output of the `network list` command.

    NOTE: one more upgrade than specified might occur due to timing issues.
    """
    # Check if we can find the Raid window
    window_title = "Raid: Shadow Legends"
    if not window_exists(window_title):
        logger.warning("Raid window not found. Check if Raid is running.")
        sys.exit(1)

    # Take screenshot
    ctx = click.get_current_context()
    screenshot_dir = ctx.obj["screenshot_dir"]

    screenshot = take_screenshot_of_window(window_title, screenshot_dir)
    window_size = [screenshot.shape[0], screenshot.shape[1]]

    # Get cache from context
    ctx = click.get_current_context()
    cache = ctx.obj["cache"]

    # Create a cache key based on window size
    cache_key_regions = f"regions_{window_size[0]}_{window_size[1]}"
    cache_key_screenshot = f"screenshot_{window_size[0]}_{window_size[1]}"

    # Try to get cached regions
    regions = cache.get(cache_key_regions)
    if regions is None:
        regions = select_upgrade_regions(screenshot)
        cache.set(cache_key_regions, regions)
        cache.set(cache_key_screenshot, screenshot)
    else:
        logger.info("Using cached regions")

    # TODO: add a region validation based on the color of the regions

    # TODO: add network management
    # if network_adapter_id:
    # manager = NetworkManager()
    # manager.toggle_adapter(network_adapter_id, True)

    # Count upgrades until levelup or fails have been reaced
    n_fails = count_upgrade_fails(
        window_title,
        regions["upgrade_bar"],
        regions["upgrade_button"],
        max_fails,
        screenshot_dir,
    )
    logger.info(f"Detected {n_fails} fails")


@raid_autoupgrade.command()
@click.option(
    "--save-image",
    "-s",
    is_flag=True,
    default=False,
    help="Save image with regions to cache directory",
)
def show_regions(save_image: bool):
    """Show the currently cached regions and screenshot."""
    # Check if we can find the Raid window
    window_title = "Raid: Shadow Legends"
    if not window_exists(window_title):
        logger.warning("Raid window not found. Check if Raid is running.")
        sys.exit(1)

    screenshot = take_screenshot_of_window(window_title)
    window_size = [screenshot.shape[0], screenshot.shape[1]]

    # Get cache from context
    ctx = click.get_current_context()
    cache = ctx.obj["cache"]

    # Create a cache key based on window size
    cache_key_regions = f"regions_{window_size[0]}_{window_size[1]}"
    cache_key_screenshot = f"screenshot_{window_size[0]}_{window_size[1]}"

    # Try to get cached regions
    regions = cache.get(cache_key_regions)
    screenshot = cache.get(cache_key_screenshot)
    if regions is None:
        logger.error(
            "No cached regions found for current window size. Run count command first to cache regions."
        )
        sys.exit(1)

    logger.info("Showing cached regions")

    ctx = click.get_current_context()
    image = show_regions_in_image(screenshot, regions)

    output_dir = ctx.obj["cache_dir"]
    if save_image:
        output_path = Path(output_dir) / f"{get_timestamp()}_image_with_regions.png"
        logger.info(f"Saving image with regions to {output_path}")
        cv2.imwrite(output_path, image)


@raid_autoupgrade.command()
def select_regions():
    """Select and cache regions for upgrade bar and button.

    This command allows you to manually select the regions for the upgrade bar and button.
    The selected regions will be cached for future use.
    """
    # Check if we can find the Raid window
    window_title = "Raid: Shadow Legends"
    if not window_exists(window_title):
        logger.warning("Raid window not found. Check if Raid is running.")
        sys.exit(1)

    ctx = click.get_current_context()
    screenshot_dir = ctx.obj["screenshot_dir"]

    screenshot = take_screenshot_of_window(window_title, screenshot_dir)
    window_size = [screenshot.shape[0], screenshot.shape[1]]

    # Get cache from context
    ctx = click.get_current_context()
    cache = ctx.obj["cache"]

    # Create cache keys
    cache_key_regions = f"regions_{window_size[0]}_{window_size[1]}"
    cache_key_screenshot = f"screenshot_{window_size[0]}_{window_size[1]}"

    # Select new regions
    regions = select_upgrade_regions(screenshot)

    # Cache the regions and screenshot
    cache.set(cache_key_regions, regions)
    cache.set(cache_key_screenshot, screenshot)

    logger.info("Regions selected and cached successfully")
    logger.info("You can now use the count or show-regions commands")


@raid_autoupgrade.group()
def network():
    """Manage network adapters for the airplane mode trick."""
    pass


@network.command()
def list():
    """List all network adapters."""
    if not platform.system() == "Windows":
        logger.error("This command only works on Windows")
        sys.exit(1)

    manager = NetworkManager()
    adapters = manager.get_adapters()
    manager.display_adapters(adapters)


@network.command()
@click.argument("adapter", required=False)
def disable(adapter: str | None):
    """Disable selected network adapters.

    If ADAPTER is provided, it will try to find and disable that specific adapter.
    Otherwise, it will prompt you to select adapters interactively.
    """
    if not platform.system() == "Windows":
        logger.error("This command only works on Windows")
        sys.exit(1)

    manager = NetworkManager()
    if adapter:
        adapters = manager.get_adapters()
        found_adapter = manager.find_adapter(adapters, adapter)
        if not found_adapter:
            logger.error(f"No adapter found matching: {adapter}")
            sys.exit(1)
        if manager.toggle_adapter(found_adapter.id, False):
            logger.info(f"Successfully disabled adapter: {found_adapter.name}")
        else:
            logger.error(f"Failed to disable adapter: {found_adapter.name}")
    else:
        manager.toggle_selected_adapters(False)


@network.command()
@click.argument("adapter", required=False)
def enable(adapter: str | None):
    """Enable selected network adapters.

    If ADAPTER is provided, it will try to find and enable that specific adapter.
    Otherwise, it will prompt you to select adapters interactively.
    """
    if not platform.system() == "Windows":
        logger.error("This command only works on Windows")
        sys.exit(1)

    manager = NetworkManager()
    if adapter:
        adapters = manager.get_adapters()
        found_adapter = manager.find_adapter(adapters, adapter)
        if not found_adapter:
            logger.error(f"No adapter found matching: {adapter}")
            sys.exit(1)
        if manager.toggle_adapter(found_adapter.id, True):
            logger.info(f"Successfully enabled adapter: {found_adapter.name}")
        else:
            logger.error(f"Failed to enable adapter: {found_adapter.name}")
    else:
        manager.toggle_selected_adapters(True)


if __name__ == "__main__":
    raid_autoupgrade()
