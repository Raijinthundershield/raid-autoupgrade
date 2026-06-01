"""Upgrade orchestration service for coordinating upgrade monitoring.

This service orchestrates the upgrade monitoring process with configurable
stop conditions and optional debug logging. It drives the in-game surface
through an injected :class:`UpgradeScreen`, owning only the network context,
the offline-required guard, and the monitor loop.
"""

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from raid_autoupgrade.detection.progress_bar_detector import ProgressBarState
from raid_autoupgrade.exceptions import WorkflowValidationError
from raid_autoupgrade.orchestration.debug_frame_logger import DebugFrameLogger
from raid_autoupgrade.orchestration.progress_bar_monitor import ProgressBarMonitor
from raid_autoupgrade.orchestration.stop_conditions import (
    StopConditionChain,
    StopReason,
)
from raid_autoupgrade.protocols import (
    NetworkManagerProtocol,
    ProgressBarDetectorProtocol,
    UpgradeScreenProtocol,
)
from raid_autoupgrade.services.network import AdapterId, NetworkState
from raid_autoupgrade.utils.network_context import NetworkContext


@dataclass(frozen=True)
class MonitorRun:
    """Run intent for a single monitor loop.

    Carries no coordinates — Region resolution and game clicks live in the
    injected :class:`UpgradeScreen`.
    """

    stop_conditions: StopConditionChain
    check_interval: float = 0.25
    network_adapter_ids: list[AdapterId] | None = None
    disable_network: bool = False
    require_offline: bool = False
    debug_dir: Path | None = None


@dataclass(frozen=True)
class ProgressEvent:
    """Progress snapshot emitted each monitor-loop iteration."""

    fail_count: int
    frames: int
    state: ProgressBarState | None


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

    def __init__(
        self,
        upgrade_screen: UpgradeScreenProtocol,
        network_manager: NetworkManagerProtocol,
        detector: ProgressBarDetectorProtocol,
    ):
        """
        Initialize orchestrator with injected dependencies.

        Args:
            upgrade_screen: The in-game upgrade surface (owns Region resolution
                and the start/capture actions)
            network_manager: Service for network adapter management
            detector: Detector for progress bar state detection
        """
        self._upgrade_screen = upgrade_screen
        self._network_manager = network_manager
        self._detector = detector

    def run_monitor(
        self,
        run: MonitorRun,
        cancel_event: threading.Event | None = None,
        on_progress: Callable[[ProgressEvent], None] | None = None,
    ) -> UpgradeResult:
        # Create fresh monitor for this run
        monitor = ProgressBarMonitor(detector=self._detector)

        # Create debug logger if debug_dir is provided
        debug_logger = None
        if run.debug_dir is not None:
            debug_logger = DebugFrameLogger(output_dir=run.debug_dir)

        logger.info("Starting monitor run")
        logger.debug(
            f"Run config: disable_network={run.disable_network}, "
            f"adapters={run.network_adapter_ids}, "
            f"check_interval={run.check_interval}"
        )

        # Use NetworkContext for automatic network adapter management
        with NetworkContext(
            network_manager=self._network_manager,
            adapter_ids=run.network_adapter_ids,
            disable_network=run.disable_network,
        ):
            # Refuse to start an offline-only run while the network is still
            # reachable. Counting online would spend real upgrade attempts and
            # could upgrade the piece. This runs after adapters are disabled, so
            # it also catches the case where the wrong adapter was selected.
            if (
                run.require_offline
                and self._network_manager.check_network_access() == NetworkState.ONLINE
            ):
                raise WorkflowValidationError(
                    "Network is still reachable, so counting can't start — it must "
                    "run offline to avoid spending real upgrade attempts. Select a "
                    "network adapter to disable in the Network panel."
                )

            # Begin the Attempt
            logger.info("Beginning attempt to start monitoring")
            self._upgrade_screen.start_attempt()

            # Monitor loop
            stop_reason = self._monitor_loop(
                run, monitor, debug_logger, cancel_event, on_progress
            )

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
                        "check_interval": run.check_interval,
                    }
                )

            logger.info(
                f"Monitor run complete: fails={final_state.fail_count}, "
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
        run: MonitorRun,
        monitor: ProgressBarMonitor,
        debug_logger: DebugFrameLogger | None = None,
        cancel_event: threading.Event | None = None,
        on_progress: Callable[[ProgressEvent], None] | None = None,
    ) -> StopReason:
        logger.info("Starting progress bar monitoring loop")

        prev_fail_count = 0

        while True:
            if cancel_event is not None and cancel_event.is_set():
                return StopReason.MANUAL_STOP

            # Capture one frame plus the progress-bar ROI from the screen
            capture = self._upgrade_screen.capture_progress_bar()

            # Process frame with monitor (detector sees the ROI)
            current_state = monitor.process_frame(capture.roi)
            monitor_state = monitor.get_state()

            # Emit progress event
            if on_progress is not None:
                on_progress(
                    ProgressEvent(
                        fail_count=monitor_state.fail_count,
                        frames=monitor_state.frames_processed,
                        state=monitor_state.current_state,
                    )
                )

            # Log progress on fail count changes
            if monitor_state.fail_count > prev_fail_count:
                logger.info(f"Progress: {monitor_state.fail_count} fails detected")
                prev_fail_count = monitor_state.fail_count

            # Optional debug logging (gets both the full frame and the ROI)
            if debug_logger:
                debug_logger.log_frame(
                    frame_number=monitor_state.frames_processed - 1,
                    detected_state=current_state,
                    fail_count=monitor_state.fail_count,
                    screenshot=capture.frame,
                    roi=capture.roi,
                )

            # Check stop conditions
            stop_reason = run.stop_conditions.check(monitor_state)
            if stop_reason is not None:
                logger.debug(f"Stop condition met: {stop_reason.value}")
                return stop_reason

            # Wait before next iteration
            time.sleep(run.check_interval)
