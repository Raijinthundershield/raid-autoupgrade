import json
import click
from pathlib import Path
import time
import sys
import cv2
from loguru import logger

from autoraid.interaction import (
    click_region_center,
    take_screenshot_of_window,
    window_exists,
)
from autoraid.network import NetworkManager
from autoraid.autoupgrade.autoupgrade import (
    StopCountReason,
    count_upgrade_fails,
    get_regions,
    select_upgrade_regions,
)
from autoraid.utils import get_timestamp
from autoraid.visualization import show_regions_in_image


@click.group()
def upgrade():
    """Raid: Shadow Legends auto-upgrade tool.

    This tool helps automate the process of upgrading equipment in Raid: Shadow Legends
    by monitoring upgrade attempts.

    """


@upgrade.command()
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
    manager.toggle_adapters(network_adapter_id, enable=False)
    for _ in range(3):
        logger.info("Waiting for network to turn off.")
        time.sleep(1)
        if not manager.check_network_access():
            break
    else:
        logger.warning("Failed to turn off network. Aborting.")
        sys.exit(1)

    try:
        # Take screenshot
        ctx = click.get_current_context()
        screenshot = take_screenshot_of_window(window_title)
        regions = get_regions(screenshot, ctx.obj["cache"])

        debug_dir = ctx.obj["debug_dir"]
        if ctx.obj["debug"]:
            output_dir = debug_dir / "count"
            output_dir.mkdir(exist_ok=True)

            timestamp = get_timestamp()
            cv2.imwrite(output_dir / f"{timestamp}_screenshot.png", screenshot)
            with open(output_dir / f"{timestamp}_regions.json", "w") as f:
                json.dump(regions, f)

        # Click the upgrade level to start upgrading
        logger.info("Clicking upgrade button")
        click_region_center(window_title, regions["upgrade_button"])

        # Count upgrades until levelup or fails have been reaced
        n_fails, reason = count_upgrade_fails(
            window_title=window_title,
            upgrade_bar_region=regions["upgrade_bar"],
            max_attempts=99,
            debug_dir=debug_dir,
        )

        # Wait for Raid to reach connection timeout before enabling network.
        time.sleep(3)
    finally:
        manager.toggle_adapters(network_adapter_id, enable=True)

    logger.info(f"Detected {n_fails} fails. Stop reason: {reason}")


@upgrade.command()
@click.option(
    "--max-attempts",
    "-m",
    type=int,
    required=True,
    help="Maximum number of upgrade attempts to count before stopping.",
)
@click.option(
    "--continue-upgrade",
    "-c",
    is_flag=True,
    help="Continue upgrading after reaching an upgrade. Only use if the piece is level 10.",
)
def spend(max_attempts: int, continue_upgrade: bool):
    """
    Upgrade the piece until the max number of fails is reached.
    """

    ctx = click.get_current_context()
    debug_dir = ctx.obj["debug_dir"]

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
    screenshot = take_screenshot_of_window(window_title)
    regions = get_regions(screenshot, ctx.obj["cache"])

    debug_dir = ctx.obj["debug_dir"]
    if ctx.obj["debug"]:
        output_dir = debug_dir / "upgrade"
        output_dir.mkdir(exist_ok=True)

        timestamp = get_timestamp()
        cv2.imwrite(output_dir / f"{timestamp}_screenshot.png", screenshot)
        with open(output_dir / f"{timestamp}_regions.json", "w") as f:
            json.dump(regions, f)

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
            debug_dir=debug_dir,
        )
        n_attempts += n_fails

        if reason == StopCountReason.MAX_FAILS:
            logger.info(
                f"Reached max attempts at {n_attempts} upgrade attempts. Cancelling upgrade."
            )
            click_region_center(window_title, regions["upgrade_button"])

        elif reason == StopCountReason.UPGRADED:
            n_attempts += 1
            n_upgrades += 1
            logger.info(f"Piece upgraded at {n_attempts} upgrade attempts.")

        if continue_upgrade and n_upgrades == 1 and n_attempts < max_attempts:
            upgrade = True
            logger.info("Continue upgrade.")

    logger.info(
        f"Total upgrade attempts: {n_attempts}. There are {max_attempts - n_attempts} left."
    )


# TODO:
# - Don't take a screenshot, but rather use cached screenshot
# - change get_regions get_cached_regions
@upgrade.command()
@click.option(
    "--save-image",
    "-s",
    is_flag=True,
    default=False,
    help="Save image with regions to cache directory",
)
def check_regions(save_image: bool):
    """Show the currently cached regions within a screenshot of the current window"""
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
        output_path = (
            Path(output_dir)
            / "show_regions"
            / f"{get_timestamp()}_image_with_regions.png"
        )
        logger.info(f"Saving image with regions to {output_path}")
        cv2.imwrite(output_path, image)


@upgrade.command()
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
