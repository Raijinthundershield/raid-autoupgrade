import json
import click
from pathlib import Path
import sys
import cv2
from loguru import logger
from dependency_injector.wiring import inject, Provide

from autoraid.container import Container
from autoraid.exceptions import (
    WindowNotFoundException,
    NetworkAdapterError,
    UpgradeWorkflowError,
)
from autoraid.services.cache_service import CacheService
from autoraid.services.locate_region_service import LocateRegionService
from autoraid.services.screenshot_service import ScreenshotService
from autoraid.services.upgrade_orchestrator import UpgradeOrchestrator
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
@inject
def count(
    network_adapter_id: list[int],
    show_most_recent_gear: bool,
    orchestrator: UpgradeOrchestrator = Provide[Container.upgrade_orchestrator],
):
    """Count the number of upgrade fails.

    Use network adapter ids to enable automatically turning network off and on.
    Use ids from the output of the `network list` command.
    """
    ctx = click.get_current_context()

    # Handle show most recent gear flag
    if show_most_recent_gear:
        screenshot = ctx.obj["cache"].get("current_gear_counted")
        if screenshot is None:
            logger.warning("No gear piece has been counted yet. Aborting.")
            sys.exit(1)
        cv2.imshow("Gear", screenshot)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        sys.exit(0)

    # Execute count workflow via orchestrator
    try:
        n_fails, reason = orchestrator.count_workflow(
            network_adapter_id=list(network_adapter_id) if network_adapter_id else None,
            max_attempts=99,
            debug_dir=ctx.obj["debug_dir"],
        )
        logger.info(f"Detected {n_fails} fails. Stop reason: {reason}")
    except (WindowNotFoundException, NetworkAdapterError, UpgradeWorkflowError) as e:
        logger.error(str(e))
        sys.exit(1)


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
@inject
def spend(
    max_attempts: int,
    continue_upgrade: bool,
    orchestrator: UpgradeOrchestrator = Provide[Container.upgrade_orchestrator],
):
    """Upgrade the piece until the max number of fails is reached."""
    ctx = click.get_current_context()

    # Execute spend workflow via orchestrator
    try:
        result = orchestrator.spend_workflow(
            max_attempts=max_attempts,
            continue_upgrade=continue_upgrade,
            debug_dir=ctx.obj["debug_dir"],
        )
        logger.info(
            f"Total upgrade attempts: {result['n_attempts']}. "
            f"There are {result['n_remaining']} left."
        )
    except (WindowNotFoundException, NetworkAdapterError, UpgradeWorkflowError) as e:
        logger.error(str(e))
        sys.exit(1)


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
@inject
def regions_show(
    output_dir: str,
    cache_service: CacheService = Provide[Container.cache_service],
    screenshot_service: ScreenshotService = Provide[Container.screenshot_service],
):
    """Show the currently cached regions within a screenshot of the current window.

    This command displays an image showing the currently cached regions for the upgrade bar
    and button. If no regions are cached for the current window size, it will exit with an error.
    Use the -o flag to save the image and regions to a directory.
    """
    # Check if we can find the Raid window
    window_title = "Raid: Shadow Legends"
    if not screenshot_service.window_exists(window_title):
        logger.warning("Raid window not found. Check if Raid is running.")
        sys.exit(1)

    # Take screenshot and get window size
    current_screenshot = screenshot_service.take_screenshot(window_title)
    window_size = (current_screenshot.shape[0], current_screenshot.shape[1])

    # Get cached regions and screenshot
    regions = cache_service.get_regions(window_size)
    screenshot = cache_service.get_screenshot(window_size)

    if regions is None:
        logger.error(
            "No cached regions found for current window size. Run count command first to cache regions."
        )
        sys.exit(1)

    logger.info("Showing cached regions")

    screenshot_w_regions = show_regions_in_image(screenshot, regions)

    if output_dir:
        output_dir = Path(output_dir) / "region_show"
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = get_timestamp()
        region_cache_key = CacheService.create_regions_key(window_size)
        screenshot_cache_key = CacheService.create_screenshot_key(window_size)

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
@inject
def regions_select(
    manual: bool,
    cache_service: CacheService = Provide[Container.cache_service],
    screenshot_service: ScreenshotService = Provide[Container.screenshot_service],
    locate_region_service: LocateRegionService = Provide[
        Container.locate_region_service
    ],
):
    """Select and cache regions for upgrade bar and button.

    This command allows you to select the regions used for detecting the upgrade bar and button.
    The selected regions will be cached for future use by other commands.

    By default, it will only prompt for manual selection if no regions are cached for the
    current window size. Use the -m flag to force manual selection regardless of cached regions.
    """
    # Check if we can find the Raid window
    window_title = "Raid: Shadow Legends"
    if not screenshot_service.window_exists(window_title):
        logger.warning("Raid window not found. Check if Raid is running.")
        sys.exit(1)

    # Select and cache regions using locate_region_service
    # Note: locate_region_service.get_regions() already handles caching internally
    screenshot = screenshot_service.take_screenshot(window_title)
    locate_region_service.get_regions(screenshot, manual=manual)

    logger.info("Regions selected and cached successfully")
