"""Upgrade orchestration service for coordinating upgrade monitoring.

This service orchestrates the upgrade monitoring process with configurable
stop conditions and optional debug logging.
"""

from dataclasses import dataclass
import time
from pathlib import Path
from loguru import logger

from autoraid.orchestration.progress_bar_monitor import ProgressBarMonitor
from autoraid.orchestration.stop_conditions import StopConditionChain, StopReason
from autoraid.orchestration.debug_frame_logger import DebugFrameLogger
from autoraid.protocols import (
    ProgressBarDetectorProtocol,
    ScreenshotProtocol,
    WindowInteractionProtocol,
    CacheProtocol,
    NetworkManagerProtocol,
)
from autoraid.utils.network_context import NetworkContext
from autoraid.exceptions import WindowNotFoundException, WorkflowValidationError


@dataclass(frozen=True)
class UpgradeSession:
    """Configuration for a single upgrade monitoring session."""

    upgrade_bar_region: tuple[int, int, int, int]
    upgrade_button_region: tuple[int, int, int, int]
    stop_conditions: StopConditionChain
    check_interval: float = 0.25
    network_adapter_ids: list[int] | None = None
    disable_network: bool = False
    debug_dir: Path | None = None


@dataclass(frozen=True)
class UpgradeResult:
    """Result from a single upgrade monitoring session."""

    fail_count: int
    frames_processed: int
    stop_reason: StopReason
    debug_session_dir: Path | None = None


class UpgradeOrchestrator:
    """
    Orchestrates upgrade monitoring with configurable stop conditions.
    """

    WINDOW_TITLE = "Raid: Shadow Legends"

    def __init__(
        self,
        screenshot_service: ScreenshotProtocol,
        window_interaction_service: WindowInteractionProtocol,
        cache_service: CacheProtocol,
        network_manager: NetworkManagerProtocol,
        detector: ProgressBarDetectorProtocol,
    ):
        """
        Initialize orchestrator with injected services.

        Args:
            screenshot_service: Service for capturing screenshots
            window_interaction_service: Service for window operations
            cache_service: Service for region caching
            network_manager: Service for network adapter management
            detector: Detector for progress bar state detection
        """
        self._screenshot_service = screenshot_service
        self._window_interaction_service = window_interaction_service
        self._cache_service = cache_service
        self._network_manager = network_manager
        self._detector = detector

    def validate_prerequisites(self, session: UpgradeSession) -> None:
        logger.info("Validating orchestrator prerequisites")

        # Window exists
        if not self._window_interaction_service.window_exists(self.WINDOW_TITLE):
            raise WindowNotFoundException(
                f"Raid window not found. Ensure {self.WINDOW_TITLE} is running."
            )

        # Regions cached for current window size
        current_size = self._window_interaction_service.get_window_size(
            self.WINDOW_TITLE
        )
        regions = self._cache_service.get_regions(current_size)
        if regions is None:
            raise WorkflowValidationError(
                f"No regions cached for window size {current_size}. "
                "Please select regions using 'autoraid upgrade region select'."
            )

        logger.debug(
            f"Prerequisites validated: window exists, regions cached for {current_size}"
        )

    def run_upgrade_session(
        self,
        session: UpgradeSession,
    ) -> UpgradeResult:
        # Validate prerequisites first
        self.validate_prerequisites(session)

        # Create fresh monitor for this session
        monitor = ProgressBarMonitor(detector=self._detector)

        # Create debug logger if debug_dir is provided
        debug_logger = None
        if session.debug_dir is not None:
            debug_logger = DebugFrameLogger(output_dir=session.debug_dir)

        logger.info("Starting upgrade session")
        logger.debug(
            f"Session config: disable_network={session.disable_network}, "
            f"adapters={session.network_adapter_ids}, "
            f"check_interval={session.check_interval}"
        )

        # Use NetworkContext for automatic network adapter management
        with NetworkContext(
            network_manager=self._network_manager,
            adapter_ids=session.network_adapter_ids,
            disable_network=session.disable_network,
        ):
            # Click upgrade button to start
            logger.info("Clicking upgrade button to start monitoring")
            self._window_interaction_service.click_region(
                self.WINDOW_TITLE,
                session.upgrade_button_region,
            )

            # Monitor loop
            stop_reason = self._monitor_loop(session, monitor, debug_logger)

            # Get final state
            final_state = monitor.get_state()

            # Save debug summary if logger provided
            debug_dir = None
            if debug_logger:
                debug_dir = debug_logger.session_dir
                debug_logger.save_summary(
                    {
                        "stop_reason": stop_reason.value,
                        "final_fail_count": final_state.fail_count,
                        "check_interval": session.check_interval,
                    }
                )

            logger.info(
                f"Session complete: fails={final_state.fail_count}, "
                f"frames={final_state.frames_processed}, "
                f"reason={stop_reason.value}"
            )

            return UpgradeResult(
                fail_count=final_state.fail_count,
                frames_processed=final_state.frames_processed,
                stop_reason=stop_reason,
                debug_session_dir=debug_dir,
            )
        # NetworkContext automatically re-enables adapters on exit

    def _monitor_loop(
        self,
        session: UpgradeSession,
        monitor: ProgressBarMonitor,
        debug_logger: DebugFrameLogger | None = None,
    ) -> StopReason:
        logger.info("Starting progress bar monitoring loop")

        prev_fail_count = 0

        while True:
            # Capture screenshot and extract ROI
            screenshot = self._screenshot_service.take_screenshot(self.WINDOW_TITLE)
            upgrade_bar_roi = self._screenshot_service.extract_roi(
                screenshot,
                session.upgrade_bar_region,
            )

            # Process frame with monitor
            current_state = monitor.process_frame(upgrade_bar_roi)
            monitor_state = monitor.get_state()

            # Log progress on fail count changes
            if monitor_state.fail_count > prev_fail_count:
                logger.info(f"Progress: {monitor_state.fail_count} fails detected")
                prev_fail_count = monitor_state.fail_count

            # Optional debug logging
            if debug_logger:
                debug_logger.log_frame(
                    frame_number=monitor_state.frames_processed - 1,
                    detected_state=current_state,
                    fail_count=monitor_state.fail_count,
                    screenshot=screenshot,
                    roi=upgrade_bar_roi,
                )

            # Check stop conditions
            stop_reason = session.stop_conditions.check(monitor_state)
            if stop_reason is not None:
                logger.debug(f"Stop condition met: {stop_reason.value}")
                return stop_reason

            # Wait before next iteration
            time.sleep(session.check_interval)
