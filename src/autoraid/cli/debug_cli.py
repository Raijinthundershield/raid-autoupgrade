"""Debug CLI commands for AutoRaid.

This module provides debug commands for monitoring and diagnosing AutoRaid behavior.
"""

import sys

import click
from dependency_injector.wiring import Provide, inject
from loguru import logger

from autoraid.container import Container
from autoraid.exceptions import WindowNotFoundException, WorkflowValidationError
from autoraid.workflows.debug_monitor_workflow import DebugMonitorWorkflow
from autoraid.protocols import (
    CacheProtocol,
    ScreenshotProtocol,
    WindowInteractionProtocol,
    NetworkManagerProtocol,
    ProgressBarDetectorProtocol,
)


@click.group()
def debug():
    """Debug commands for monitoring and diagnostics.

    These commands help diagnose issues and analyze AutoRaid behavior by capturing
    diagnostic data and monitoring internal state.
    """
    pass


@debug.command()
@click.option(
    "--network-adapter-id",
    "-n",
    type=str,
    multiple=True,
    help="Network adapter ids to manage during monitoring (use 'autoraid network list' to see available adapters).",
)
@click.option(
    "--max-frames",
    "-m",
    type=int,
    default=None,
    help="Maximum number of frames to capture (default: infinite, press Ctrl+C to stop)",
)
@click.option(
    "--interval",
    "-i",
    type=float,
    default=0.2,
    help="Time between captures in seconds (default: 0.2)",
)
@click.option(
    "--disable-network/--keep-network",
    default=True,
    help="Disable network adapters during monitoring (default: --disable-network)",
)
@click.pass_context
@inject
def progressbar(
    ctx,
    network_adapter_id: list[int],
    max_frames: int | None,
    interval: float,
    disable_network: bool,
    cache_service: CacheProtocol = Provide[Container.cache_service],
    window_interaction_service: WindowInteractionProtocol = Provide[
        Container.window_interaction_service
    ],
    network_manager: NetworkManagerProtocol = Provide[Container.network_manager],
    screenshot_service: ScreenshotProtocol = Provide[Container.screenshot_service],
    detector: ProgressBarDetectorProtocol = Provide[Container.progress_bar_detector],
):
    """Monitor progress bar state and save diagnostic data.

    Continuously monitors the progress bar, detects its state, and saves screenshots,
    ROIs, and metadata to the debug directory. Useful for debugging progress bar
    detection issues or analyzing state transitions.

    Output is saved to: cache-raid-autoupgrade/debug/progressbar_monitor/{timestamp}/

    Press Ctrl+C to stop monitoring and save results.
    """
    logger.info("Starting progress bar debug monitoring")

    # Get app_data from context
    app_data = ctx.obj["app_data"]
    debug_dir = app_data.debug_dir

    if debug_dir is None:
        raise click.UsageError("Debug mode not enabled. Use --debug flag.")

    # Construct workflow instance directly with injected services
    workflow = DebugMonitorWorkflow(
        cache_service=cache_service,
        window_interaction_service=window_interaction_service,
        network_manager=network_manager,
        screenshot_service=screenshot_service,
        detector=detector,
        network_adapter_ids=list(network_adapter_id) if network_adapter_id else None,
        disable_network=disable_network,
        max_frames=max_frames,
        check_interval=interval,
        debug_dir=debug_dir,
    )

    try:
        workflow.validate()
        result = workflow.run()

        logger.info(f"Monitoring complete: {result.total_frames} frames captured")
        logger.info(f"Stop reason: {result.stop_reason.value}")
        logger.info(f"Output saved to: {result.output_dir}")

    except WorkflowValidationError as e:
        logger.error(f"Validation failed: {e}")
        sys.exit(1)
    except WindowNotFoundException as e:
        logger.error(str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Monitoring interrupted by user")
        sys.exit(0)


@debug.command()
@click.pass_context
def review_progressbar(ctx):
    """Launch GUI to review progress bar detection results.

    Opens a graphical interface to manually review and validate progress bar
    state detection from previous monitoring sessions. Allows setting the
    "ground truth" state for each frame to evaluate detector accuracy.

    Loads sessions from: cache-raid-autoupgrade/debug/progressbar_monitor/
    Creates review copies in: {session}_review/
    """
    from autoraid.debug.app import main

    cache_dir = ctx.obj["cache_dir"]
    main(cache_dir=cache_dir)
