"""Orchestrator for coordinating upgrade workflows with all services."""

import json
import time
from pathlib import Path
from collections.abc import Callable

import cv2
from loguru import logger

from autoraid.core.state_machine import UpgradeStateMachine, StopCountReason
from autoraid.exceptions import (
    WindowNotFoundException,
    NetworkAdapterError,
    UpgradeWorkflowError,
)
from autoraid.platform.network import NetworkManager
from autoraid.services.cache_service import CacheService
from autoraid.services.locate_region_service import LocateRegionService
from autoraid.services.screenshot_service import ScreenshotService
from autoraid.services.window_interaction_service import WindowInteractionService
from autoraid.utils.common import get_timestamp


class UpgradeOrchestrator:
    """Orchestrates upgrade workflows by coordinating all services.

    This class is responsible for high-level workflow coordination:
    - Count workflow: Count upgrade fails with network disabled
    - Spend workflow: Execute upgrade attempts with network enabled

    The orchestrator handles:
    - Service coordination
    - Network adapter management (disable/enable)
    - Debug data collection
    - Error recovery (finally blocks)
    """

    def __init__(
        self,
        cache_service: CacheService,
        screenshot_service: ScreenshotService,
        locate_region_service: LocateRegionService,
        window_interaction_service: WindowInteractionService,
        state_machine_provider: Callable,
    ):
        """Initialize orchestrator with service dependencies.

        Args:
            cache_service: Service for caching regions and screenshots
            screenshot_service: Service for capturing screenshots and ROI extraction
            locate_region_service: Service for region detection
            window_interaction_service: Service for window interactions and clicking
            state_machine_provider: Factory provider for creating state machine instances
        """
        self._cache_service = cache_service
        self._screenshot_service = screenshot_service
        self._locate_region_service = locate_region_service
        self._window_interaction_service = window_interaction_service
        self._state_machine_provider = state_machine_provider

    def _count_upgrade_fails(
        self,
        window_title: str,
        upgrade_bar_region: tuple[int, int, int, int],
        max_attempts: int,
        check_interval: float = 0.25,
        debug_dir: Path | None = None,
    ) -> tuple[int, StopCountReason]:
        """Count upgrade fails using state machine.

        Args:
            window_title: Title of the Raid window
            upgrade_bar_region: Region coordinates (left, top, width, height)
            max_attempts: Maximum upgrade attempts
            check_interval: Time between frame checks
            debug_dir: Directory for debug artifacts

        Returns:
            Tuple of (fail_count, stop_reason)
        """
        state_machine: UpgradeStateMachine = self._state_machine_provider(
            max_attempts=max_attempts
        )

        debug_metadata = {
            "upgrade_bar_region": upgrade_bar_region,
            "timestamp": [],
            "current_state": {},
            "n_fails": {},
        }
        debug_screenshots = {}
        debug_upgrade_bar_rois = {}

        logger.info("Starting to monitor upgrade bar color changes...")

        stop_reason = None
        while stop_reason is None:
            screenshot = self._screenshot_service.take_screenshot(window_title)
            upgrade_bar = self._screenshot_service.extract_roi(
                screenshot, upgrade_bar_region
            )

            # Process frame using state machine
            n_fails, stop_reason = state_machine.process_frame(upgrade_bar)

            # Store debug information
            if debug_dir is not None:
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
                current_state = debug_metadata["current_state"].get(
                    timestamp, "unknown"
                )
                cv2.imwrite(
                    str(output_dir / f"{timestamp}_{current_state}_screenshot.png"),
                    debug_screenshots[timestamp],
                )
                cv2.imwrite(
                    str(
                        output_dir / f"{timestamp}_{current_state}_upgrade_bar_roi.png"
                    ),
                    debug_upgrade_bar_rois[timestamp],
                )
            with open(output_dir / "debug_metadata.json", "w") as f:
                json.dump(debug_metadata, f)

        logger.info(f"Finished counting. Detected {n_fails} fails.")
        return n_fails, stop_reason

    def count_workflow(
        self,
        network_adapter_id: list[int] | None = None,
        max_attempts: int = 99,
        debug_dir: Path | None = None,
    ) -> tuple[int, StopCountReason]:
        """Execute count workflow to count upgrade fails with network disabled.

        This workflow:
        1. Validates Raid window exists
        2. Disables network adapters (if specified)
        3. Takes screenshot and gets regions
        4. Clicks upgrade button
        5. Counts upgrade fails
        6. Re-enables network adapters (in finally block)

        Args:
            network_adapter_id: List of network adapter IDs to disable/enable
            max_attempts: Maximum upgrade attempts before stopping
            debug_dir: Directory to save debug screenshots and metadata

        Returns:
            Tuple of (fail_count, stop_reason)

        Raises:
            ValueError: If Raid window not found
            RuntimeError: If network disable/enable fails
        """
        logger.info("[UpgradeOrchestrator] Starting count workflow")
        logger.debug(
            f"[UpgradeOrchestrator] count_workflow called with network_adapter_id={network_adapter_id}, "
            f"max_attempts={max_attempts}, debug_dir={debug_dir}"
        )

        window_title = "Raid: Shadow Legends"

        # Validate window exists
        if not self._window_interaction_service.window_exists(window_title):
            logger.error("[UpgradeOrchestrator] Raid window not found")
            raise WindowNotFoundException(
                "Raid window not found. Check if Raid is running."
            )

        # Initialize network manager
        manager = NetworkManager()

        # Check network access and disable if needed
        if manager.check_network_access() and not network_adapter_id:
            logger.warning(
                "[UpgradeOrchestrator] Internet access detected but no network adapter specified"
            )
            raise UpgradeWorkflowError(
                "Internet access detected and network id not specified. This will upgrade the piece. Aborting."
            )

        # Disable network adapters
        if network_adapter_id:
            logger.info(
                f"[UpgradeOrchestrator] Disabling network adapters: {network_adapter_id}"
            )
            manager.toggle_adapters(network_adapter_id, enable=False)

            # Wait for network to turn off (max 3 seconds)
            for _ in range(3):
                logger.debug("[UpgradeOrchestrator] Waiting for network to turn off")
                time.sleep(1)
                if not manager.check_network_access():
                    logger.info("[UpgradeOrchestrator] Network disabled successfully")
                    break
            else:
                logger.error("[UpgradeOrchestrator] Failed to disable network")
                raise NetworkAdapterError("Failed to turn off network. Aborting.")

        try:
            # Capture screenshot
            logger.info("[UpgradeOrchestrator] Captured screenshot")
            screenshot = self._screenshot_service.take_screenshot(window_title)

            # Get regions (from cache or detection)
            logger.debug("[UpgradeOrchestrator] Getting upgrade regions")
            regions = self._locate_region_service.get_regions(screenshot, manual=False)

            # Save debug data if requested
            if debug_dir is not None:
                output_dir = debug_dir / "count"
                output_dir.mkdir(exist_ok=True)
                timestamp = get_timestamp()
                cv2.imwrite(str(output_dir / f"{timestamp}_screenshot.png"), screenshot)
                with open(output_dir / f"{timestamp}_regions.json", "w") as f:
                    json.dump(regions, f)
                logger.debug(f"[UpgradeOrchestrator] Saved debug data to {output_dir}")

            # Click upgrade button
            logger.info("[UpgradeOrchestrator] Clicking upgrade button")
            self._window_interaction_service.click_region(
                window_title, regions["upgrade_button"]
            )

            # Count upgrade fails
            logger.info("[UpgradeOrchestrator] Counting upgrade fails")
            n_fails, reason = self._count_upgrade_fails(
                window_title=window_title,
                upgrade_bar_region=regions["upgrade_bar"],
                max_attempts=max_attempts,
                debug_dir=debug_dir,
            )

            # Wait for connection timeout
            logger.debug("[UpgradeOrchestrator] Waiting for connection timeout (3s)")
            time.sleep(3)

            logger.info(
                f"[UpgradeOrchestrator] Count workflow completed: {n_fails} fails, reason={reason}"
            )
            return n_fails, reason

        finally:
            # Always re-enable network adapters
            if network_adapter_id:
                logger.info(
                    f"[UpgradeOrchestrator] Re-enabling network adapters: {network_adapter_id}"
                )
                manager.toggle_adapters(network_adapter_id, enable=True)
                logger.debug("[UpgradeOrchestrator] Network adapters re-enabled")

    def spend_workflow(
        self,
        max_attempts: int,
        continue_upgrade: bool = False,
        debug_dir: Path | None = None,
    ) -> dict:
        """Execute spend workflow to use upgrade attempts with network enabled.

        This workflow:
        1. Validates Raid window exists
        2. Validates network access available
        3. Takes screenshot and gets regions
        4. Loops clicking upgrade button and counting fails until max_attempts reached
        5. Returns summary of upgrade attempts

        Args:
            max_attempts: Maximum upgrade attempts before stopping
            continue_upgrade: Continue upgrading after first successful upgrade (for level 10+)
            debug_dir: Directory to save debug screenshots and metadata

        Returns:
            Dictionary with workflow results:
                - n_upgrades: Number of successful upgrades
                - n_attempts: Total upgrade attempts used
                - n_remaining: Remaining attempts
                - last_reason: Last stop reason

        Raises:
            ValueError: If Raid window not found
            RuntimeError: If no internet access detected
        """
        logger.info("[UpgradeOrchestrator] Starting spend workflow")
        logger.debug(
            f"[UpgradeOrchestrator] spend_workflow called with max_attempts={max_attempts}, "
            f"continue_upgrade={continue_upgrade}, debug_dir={debug_dir}"
        )

        window_title = "Raid: Shadow Legends"

        # Validate window exists
        if not self._window_interaction_service.window_exists(window_title):
            logger.error("[UpgradeOrchestrator] Raid window not found")
            raise WindowNotFoundException(
                "Raid window not found. Check if Raid is running."
            )

        # Validate network access
        manager = NetworkManager()
        if not manager.check_network_access():
            logger.error("[UpgradeOrchestrator] No internet access detected")
            raise NetworkAdapterError("No internet access detected. Aborting.")

        # Capture screenshot
        logger.info("[UpgradeOrchestrator] Captured screenshot")
        screenshot = self._screenshot_service.take_screenshot(window_title)

        # Get regions
        logger.debug("[UpgradeOrchestrator] Getting upgrade regions")
        regions = self._locate_region_service.get_regions(screenshot, manual=False)

        # Save debug data if requested
        if debug_dir is not None:
            output_dir = debug_dir / "upgrade"
            output_dir.mkdir(exist_ok=True)
            timestamp = get_timestamp()
            cv2.imwrite(str(output_dir / f"{timestamp}_screenshot.png"), screenshot)
            with open(output_dir / f"{timestamp}_regions.json", "w") as f:
                json.dump(regions, f)
            logger.debug(f"[UpgradeOrchestrator] Saved debug data to {output_dir}")

        # Loop upgrading until max attempts reached
        upgrade = True
        n_upgrades = 0
        n_attempts = 0
        last_reason = None

        while upgrade:
            upgrade = False

            logger.info("[UpgradeOrchestrator] Clicking upgrade button")
            self._window_interaction_service.click_region(
                window_title, regions["upgrade_button"]
            )

            # Count upgrade fails
            logger.debug(
                f"[UpgradeOrchestrator] Counting upgrade fails (remaining: {max_attempts - n_attempts})"
            )
            n_fails, reason = self._count_upgrade_fails(
                window_title=window_title,
                upgrade_bar_region=regions["upgrade_bar"],
                max_attempts=max_attempts - n_attempts,
                debug_dir=debug_dir,
            )
            n_attempts += n_fails
            last_reason = reason

            if reason == StopCountReason.MAX_ATTEMPTS_REACHED:
                logger.info(
                    f"[UpgradeOrchestrator] Reached max attempts at {n_attempts} upgrade attempts. Cancelling upgrade."
                )
                self._window_interaction_service.click_region(
                    window_title, regions["upgrade_button"]
                )

            elif reason == StopCountReason.UPGRADED:
                n_attempts += 1
                n_upgrades += 1
                logger.info(
                    f"[UpgradeOrchestrator] Piece upgraded at {n_attempts} upgrade attempts."
                )

            # Check if should continue upgrading
            if continue_upgrade and n_upgrades == 1 and n_attempts < max_attempts:
                upgrade = True
                logger.info(
                    "[UpgradeOrchestrator] Continue upgrade enabled, starting next upgrade"
                )

        result = {
            "n_upgrades": n_upgrades,
            "n_attempts": n_attempts,
            "n_remaining": max_attempts - n_attempts,
            "last_reason": last_reason,
        }

        logger.info(
            f"[UpgradeOrchestrator] Spend workflow completed: {n_upgrades} upgrades, "
            f"{n_attempts} attempts, {result['n_remaining']} remaining"
        )
        return result
