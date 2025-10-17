import json
import click
from pathlib import Path
import time
import sys
import cv2
from loguru import logger

from autoraid.interaction import (
    click_region_center,
)
from autoraid.services.screenshot_service import ScreenshotService
from autoraid.network import NetworkManager
from autoraid.autoupgrade.autoupgrade import (
    StopCountReason,
    count_upgrade_fails,
    create_cache_key_regions,
    create_cache_key_screenshot,
    get_cached_regions,
    get_cached_screenshot,
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
@click.option(
    "--show-most-recent-gear",
    "-s",
    required=False,
    is_flag=True,
    help="Show the most recent gear piece that was counted.",
)
def count(network_adapter_id: list[int], show_most_recent_gear: bool):
    """Count the number of upgrade fails.

    Use network adapter ids to enable automatically turning network off and on.
    Use ids from the output of the `network list` command.
    """

    if show_most_recent_gear:
        logger.info("Showing the most recent gear piece that was counted.")
        ctx = click.get_current_context()
        if ctx.obj["cache"].get("current_gear_counted") is None:
            logger.warning("No gear piece has been counted yet. Aborting.")
            sys.exit(1)

        screenshot = ctx.obj["cache"].get("current_gear_counted")
        cv2.imshow("Gear", screenshot)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        sys.exit(0)

    # Check if we can find the Raid window
    # Create temporary screenshot service instance (will be injected in Phase 6)
    screenshot_service = ScreenshotService()
    window_title = "Raid: Shadow Legends"
    if not screenshot_service.window_exists(window_title):
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
        ctx = click.get_current_context()

        # Take screenshot
        screenshot = screenshot_service.take_screenshot(window_title)
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

    ctx.obj["cache"].set("current_gear_counted", screenshot)
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
    # Create temporary screenshot service instance (will be injected in Phase 6)
    screenshot_service = ScreenshotService()
    window_title = "Raid: Shadow Legends"
    if not screenshot_service.window_exists(window_title):
        logger.warning("Raid window not found. Check if Raid is running.")
        sys.exit(1)

    # Initialize network manager and check network access
    manager = NetworkManager()
    if not manager.check_network_access():
        logger.warning("No internet access detected. Aborting.")
        sys.exit(1)

    # Take screenshot
    screenshot = screenshot_service.take_screenshot(window_title)
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


@upgrade.group()
def region():
    """
    Commands for managing regions used for upgrade detection.

    These commands allow you to view, select, and manage the regions used for detecting
    the upgrade bar and button in the Raid window. The regions are cached and used by
    other commands to automate the upgrade process.
    """
    pass


@region.command("show")
@click.option(
    "--output-dir",
    "-o",
    type=str,
    default=None,
    help="Save image with regions to cache directory",
)
def regions_show(output_dir: str):
    """Show the currently cached regions within a screenshot of the current window.

    This command displays an image showing the currently cached regions for the upgrade bar
    and button. If no regions are cached for the current window size, it will exit with an error.
    Use the -o flag to save the image and regions to a directory.
    """
    # Check if we can find the Raid window
    # Create temporary screenshot service instance (will be injected in Phase 6)
    screenshot_service = ScreenshotService()
    window_title = "Raid: Shadow Legends"
    if not screenshot_service.window_exists(window_title):
        logger.warning("Raid window not found. Check if Raid is running.")
        sys.exit(1)

    # Get cache from context
    ctx = click.get_current_context()
    cache = ctx.obj["cache"]

    current_screenshot = screenshot_service.take_screenshot(window_title)
    regions = get_cached_regions(current_screenshot.shape, cache)
    screenshot = get_cached_screenshot(current_screenshot.shape, cache)

    if regions is None:
        logger.error(
            "No cached regions found for current window size. Run count command first to cache regions."
        )
        sys.exit(1)

    logger.info("Showing cached regions")

    ctx = click.get_current_context()
    screenshot_w_regions = show_regions_in_image(screenshot, regions)

    if output_dir:
        output_dir = Path(output_dir) / "region_show"
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = get_timestamp()
        region_cache_key = create_cache_key_regions(screenshot.shape)
        screenshot_cache_key = create_cache_key_screenshot(screenshot.shape)

        json_path = output_dir / f"{timestamp}-{region_cache_key}-regions.json"
        screenshot_path = (
            output_dir / f"{timestamp}-{screenshot_cache_key}-screenshot.png"
        )
        screenshot_w_regions_path = (
            output_dir
            / f"{timestamp}-{screenshot_cache_key}-screenshot_with_regions.png"
        )
        rois = {
            name: screenshot_service.extract_roi(screenshot, region)
            for name, region in regions.items()
        }
        roi_paths = {
            name: output_dir / f"{timestamp}-{screenshot_cache_key}-{name}_roi.png"
            for name in regions.keys()
        }

        metadata = {}
        metadata["regions"] = regions
        metadata["screenshot"] = screenshot_path.name
        metadata["screenshot_w_regions"] = screenshot_w_regions_path.name
        metadata["rois"] = {name: roi_path.name for name, roi_path in roi_paths.items()}

        logger.info(f"Saving regions to {json_path}")
        with open(json_path, "w") as f:
            json.dump(metadata, f, indent=4)

        logger.info(f"Saving screenshot to {screenshot_path}")
        cv2.imwrite(screenshot_path, screenshot)

        logger.info(f"Saving screenshot with regions to {screenshot_w_regions_path}")
        cv2.imwrite(screenshot_w_regions_path, screenshot_w_regions)

        for name, roi in rois.items():
            cv2.imwrite(
                output_dir / f"{timestamp}-{screenshot_cache_key}-{name}_roi.png", roi
            )


@region.command("select")
@click.option(
    "--manual",
    "-m",
    is_flag=True,
    default=False,
    help="Manually select the regions.",
)
def regions_select(manual: bool):
    """Select and cache regions for upgrade bar and button.

    This command allows you to select the regions used for detecting the upgrade bar and button.
    The selected regions will be cached for future use by other commands.

    By default, it will only prompt for manual selection if no regions are cached for the
    current window size. Use the -m flag to force manual selection regardless of cached regions.
    """
    # Check if we can find the Raid window
    # Create temporary screenshot service instance (will be injected in Phase 6)
    screenshot_service = ScreenshotService()
    window_title = "Raid: Shadow Legends"
    if not screenshot_service.window_exists(window_title):
        logger.warning("Raid window not found. Check if Raid is running.")
        sys.exit(1)

    # Select new regions
    screenshot = screenshot_service.take_screenshot(window_title)
    regions = select_upgrade_regions(screenshot, manual=manual)

    # Cache the regions and screenshot
    ctx = click.get_current_context()
    cache = ctx.obj["cache"]

    window_size = [screenshot.shape[0], screenshot.shape[1]]
    cache_key_regions = create_cache_key_regions(window_size)
    cache_key_screenshot = create_cache_key_screenshot(window_size)

    cache.set(cache_key_regions, regions)
    cache.set(cache_key_screenshot, screenshot)

    logger.info("Regions selected and cached successfully")
