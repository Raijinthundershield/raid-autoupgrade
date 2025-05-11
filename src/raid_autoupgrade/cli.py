from collections import deque
from pathlib import Path
import sys
import cv2
import time
import platform
from enum import Enum

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
    screenshot_dir: str | None = None,
) -> tuple[int, StopCountReason]:
    """
    Assumptions:
        * Raid window is in the upgrade section of a piece of equipment.

    Start upgrade and count the number of upgrade fails by counting the number
    of times the upgrade bar changes color to red.

    Args:
        window_title (str): Title of the window to monitor
        upgrade_bar_region (tuple): Region coordinates (left, top, width, height) relative to the window
        max_attempts (int, optional): Maximum number of upgrade attempts to count before stopping. Defaults to 99.
        check_interval (float, optional): Time between checks in seconds. Defaults to 0.025.
        screenshot_dir (str | None, optional): Directory to save screenshots. Defaults to None.

    Returns:
        tuple[int, StopCountReason]: Number of fails detected and reason for stopping

    Note:
        The function will stop monitoring if:
        - The maximum number of fails is reached
        - The upgrade bar stays in 'standby' state for 5 consecutive checks
        - The upgrade bar stays in 'connection_error' state for 5 consecutive checks
        - The upgrade bar stays in 'unknown' state for 5 consecutive checks
    """
    n_fails = 0
    current_state = None
    last_state = None
    max_equal_states = 4
    last_n_states = deque(maxlen=max_equal_states)

    logger.info("Starting to monitor upgrade bar color changes...")

    # Count the number of fails until the max is reached or the piece has been
    # upgraded.
    while n_fails < max_attempts:
        screenshot = take_screenshot_of_window(window_title, screenshot_dir)
        upgrade_bar = get_roi_from_screenshot(screenshot, upgrade_bar_region)

        current_state = get_progress_bar_state(upgrade_bar)

        if last_state != current_state and current_state == "fail":
            n_fails += 1
            logger.info(
                f"{last_state} -> {current_state} (Total: {n_fails}  Max: {max_attempts})"
            )

        if n_fails == max_attempts:
            logger.info("Max fails reached. Clicking cancel upgrade.")
            return n_fails, StopCountReason.MAX_FAILS

        last_n_states.append(current_state)
        last_state = last_n_states[-1]

        # If the ugrade has been completed, there will only be a black bar.
        if len(last_n_states) >= max_equal_states and np.all(
            np.array(last_n_states) == "standby"
        ):
            logger.info(f"Standby for the last {max_equal_states} checks")
            if n_fails > 0:
                return n_fails, StopCountReason.UPGRADED
            else:
                return n_fails, StopCountReason.STANDBY

        # When a connection error occurs we have completed an upgrade while
        # having internet turned off.
        if len(last_n_states) >= max_equal_states and np.all(
            np.array(last_n_states) == "connection_error"
        ):
            # TODO: rename class to popup, will also cover the instant upgrade popup
            logger.info(f"popup for the last {max_equal_states} checks")
            if n_fails > 0:
                return n_fails, StopCountReason.CONNECTION_ERROR
            else:
                return n_fails, StopCountReason.POPUP

        if len(last_n_states) >= max_equal_states and np.all(
            np.array(last_n_states) == "unknown"
        ):
            logger.info(f"unknown state for the last {max_equal_states} checks")
            return n_fails, StopCountReason.UNKNOWN

        time.sleep(check_interval)

    logger.info(f"Finished monitoring. Detected {n_fails} fails.")
    return n_fails, StopCountReason.UNKNOWN


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
    help="Network adapter ids to enable automatically turning network off and on.",
)
def count(network_adapter_id: list[int]):
    """Count the number of upgrade fails.

    Use network adapter ids to enable automatically turning network off and on.
    Use ids from the output of the `network list` command.
    """

    # Check if we can find the Raid window
    window_title = "Raid: Shadow Legends"
    if not window_exists(window_title):
        logger.warning("Raid window not found. Check if Raid is running.")
        sys.exit(1)

    # Initialize network manager and check network access
    manager = NetworkManager()
    if manager.check_network_access() and not network_adapter_id:
        logger.warning(
            "Internet access detected and netwrok id not specified. This will upgrade the piece. Aborting."
        )
        sys.exit(1)

    # Take screenshot
    ctx = click.get_current_context()
    screenshot_dir = ctx.obj["screenshot_dir"]
    screenshot = take_screenshot_of_window(window_title, screenshot_dir)

    regions = get_regions(screenshot, ctx.obj["cache"])
    manager.toggle_adapters(network_adapter_id, enable=False)

    # Click the upgrade level to start upgrading
    logger.info("Clicking upgrade button")
    click_region_center(window_title, regions["upgrade_button"])

    # Count upgrades until levelup or fails have been reaced
    n_fails, reason = count_upgrade_fails(
        window_title=window_title,
        upgrade_bar_region=regions["upgrade_bar"],
        max_attempts=99,
        screenshot_dir=screenshot_dir,
    )

    # Wait for Raid to reach connection timeout before enabling network.
    time.sleep(3)
    manager.toggle_adapters(network_adapter_id, enable=True)

    logger.info(f"Detected {n_fails} fails. Stop reason: {reason}")


