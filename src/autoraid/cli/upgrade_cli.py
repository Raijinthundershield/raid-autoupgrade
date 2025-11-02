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
    WorkflowValidationError,
)
from autoraid.protocols import (
    CacheProtocol,
    LocateRegionProtocol,
    ScreenshotProtocol,
    WindowInteractionProtocol,
    NetworkManagerProtocol,
    ProgressBarDetectorProtocol,
)
from autoraid.workflows.count_workflow import CountWorkflow
from autoraid.workflows.spend_workflow import SpendWorkflow
from autoraid.utils.common import get_timestamp
from autoraid.utils.visualization import show_regions_in_image


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
    type=str,
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
    cache_service: CacheProtocol = Provide[Container.cache_service],
    window_interaction_service: WindowInteractionProtocol = Provide[
        Container.window_interaction_service
    ],
    network_manager: NetworkManagerProtocol = Provide[Container.network_manager],
    screenshot_service: ScreenshotProtocol = Provide[Container.screenshot_service],
    detector: ProgressBarDetectorProtocol = Provide[Container.progress_bar_detector],
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

    # Execute count workflow with direct construction
    try:
        # Get app_data from context
        app_data = ctx.obj["app_data"]
        debug_dir = app_data.debug_dir

        # Construct workflow instance directly with injected services
        workflow = CountWorkflow(
            cache_service=cache_service,
            window_interaction_service=window_interaction_service,
            network_manager=network_manager,
            screenshot_service=screenshot_service,
            detector=detector,
            network_adapter_ids=list(network_adapter_id)
            if network_adapter_id
            else None,
            max_attempts=99,
            debug_dir=debug_dir,
        )

        # Run validate-then-run lifecycle
        workflow.validate()
        result = workflow.run()

        logger.info(
            f"Detected {result.fail_count} fails. Stop reason: {result.stop_reason.name}"
        )
    except WorkflowValidationError as e:
        logger.error(f"Validation failed: {e}")
        sys.exit(1)
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
    cache_service: CacheProtocol = Provide[Container.cache_service],
    window_interaction_service: WindowInteractionProtocol = Provide[
        Container.window_interaction_service
    ],
    network_manager: NetworkManagerProtocol = Provide[Container.network_manager],
    screenshot_service: ScreenshotProtocol = Provide[Container.screenshot_service],
    detector: ProgressBarDetectorProtocol = Provide[Container.progress_bar_detector],
):
    """Upgrade the piece until the max number of fails is reached."""
    ctx = click.get_current_context()

    # Execute spend workflow with direct construction
    try:
        # Get app_data from context
        app_data = ctx.obj["app_data"]
        debug_dir = app_data.debug_dir

        # Construct workflow instance directly with injected services
        workflow = SpendWorkflow(
            cache_service=cache_service,
            window_interaction_service=window_interaction_service,
            network_manager=network_manager,
            screenshot_service=screenshot_service,
            detector=detector,
            max_upgrade_attempts=max_attempts,
            continue_upgrade=continue_upgrade,
            debug_dir=debug_dir,
        )

        # Run validate-then-run lifecycle
        workflow.validate()
        result = workflow.run()

        logger.info(
            f"Upgraded {result.upgrade_count} times. "
            f"Total upgrade attempts: {result.attempt_count}. "
            f"There are {result.remaining_attempts} left. "
            f"Stop reason: {result.stop_reason.name}"
        )
    except WorkflowValidationError as e:
        logger.error(f"Validation failed: {e}")
        sys.exit(1)
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
    cache_service: CacheProtocol = Provide[Container.cache_service],
    window_interaction_service: WindowInteractionProtocol = Provide[
        Container.window_interaction_service
    ],
    screenshot_service: ScreenshotProtocol = Provide[Container.screenshot_service],
):
    """Show the currently cached regions within a screenshot of the current window.

    This command displays an image showing the currently cached regions for the upgrade bar
    and button. If no regions are cached for the current window size, it will exit with an error.
    Use the -o flag to save the image and regions to a directory.
    """
    # Check if we can find the Raid window
    window_title = "Raid: Shadow Legends"
    if not window_interaction_service.window_exists(window_title):
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
        region_cache_key = cache_service.create_regions_key(window_size)
        screenshot_cache_key = cache_service.create_screenshot_key(window_size)

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
    screenshot_service: ScreenshotProtocol = Provide[Container.screenshot_service],
    window_interaction_service: WindowInteractionProtocol = Provide[
        Container.window_interaction_service
    ],
    locate_region_service: LocateRegionProtocol = Provide[
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
    if not window_interaction_service.window_exists(window_title):
        logger.warning("Raid window not found. Check if Raid is running.")
        sys.exit(1)

    # Select and cache regions using locate_region_service
    # Note: locate_region_service.get_regions() already handles caching internally
    screenshot = screenshot_service.take_screenshot(window_title)
    locate_region_service.get_regions(screenshot, manual=manual)

    logger.info("Regions selected and cached successfully")
