"""
Spend workflow implementation.

This module implements the SpendWorkflow class for spending upgrade attempts
with internet verification and optional continue upgrade logic.
"""

from __future__ import annotations
import time
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from autoraid.core.stop_conditions import (
    ConnectionErrorCondition,
    MaxAttemptsCondition,
    StopConditionChain,
    StopReason,
    UpgradedCondition,
)
from autoraid.exceptions import WorkflowValidationError
from autoraid.services.cache_service import CacheService
from autoraid.services.network import NetworkManager, NetworkState
from autoraid.services.upgrade_orchestrator import (
    UpgradeOrchestrator,
    UpgradeSession,
)
from autoraid.services.window_interaction_service import WindowInteractionService


@dataclass(frozen=True)
class SpendResult:
    """Result from spend workflow."""

    upgrade_count: int
    attempt_count: int
    remaining_attempts: int
    stop_reason: StopReason


class SpendWorkflow:
    """
    This workflow spends a specified number of upgrade attempts.
    """

    WINDOW_TITLE = "Raid: Shadow Legends"

    def __init__(
        self,
        orchestrator: UpgradeOrchestrator,
        cache_service: CacheService,
        window_interaction_service: WindowInteractionService,
        network_manager: NetworkManager,
        max_upgrade_attempts: int,
        continue_upgrade: bool = False,
        debug_dir: Path | None = None,
    ):
        """Initialize SpendWorkflow.

        Args:
            orchestrator: UpgradeOrchestrator for executing upgrade sessions
            cache_service: CacheService for retrieving cached regions
            window_interaction_service: WindowInteractionService for window operations
            network_manager: NetworkManager for network state validation
            max_upgrade_attempts: Maximum upgrade attempts to spend
            continue_upgrade: Whether to continue upgrading to next level after success
            debug_dir: Optional debug directory for logging
        """
        self._orchestrator = orchestrator
        self._cache_service = cache_service
        self._window_interaction_service = window_interaction_service
        self._network_manager = network_manager
        self._max_upgrade_attempts = max_upgrade_attempts
        self._continue_upgrade = continue_upgrade
        self._debug_dir = debug_dir

    def validate(self) -> None:
        logger.info("Starting spend workflow validation")

        if self._network_manager.check_network_access() != NetworkState.ONLINE:
            raise WorkflowValidationError(
                "No internet access detected. "
                "Spend workflow requires internet to save upgrades. "
                "Check your network connection."
            )

        logger.info("Spend workflow validation completed successfully")

    def run(self) -> SpendResult:
        logger.info("Starting spend workflow execution")

        # Get regions from cache
        current_size = self._window_interaction_service.get_window_size(
            self.WINDOW_TITLE
        )
        regions = self._cache_service.get_regions(current_size)

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

            # Create session configuration
            session = UpgradeSession(
                upgrade_bar_region=regions["upgrade_bar"],
                upgrade_button_region=regions["upgrade_button"],
                stop_conditions=stop_conditions,
                check_interval=0.25,
                network_adapter_ids=None,
                disable_network=False,
                debug_dir=(
                    self._debug_dir / "spend" / f"upgrade_{upgrade_count + 1}"
                    if self._debug_dir
                    else None
                ),
            )

            # Execute monitoring session
            result = self._orchestrator.run_upgrade_session(session)

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