@raid_autoupgrade.command()
@click.option(
    "--max-attempts",
    "-m",
    type=int,
    default=99,
    required=True,
    help="Maximum number of upgrade attempts to count before stopping.",
)
@click.option(
    "--continue-upgrade",
    "-c",
    is_flag=True,
    help="Continue upgrading after reaching an upgrade. Only use if the piece is level 10.",
)
def upgrade(max_attempts: int, continue_upgrade: bool):
    """
    Upgrade the piece until the max number of fails is reached.
    """

    # Check if we can find the Raid window
    window_title = "Raid: Shadow Legends"
    if not window_exists(window_title):
        logger.warning("Raid window not found. Check if Raid is running.")
        sys.exit(1)

    # Initialize network manager and check network access
    manager = NetworkManager()
    if not manager.check_network_access():
        logger.warning("No internet access detected. Aborting.")
        sys.exit(1)

    # Take screenshot
    ctx = click.get_current_context()
    screenshot_dir = ctx.obj["screenshot_dir"]
    screenshot = take_screenshot_of_window(window_title, screenshot_dir)

    regions = get_regions(screenshot, ctx.obj["cache"])

    upgrade = True
    n_upgrades = 0
    n_attempts = 0
    n_fails = 0  # Initialize n_fails
    while upgrade:
        upgrade = False

        logger.info("Clicking upgrade button")
        click_region_center(window_title, regions["upgrade_button"])

        # Count upgrades until levelup or fails have been reaced
        n_fails, reason = count_upgrade_fails(
            window_title=window_title,
            upgrade_bar_region=regions["upgrade_bar"],
            max_attempts=max_attempts - n_attempts,
            screenshot_dir=screenshot_dir,
        )
        n_attempts += n_fails

        if reason == StopCountReason.MAX_FAILS:
            logger.info(
                "Reached max attempts at {n_attempts} upgrade attempts. Cancelling upgrade."
            )
            click_region_center(window_title, regions["upgrade_button"])

        elif reason == StopCountReason.UPGRADED:
            n_attempts += 1
            n_upgrades += 1
            logger.info(f"Piece upgraded at {n_attempts} upgrade attempts.")

        if continue_upgrade and n_upgrades < 1 and n_attempts < max_attempts:
            upgrade = True
            logger.info("Continue upgrade.")

    logger.info(
        f"Total upgrade attempts: {n_attempts}. There are {max_attempts-n_attempts} left."
    )


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

    # Get cache from context
    ctx = click.get_current_context()
    cache = ctx.obj["cache"]

    regions = get_regions(screenshot, cache)
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
