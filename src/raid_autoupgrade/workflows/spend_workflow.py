"""
Spend workflow implementation.

This module implements the SpendWorkflow class for spending upgrade attempts
with internet verification and optional continue upgrade logic.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from raid_autoupgrade.constants import RAID_WINDOW_TITLE
from raid_autoupgrade.detection.progress_bar_detector import ProgressBarState
from raid_autoupgrade.exceptions import WorkflowValidationError
from raid_autoupgrade.orchestration.stop_conditions import (
    ConnectionErrorCondition,
    MaxAttemptsCondition,
    StopConditionChain,
    StopReason,
    UpgradedCondition,
)
from raid_autoupgrade.orchestration.upgrade_orchestrator import (
    MonitorRun,
    ProgressEvent,
    UpgradeOrchestrator,
)
from raid_autoupgrade.orchestration.upgrade_screen import UpgradeScreen
from raid_autoupgrade.protocols import (
    CacheProtocol,
    NetworkManagerProtocol,
    ProgressBarDetectorProtocol,
    ScreenshotProtocol,
    WindowInteractionProtocol,
)
from raid_autoupgrade.services.network import NetworkState


@dataclass(frozen=True)
class SpendResult:
    """Result from spend workflow."""

    upgrade_count: int
    attempt_count: int
    remaining_attempts: int
    stop_reason: StopReason


@dataclass(frozen=True)
class SpendProgress:
    """A cumulative, live Spend snapshot emitted each monitor-loop frame.

    Unlike the orchestrator's per-session ``ProgressEvent``, these totals are
    cumulative across the whole Spend: ``attempts_used`` counts up and
    ``remaining`` counts down within a single session, not only at boundaries.
    """

    attempts_used: int
    remaining: int
    upgrades: int
    state: ProgressBarState | None


def enrich_spend_progress(
    attempt_count: int,
    remaining_attempts: int,
    upgrade_count: int,
    event: ProgressEvent,
) -> SpendProgress:
    """Map a session ``ProgressEvent`` plus the Spend loop's running base totals
    to a cumulative Spend snapshot.

    Within-session liveness comes from the session's own ``fail_count``:
    ``attempts_used = attempt_count + fail_count`` and
    ``remaining = remaining_attempts - fail_count``. ``upgrade_count`` is carried
    through unchanged (an upgrade is only recognised at a session boundary).
    """
    return SpendProgress(
        attempts_used=attempt_count + event.fail_count,
        remaining=remaining_attempts - event.fail_count,
        upgrades=upgrade_count,
        state=event.state,
    )


class SpendWorkflow:
    """
    This workflow spends a specified number of upgrade attempts.
    """

    WINDOW_TITLE = RAID_WINDOW_TITLE

    def __init__(
        self,
        cache_service: CacheProtocol,
        window_interaction_service: WindowInteractionProtocol,
        network_manager: NetworkManagerProtocol,
        screenshot_service: ScreenshotProtocol,
        detector: ProgressBarDetectorProtocol,
        max_upgrade_attempts: int,
        continue_upgrade: bool = False,
        debug_dir: Path | None = None,
    ):
        """Initialize SpendWorkflow.

        Args:
            cache_service: CacheService for retrieving cached regions
            window_interaction_service: WindowInteractionService for window operations
            network_manager: NetworkManager for network state validation
            screenshot_service: Service for screenshot capture
            detector: Detector for progress bar state detection
            max_upgrade_attempts: Maximum upgrade attempts to spend
            continue_upgrade: Whether to continue upgrading to next level after success
            debug_dir: Optional debug directory for logging
        """
        self._cache_service = cache_service
        self._window_interaction_service = window_interaction_service
        self._network_manager = network_manager
        self._screenshot_service = screenshot_service
        self._detector = detector
        self._max_upgrade_attempts = max_upgrade_attempts
        self._continue_upgrade = continue_upgrade
        self._debug_dir = debug_dir

    def validate(self) -> None:
        logger.info("Starting spend workflow validation")

        if self._network_manager.check_network_access() != NetworkState.ONLINE:
            raise WorkflowValidationError(
                "No internet access detected. "
                "Spending requires internet so upgrades are saved. "
                "Re-enable your network adapter and check your connection."
            )

        logger.info("Spend workflow validation completed successfully")

    def run(
        self,
        cancel_event: threading.Event | None = None,
        on_progress: Callable[[SpendProgress], None] | None = None,
    ) -> SpendResult:
        logger.info("Starting spend workflow execution")

        # Pre-flight validation (spend requires internet to save upgrades).
        self.validate()

        # Get regions from cache
        current_size = self._window_interaction_service.get_window_size(
            self.WINDOW_TITLE
        )
        regions = self._cache_service.get_regions(current_size)
        if regions is None:
            raise WorkflowValidationError(
                f"No upgrade regions saved for this window size ({current_size}). "
                "Open the Calibration tab and select the upgrade regions first."
            )

        # One UpgradeScreen per run, shared with the orchestrator across attempts
        upgrade_screen = UpgradeScreen(
            window_interaction_service=self._window_interaction_service,
            cache_service=self._cache_service,
            screenshot_service=self._screenshot_service,
        )

        # Create orchestrator for this workflow
        orchestrator = UpgradeOrchestrator(
            upgrade_screen=upgrade_screen,
            network_manager=self._network_manager,
            detector=self._detector,
        )

        upgrade_count = 0
        attempt_count = 0
        remaining_attempts = self._max_upgrade_attempts
        final_stop_reason = None

        logger.info("Starting upgrade loop")

        while remaining_attempts > 0:
            logger.info(
                f"Clicking upgrade button "
                f"(attempt {attempt_count + 1}/{self._max_upgrade_attempts})"
            )

            # Configure stop conditions for this iteration
            stop_conditions = StopConditionChain(
                [
                    MaxAttemptsCondition(max_attempts=remaining_attempts),
                    UpgradedCondition(network_disabled=False),
                    ConnectionErrorCondition(),
                ]
            )

            # Describe this attempt's run intent (coordinate-free)
            run = MonitorRun(
                stop_conditions=stop_conditions,
                check_interval=0.25,
                network_adapter_ids=None,
                disable_network=False,
                # ``self._debug_dir`` is already the kind-namespaced
                # ``.../debug/spend`` (run_fn does that). Each upgrade attempt
                # runs its own monitor run, so they are grouped per attempt;
                # the timestamp dir under that is added by the DebugFrameLogger.
                debug_dir=(
                    self._debug_dir / f"upgrade_{upgrade_count + 1}"
                    if self._debug_dir
                    else None
                ),
            )

            # Wrap the caller's progress callback so each per-session
            # ProgressEvent is enriched with this Spend's running loop totals,
            # making attempts_used / remaining tick live within the session
            # rather than jumping only at session boundaries. The base totals are
            # frozen via default args at wrapper-creation time (this iteration's
            # values, before this session's fails accrue).
            session_on_progress: Callable[[ProgressEvent], None] | None = None
            if on_progress is not None:

                def session_on_progress(
                    event: ProgressEvent,
                    _base_attempts: int = attempt_count,
                    _base_remaining: int = remaining_attempts,
                    _base_upgrades: int = upgrade_count,
                ) -> None:
                    on_progress(
                        enrich_spend_progress(
                            _base_attempts, _base_remaining, _base_upgrades, event
                        )
                    )

            # Execute the monitor run for this attempt
            result = orchestrator.run_monitor(
                run, cancel_event=cancel_event, on_progress=session_on_progress
            )

            # Update counters
            attempt_count += result.fail_count
            remaining_attempts -= result.fail_count
            final_stop_reason = result.stop_reason

            logger.debug(
                f"Session complete: reason={final_stop_reason.value}, "
                f"attempts_used={result.fail_count}"
            )

            # Handle stop reasons
            if final_stop_reason == StopReason.MAX_ATTEMPTS_REACHED:
                logger.info("Maximum attempts reached, canceling upgrade")
                self._window_interaction_service.click_region(
                    self.WINDOW_TITLE, regions["upgrade_button"]
                )
                break

            elif final_stop_reason == StopReason.UPGRADED:
                # Track upgrades: SpendWorkflow-specific logic
                # Monitor doesn't track this - only fail transitions
                upgrade_count += 1
                remaining_attempts -= 1  # Successful upgrade uses an attempt
                logger.info(
                    f"Piece upgraded successfully! Total upgrades: {upgrade_count}"
                )

                if self._continue_upgrade and remaining_attempts > 0:
                    # We only continue once. lvl 10->11->12. Never below 10 and never above 12.
                    self._continue_upgrade = False
                    logger.info(
                        f"Continue upgrade enabled, waiting 1s for UI update "
                        f"(remaining: {remaining_attempts})"
                    )
                    time.sleep(1)
                    continue
                else:
                    logger.info("Stopping after successful upgrade")
                    break

            elif final_stop_reason == StopReason.CONNECTION_ERROR:
                logger.warning("Connection error detected, stopping workflow")
                break

        logger.info(
            f"Spend workflow completed: {upgrade_count} upgrades, "
            f"{attempt_count} attempts used, {remaining_attempts} remaining"
        )

        return SpendResult(
            upgrade_count=upgrade_count,
            attempt_count=attempt_count,
            remaining_attempts=remaining_attempts,
            stop_reason=final_stop_reason,
        )
