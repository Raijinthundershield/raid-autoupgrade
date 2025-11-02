"""
Count workflow implementation.

This module implements the CountWorkflow class for counting upgrade fails offline
with optional network adapter management.
"""

from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from autoraid.orchestration.stop_conditions import (
    StopReason,
    MaxAttemptsCondition,
    UpgradedCondition,
    StopConditionChain,
)
from autoraid.exceptions import WorkflowValidationError
from autoraid.services.cache_service import CacheService
from autoraid.services.network import NetworkManager, NetworkState
from autoraid.services.window_interaction_service import WindowInteractionService
from autoraid.services.screenshot_service import ScreenshotService
from autoraid.detection.progress_bar_detector import ProgressBarStateDetector
from autoraid.orchestration.upgrade_orchestrator import (
    UpgradeOrchestrator,
    UpgradeSession,
)


@dataclass(frozen=True)
class CountResult:
    """Result from count workflow."""

    fail_count: int
    stop_reason: StopReason


class CountWorkflow:
    """Workflow for counting upgrade fails offline with network adapter management.

    This workflow coordinates the upgrade counting process by:
    1. Validating prerequisites (window, regions, network state)
    2. Configuring stop conditions (max attempts, upgraded detection)
    3. Creating optional debug logger
    4. Running upgrade session via orchestrator
    5. Converting orchestrator result to CountResult
    """

    WINDOW_TITLE = "Raid: Shadow Legends"

    def __init__(
        self,
        cache_service: CacheService,
        window_interaction_service: WindowInteractionService,
        network_manager: NetworkManager,
        screenshot_service: ScreenshotService,
        detector: ProgressBarStateDetector,
        network_adapter_ids: list[int] | None = None,
        max_attempts: int = 99,
        debug_dir: Path | None = None,
    ):
        """Initialize count workflow.

        Args:
            cache_service: Service for region caching
            window_interaction_service: Service for window validation
            network_manager: Service for network state checks
            screenshot_service: Service for screenshot capture
            detector: Detector for progress bar state detection
            network_adapter_ids: List of adapter IDs to disable during counting
            max_attempts: Maximum number of fail attempts before stopping
            debug_dir: Optional directory for debug artifacts
        """
        self._cache_service = cache_service
        self._window_interaction_service = window_interaction_service
        self._network_manager = network_manager
        self._screenshot_service = screenshot_service
        self._detector = detector
        self._network_adapter_ids = network_adapter_ids
        self._max_attempts = max_attempts
        self._debug_dir = debug_dir

    def validate(self) -> None:
        """Validate count workflow prerequisites.

        Validates:
        - Network configuration (internet access requires adapter specification)

        Note: Window and region validation delegated to orchestrator.
        """
        logger.info("Starting count workflow validation")

        # Validate network configuration (workflow-specific validation)
        if (
            self._network_manager.check_network_access() == NetworkState.ONLINE
            and not self._network_adapter_ids
        ):
            logger.error(
                "Internet access detected but no network adapter specified - this will upgrade the piece"
            )
            raise WorkflowValidationError(
                "Internet access detected but no network adapter specified. "
                "This will upgrade the piece. "
                "Specify adapter IDs with --adapter-id."
            )
        logger.debug("Network configuration validation passed")

        if self._network_adapter_ids:
            logger.debug(
                f"Network adapters specified for disable: {self._network_adapter_ids}"
            )

        logger.info("Count workflow validation completed successfully")

    def run(self) -> CountResult:
        """Execute count workflow.

        Returns:
            CountResult with fail count and stop reason
        """
        logger.info("Starting count workflow execution")
        logger.debug(
            f"count_workflow(adapters={self._network_adapter_ids}, max_attempts={self._max_attempts})"
        )

        # Get regions from cache
        current_size = self._window_interaction_service.get_window_size(
            self.WINDOW_TITLE
        )
        regions = self._cache_service.get_regions(current_size)
        if regions is None:
            raise WorkflowValidationError(
                f"No regions cached for window size {current_size}. "
                "Please select regions using 'autoraid upgrade region select'."
            )

        # Configure stop conditions
        stop_conditions = StopConditionChain(
            [
                MaxAttemptsCondition(max_attempts=self._max_attempts),
                UpgradedCondition(
                    network_disabled=self._network_adapter_ids is not None
                ),
            ]
        )

        # Create upgrade session
        session = UpgradeSession(
            upgrade_bar_region=regions["upgrade_bar"],
            upgrade_button_region=regions["upgrade_button"],
            stop_conditions=stop_conditions,
            check_interval=0.25,
            network_adapter_ids=self._network_adapter_ids,
            disable_network=self._network_adapter_ids is not None,
            debug_dir=self._debug_dir / "count" if self._debug_dir else None,
        )

        # Create orchestrator and run session
        orchestrator = UpgradeOrchestrator(
            screenshot_service=self._screenshot_service,
            window_interaction_service=self._window_interaction_service,
            cache_service=self._cache_service,
            network_manager=self._network_manager,
            detector=self._detector,
        )
        result = orchestrator.run_upgrade_session(session)

        logger.info(
            f"Count workflow completed: {result.fail_count} fails, reason={result.stop_reason.value}"
        )

        # Convert orchestrator result to CountResult
        return CountResult(
            fail_count=result.fail_count,
            stop_reason=result.stop_reason,
        )
